#!/usr/bin/env python
"""

This file is part of the MuMax-EC2 package.

Copyright (c) 2014-2015 Colin Jermain, Graham Rowlands

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

"""

__version__ = 1.1

PORT = 35367
MUMAX_OUTPUT = "=" * 20 + " MuMax3 Output " + "=" * 20
SCREEN = "mumax-ec2"


import boto.ec2
import paramiko
import sys, os
from time import sleep
import select
from sshtunnel import SSHTunnelForwarder

import argparse
import ConfigParser
config = ConfigParser.ConfigParser()
config.read(os.path.dirname(os.path.realpath(__file__))+"/config.ini")

# Connect to Amazon Web Services (AWS)
aws = boto.ec2.connect_to_region(
    config.get('EC2', 'Region'),
    aws_access_key_id=config.get('EC2', 'AccessID'),
    aws_secret_access_key=config.get('EC2', 'SecretKey')
)

def rexists(sftp, path):
    try:
        sftp.stat(path)
    except IOError, e:
        if e[0] == 2:
            return False
        raise
    else:
        return True


class Instance(object):

    def __init__(self, aws_instance):
        self._instance = aws_instance


    def start(self):
        aws.start_instances(instance_ids=self.id)
        self.add_ready_tags()


    def add_ready_tags(self):
        self._instance.add_tag('mumax-ec2', __version__)
        self._instance.add_tag('status', 'ready')


    def stop(self):
        self._instance.add_tag('status', 'stopped')
        aws.stop_instances(instance_ids=[self.id])


    def terminate(self):
        self._instance.add_tag('status', 'terminated')
        # Toggle on delete on termination
        devices = ["%s=1" % dev for dev, bd in self._instance.block_device_mapping.items()]
        self._instance.modify_attribute('BlockDeviceMapping', devices)
        aws.terminate_instances(instance_ids=[self.id])


    def is_up(self):
        return self._instance.state == u'running'


    def is_ready(self):
        return ('status' in self._instance.tags and
            self._instance.tags['status'] == 'ready')


    def is_running(self):
        return ('status' in self._instance.tags and
            self._instance.tags['status'] == 'running')


    def wait_for_boot(self):
        """ Waits for an instance to boot up """
        while not self.is_up():
            sleep(delay)
            self._instance.update()
        sleep(delay)


    @property
    def directory(self):
        return "/home/%s" % config.get('EC2', 'User')


    def paths(self, local_input_file):
        basename = os.path.basename(local_input_file)
        directory = "/home/%s" % config.get('EC2', 'User')

        return {
            'local_input_file': local_input_file,
            'local_output_dir': local_input_file.replace(".mx3", ".out"),
            'input_file': "%s/simulations/%s" % (directory, basename),
            'output_dir': "%s/simulations/%s" % (directory, basename.replace(".mx3", ".out")),
            'basename': basename,
            'log': "%s/log.txt" % directory,
            'finished': "%s/finished" % directory,
        }


    def run(self, local_input_file, port=PORT):
        """ Run the mumax input file on a ready instance """

        if not self.is_ready():
            raise Exception("The instance %s is not ready to be run" % repr(self))

        try:
            print "Making secure connection to instance %s..." % self.id
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.ip, 
                username=config.get('EC2', 'User'),
                key_filename=config.get('EC2', 'PrivateKeyFile')
            )
            sftp = ssh.open_sftp()
        except:
            print "Could not connect to remote server"
            return

        try:

            # Determine file paths
            paths = self.paths(local_input_file)

            self._instance.remove_tag('status')
            self._instance.add_tags({
                'status': 'running',
                'local_input_file': local_input_file,
                'port': port,
            })

            print "Transferring input file to instance: %s" % paths['basename']
            sftp.put(local_input_file, paths['input_file'])

            print "Starting port forwarding"
            self.port_forward(port)

            # Starting screen
            ssh.exec_command("screen -dmS %s" % SCREEN)

            cmd = "source ./run_mumax3 %s %s" % (port, paths['input_file'])
            print "Running %s on MuMax3" % paths['basename']
            ssh.exec_command("screen -S %s -X stuff $'%s'\r" % (SCREEN, cmd))

        except KeyboardInterrupt:
            print "\n\nCanceling simulation on keyboard interrupt"
            self.partial_clean(ssh, sftp)
            return

        disconnect = self.wait_for_simulation(ssh, sftp)

        print MUMAX_OUTPUT
        print "Stopping port forwarding"
        self.stop_port_forward()
        
        if disconnect:
            return

        # Exit screen
        ssh.exec_command("screen -S %s -X stuff $'exit\r'" % SCREEN)

        self.clean(ssh, sftp)

        answer = raw_input("Terminate the instance? [Yn]: ")
        if len(answer) == 0 or answer.startswith(("Y", "y")):
            print "Terminating instance"
            self.terminate()
        else:
            self._instance.add_tag('status', 'ready')
            answer = raw_input("Stop the instance? [Yn]: ")
            if len(answer) == 0 or answer.startswith(("Y", "y")):
                print "Stopping instance"
                self.stop()
            else:
                print "The instance has been left running"


    def wait_for_simulation(self, ssh, sftp):
        local_input_file = self._instance.tags['local_input_file']
        paths = self.paths(local_input_file)

        try:
            print MUMAX_OUTPUT
            sleep(0.5)

            f = sftp.open(paths['log'], 'r')
            while not rexists(sftp, paths['finished']):
                data = f.read()
                if data != "":
                    print data, # ending comma to prevent newline
            print f.read(),

        except KeyboardInterrupt:
            print "\n\nCaught keyboard interrupt during simulation"
            answer = raw_input("Disconnect, abort, or continue the simulation? [Dac]: ")
            if len(answer) == 0 or answer.startswith(("D", "d")):
                print "Disconnecting from instance"
                print "Reconnect with: python mumax-ec2.py reconnect %s" % self.id
                return True
            elif answer.startswith(("A", "a")):
                print "Aborting the simulation"
                # Keyboard interrupt
                ssh.exec_command("screen -S %s -X stuff $'\\003\r'" % SCREEN)
                return False
            else:
                print "Continuing the simulation"
                return self.wait_for_simulation(ssh, sftp)


    def clean(self, ssh, sftp):
        """ Clean the instance when the simulation has been stopped
        """
        local_input_file = self._instance.tags['local_input_file']
        paths = self.paths(local_input_file)

        print "Receiving output files from instance"
        if not os.path.isdir(paths['local_output_dir']):
            os.mkdir(paths['local_output_dir'])
        os.chdir(paths['local_output_dir'])
        sftp.chdir(paths['output_dir'])
        files = sftp.listdir()
        for f in files:
            sftp.get(f, f)

        print "Removing logs from instance"
        sftp.remove(paths['log'])
        if rexists(sftp, paths['finished']):
            sftp.remove(paths['finished'])

        print "Removing simulation files from instance"
        sftp.remove(paths['input_file'])
        ssh.exec_command("rm -r %s" % paths['output_dir'])

        ssh.close()

        # Remove tags
        self._instance.remove_tags({
            'local_input_file': None,
            'port': None,
        })

        self._instance.add_tag('status', 'ready')


    def partial_clean(self, ssh, sftp):
        """ Clean the instance when the simulation has not been started
        """
        if 'local_input_file' in self._instance.tags:
            local_input_file = self._instance.tags['local_input_file']
            paths = self.paths(local_input_file)

            if rexists(sftp, paths['input_file']):
                print "Removing input file from instance"
                sftp.remove(paths['input_file'])


    def reconnect(self):
        # Get the file paths from the tags
        local_input_file = self._instance.tags['local_input_file']
        local_output_dir = self._instance.tags['local_output_dir']
        input_file = self._instance.tags['input_file']
        output_dir = self._instance.tags['output_dir']


    def port_forward(self, port=PORT):
        key = paramiko.RSAKey.from_private_key_file(
            config.get('EC2', 'PrivateKeyFile')
        )
        self._forward = SSHTunnelForwarder(
            ssh_address=(self.ip, 22),
            ssh_username=config.get('EC2', 'User'),
            ssh_private_key=key,
            remote_bind_address=('127.0.0.1', PORT),
            local_bind_address=('127.0.0.1', PORT)
        )
        self._forward.start()


    def stop_port_forward(self):
        self._forward.stop()


    def halt(self, ssh):
        try:
            # Try to kill the process
            ssh.get_transport().open_session().exec_command(
                "kill -9 `ps -fu | grep mumax3 | grep -v grep | awk '{print $2}'`"
            )
        except:
            pass


    def disconnect(self):
        pass


    @property
    def ip(self):
        return self._instance.ip_address


    @property
    def id(self):
        return self._instance.id


    @property
    def tags(self):
        return self._instance.tags
        

    @staticmethod
    def has_mumax(aws_instance):
        return ('status' in aws_instance.tags and
            aws_instance.state != u'terminated')

    @staticmethod
    def launch():
        """ Launch a new AWS instance """
        reservation = aws.run_instances(
            config.get('EC2', 'Image'),
            key_name=config.get('EC2', 'PrivateKeyName'),
            instance_type=config.get('EC2', 'InstanceType'),
            security_groups=config.get('EC2', 'SecurityGroups').split(',')
        )
        instance = Instance(reservation.instances[0])
        instance.add_ready_tags()
        return instance


    def __repr__(self):
        return "<MuMax-EC2 Instance(id='%s')>" % self.id



