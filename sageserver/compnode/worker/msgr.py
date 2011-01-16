import logging
import os
from Queue import Queue
import thread
from traceback import format_exc

from sageserver.msg.decodedmsg import CallbackMsgDecoder


class ShutdownNow(Exception):
    pass


class PipeMsgr(object):
    def __init__(self, readfd, writefd):
        self._log = logging.getLogger(
            "%s[pid=%s]" % (self.__class__.__name__, os.getpid()) )
        self._readfd = readfd
        self._writefd = writefd
        self._recv_handlers = {}
        self._shutdown_test = lambda: True
        self._on_shutdown = lambda: False
        self._send_q = Queue()
        
    @property
    def recv_handlers(self):
        return self._recv_handlers

    def set_shutdown_test(self, shutdown_test):
        """
        shutdown_test should return True when we should stop receving/sending
        messages.
        """
        self._shutdown_test = shutdown_test
        
    def set_on_shutdown(self, on_shutdown):
        self._on_shutdown = on_shutdown
        
    def get_send_queue(self):
        """
        Returns the send queue that should be used for sending messages.
        """
        return self._send_q
    
    def start_io(self):
        """
        Runs the io.
        """
        thread.start_new_thread(self._recv_thread, ())
        thread.start_new_thread(self._send_thread, ())
        
    def _recv_thread(self):
        """
        Receives messages.
        """
        try:
            decoder = CallbackMsgDecoder(self._recv_handlers, self._log)
            while not self._shutdown_test():
                rbytes = os.read(self._readfd, 4096)
                if not rbytes:
                    self._log.info("[_recv_thread] Got EOF.")
                    break
                decoder.feed(rbytes)
        except ShutdownNow:
            # raised by the Shutdown msg handler
            pass
        except:
            self._log.error("[_recv_thread] %s", format_exc())
        finally:
            self._log.debug("[_recv_thread] Exiting.")
            self._on_shutdown()
    
    def _send_thread(self):
        """
        Sends messages.
        """
        try:
            while not self._shutdown_test():
                m = self._send_q.get()
                self._log.debug("[_send_thread] Got %r", m)
                self._blocking_write(m.encode())
        except:
            self._log.error("[_send_thread] %s", format_exc())
        finally:
            self._log.debug("[_send_thread] Exiting.")
            self._on_shutdown()
            
    def _blocking_write(self, bytes):
        i = 0
        while not self._shutdown_test() and i < len(bytes):
            i += os.write(self._writefd, buffer(bytes, i))
        
        