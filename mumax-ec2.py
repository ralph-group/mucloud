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
        self._forward = None


    def start(self):
        aws.start_instances(instance_ids=self.id)
        self.add_ready_tags()


    def add_ready_tags(self):
        self._instance.add_tag('mumax-ec2', __version__)


    def stop(self):
        aws.stop_instances(instance_ids=[self.id])


    def terminate(self):
        # Toggle on delete on termination
        devices = ["%s=1" % dev for dev, bd in self._instance.block_device_mapping.items()]
        self._instance.modify_attribute('BlockDeviceMapping', devices)
        aws.terminate_instances(instance_ids=[self.id])


    def is_up(self):
        return self._instance.state == u'running'


    def is_ready(self):
        return self.state == u'ready'


    def is_simulating(self):
        return self.state == u'simulating'


    def wait_for_boot(self, delay=10):
        """ Waits for an instance to boot up """
        print "Waiting for instance to boot..."
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

            self._instance.add_tags({
                'local_input_file': local_input_file,
                'port': port,
            })

            print "Transferring input file to instance: %s" % paths['basename']
            sftp.put(local_input_file, paths['input_file'])

            print "Starting port forwarding: http://127.0.0.1:%d" % port
            self.port_forward(port)

            # Starting screen
            ssh.exec_command("screen -dmS %s" % SCREEN)
            sleep(0.5)

            cmd = "source ./run_mumax3 %s %s" % (port, paths['input_file'])
            print "Running %s on MuMax3" % paths['basename']
            ssh.exec_command("screen -S %s -X stuff $'%s'\r" % (SCREEN, cmd))

        except KeyboardInterrupt:
            print "\n\nCanceling simulation on keyboard interrupt"
            self.clean(ssh, sftp)
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

        self.stop_or_terminate()



    def wait_for_simulation(self, ssh, sftp):
        local_input_file = self.tags['local_input_file']
        paths = self.paths(local_input_file)

        try:
            print MUMAX_OUTPUT

            while not rexists(sftp, paths['log']):
                sleep(0.1) # Wait for log

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
        local_input_file = self.tags['local_input_file']
        paths = self.paths(local_input_file)

        if rexists(sftp, paths['local_output_dir']):
            print "Receiving output files from instance"
            if not os.path.isdir(paths['local_output_dir']):
                os.mkdir(paths['local_output_dir'])
            os.chdir(paths['local_output_dir'])
            sftp.chdir(paths['output_dir'])
            files = sftp.listdir()
            for f in files:
                sftp.get(f, f)

            print "Removing simulation output from instance"
            ssh.exec_command("rm -r %s" % paths['output_dir'])

        if rexists(sftp, paths['input_file']):
            print "Removing input file from instance"
            sftp.remove(paths['input_file'])

        if rexists(sftp, paths['log']):
            print "Removing logs from instance"
            sftp.remove(paths['log'])

        if rexists(sftp, paths['finished']):
            sftp.remove(paths['finished'])

        ssh.close()

        # Remove tags
        self._instance.remove_tags({
            'local_input_file': None,
            'port': None,
        })


    def stop_or_terminate(self):
        answer = raw_input("Terminate the instance? [Yn]: ")
        if len(answer) == 0 or answer.startswith(("Y", "y")):
            print "Terminating instance"
            self.terminate()
        else:
            answer = raw_input("Stop the instance? [Yn]: ")
            if len(answer) == 0 or answer.startswith(("Y", "y")):
                print "Stopping instance"
                self.stop()
            else:
                print "The instance has been left running"


    def reconnect(self):
        if 'local_input_file' in self.tags:
            local_input_file = self.tags['local_input_file']
            port = self.tags['port']
            paths = self.paths(local_input_file)

            print "Reconnecting to running instance"

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

            if not rexists(sftp, paths['input_file']):
                print "The input file has not been uploaded correctly"
                return

            print "Starting port forwarding: http://127.0.0.1:%d" % port
            self.port_forward(port)

            disconnect = self.wait_for_simulation(ssh, sftp)

            print MUMAX_OUTPUT
            print "Stopping port forwarding"
            self.stop_port_forward()

            if disconnect:
                return

            # Exit screen
            ssh.exec_command("screen -S %s -X stuff $'exit\r'" % SCREEN)

            self.clean(ssh, sftp)

            self.stop_or_terminate()
                
        else:
            print "Instance %s is not running a simulation" % self.id

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
        if self._forward is not None:
            self._forward.stop()
            self._forward = None


    @property
    def ip(self):
        return self._instance.ip_address


    @property
    def id(self):
        return self._instance.id


    @property
    def tags(self):
        return self._instance.tags


    @property
    def state(self):
        if self._instance.state == u'running':
            # Determine if its ready or simulating
            if 'local_input_file' in self.tags:
                return u'simulating'
            else:
                return u'ready'
        else:
            return self._instance.state
        

    @staticmethod
    def has_mumax(aws_instance):
        return ('mumax-ec2' in aws_instance.tags and
            aws_instance.tags['mumax-ec2'] == str(__version__) and
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
        sleep(1)
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
                instance = Instance.launch()
                instance.wait_for_boot()
                return instance
            else:
                print "No instance will be launched"
                return None
        else:
            instance = ready_instances[0] # Select the 1st ready instance
            print "Instance %s is ready" % instance.id
            return instance








def run_instance(args):
    group = InstanceGroup()
    instance = group.ready_instance()
    if instance is not None:
        instance.run(os.path.realpath(args.filename[0]), args.port[0])


def reconnect_instance(args):
    group = InstanceGroup()
    instance = group.by_id(args.id[0])
    if instance is not None:
        if instance.is_simulating():
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
        print "    ID\t\tIP\t\tState\t\tPort\t\tFile"
        for instance in instances:
            if instance.ip is None:
                ip = "None\t"
            else:
                ip = instance.ip
            if 'port' in instance.tags:
                port = instance.tags['port']
            else:
                port = ''
            if 'local_input_file' in instance.tags:
                mx3_file = os.path.basename(instance.tags['local_input_file'])
            else:
                mx3_file = ''
            print "    %s\t%s\t(%s)\t%s\t\t%s" % (instance.id, ip, instance.state, port, mx3_file)

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
        if instance.is_simulating():
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
        if instance.is_simulating():
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
        if instance.state == u'stopped':
            print "Starting instance %s" % instance.id
            instance.start()
            if args.wait:
                print "Waiting for instance to boot..."
                instance.wait_for_boot()
        else:
            print "Instance %s is not in a state that can be started from" % args.id[0]
    else:
        print "Instance %s is not a valid MuMax-EC2 instance" % args.id[0]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Runs MuMax3 .mx3 files on Amazon Web Services (AWS) instances')
    subparsers = parser.add_subparsers(help='sub-command help')

    parser_run = subparsers.add_parser('run', help='run help')
    parser_run.add_argument('filename', metavar='filename', type=str, nargs=1,
        help='A .mx3 input file for MuMax3')
    parser_run.add_argument('--port', type=int, default=[PORT], nargs=1,
        help="Desired local port number for the MuMax3 web interface (default: %d)" % PORT)
    parser_run.set_defaults(func=run_instance)

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

    parser_reconnect = subparsers.add_parser('reconnect', help='reconnect help')
    parser_reconnect.add_argument('id', metavar='aws_id', type=str, nargs=1,
        help='AWS ID of instance')
    parser_reconnect.set_defaults(func=reconnect_instance)

    args = parser.parse_args()
    args.func(args)
