import sys
import pexpect
import time
import logging, os, argparse

parser = argparse.ArgumentParser(description='SSH Connection and then scp the files',
                                  usage='sshTest.py [Options...]',
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('-local_machine_ip', action='store', required=True, default=None, help='Ip address of local machine')
parser.add_argument('-local_machine_username', action='store',required=True,  default=None, help='Username of local machine')
parser.add_argument('-local_machine_password', action='store', required=True, default=None, help='Password of local machine')
parser.add_argument('-remote_machine_ip', action='store', required=True, default=None, help='Ip address of Remote machine')
parser.add_argument('-remote_machine_username', action='store', required=True, default=None, help='Username of Remote machine')

parser.add_argument('-remote_folder', action='store', default=None, help='Password of Remote machine')

'''
python3 sshTest.py -local_machine_ip=11 -local_machine_username=22 -local_machine_password=33 -remote_machine_ip=44 -remote_machine_username=55 -remote_machine_password=66
'''
args = parser.parse_args()

local_machine_ip = args.local_machine_ip
local_machine_username =args.local_machine_username
local_machine_password = args.local_machine_password

remote_machine_ip = args.remote_machine_ip
remote_machine_username = args.remote_machine_username
remote_machine_password = args.remote_machine_password

remote_folder = sys.argv[7]


class SSH():
    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password
        self.pexpectTimeout = 15
        ''' Below command to remove RSA key if needed'''
        self.cmdRSA = "ssh-keygen -f ~/.ssh/known_hosts -R %s &> /dev/null" % host

        '''
            Try Opening SSH connection to host machine few times before giving up
            Return a handle if succesful
        '''
        for i in range(0, 5):
            if self.openConnection():
                break
            else:
                self.close()
        if not self.handle:
            raise IOError("ssh connectivity could not be established")

    def openConnection(self):
        logging.info("Opening SSH connection to %s" % self.host)
        self.handle = None
        try:
            cmd = 'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no'
            self.handle = pexpect.spawn("%s  %s@%s" % (cmd, self.username, self.host), timeout=self.pexpectTimeout)
            self.handle.logfile_read = sys.stdout
        except:
            errMsg = "Could not open ssh connection [%s@%s]" % (self.username, self.host)
            logging.error(errMsg)
            return None

        rc = self.handle.expect([pexpect.EOF, pexpect.TIMEOUT, "password", "yes", "WARNING"])
        time.sleep(1)
        # if ssh key error
        if rc == 4:
            logging.info("Removing ssh key for host %s" % self.host)
            os.system(self.cmdRSA)
            return None
        elif rc == 3:
            logging.debug("Adding key for %s" % self.host)
            self.handle.sendline("yes")
            time.sleep(1)
            logging.debug("SSH lib first time yes fix")
            return None
        elif rc == 2:
            logging.debug("Entering password for %s" % self.host)
            if self.password:
                self.handle.sendline(self.password)
                time.sleep(1)
            else:
                logging.error("Password required for ssh but not provided")
                return None
        elif rc == 0:
            logging.error("SSH session timed out [%s@%s]" % (self.uname, self.host))
            return None
        else:
            logging.debug("SSH expect timed out")
            self.handle.close()  # close this shell, we've given up
            self.pexpectTimeout = 60  # try with a longer timeout on the next retry
            return None

        rc = self.handle.expect([pexpect.EOF, pexpect.TIMEOUT, self.prompt])

        if rc != 2:
            logging.error("SSH authentication failed [%s@%s]" % (self.uname, self.host))
            self.handle.close()
            self.handle = None

        return self.handle

    def __str__(self):
        return ("SSH to host[%s]" % (self.host))

    def __del__(self):
        self.close()

    def close(self):
        try:
            if self.handle:
                self.handle.close()
                self.handle = None
        except:
            logging.info("Unable to close ssh handle.")

    def scp(self, src, dst, scptimeout=30):
        logging.info("SCP file from %s to %s" % (src, dst))
        startTime = time.time()
        try:
            cmd = 'scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no'
            scpHandle = pexpect.spawn("%s %s %s" % (cmd, src, dst))
        except:
            logging.debug("Time taken = %s seconds" % (time.time() - startTime))
            raise IOError("Could not scp [%s@%s]" % (self.uname, self.host))

        rc = scpHandle.expect([pexpect.EOF, pexpect.TIMEOUT, "password", "yes"],
                                   timeout=scptimeout)

        if rc == 3:
            scpHandle.sendline("yes")

        if rc == 2 or rc == 3:
            scpHandle.sendline(self.password)
            scpHandle.expect([pexpect.EOF, pexpect.TIMEOUT], timeout=scptimeout)
        else:
            if scpHandle: scpHandle.close()
            raise IOError("SCP session timed out. Time taken = %s seconds" %
                          (time.time() - startTime))
        # Allow some time for I/O latency before doing a file size check
        time.sleep(1)
        if rc:
            logging.info("SCP Success. Time taken = %s seconds" % (time.time() - startTime))
        else:
            logging.error("SCP Failed. Time taken = %s seconds" % (time.time() - startTime))

        if scpHandle:
            scpHandle.close()
        return rc


remote_connection = SSH(remote_machine_ip, remote_machine_username, remote_machine_password)
remote_connection.scp('~/.ssh/known_hosts')
remote_connection.scp('~/.ssh/authorized_keys')