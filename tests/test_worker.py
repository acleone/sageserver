import os
import select
import time
import unittest

from sageserver.compnode.worker import Worker
from sageserver.compnode.worker.msgr import PipeMsgr
import sageserver.msg as msg
from sageserver.msg.decodedmsg import MsgDecoder

class TestWorker(unittest.TestCase):
    
    def setUp(self):
        p2c_r, self._p2c_w = os.pipe()
        self._c2p_r, c2p_w = os.pipe()
        from multiprocessing import Process
        self._childp = Process(target=self._child_start, args=(p2c_r, c2p_w))
        self._childp.start()
        
    def _child_start(self, p2c_r, c2p_w):
        msgr = PipeMsgr(p2c_r, c2p_w)
        w = Worker(msgr)
        w.loop_forever()
        
    def _send_msg(self, m):
        bytes = m.encode()
        i = 0
        while i < len(bytes):
            i += os.write(self._p2c_w, buffer(bytes, i))
            
    def _get_child_msgs(self, n=1, timeout=None):
        """
        Returns a list of child messages.
        """
        decoder = MsgDecoder()
        msgs = []
        if timeout is None:
            endt = time.time() - 1.0
        else:
            endt = time.time() + timeout
        while time.time() < endt and len(msgs) < n:
            rlist, _, _ = select.select([self._c2p_r], [], [], timeout)
            #print "rlist: %r" % (rlist,)
            for fd in rlist:
                rbytes = os.read(fd, 4096)
                msgs.extend(decoder.feed(rbytes))
        return msgs
        

    def test_Shutdown(self):
        self._send_msg(msg.Shutdown())
        self._childp.join(1.0)
        self.assertFalse(self._childp.is_alive())
        
    def test_IsComputing(self):
        self._send_msg(msg.IsComputing())
        msgs = self._get_child_msgs(timeout=0.25)
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].type, msg.NO)
        
    def test_exec_hello_world(self):
        self._send_msg(msg.ExecCell('print "Hello World!"'))
        msgs = self._get_child_msgs(2, timeout=0.25)
        self.assertEqual([m.type for m in msgs],
                         [msg.STDOUT, msg.STDOUT, msg.DONE])
        
    
    def tearDown(self):
        if self._childp.is_alive():
            self._send_msg(msg.Shutdown())
            self._childp.join(0.25)
            if self._childp.is_alive():
                self._childp.terminate()
        

if __name__ == '__main__':
    unittest.main()