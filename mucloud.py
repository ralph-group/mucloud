#!/usr/bin/env python
"""

This file is part of the MuCloud package.

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

from __future__ import print_function
try:
    input = raw_input # Python 2.7
except:
    from builtins import input # Python 3.x

import boto.ec2
import paramiko
import os
import sys
from tqdm import tqdm
from time import sleep
from sshtunnel import SSHTunnelForwarder

import argparse
try:
    import ConfigParser as configparser # Python 2.7
except ImportError:
    import configparser # Python 3.x

import logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.StreamHandler(sys.stdout))

# Suppress other logs from printing to stdout
for log_name in ["paramiko.transport", "sshtunnel"]:
    logging.getLogger(log_name).addHandler(
        logging.NullHandler()
    )

__version__ = 1.2

PORT = 35367
MUMAX_OUTPUT = "=" * 20 + " MuMax3 output " + "=" * 20
SCREEN = "mucloud"

CONFIG_FILE = os.path.join(os.path.dirname(
        os.path.realpath(__file__)), "config.ini")

if not os.path.exists(CONFIG_FILE):
    raise IOError("Configuration file (config.ini) not found"
                  " in the mucloud path")

config = configparser.ConfigParser()
config.read(CONFIG_FILE)

# Check the configuration settings are not empty
config_settings = [
    'User', 'Image', 'InstanceType', 'Region',
    'AccessID', 'SecretKey', 'PrivateKeyFile', 
    'PrivateKeyName', 'SecurityGroups'
]
for setting in config_settings:
    if config.get('EC2', setting) == '':
        raise ValueError("The config.ini setting '%s' is empty" % setting)

# Connect to Amazon Web Services (AWS)
aws = boto.ec2.connect_to_region(
    config.get('EC2', 'Region'),
    aws_access_key_id=config.get('EC2', 'AccessID'),
    aws_secret_access_key=config.get('EC2', 'SecretKey')
)


def rexists(sftp, path):
    try:
        sftp.stat(path)
    except IOError as e:
        if 'No such file' in str(e):
            return False
        raise
    else:
        return True


class Instance(object):
    """ Encapsulates the AWS EC2 instance to add additional functionality
    for running the MuMax3 simulations.
    """

    def __init__(self, aws_instance):
        self._instance = aws_instance
        self._forward = None

    def start(self):
        aws.start_instances(instance_ids=self.id)
        self.add_ready_tags()

    def add_ready_tags(self):
        self._instance.add_tag('mucloud', __version__)

    def stop(self):
        aws.stop_instances(instance_ids=[self.id])

    def terminate(self):
        # Toggle on delete on termination
        devices = ["%s=1" % dev for dev, bd in
                   self._instance.block_device_mapping.items()]
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
        log.info("Waiting for instance to boot...")
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
            'output_dir': "%s/simulations/%s" % (
                directory,
                basename.replace(".mx3", ".out")
            ),
            'basename': basename,
            'log': "%s/log.txt" % directory,
            'finished': "%s/finished" % directory,
        }

    def connect(self):
        """ Connects to the instance through SSH and SFTP
        """
        log.info("Making secure connection to instance %s..." % self.id)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            self.ip,
            username=config.get('EC2', 'User'),
            key_filename=config.get('EC2', 'PrivateKeyFile')
        )
        sftp = ssh.open_sftp()
        return ssh, sftp

    def run(self, local_input_file, port=PORT, detach=False):
        """ Run the mumax input file on a ready instance """

        if not self.is_ready():
            raise Exception("The instance %s is not ready to be run" % repr(
                            self))

        try:
            ssh, sftp = self.connect()
        except:
            log.error("Could not connect to remote server")
            return

        try:

            # Determine file paths
            paths = self.paths(local_input_file)

            self._instance.add_tags({
                'local_input_file': local_input_file,
                'port': port,
            })

            log.info("Transferring input file to instance:"
                     " %s" % paths['basename'])
            sftp.put(local_input_file, paths['input_file'])

            log.info("Starting port forwarding: http://127.0.0.1:%d" % port)
            self.port_forward(port)

            # Starting screen
            ssh.exec_command("screen -dmS %s" % SCREEN)
            sleep(0.5)

            cmd = "source ./run_mumax3 %s %s" % (port, paths['input_file'])
            log.info("Running %s on MuMax3" % paths['basename'])
            ssh.exec_command("screen -S %s -X stuff $'%s'\r" % (SCREEN, cmd))

        except KeyboardInterrupt:
            log.info("\n\nCanceling simulation on keyboard interrupt")
            self.clean(ssh, sftp)
            return

        if detach:
            log.info("Stopping port forwarding")
            self.stop_port_forward()
            log.info("Detaching from instance with simulation running")
            log.info("Reattach with: python mucloud.py "
                     "reattach %s" % self.id)
            return

        detach = self.wait_for_simulation(ssh, sftp)

        log.info(MUMAX_OUTPUT)
        log.info("Stopping port forwarding")
        self.stop_port_forward()

        if detach:
            return

        # Exit screen
        ssh.exec_command("screen -S %s -X stuff $'exit\r'" % SCREEN)

        self.clean(ssh, sftp)

        self.stop_or_terminate()

    def wait_for_simulation(self, ssh, sftp):
        local_input_file = self.tags['local_input_file']
        paths = self.paths(local_input_file)

        try:
            log.info(MUMAX_OUTPUT)

            while not rexists(sftp, paths['log']):
                sleep(0.1)  # Wait for log

            f = sftp.open(paths['log'], 'r')
            while not rexists(sftp, paths['finished']):
                data = f.read()
                if data != "":
                    # TODO: Incorporate with logging module
                    print(data.decode('utf8'), end='')  # end argument to prevent newline
            print(f.read().decode('utf8'), end='')

        except KeyboardInterrupt:
            log.info("\n\nCaught keyboard interrupt during simulation")
            answer = input("Detach, abort, or continue the "
                               "simulation? [Dac]: ")
            if len(answer) == 0 or answer.startswith(("D", "d")):
                log.info("Detaching from instance with simulation running")
                log.info("Reattach with: python mucloud.py"
                         " reattach %s" % self.id)
                return True
            elif answer.startswith(("A", "a")):
                self.halt(ssh, sftp)
                return False
            else:
                log.info("Continuing the simulation")
                return self.wait_for_simulation(ssh, sftp)

    def halt(self, ssh, sftp):
        log.info("Aborting the simulation")
        # Keyboard interrupt the screen
        ssh.exec_command("screen -S %s -X stuff $'\\003\r'" % SCREEN)

    def clean(self, ssh, sftp):
        """ Clean the instance when the simulation has been stopped
        """
        local_input_file = self.tags['local_input_file']
        paths = self.paths(local_input_file)

        if rexists(sftp, paths['output_dir']):
            log.info("Receiving output files from instance")
            if not os.path.isdir(paths['local_output_dir']):
                os.mkdir(paths['local_output_dir'])
            os.chdir(paths['local_output_dir'])
            sftp.chdir(paths['output_dir'])
            files = sftp.listdir()
            for f in tqdm(files):
                sftp.get(f, f)

            log.info("Removing simulation output from instance")
            ssh.exec_command("rm -r %s" % paths['output_dir'])

        if rexists(sftp, paths['input_file']):
            log.info("Removing input file from instance")
            sftp.remove(paths['input_file'])

        if rexists(sftp, paths['log']):
            log.info("Removing logs from instance")
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
        answer = input("Terminate the instance? [Yn]: ")
        if len(answer) == 0 or answer.startswith(("Y", "y")):
            log.info("Terminating instance")
            self.terminate()
        else:
            answer = input("Stop the instance? [Yn]: ")
            if len(answer) == 0 or answer.startswith(("Y", "y")):
                log.info("Stopping instance")
                self.stop()
            else:
                log.info("The instance has been left running")

    def reattach(self):
        if 'local_input_file' in self.tags:
            local_input_file = self.tags['local_input_file']
            port = int(self.tags['port'])
            paths = self.paths(local_input_file)

            log.info("Reconnecting to running instance")

            try:
                ssh, sftp = self.connect()
            except:
                log.error("Could not connect to remote server")
                return

            if not rexists(sftp, paths['input_file']):
                log.info("The input file has not been uploaded correctly")
                return

            log.info("Starting port forwarding: http://127.0.0.1:%d" % port)
            self.port_forward(port)

            disconnect = self.wait_for_simulation(ssh, sftp)

            log.info(MUMAX_OUTPUT)
            log.info("Stopping port forwarding")
            self.stop_port_forward()

            if disconnect:
                return

            # Exit screen
            ssh.exec_command("screen -S %s -X stuff $'exit\r'" % SCREEN)

            self.clean(ssh, sftp)

            self.stop_or_terminate()
        else:
            log.info("Instance %s is not running a simulation" % self.id)

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
        return (
            'mucloud' in aws_instance.tags and
            aws_instance.tags['mucloud'] == str(__version__) and
            aws_instance.state != u'terminated'
        )

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
        log.info("Creating a new instance %s from image %s" % (
            instance.id, config.get('EC2', 'Image')))
        sleep(1)
        instance.add_ready_tags()
        return instance

    def __repr__(self):
        return "<MuCloud Instance(id='%s')>" % self.id


class InstanceGroup(object):

    def __init__(self):
        all_instances = aws.get_only_instances()
        self.instances = [Instance(i) for i in
                          all_instances if Instance.has_mumax(i)]

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
            log.info("There are no instances waiting to be used.")
            answer = input("Create a new instance for this "
                               "simulation? [Yn]: ")
            if len(answer) == 0 or answer.startswith(("Y", "y")):
                instance = Instance.launch()
                instance.wait_for_boot()
                log.info("Instance %s is ready" % instance.id)
                return instance
            else:
                log.info("No instance will be launched")
                return None
        else:
            instance = ready_instances[0]  # Select the 1st ready instance
            log.info("Instance %s is ready" % instance.id)
            return instance

########################################
# Functions for main method sub-commands
########################################


def run_instance(args):
    if not os.path.isfile(args.filename[0]):
        log.info("The specified .mx3 file does not exist")
        return
    group = InstanceGroup()
    instance = group.ready_instance()
    if instance is not None:
        instance.run(
            os.path.realpath(args.filename[0]),
            args.port[0],
            args.detach
        )


def reattach_instance(args):
    group = InstanceGroup()
    instance = group.by_id(args.id[0])
    if instance is not None:
        if instance.is_simulating():
            instance.reattach()
        else:
            log.info("Instance %s is not running" % args.id[0])
    else:
        log.info("Instance %s is not a valid MuCloud instance" % args.id[0])


def list_instances(args):
    group = InstanceGroup()
    instances = group.instances
    if len(instances) > 0:
        log.info("MuCloud Instances:")
        log.info("    ID\t\tIP\t\tState\t\tPort\t\tFile")
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
            log.info("    %s\t%s\t%s\t%s\t\t%s" % (
                instance.id,
                ip,
                instance.state,
                port,
                mx3_file
            ))

    else:
        log.info("No MuCloud instances currently running")


def launch_instance(args):
    instance = Instance.launch()
    if args.wait:
        instance.wait_for_boot()


def terminate_instance(args):
    group = InstanceGroup()
    instance = group.by_id(args.id[0])
    if instance is not None:
        if instance.is_simulating():
            log.info("This instance is currently running.")
            answer = input("Proceed to terminate the instance? [Yn]: ")
            if len(answer) == 0 or answer.startswith(("Y", "y")):
                try:
                    ssh, sftp = instance.connect()
                except:
                    log.error("Could not connect to remote server")
                    return
                instance.halt(ssh, sftp)
                instance.clean(ssh, sftp)
            else:
                return
        log.info("Terminating instance %s" % instance.id)
        instance.terminate()
    else:
        log.info("Instance %s is not a valid MuCloud instance" % args.id[0])


def stop_instance(args):
    group = InstanceGroup()
    instance = group.by_id(args.id[0])
    if instance is not None:
        if instance.is_simulating():
            log.info("This instance is currently running.")
            answer = input("Proceed to stop the instance? [Yn]: ")
            if len(answer) == 0 or answer.startswith(("Y", "y")):
                try:
                    ssh, sftp = instance.connect()
                except:
                    log.error("Could not connect to remote server")
                    return
                instance.halt(ssh, sftp)
                instance.clean(ssh, sftp)
            else:
                return
        log.info("Stopping instance %s" % instance.id)
        instance.stop()
    else:
        log.info("Instance %s is not a valid MuCloud instance" % args.id[0])


def start_instance(args):
    group = InstanceGroup()
    instance = group.by_id(args.id[0])
    if instance is not None:
        if instance.state == u'stopped':
            log.info("Starting instance %s" % instance.id)
            instance.start()
            if args.wait:
                log.info("Waiting for instance to boot...")
                instance.wait_for_boot()
        else:
            log.info("Instance %s is not in a state that can be "
                     "started from" % args.id[0])
    else:
        log.info("Instance %s is not a valid MuCloud instance" % args.id[0])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Runs MuMax3 .mx3 files on Amazon Web Services"
                    " (AWS) instances")
    subparsers = parser.add_subparsers(help='sub-command help')

    parser_run = subparsers.add_parser('run', help='run help')
    parser_run.add_argument(
        'filename', metavar='filename', type=str, nargs=1,
        help='A .mx3 input file for MuMax3'
    )
    parser_run.add_argument(
        '--port', type=int, default=[PORT], nargs=1,
        help="Desired local port number for the MuMax3 web "
             "interface (default: %d)" % PORT)
    parser_run.add_argument(
        '--detach', action='store_true',
        help="Starts the simulation and immediately detaches if set")
    parser_run.set_defaults(func=run_instance)

    parser_list = subparsers.add_parser('list', help='list help')
    parser_list.set_defaults(func=list_instances)

    parser_launch = subparsers.add_parser('launch', help='launch help')
    parser_launch.add_argument('--wait', action='store_true')
    parser_launch.set_defaults(func=launch_instance, wait=False)

    parser_terminate = subparsers.add_parser(
        'terminate', help='terminate help')
    parser_terminate.add_argument(
        'id', metavar='aws_id', type=str, nargs=1,
        help='AWS ID of instance')
    parser_terminate.set_defaults(func=terminate_instance)

    parser_stop = subparsers.add_parser('stop', help='stop help')
    parser_stop.add_argument(
        'id', metavar='aws_id', type=str, nargs=1,
        help='AWS ID of instance')
    parser_stop.set_defaults(func=stop_instance)

    parser_start = subparsers.add_parser('start', help='start help')
    parser_start.add_argument(
        'id', metavar='aws_id', type=str, nargs=1,
        help='AWS ID of instance')
    parser_start.add_argument(
        '--wait', action='store_true',
        help="Waits for the instance to boot up if set")
    parser_start.set_defaults(func=start_instance)

    parser_reattach = subparsers.add_parser('reattach', help='reattach help')
    parser_reattach.add_argument(
        'id', metavar='aws_id', type=str, nargs=1,
        help='AWS ID of instance')
    parser_reattach.set_defaults(func=reattach_instance)

    args = parser.parse_args()
    args.func(args)
