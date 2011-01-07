import logging
import os
from Queue import Queue
from socket import create_connection
import thread
from time import sleep as _sleep, time as _time
from traceback import format_exc

from exec_env import ExecEnv
import sageserver.msg as msg
from sageserver.util import JoinBuffer

logging.basicConfig(level=logging.DEBUG)


RMSG_PIPE = 3
WMSG_PIPE = 4    
            

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
    def __init__(self):
        self._log = logging.getLogger(
            "%s[pid=%s]" % (self.__class__.__name__, os.getpid()) )
        
        self.RECV_HANDLERS = set((msg.SHUTDOWN, msg.INTERRUPT,
                                  msg.IS_COMPUTING))
            
    def loop(self):
        self._shutdown = False
        self._shutdown_called = False
        
        self._main_dead = False
        self._main_receiving = False # the main thread is blocking on a get()

        self._main_q = Queue()
        self._send_q = Queue()

        self._exec_env = ExecEnv(self._send_q)
        
        thread.start_new_thread(self._recv_thread, ())
        thread.start_new_thread(self._send_thread, ())
        
        self._main_thread()
        
            
    def _main_thread(self):
        """
        Executes messages from sent from the recv thread over self._main_q.
        """
        try:  
            while not self._shutdown:
                self._main_receiving = True
                try:
                    m = self._main_q.get()
                except KeyboardInterrupt:
                    continue
                self._main_receiving = False
                self._log.debug("[_main_thread] Got %r", m)
                if m.type == msg.SHUTDOWN:
                    self._shutdown = m
                    break
                if m.type == msg.INTERRUPT:
                    continue
                try:
                    self._exec_env.MAIN_HANDLERS[mtype](o)
                except KeyError:
                    self._log.error("[_main_thread] unhandled message %s", o)
        except KeyboardInterrupt:
            pass
        except:
            self._log.error("[_main_thread] %s", format_exc())
        finally:
            self._main_dead = True
            self._main_receiving = False
            self._log.info("[_main_thread] Exiting.")
            self.shutdown()
            
    def _recv_thread(self):
        """
        Receives bson messages over RMSG_PIPE.
        """
        try:
            rdr = BlockingPipeReader(RMSG_PIPE, self.is_shutdown)
            while not self._shutdown:
                hdr = msg.Hdr.decode(rdr.read(msg.HDR_LEN))
                if self._on_recv_hdr(hdr):
                    self._log.debug("Reading Message %d", hdr.type)
                    bodybytes = rdr.read(hdr.length)
                    m = msg.TYPE_DICT[hdr.type](hdr, bodybytes)
                    self._on_recv_msg(m)
                else:
                    self._log.debug("Skipping Message %d", hdr.type)
                    rdr.skip(hdr.length)
        except EOFError:
            self._log.info("[_recv_thread] Got EOF.")
        except:
            self._log.error("[_recv_thread] %s", format_exc())
        finally:
            self._log.debug("[_recv_thread] Exiting.")
            self.shutdown()
            
    def _on_recv_hdr(self, hdr):
        return hdr.type in msg.TYPE_DICT
    
    def _on_recv_msg(self, m):
        sendm = None
        if m.type in self.RECV_HANDLERS:
            if m.type == msg.SHUTDOWN:
                self._shutdown = m
                raise EOFError()
            elif m.type == msg.INTERRUPT:
                for _ in range(m['retries']):
                    if self._interrupt_main(m['poll_for']):
                        sendm = msg.Yes().init()
                        break
                else:
                    sendm = msg.No().init()
            elif m.type == msg.IS_COMPUTING:
                sendm = (msg.No().init() if self._main_receiving
                         else msg.Yes().init())
        elif m.type in self._exec_env.MAIN_HANDLERS:
            # send the message to the main thread
            self._main_q.put(m)
        else:
            try:
                sendm = self._exec_env.RECV_HANDLERS[m.type](m)
            except KeyError:
                self._log.warning("Unhandled msg: %r", m)
        if sendm is not None:
            sendm.hdr.sid = m.hdr.sid
            sendm.hdr.flags |= msg.HDRF_SCLOSE
            self._send_q.put(sendm)        
                    
    def _send_thread(self):
        """
        Sends messages.
        """
        try:
            while not self._shutdown:
                m = self._send_q.get()
                if self._send_q.empty() or m.type == msg.SHUTDOWN:
                    self._log.debug("[_send_thread] Got single %r", m)
                    self._blocking_write(m.encode())
                    if m.type == msg.SHUTDOWN:
                        break
                    continue
                msgs = [m]
                while not self._send_q.empty():
                    m = self._send_q.get()
                    msgs.append(m)
                    if m.type == msg.SHUTDOWN:
                        break
                
                self._log.debug("[_send_thread] Got multiple %r", msgs)
                #sendall(msg.combine_and_encode(msgs))
                self._blocking_write(b''.join([m.encode() for m in msgs]))
                if msgs[-1].type == msg.SHUTDOWN:
                    break
        except EOFError:
            self._log.debug("[_send_thread] Got EOF.")
        except:
            self._log.error("[_send_thread] %s", format_exc())
        finally:
            self._log.debug("[_send_thread] Exiting.")
            self.shutdown()
            
    def _blocking_write(self, bytes):
        i = 0
        while not self._shutdown and i < len(bytes):
            i += os.write(WMSG_PIPE, buffer(bytes, i))
        
    def shutdown(self):
        if self._shutdown_called:
            return
        self._shutdown_called = True
        if not self._shutdown:
            self._shutdown = msg.Shutdown().init()
        sd = self._shutdown
        self._send_q.put(sd)
        self._main_q.put(sd)
        
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
        return self._shutdown
    
    
