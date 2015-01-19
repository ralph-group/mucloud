#!/usr/bin/env python
"""
All settings should be stored in the config.ini file

"""

__version__ = 1.0

__TAG__ = u'mumax-ec2'
__STATUS__ = u'status'
__READY__ = 1

# TODO: Compare mumax-ec2 tag with version

import boto.ec2
import paramiko
import sys, os
from time import sleep
import select

# Start the config parser
import ConfigParser
config = ConfigParser.ConfigParser()
config.read("./config.ini")

# Connect to Amazon Web Services (AWS)
conn = boto.ec2.connect_to_region(config.get('EC2', 'Region'),
            aws_access_key_id=config.get('EC2', 'AccessID'),
            aws_secret_access_key=config.get('EC2', 'SecretKey'))
            
search_condition = lambda i: (i.state == u'running' and 
    __TAG__ in i.tags and 
    __STATUS__ in i.tags and
    i.tags[__STATUS__] == __READY__
)

instances          = conn.get_only_instances()
ready_instances     = [i for i in instances if search_condition(i)]


def launch_instance(conn):
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


def stop_instance(conn, instance):
    """ Stops an AWS instance """
    print "Stopping instance"
    conn.stop_instances(instance_ids=[instance.id])


def terminate_instance(conn, instance):
    """ Stops an AWS instance """
    print "Terminating instance"
    conn.terminate_instances(instance_ids=[instance.id])


def put_input_file(ssh, filename):
    """ Put the file in the input directory """
    print "Transferring input file to instance"
    sftp = ssh.open_sftp()
    sftp.put(filename, "input/"+filename)


def get_output_files(ssh, filename):
    """ Get the simulation files and put them in the 
    current directory
    """
    print "Receiving output files from instance"
    sftp = ssh.open_sftp()
    sftp.get() #TODO: Implement the getting of the files


def run(job_name, script_file):
    """Run the mumax input file on a ready instance
    """

    if len(ready_instances) == 0:
        print "There are no instances waiting to be used."
        answer = raw_input("Create a new instance for this job? [Yn]: ")
        if len(answer) == 0 or answer.startswith(("Y", "y")):
            instance = launch_instance()
            print "Waiting for instance to boot up..."
            while instance.state != u'running':
                sleep(0.5)
            print "Instance is ready"

            instace.remove_tag(__STATUS__)
            try:
                # Establish connection
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(instance.public_dns_name, 
                    username='ec2-user', 
                    key_filename=config.get('EC2', 'PrivateKeyFile')
                )
 
                put_input_file(ssh, script_file)

                transport = ssh.get_transport()
                channel = transport.open_session()

                channel.exec_command("mumax3 input/%s" % script_file)

                # TODO: Test blocking ability
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

                print "Finished simulations"

                get_output_files(ssh)

                answer = raw_input("Terminate the instance? [Yn]: ")
                if len(answer) == 0 or answer.startswith(("Y", "y")):
                    terminate_instance(instance)
                else:
                    answer = raw_input("Stop the instance? [Yn]: ")
                    if len(answer) == 0 or answer.startswith(("Y", "y")):
                        stop_instance(instance)
                    else:
                        print "The instance has been left running"
        else:
            print "No instance will be launched"

        print "Mumax-ec2 has finished"


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print  "Usage: mumax-ec2.py name filename"
        sys.exit()
        
    name     = sys.argv[1]
    filename = sys.argv[2]
    run(name, filename)
