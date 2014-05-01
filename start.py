import boto.ec2
import paramiko
import sys

conn = boto.ec2.connect_to_region('us-east-1b',
            aws_access_key_id='',
            aws_secret_access_key='')
conn.run_instance('mumax3-gpu2', 
            key_name='mumax3', 
            instance_type='g2.2xlarge',
            security_groups=[''])
            
instance_ids = [ instance.id for instance in load_balancer.instances ]
reservations = ec2_connection.get_all_instances(instance_ids)
instance_addresses = [ i.public_dns_name for r in reservations for i in r.instances ]
