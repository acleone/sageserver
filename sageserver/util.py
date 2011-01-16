"""
Random Utility Classes.
"""

from collections import deque


class JoinBuffer(object):
    """
    For reading a lot of bytes in 4K increments from a socket.
    """
    
    def __init__(self):
        self._bufs = deque()
        self.clear()
        
    def __len__(self):
        return self._buflen
    
    def clear(self):
        self._bufs.clear()
        self._buflen = 0
        
    def extend(self, bytes):
        self._bufs.append(bytes)
        self._buflen += len(bytes)
        
    def popleft(self, n, join=True):
        """
        Pop the first n octets off and return a contiguous bytes(...) object.
        Returns None if there isn't enough bytes yet.
        """
        if n == 0:
            return b''
        if self._buflen < n:
            return None
        if self._buflen == n:
            r = b''.join(map(bytes, self._bufs)) if join else None
            self.clear()
            return r
        # else buflen > n
        ilen = 0
        joins = []
        while 1:
            buf = self._bufs.popleft()
            ilen += len(buf)
            if ilen < n:
                joins.append(buf)
                continue
            if ilen == n:
                joins.append(buf)
                break
            # else ilen > n:
            # split this buffer, leave half on self._bufs
            extra = ilen - n
            split_idx = len(buf) - extra
            joins.append(buffer(buf, 0, split_idx))
            self._bufs.appendleft(buffer(buf, split_idx))
            ilen -= extra
            break
        self._buflen -= ilen
        return b''.join(map(bytes, joins)) if join else None