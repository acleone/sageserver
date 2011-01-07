import bson
from bson.son import SON
from collections import namedtuple
import struct

MAX_OBJ_SIZE = 4 * 1024 * 1024

DSTATE_GET_LENGTH = 1
DSTATE_GET_BODY = 2

Obj = namedtuple('Obj', 'son bytes')

class Decoder(object):
    """
    See bson._bson_to_dict
    """
    __slots__ = ('_buf', '_obj_size', 'state')
    
    def __init__(self):
        self._buf = bytearray()
        self.state = DSTATE_GET_LENGTH
        
    def feed(self, bytes):
        objs = []
        self._buf.extend(bytes)
        while 1:
            if self.state == DSTATE_GET_LENGTH:
                if len(self._buf) < 4:
                    return objs
                obj_size = struct.unpack_from("<i", buffer(self._buf, 0, 4))[0]
                if obj_size > MAX_OBJ_SIZE:
                    raise bson.InvalidBSON("BSON objects are limited to "
                                           "4MB")
                self._obj_size = obj_size
                self.state = DSTATE_GET_BODY
            elif self.state == DSTATE_GET_BODY:
                endi = self._obj_size
                if len(self._buf) < endi:
                    return objs
                obytes = buffer(self._buf, 0, endi)
                objs.append(Obj(son=bson._bson_to_dict(obytes, SON, False),
                                bytes=obytes))
                self._buf = self._buf[endi:]
                self.state = DSTATE_GET_LENGTH
                
        # should never reach here
                
                    
                
            