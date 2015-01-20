#!/usr/bin/env python
"""
All settings should be stored in the config.ini file

"""

__version__ = 1.0

__TAG__ = u'mumax-ec2'
__STATUS__ = u'status'
__READY__ = u'1'
PORT = 35367


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
                sleep(0.5)
            print "Instance %s is ready" % instance.id
            return instance
        else:
            print "No instance will be launched"
            return None
    else:
        instance = ready_instances[0] # Select the 1st ready instance
        print "Instance %s is ready" % instance.id
        return instance


def stop_instance(instance):
    """ Stops an AWS instance """
    print "Stopping instance"
    conn.stop_instances(instance_ids=[instance.id])


def terminate_instance(instance):
    """ Stops an AWS instance """
    print "Terminating instance"
    conn.terminate_instances(instance_ids=[instance.id])



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
    input_file = "%s/input/%s" % (directory, basename)
    output_dir = "%s/output/%s" % (directory, basename)

    print "Transferring input file to instance: %s" % basename
    sftp.put(local_input_file, input_file)

    print "Starting port forwarding"
    server = SSHTunnelForwarder(
        ssh_address=(instance.public_dns_name, PORT),
        ssh_username=config.get('EC2', 'User'),
        ssh_private_key=config.get('EC2', 'PrivateKeyFile'),
        remote_bind_address=('127.0.0.1', PORT)
    )
    server.start()

    transport = ssh.get_transport()
    channel = transport.open_session()


    binary = "%s/mumax3/%s" % (directory, config.get('EC2', 'MuMaxBinary'))
    channel.exec_command("%s -http=:%i -o=%s %s" % (binary, PORT, output_dir, input_file))

    #TODO: Test blocking ability
    while True:
        try:
            rl, wl, xl = select.select([channel], [], [], 0.0)
            if len(rl) > 0:
                print channel.recv(1024)
        except KeyboardInterrupt:
            print "Caught Ctrl-C"
            channel.close()

            try:
                # Try to kill the process
                ssh.get_transport().open_session().exec_command(
                    "kill -9 `ps -fu | grep mumax3 | grep -v grep | awk '{print $2}'`"
                )
            except:
                pass

            ssh.close()

    print "Receiving output files from instance"
    sftp.chdir()
    files = sftp.listdir()
    for item in files:
        sftp.get(files, local_data) #TODO: Actually implement file transfer

    print "Stopping port forwarding"
    server.stop()

    answer = raw_input("Terminate the instance? [Yn]: ")
    if len(answer) == 0 or answer.startswith(("Y", "y")):
        terminate_instance(instance)
    else:
        instance.add_tag(__STATUS__, __READY__)
        answer = raw_input("Stop the instance? [Yn]: ")
        if len(answer) == 0 or answer.startswith(("Y", "y")):
            stop_instance(instance)
        else:
            print "The instance has been left running"



if __name__ == '__main__':
    if len(sys.argv) < 2:
        print  "Usage: mumax-ec2.py filename"
        sys.exit()
        
    filename = os.path.realpath(sys.argv[1])
    run(filename)
