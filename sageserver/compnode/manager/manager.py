from twisted.internet import protocol
from twisted.internet import reactor
from twisted.python import log

from bson.errors import BSONError
from collections import deque
from sys import argv as sys_argv

import sageserver.msg as msg
from sageserver.util import JoinBuffer

def get_worker_path(rel_path):
    from sys import argv
    from os.path import join, dirname
    return join(dirname(argv[0]), rel_path)

WORKER_PATH = get_worker_path('run_worker.py')


def main():
    WorkerProcessProtocol.spawn_worker()
    reactor.run()

WP_READING_HEADER = 1
WP_READING_BODY = 2
WP_SKIPPING_BODY = 3

class WorkerProcessProtocol(protocol.ProcessProtocol):    
    @classmethod
    def spawn_worker(cls):
        wpp = cls()
        childFDs = {0: "w", 1: "r", 2: "r", 3: "w", 4: "r"}
        reactor.spawnProcess(wpp, "python", ["python", WORKER_PATH],
                             childFDs=childFDs)
        print ">>>>> spawned pid %s <<<<<" % (wpp.transport.pid,)
        wpp._rm_pid = reactor.addSystemEventTrigger('before', 'shutdown',
                                      _rm_child_proc, wpp.transport.pid)
        return wpp
    
    def __init__(self):
        print ">>>>> __init__ <<<<<"
        self._jbuf = JoinBuffer()
        self._hdr = None
        self._reset_msg_parser()
        
    def _reset_msg_parser(self):
        self._state = WP_READING_HEADER
        self._n_needed = msg.HDR_LEN
        
    def connectionMade(self):
        print ">>>>> connectionMade <<<<<"
        if 0:
            print ">>>>> closing fd 3 <<<<<"
            self.transport.closeChildFD(3)
        if 1:
            bs = bytes(msg.Interrupt().init().encode())
            print ">>>>> sending %r <<<<<" % (bs,)
            self.transport.writeToChild(3, bs)
        
    def childDataReceived(self, childFD, data):
        
        if childFD != 4:
            #print "childDataReceived %d:\n%s" % (childFD, data)
            print data,
        if childFD == 4:
            print ">>>>> from send_thread: %r <<<<<" % (data,)
            self._jbuf.append(data)
            while len(self._jbuf) >= self._n_needed:
                if self._state == WP_READING_HEADER:
                    dbytes = self._jbuf.popleft(self._n_needed)
                    try:
                        hdr = msg.Hdr.decode(dbytes)
                    except HdrDecodeError:
                        log.err()
                        self.stopWorker()
                        return
                    self._state, self._n_needed = self.msgHeaderReceived(hdr)
                elif self._state == WP_READING_BODY:
                    dbytes = self._jbuf.popleft(self._n_needed)
                    self.msgBodyReceived(dbytes)
                    self._reset_msg_parser()
                elif self._state == WP_SKIPPING_BODY:
                    self._jbuf.popleft(self._n_needed, join=False)
                    self._reset_msg_parser()
                    

                    
    def msgHeaderReceived(self, hdr):
        """
        Returns (state, n_needed)
        """
        if hdr.type in msg.TYPE_DICT:
            self._hdr = hdr
            print ">>>>> Got %d %s header, len %d <<<<<" % (
                        hdr.type, msg.TYPE_STRS[hdr.type], hdr.length)
            return (WP_READING_BODY, hdr.length)
        else:
            print ">>>>> Got Unknown type %d header, len %d <<<<<" % (
                        hdr.type, hdr.length)
            return (WP_SKIPPING_BODY, hdr.length)
        
    def msgBodyReceived(self, bodybytes):
        print ">>>>> Got message body: %r <<<<<" % (bodybytes,)
        
        
            
        
                        
                        
    def stopWorker(self):
        print ">>>>> stopWorker <<<<<"
        self.transport.closeChildFD(3)
        self.transport.signalProcess('KILL')
        
                
                
            
            
    def childConnectionLost(self, childFD):
        print ">>>>> childConnectionLost %d <<<<<" % (childFD,)
                
    def processExited(self, reason):
        print ">>>>> processExited, status %d <<<<<" % (reason.value.exitCode,)
    def processEnded(self, reason):
        print ">>>>> processEnded, status %d <<<<<" % (reason.value.exitCode,)
        reactor.removeSystemEventTrigger(self._rm_pid)
        reactor.stop()
        
        
def _rm_child_proc(pid):
    from os import kill
    from signal import SIGKILL
    print "killing pid %s" % (pid,)
    try:
        kill(pid, SIGKILL)
    except OSError:
        pass
        
    
if __name__ == '__main__':
    main()