import sys, os, shutil
from twisted.web import xmlrpc, server
from twisted.internet import reactor, utils
from twisted.python import log

from twisted.internet import protocol
from twisted.application import service, internet

import paramiko
log.startLogging(sys.stdout)

# Start the config parser
import ConfigParser
config = ConfigParser.ConfigParser()
config.read(os.path.dirname(os.path.realpath(__file__))+"/config.ini")
print "Reading config file", os.path.dirname(os.path.realpath(__file__))+"/config.ini"

class MumaxController(xmlrpc.XMLRPC):
    """
    An example object to be published.
    """
    _simQueue = []
    _running = False
    _running_name = ''
    _last_data_dir = ''
    deferred = None

    def run(self, job):
        print "Running job", job
        script_file = "/home/ec2-user/input/%s" % job[1]
        output_dir  = "/home/ec2-user/output/%s.out" % job[0]
        binary      = "/home/ec2-user/mumax3/mumax3-cuda5.5"
        self._last_data_dir    = output_dir
        self._last_script_file = script_file
        self.deferred = utils.getProcessOutput(binary, ['-http=:35367',("-o=%s" % output_dir), script_file], errortoo=True)
        self.deferred.addCallbacks(self.done, self.abort)

    def next(self):
        if self._running:
            print "Cannot start next job, already running."
        else:
            if len(self._simQueue) == 0:
                print "No jobs left"
            else:
                next_job = self._simQueue.pop(0)
                self._running = True
                self._running_name = next_job[0]
                self.run(next_job)
    
    def done(self, result):
        print "Done!", result
        # Establish the connection
        try:
            print "Establishing seceure connection to remote storage host"
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(config.get('Storage', 'Server'), username=config.get('Storage', 'Username'), password=config.get('Storage', 'Password'))
            print "Establishing sftp connection"
            # Put the data on the server
            sftp = ssh.open_sftp()
            sftp.chdir('mumax')
            files = sftp.listdir()
            if not os.path.basename(self._last_data_dir) in files:
                print "Creating directory mumax/%s" % os.path.basename(self._last_data_dir)
                sftp.mkdir(os.path.basename(self._last_data_dir))
            else:
                print "Directory %s already exists." % os.path.basename(self._last_data_dir)
            sftp.chdir(os.path.basename(self._last_data_dir))
            print "Here..."
            for item in os.listdir(self._last_data_dir):
                print "Uploading", item, "to", config.get('Storage', 'Server')
                sftp.put(self._last_data_dir+"/"+item, item) 

            print "Removing files from previous run"
            os.remove(self._last_script_file)
            shutil.rmtree(self._last_data_dir)
        except:
            print "Error while pushing results to remote storage host."

        self._running = False
        self._running_name = ''
        self._last_data_dir = ''
        self._last_script_file = ''
        self.next()

    def abort(self, result):
        print "Failed! Result:", result
        self._running = False
        self._running_name = ''

    def xmlrpc_running(self):
        """
        Returns boolean based on whether a mumax3 process is running.
        """   
        if self._running:
            return True, "%s is running." % self._running_name
        else:
            return False, "No jobs are running."

    def xmlrpc_listqueue(self):
        """
        Returns a list of enqueued simulations
        """
        if len(self._simQueue)>0:         
            names = [q[0] for q in self._simQueue]
        else:
            names = ''
        return names

    def xmlrpc_load(self):
        """
        Returns a number representing the load
        """
        load = len(self._simQueue)
        if self._running:
            load += 1
        return load

    def xmlrpc_clearqueue(self):
        """
        Returns a list of enqueued simulations
        """
        try:
            self._simQueue = []   
            return True, "Successfully cleared queue."
        except:
            return False, "Could not clear the queue."

    def xmlrpc_addtoqueue(self, name, script):
        """
        Add a simulation to the queue
        """         
        try:
            names = [q[0] for q in self._simQueue]
            if name not in names:
                # print "Adding mumax script\n", script
                self._simQueue.append([name, script])
                print "Added"
                self.next()
                return True, "Successfully added to queue."
            else:
                return False, "Simulation with that name already queued."
        except:
            print "Error"
            return False, "An error occured."

    def xmlrpc_removefromqueue(self, name):
        """
        Returns a list of enqueued simulations
        """         
        names = [q[0] for q in self._simQueue]
        try:
            index = names.index(name)
            self._simQueue.pop(index)
            return True, "Successfully removed %s from the queue." % name
        except:
            return False, "Could not remove %s from the queue." % name

if __name__ == '__main__':
    r = MumaxController()
    reactor.listenTCP(7080, server.Site(r))
    reactor.run()
else:
    r = MumaxController()
    application = service.Application("qserver")
    internet.TCPServer(7080, server.Site(r)).setServiceParent(application)