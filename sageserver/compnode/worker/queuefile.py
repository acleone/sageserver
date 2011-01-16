from io import IOBase

import sageserver.msg as msg
from sageserver.util import JoinBuffer

class QueueFileOut(IOBase):
    r"""
    Puts :func:`write` or :func:`writelines` data onto a queue.  Replaces
    :obj:`sys.stdout` and :obj:`sys.stderr` in worker exec's, where the queue
    is serviced by the sending thread and gets sent over a socket.
        
    EXAMPLES:
        >>> import Queue
        >>> q = Queue.Queue()
        >>> f = QueueFileOut(q, msg.Stdout, 1)
        >>> print >>f, "Hello World!"
        >>> q.qsize()
        2
        >>> m1 = q.get(); m2 = q.get()
        >>> m1
        Stdout('Hello World!', id=1)
        >>> m2
        Stdout('\n', id=1)
    """
        
    def __init__(self, send_q, msg_cls, sid):
        """
        :param send_q: a :class:`Queue.Queue` object to put Msgs onto.
        :param msg_cls: a subclass of :class:`msg.MsgWithId`, usually
            :class:`Stdin` or :class:`Stderr`.
        :param id: an unsigned integer to pass to :class:`msg.MsgWithId`.
        :raises: ValueError if msg_cls is not a subclass of
            :class:`msg.MsgWithId` or id is less than zero.
        """
        self._send_q = send_q
        self._msg_cls = msg_cls
        self._sid = sid
        
    @property
    def encoding(self):
        return 'UTF-8'
        
    def flush(self):
        pass
  
    @property
    def mode(self):
        return 'wb'
        
    @property
    def name(self):
        return '<QueueFileOut:%s(sid=%s)>' % (self._msg_cls.__name__,
                                              self._sid)
    
    def write(self, s):
        if not isinstance(s, basestring):
            s = str(s)
        self._send_q.put(self._msg_cls(s, _hsid=self._sid))
        
    def writelines(self, iterable):
        out = []
        for line in iterable:
            if not isinstance(line, basestring):
                line = str(line)
            out.append(line)
        self.write(''.join(out))
        

class QueueFileIn(IOBase):
    r"""
    Reads data from a queue to return to :func:`read` calls.

    EXAMPLES:
        >>> import Queue
        >>> recv_q = Queue.Queue()
        >>> send_q = Queue.Queue()
        >>> def need_recv_func(id, size):
        ...     recv_q.put(msg.Stdin('Hello World!', id=3))
        ...     recv_q.put(msg.Stdin(id=3))
        >>> f = QueueFileIn(recv_q, send_q, 2, need_recv_func)
        >>> f.read()
        'Hello World!'
        >>> send_q.qsize()
        2
        >>> m1 = send_q.get(); m2 = send_q.get()
        >>> m1
        Stdin('Hello World!', id=2)
        >>> m2
        Stdin(id=2)
    """
    
    def __init__(self, recv_q, send_q, sid, echo_stdin=True):
        """
        :param recv_q: a :class:`Queue.Queue` object to get Msg objects
            from. If the received Msg object is not an instance of
            :class:`msg.Stdin`, return from the read.  If the message is a
            :class:`msg.Stdin` with bytes='', then simulate an EOF and
            return from read.
        :param send_q: a :class:`Queue.Queue` object to put
            :class:`msg.Stdin` objects onto, or None if Stdin messages
            should not be sent out.  The reason for sending Stdin messages
            out is so that they can be displayed in sequence with the Stdout
            and Stderr messages.  The id of the messages will be the id passed.
        :param id: an integer >= to pass to need_recv_func.
        :param need_recv_func: A function (id, size) to call when read is
            called and there's nothing in the buffer to send.
        """
        self._recv_q = recv_q
        self._send_q = send_q
        self._sid = sid
        self._echo_stdin = echo_stdin
        self._jbuf = JoinBuffer()
        self._waiting = False

    @property
    def encoding(self):
        return 'UTF-8'
        
    def flush(self):
        pass

    @property
    def mode(self):
        return 'rb'
        
    @property
    def name(self):
        return '<QueueFileIn(sid=%s)>' % (self._sid,)
        
    @property
    def waiting(self):
        """
        True if currently wiating for something over the queue.
        """
        return self._waiting
        
    def _recv_stdin(self, size):
        """
        Sends a :class:`msg.NeedStdin` if there's nothing to return in the
        buffer.

        :raises: KeyboardInterrupt if we received a :class:`msg.Interrupt`.
        """
        if self._recv_q.empty():
            self._send_q.put(msg.NeedStdin(size, _hsid=self._sid))
        m = self._recv_q.get()
        if m.type == msg.INTERRUPT:
            raise KeyboardInterrupt
        if not m.type == msg.STDIN:
            return ''
        return m.bytes
        
    def _send_stdin(self, bytes, wasEOF=True):
        """
        Sends msg.Stdin to send_queue if not None.  Adds empty Stdin() if
        wasEOF is true.
        """
        if self._echo_stdin:
            self._send_q.put(msg.Stdin(bytes, _hsid=self._sid))
            if wasEOF:
                self._send_q.put(msg.Stdin('', _hsid=self._sid))
    
    def read(self, size=-1):
        if size == 0:
            return b''
        jbuf = self._jbuf
        self._waiting = True
        if size < 0:
            while True:
                rbytes = self._recv_stdin(-1)
                if not rbytes:
                    break
                jbuf.extend(rbytes)
            r = jbuf.popall()
            self._send_stdin(r, True)
            self._waiting = False
            return r
        # size > 0:
        wasEOF = False
        while len(jbuf) < size:
            rbytes = self._recv_stdin(size - len(jbuf))
            if not rbytes:
                wasEOF = True
                break
            jbuf.extend(rbytes)
        if wasEOF:
            r = jbuf.popall()
        else:
            r = jbuf.popleft(size)
        self._send_stdin(r, wasEOF)
        self._waiting = False
        return r            

if __name__ == '__main__':
    import doctest
    doctest.testmod()
