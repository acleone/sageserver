import logging
import os
from Queue import Queue
import thread
from time import sleep as _sleep, time as _time
from traceback import format_exc

from exec_env import ExecEnv
from msgr import ShutdownNow
import sageserver.msg as msg
from sageserver.msg.decodedmsg import CallbackMsgDecoder

logging.basicConfig(level=logging.DEBUG)

class Worker(object):
    """    
    A worker interacts with it's parent process (a manager) through
    stdin (fd 0), stdout (fd 1), stderr (fd 2), rmsg_pipe (fd 3), and
    wmsg_pipe (fd 4).  Most communication happens through rmsg_pipe and
    wmsg_pipe in BSON-encoded messages.  If something segfaults there
    might be plain output on stdin, stdout, or stderr that needs to be read.

    A worker consists of three threads:

      1. A receiving thread, ``_recv_thread``, that handles incoming BSON
         messages from rmsg_pipe.
      2. A sending thread, ``_send_thread``, that sends outgoing BSON messages
         over wmsg_pipe.
      3. The main thread, where cell execution happens.

    Execution happens in the main thread because all signals get sent
    to the main thread, so interrupting the main thread without disturbing the
    communication threads is possible.
    
    Communication between threads is done with Queue's.
    """
    def __init__(self, msgr):
        self._log = logging.getLogger(
            "%s[pid=%s]" % (self.__class__.__name__, os.getpid()) )
        self._msgr = msgr        
            
    def loop_forever(self):
        msgr = self._msgr
        self._shutdown = False
        self._shutdown_called = False
        
        self._main_dead = False
        self._main_receiving = False # the main thread is blocking on a get()

        self._main_q = Queue()
        self._send_q = msgr.get_send_queue()
        
        self._exec_env = ExecEnv(msgr)
        msgr.recv_handlers.update({
            msg.SHUTDOWN: self._recv_Shutdown,
            msg.IS_COMPUTING: self._recv_IsComputing,
        })
        msgr.set_shutdown_test(self.is_shutdown)
        msgr.set_on_shutdown(self.shutdown)
                
        msgr.start_io()
        
        try:  
            while not self._shutdown:
                self._main_receiving = True
                m = self._main_q.get()
                self._main_receiving = False
                self._log.debug("[_main_thread] Got %r", m)
                if m.type == msg.SHUTDOWN:
                    self._shutdown = m
                    break
                if m.type in self._exec_env.MAIN_HANDLERS:
                    self._exec_env.MAIN_HANDLERS[m.type](m)
                else:
                    self._log.error("[_main_thread] unhandled message %s", m)
        except KeyboardInterrupt:
            pass
        except:
            self._log.error("[_main_thread] %s", format_exc())
        finally:
            self._main_dead = True
            self._main_receiving = False
            self._log.debug("[_main_thread] Exiting.")
            self.shutdown()

    def _recv_Shutdown(self, m):
        self._shutdown = m
        raise ShutdownNow()
    
    def _recv_IsComputing(self, m):
        rm = msg.No() if self._main_receiving else msg.Yes()
        self._send_q.put(rm)
   
    def shutdown(self):
        if self._shutdown_called:
            return
        self._shutdown_called = True
        if not self._shutdown:
            self._shutdown = msg.Shutdown()
        sd = self._shutdown
        self._send_q.put(sd)
        self._main_q.put(sd)
        return
        
        if _poll_for(self, '_main_dead', timeout=sd['before_int']):
            return
            
        # currently executing something.  Try interrupting.
        for _ in range(sd['int_retries']):
            self._interrupt_main(0)
            if _poll_for(self, '_main_dead', timeout=sd['int_poll']):
                return
            
        # interrupt didn't work.  Kill ourselves
        from signal import SIGKILL
        self._log.warn("[shutdown] commiting suicide.")
        _sleep(0.1) # sleep so that the logging completes
        os.kill(os.getpid(), SIGKILL)
    
    def _interrupt_main(self, poll_for=1.0):
        if self._main_receiving:
            return True
            
        if self._exec_env.waiting_on_stdin:
            self._exec_env.interrupt_stdin()
            if _poll_for(self, '_main_receiving', timeout=poll_for):
                return True
            
        self._log.debug("[_interrupt_main] thread.interrupt_main()")
        thread.interrupt_main()
        if _poll_for(self, '_main_receiving', timeout=poll_for):
            return True
            
        return False
        
    def is_shutdown(self):
        return bool(self._shutdown)
    
if __name__ == '__main__':
    import doctest
    doctest.testmod()