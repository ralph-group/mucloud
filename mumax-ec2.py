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
            
search_condition = lambda i: (
    i.state == u'running' and 
    __TAG__ in i.tags and 
    __STATUS__ in i.tags and
    i.tags[__STATUS__] == __READY__
)

instances = conn.get_only_instances()
ready_instances = [i for i in instances if search_condition(i)]


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


def get_ready_instance():
    """ Returns an instance from the ready list or launches 
    a new instance upon prompt
    """
    if len(ready_instances) == 0:
        print "There are no instances waiting to be used."
        answer = raw_input("Create a new instance for this job? [Yn]: ")
        if len(answer) == 0 or answer.startswith(("Y", "y")):
            instance = launch_instance()
            print "Waiting for instance %s to boot up..." % instance.id
            while instance.state != u'running':
                sleep(10)
                instance.update()
            print "Instance %s is ready" % instance.id
            return instance
        else:
            print "No instance will be launched"
            return None
    else:
        instance = ready_instances[0] # Select the 1st ready instance
        print "Instance %s is ready" % instance.id
        return instance


def run(local_input_file):
    """Run the mumax input file on a ready instance
    """

    instance = get_ready_instance()
    if instance == None: return None

    instance.remove_tag(__STATUS__)
    try:
        # Establish connection
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



if __name__ == '__main__':
    if len(sys.argv) < 2:
        print  "Usage: mumax-ec2.py filename"
        sys.exit()
        
    filename = os.path.realpath(sys.argv[1])
    run(filename)