class InstanceGroup(object):

    def __init__(self):
        all_instances = aws.get_only_instances()
        self.instances = [Instance(i) for i in all_instances if Instance.has_mumax(i)]


    def has_id(id, running=True):
        """ Returns True if the ID is a valid MuMax-EC2 instance
        and if it is running or not
        """
        for instance in self.instances:
            if instance.id == id:
                if running == None:
                    return True
                elif up_condition(instance) == running:
                    return True
                else:
                    return False
        return False


    def by_id(self, id):
        """ Returns an instance object based on an id
        """
        for instance in self.instances:
            if instance.id == id:
                return instance
        return None


    def ready_instance(self):
        """ Returns an instance from the ready list or launches 
        a new instance upon prompt
        """
        ready_instances = [i for i in self.instances if i.is_ready()]
        if len(ready_instances) == 0:
            print "There are no instances waiting to be used."
            answer = raw_input("Create a new instance for this simulation? [Yn]: ")
            if len(answer) == 0 or answer.startswith(("Y", "y")):
                instance = launch_instance()
                wait_for_instance(instance)
                return instance
            else:
                print "No instance will be launched"
                return None
        else:
            instance = ready_instances[0] # Select the 1st ready instance
            print "Instance %s is ready" % instance.id
            return instance








def run(args):
    group = InstanceGroup()
    instance = group.ready_instance()
    if instance is not None:
        # TODO: Add port options
        instance.run(os.path.realpath(args.filename[0]))


