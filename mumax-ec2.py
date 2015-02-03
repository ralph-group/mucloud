#!/usr/bin/env python
"""

This file is part of the mumax-ec2 package.

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

__version__ = 1.0

__TAG__ = u'mumax-ec2'
__STATUS__ = u'status'
__READY__ = u'1'
PORT = 35367
__ON_AWS__ = "==================== AWS INSTANCE ===================="


import argparse
import boto.ec2
import paramiko
import sys, os
from time import sleep
import select
from sshtunnel import SSHTunnelForwarder


# Start the config parser
import ConfigParser
config = ConfigParser.ConfigParser()
config.read(os.path.dirname(os.path.realpath(__file__))+"/config.ini")

# Connect to Amazon Web Services (AWS)
conn = boto.ec2.connect_to_region(config.get('EC2', 'Region'),
            aws_access_key_id=config.get('EC2', 'AccessID'),
            aws_secret_access_key=config.get('EC2', 'SecretKey'))
            
up_condition = lambda i: (
    i.state == u'running'
)

mumax_ec2_condition = lambda i: (
    __TAG__ in i.tags
)

ready_condition = lambda i: (
    __STATUS__ in i.tags and
    i.tags[__STATUS__] == __READY__
)

instances = conn.get_only_instances()
mumax_ec2_instances = [i for i in instances if mumax_ec2_condition(i)]
ready_instances = [i for i in instances if (
    mumax_ec2_condition(i) and ready_condition(i)
)]


def has_id(id, running=True):
    """ Returns True if the ID is a valid mumax-ec2 instance
    and if it is running or not
    """
    for instance in mumax_ec2_instances:
        if instance.id == id:
            if up_condition(instance) == running:
                return True
            else:
                return False
    return False


def launch_instance():
    """ Launch a new AWS instance """
    print "Creating a new instance of %s" % config.get('EC2', 'Image')
    reservation = conn.run_instances(
        config.get('EC2', 'Image'),
        key_name=config.get('EC2', 'PrivateKeyName'),
        instance_type=config.get('EC2', 'InstanceType'),
        security_groups=config.get('EC2', 'SecurityGroups').split(',')
    )
    instance = reservation.instances[0]
    instance.add_tag(__TAG__, __version__)
    instance.add_tag(__STATUS__, __READY__)
    return instance


def wait_for_instance(instance, delay=10):
    """ Waits for an instance to boot up
    """
    print "Waiting for instance %s to boot up..." % instance.id
    while instance.state != u'running':
        sleep(delay)
        instance.update()
    sleep(delay)
    print "Instance %s is ready" % instance.id


def get_ready_instance():
    """ Returns an instance from the ready list or launches 
    a new instance upon prompt
    """
    if len(ready_instances) == 0:
        print "There are no instances waiting to be used."
        answer = raw_input("Create a new instance for this job? [Yn]: ")
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
    """Run the mumax input file on a ready instance
    """
    local_input_file = os.path.realpath(args.filename[0])

    instance = get_ready_instance()
    if instance == None: return None

    try:
        print "Making secure connection to instance %s..." % instance.id
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(instance.public_dns_name, 
            username=config.get('EC2', 'User'), 
            key_filename=config.get('EC2', 'PrivateKeyFile')
        )
        sftp = ssh.open_sftp()
    except:
        print "Could not connect to remote server"
        return

    instance.remove_tag(__STATUS__)
    basename = os.path.basename(local_input_file)
    directory = "/home/%s" % config.get('EC2', 'User')
    input_file = "%s/simulations/%s" % (directory, basename)
    output_dir = "%s/simulations/%s" % (directory, basename.replace(".mx3", ".out"))

    print "Transferring input file to instance: %s" % basename
    sftp.put(local_input_file, input_file)

    print "Starting port forwarding"
    mykey = paramiko.RSAKey.from_private_key_file(config.get('EC2', 'PrivateKeyFile'))
    server = SSHTunnelForwarder(
        ssh_address=(instance.public_dns_name, 22),
        ssh_username=config.get('EC2', 'User'),
        ssh_private_key=mykey,
        remote_bind_address=('127.0.0.1', PORT),
        local_bind_address=('127.0.0.1', PORT)
    )
    server.start()

    transport = ssh.get_transport()
    channel = transport.open_session()


    binary = "%s/mumax3/%s" % (directory, config.get('EC2', 'MuMaxBinary'))
    cmd = "source ./include_cuda && %s -f -http=:%i %s" % (binary, PORT, input_file)
    print cmd
    print __ON_AWS__
    channel.exec_command(cmd)

    #TODO: Test blocking ability
    try:
        while not channel.exit_status_ready():
            if channel.recv_ready():
                print channel.recv(1024), # ending comma to prevent newline
        # Finish reading everything
        while channel.recv_ready():
            print channel.recv(1024), # ending comma to prevent newline

    except KeyboardInterrupt:
        print "\nCaught Ctrl-C"
        channel.close()

        try:
            # Try to kill the process
            ssh.get_transport().open_session().exec_command(
                "kill -9 `ps -fu | grep mumax3 | grep -v grep | awk '{print $2}'`"
            )
        except:
            pass

    print __ON_AWS__
    print "Receiving output files from instance"
    local_output_dir = local_input_file.replace(".mx3", ".out")
    if not os.path.isdir(local_output_dir):
        os.mkdir(local_output_dir)
    os.chdir(local_output_dir)
    sftp.chdir(output_dir)
    files = sftp.listdir()
    for f in files:
        sftp.get(f, f)

    print "Removing simulation files from instance"
    sftp.remove(input_file)
    ssh.exec_command("rm -r %s" % output_dir)

    print "Stopping port forwarding"
    server.stop()

    ssh.close()

    answer = raw_input("Terminate the instance? [Yn]: ")
    if len(answer) == 0 or answer.startswith(("Y", "y")):
        print "Terminating instance"
        conn.terminate_instances(instance_ids=[instance.id])
    else:
        instance.add_tag(__STATUS__, __READY__)
        answer = raw_input("Stop the instance? [Yn]: ")
        if len(answer) == 0 or answer.startswith(("Y", "y")):
            print "Stopping instance"
            conn.stop_instances(instance_ids=[instance.id])
        else:
            print "The instance has been left running"


def list_instances(args):
    if len(mumax_ec2_instances) > 0:
        print "Mumax-ec2 Instances:"
        print "    ID\t\tIP\t\tStatus"
        for instance in mumax_ec2_instances:
            if mumax_ec2_condition(instance):
                if up_condition(instance):
                    if ready_condition(instance):
                        status = "ready"
                    else:
                        status = "running"
                else:
                    status = "stopped"
                print "    %s\t%s\t(%s)" % (instance.id, instance.ip_address, status)
    else:
        print "No mumax-ec2 instances currently running"


def _launch_instance(args):
    instance = launch_instance()
    if args.wait: 
        wait_for_instance(instance)


def terminate_instance(args):
    if has_id(args.id[0], running=True):
        print "Terminating instance %s" % args.id[0]
        conn.terminate_instances(instance_ids=args.id)
    else:
        print "AWS ID %s is not a valid mumax-ec2 instance" % args.id[0]


def stop_instance(args):
    if has_id(args.id[0], running=True):
        print "Stopping instance %s" % args.id[0]
        conn.stop_instances(instance_ids=args.id)
    else:
        print "AWS ID %s is not a valid mumax-ec2 instance" % args.id[0]


def start_instance(args):
    if has_id(args.id[0], running=False):
        print "Starting instance %s" % args.id[0]
        conn.start_instances(instance_ids=args.id)
        if args.wait:
            for instance in mumax_ec2_instances:
                if instance.id == args.id[0]:
                    break
            wait_for_instance(instance) 
    else:
        print "AWS ID %s is not a valid mumax-ec2 instance" % args.id[0]


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
    parser_launch.set_defaults(func=_launch_instance, wait=False)

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