class BlockingPipeReader(object):
    
    def __init__(self, fd, is_shutdown_func):
        self._fd = fd
        self._is_shutdown_func = is_shutdown_func
        self._jbuf = JoinBuffer()
        
    def read(self, n):
        """
        Returns a bytes instance with n octets.
        Throws EOFError if EOF is seen or is_shutdown_func returns True.
        """
        while len(self._jbuf) < n:
            if self._is_shutdown_func():
                raise EOFError()
            rbytes = os.read(self._fd, 4096)
            if not rbytes: # EOF
                raise EOFError()
            self._jbuf.append(rbytes)
        return self._jbuf.popleft(n)
    
    def skip(self, n):
        """
        Skips n octets of output.
        Throws EOFError if EOF is seen or is_shutdown_func returns True.
        """
        if n == 0:
            return
        if len(self._jbuf) > n:
            self._jbuf.popleft(n, join=False)
            return
        if len(self._jbuf) == n:
            self._jbuf.clear()
            return
        
        n_seen = len(self._jbuf)
        self._jbuf.clear()
        rbytes = None
        while n_seen < n:
            if self._is_shutdown_func():
                raise EOFError()
            rbytes = os.read(self._fd, 4096)
            if not rbytes: # EOF
                raise EOFError()
            n_seen += len(rbytes)
        if n_seen > n: # save some bytes.
            extra = n_seen - n
            split_idx = len(rbytes) - extra
            self._jbuf.append(buffer(rbytes, split_idx))
        return
        
        
def _poll_for(obj, attr, timeout=1.0, done_when=True, sleeptime=0.1):
    """
    Polls ``bool(getattr(obj, attr))`` occasinally until it returns
    `done_when`.  Returns the boolean value of the attribute.
    """
    def bool_val():
        a = getattr(obj, attr)
        return bool(a) if not hasattr(a, '__call__') else bool(a())
    endt = _time() + timeout
    while bool_val() != done_when and _time() < endt:
        _sleep(sleeptime)
    return bool_val()
    
if __name__ == '__main__':
    import doctest
    doctest.testmod()