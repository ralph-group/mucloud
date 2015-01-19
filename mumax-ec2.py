#!/usr/bin/env python
"""
All settings should be stored in the config.ini file

"""

__version__ = 1.0
__TAG__ = 'mumax-ec2'
# TODO: Compare mumax-ec2 tag with version

import boto.ec2
import paramiko
import sys, os

# Start the config parser
import ConfigParser
config = ConfigParser.ConfigParser()
config.read("./config.ini")

# Connect to Amazon Web Services (AWS)
conn = boto.ec2.connect_to_region(config.get('EC2', 'Region'),
            aws_access_key_id=config.get('EC2', 'AccessID'),
            aws_secret_access_key=config.get('EC2', 'SecretKey'))
            
search_condition = lambda i: i.state == u'running' and __TAG__ in i.tags

instances          = conn.get_only_instances()
live_instances     = [i for i in instances if search_condition(i)]
instance_addresses = [i.public_dns_name for i in live_instances]

#TODO: prompt to add new instance if none are available

def launch_instance(conn):
    """ Launch a new AWS instance """
    reservation = conn.run_instances(
            config.get('EC2', 'Image'),
            key_name=config.get('EC2', 'PrivateKeyName'),
            instance_type=config.get('EC2', 'InstanceType'),
            security_groups=config.get('EC2', 'SecurityGroups').split(',')
    )
    for i in reservation.instances:
        i.add_tag(__TAG__, __version__)


def stop_instance(conn, instance_id):
    """ Stops an AWS instance """
    conn.stop_instances(instance_ids=[instance_id])


def status(echo=True):
    """Poll the status of each instance"""
    loads = {}
    try:
        for address, instance in zip(instance_addresses, live_instances):
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(address, username='ec2-user', key_filename=config.get('EC2', 'PrivateKeyFile'))
            stdin, stdout, stderr = ssh.exec_command("python27 control/qclient.py list")
            if echo:
                print "==== Status of instance %s ====" % instance.id 
                print stdout.read()
            stdin, stdout, stderr = ssh.exec_command("python27 control/qclient.py load")
            loads[instance] = int(stdout.read())
    except:
        print "Couldn't contact server"
    return loads


def run(job_name, script_file):
    """Run the script file on the instance with the smallest number of queued files"""
    try:
        loads = status(echo=False)
        sortedLoads = sorted(loads, key=loads.get, reverse=False)
        for w in sortedLoads:
            print "Instance", w.id, "has a load of", loads[w]

        best_node = sortedLoads[0]
        script_name = job_name + "_" + os.path.basename(script_file) 
        print "Running on instance with lowest load:", best_node.id
        # Establish connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(best_node.public_dns_name, username='ec2-user', key_filename=config.get('EC2', 'PrivateKeyFile'))
        # Put the script file on the instance
        sftp = ssh.open_sftp()
        sftp.put(script_file, "input/"+script_name) 
        # Add the job to the queue
        stdin, stdout, stderr = ssh.exec_command("python27 control/qclient.py add %s %s" % (job_name, script_name))

    except:
        print "Couldn't contact server"


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print  "Usage: mumax-ec2.py name filename"
        sys.exit()
        
    name     = sys.argv[1]
    filename = sys.argv[2]
    run(name, filename)
    status()