def reconnect(args):
    group = InstanceGroup()
    instance = group.by_id(args.id[0])
    if instance is not None:
        if instance.is_running():
            instance.reconnect()
        else:
            print "Instance %s is not running" % args.id[0]
    else:
        print "Instance %s is not a valid MuMax-EC2 instance" % args.id[0]


def list_instances(args):
    group = InstanceGroup()
    instances = group.instances
    if len(instances) > 0:
        print "MuMax-EC2 Instances:"
        print "    ID\t\tIP\t\tStatus\t\tPort\t\tUp time (sec)"
        for instance in instances:
            if instance.is_running():
                status = 'running'
            elif instance.is_ready():
                status = 'ready'
            elif instance.is_up():
                status = 'starting'
            else:
                status = 'stopped'
            if 'port' in instance.tags:
                port = instance.tags['port']
            else:
                port = ''
            print "    %s\t%s\t(%s)\t%s" % (instance.id, instance.ip, status, port)

    else:
        print "No MuMax-EC2 instances currently running"


def launch_instance(args):
    print "Creating a new instance of %s" % config.get('EC2', 'Image')
    instance = Instance.launch()
    if args.wait:
        instance.wait_for_boot()


def terminate_instance(args):
    group = InstanceGroup()
    instance = group.by_id(args.id[0])
    if instance is not None:
        if instance.is_running():
            print "This instance is currently running."
            answer = raw_input("Proceed to terminate the instance? [Yn]: ")
            if len(answer) == 0 or answer.startswith(("Y", "y")):
                instance.halt()
                instance.clean()
            else:
                return
        print "Terminating instance %s" % instance.id
        instance.terminate()
    else:
        print "Instance %s is not a valid MuMax-EC2 instance" % args.id[0]


def stop_instance(args):
    group = InstanceGroup()
    instance = group.by_id(args.id[0])
    if instance is not None:
        if instance.is_running():
            print "This instance is currently running."
            answer = raw_input("Proceed to stop the instance? [Yn]: ")
            if len(answer) == 0 or answer.startswith(("Y", "y")):
                instance.halt()
                instance.clean()
            else:
                return
        print "Stopping instance %s" % instance.id
        instance.stop()
    else:
        print "Instance %s is not a valid MuMax-EC2 instance" % args.id[0]


def start_instance(args):
    group = InstanceGroup()
    instance = group.by_id(args.id[0])
    if instance is not None:
        if not instance.is_up():
            print "Starting instance %s" % instance.id
            instance.start()
            if args.wait:
                print "Waiting for instance to boot..."
                instance.wait_for_boot()
        else:
            print "Instance %s is already up" % args.id[0]
    else:
        print "Instance %s is not a valid MuMax-EC2 instance" % args.id[0]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Runs MuMax3 .mx3 files on Amazon Web Services (AWS) instances')
    subparsers = parser.add_subparsers(help='sub-command help')

    parser_run = subparsers.add_parser('run', help='run help')
    parser_run.add_argument('filename', metavar='filename', type=str, nargs=1,
        help='A .mx3 input file for MuMax3')
    parser_run.set_defaults(func=run)

    parser_list = subparsers.add_parser('list', help='list help')
    parser_list.set_defaults(func=list_instances)

    parser_launch = subparsers.add_parser('launch', help='launch help')
    parser_launch.add_argument('--wait', action='store_true')
    parser_launch.set_defaults(func=launch_instance, wait=False)

    parser_terminate = subparsers.add_parser('terminate', help='terminate help')
    parser_terminate.add_argument('id', metavar='aws_id', type=str, nargs=1,
        help='AWS ID of instance')
    parser_terminate.set_defaults(func=terminate_instance)

    parser_stop = subparsers.add_parser('stop', help='stop help')
    parser_stop.add_argument('id', metavar='aws_id', type=str, nargs=1,
        help='AWS ID of instance')
    parser_stop.set_defaults(func=stop_instance)

    parser_start = subparsers.add_parser('start', help='start help')
    parser_start.add_argument('id', metavar='aws_id', type=str, nargs=1,
        help='AWS ID of instance')
    parser_start.add_argument('--wait', action='store_true')
    parser_start.set_defaults(func=start_instance)

    args = parser.parse_args()
    args.func(args)
