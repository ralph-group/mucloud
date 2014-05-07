"""
All settings should be stored in the config.ini file

"""
import boto.ec2
import paramiko
import sys

# Start the config parser
import ConfigParser
config = ConfigParser.ConfigParser()
config.read("./config.ini")

# Connect to Amazon Web Services (AWS)
conn = boto.ec2.connect_to_region(config.get('EC2', 'Region'),
            aws_access_key_id=config.get('EC2', 'AccessID'),
            aws_secret_access_key=config.get('EC2', 'SecretKey'))
            
# Run an instance from the image
reservation = conn.run_instances(config.get('EC2', 'Image'), 
            key_name="mumax%s" % config.get('EC2', 'MumaxVersion'),
            instance_type=config.get('EC2', 'InstanceType'),
            security_groups=config.get('EC2', 'SecurityGroups').split(','))
            
# Get the IP address of the instance
instance_address = reservation.public_dns_name
# TODO: Verify this method works properly for retreiving the IP, or use the
#       alternative method of getting all instance and then retreiving it

# Wait for the instance to be online
# TODO: Add blocking with sleep command till the instance is ready

# SFTP the mumax input file
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(instance_address, username='ec2-user')
sftp = ssh.open_sftp()
sftp.push(input_file, "/input.in") # TODO: correctly get input file from args

# Connect port forwarding for web interface
# TODO: Add paramiko port forwarding and verify it works across platforms

# Start the mumax simulation
ssh.exec_command("/mumax %s" % input_file) # TODO: have correct input file

# Set up inotify watcher to push data to remote storage
# TODO: Implement this with rsync over SSH, requiring the user to put in the
#       password when they start this script


