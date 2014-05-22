import sys, xmlrpclib, subprocess, os, time

commands = ['help', 'status', 'add', 'delete', 'list', 'clear', 'load']
server   = xmlrpclib.Server('http://localhost:7080/')
numargs  = len(sys.argv)

# Check the server
# TODO: sometimes the daemon only seems available for the NEXT run!
if not os.path.isfile('/home/ec2-user/control/qserver.pid'):
    print  "Need to start the daemon"
    os.chdir('/home/ec2-user/control')
    args = ['/usr/bin/twistd', 
            '--pidfile=/home/ec2-user/control/qserver.pid', 
            '--logfile=/home/ec2-user/control/qserver.log',
            '--python', '/home/ec2-user/control/qserver.py']
    proc = subprocess.check_call(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    print "Launch returned:", proc
    time.sleep(1)

def usage():
    name = sys.argv[0]
    print "General syntax:        %s <command>" % name
    print "Possible commands are:", ', '.join(commands) 
    print "Add syntax:            %s add <job_name> <mumax_script>" % name
    print "Delete syntax:         %s delete <job_name>" % name
    sys.exit()

def status():
    print server.running()[1]

def listqueue():
    jobs    = server.listqueue()
    print server.running()[1]
    if len(jobs) == 0:
        print "No jobs are queued."
    else:
        print '\n'.join()

def clear():
    print server.clearqueue()[1]

def load():
    print server.load()

def add(name, script_file):
    """Scripts start off in the """
    print server.addtoqueue(name, script_file)[1]

def delete(name):
    print server.removefromqueue(name)[1]

if numargs < 2:
    usage()
else:
    c = sys.argv[1]
    if c not in commands:
        usage()
    else:
        if (c == 'add') and (numargs==4):
            add(sys.argv[2], sys.argv[3])
        elif (c == 'delete') and (numargs==3):
            delete(sys.argv[2])
        elif c == 'help':
            usage()
        elif c == 'status':
            status()
        elif c == 'clear':
            clear()
        elif c == 'load':
            load()
        elif c == 'list':
            listqueue()
        else:
            usage()

