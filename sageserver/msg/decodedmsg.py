from bson import _bson_to_dict, _dict_to_bson, SON

from hdr import Hdr, HDR_LEN, HDRF_SCLOSE
from sageserver.util import JoinBuffer

class DecodedMsg(object):
    """
    Messages decoded will be Msg instances.  Message instances created by the
    user will be subclasses of Msg.  Both decoded and created messages should
    be handled by checking m.type, eg m.type = msg.SHUTDOWN.
    
    Msg instances are created when decoding messages.  The body of the message
    is only decoded when needed.
    """
    type = None
    
    def __init__(self, _hdr, _bodybytes):
        self.hdr = _hdr
        self._bodybytes = _bodybytes
        self.type = _hdr.type
        self._body = None
        
    def as_reply_to(self, m):
        self.hdr.sid = m.hdr.sid
        self.hdr.flags |= HDRF_SCLOSE
        return self
        
    def __getitem__(self, key):
        self.ensure_decoded()
        return self._body[key]
    
    def __setitem__(self, key, value):
        self.ensure_decoded()
        self._body[key] = value
        
    def ensure_decoded(self):
        """
        Decodes the body if not yet decoded.
        """
        if self._body is None:
            self._body = self._decode_body(self._bodybytes)
            
    def _decode_body(self, bodybytes):
        """
        Returns a body object.
        """
        return _bson_to_dict(bodybytes, SON, False)[0]
            
    def encode(self):
        """
        Returns a string.
        """
        if self._body is not None:
            self._bodybytes = _dict_to_bson(self._body, False)
            self.hdr.length = len(self._bodybytes)
        return self.hdr.encode() + self._bodybytes
    
    def __repr__(self):
        if self._body is None:
            return "<DecodedMsg instance at 0x%x with undecoded body>" % (
                        id(self),)
        else:
            return "<DecodedMsg instance at 0x%x with body=%r>" % (
                        id(self), self._body)
            
class MsgDecoder(object):
    
    def __init__(self):
        self._jbuf = JoinBuffer()
        self._hdr = None
        
    def feed(self, bytes):
        """
        Returns a list of DecodedMsg instances.
        """
        jbuf = self._jbuf
        jbuf.extend(bytes)
        msgs = []
        while True:
            if self._hdr is None:
                if len(jbuf) < HDR_LEN:
                    break
                hdrbytes = jbuf.popleft(HDR_LEN)
                self._hdr = Hdr.decode(hdrbytes)
            else:
                if len(jbuf) < self._hdr.length:
                    break
                bodybytes = jbuf.popleft(self._hdr.length)
                m = DecodedMsg(self._hdr, bodybytes)
                msgs.append(m)
                self._hdr = None
                
        return msgs
    
class CallbackMsgDecoder(object):
    
    def __init__(self, callbacks, log=None):
        self._callbacks = callbacks
        self._log = log
        self._jbuf = JoinBuffer()
        self._hdr = None
        
    def feed(self, bytes):
        callbacks = self._callbacks
        jbuf = self._jbuf
        jbuf.extend(bytes)
        while True:
            if self._hdr is None:
                if len(jbuf) < HDR_LEN:
                    break
                hdrbytes = jbuf.popleft(HDR_LEN)
                self._hdr = Hdr.decode(hdrbytes)
            else:
                if len(jbuf) < self._hdr.length:
                    break
                if self._hdr.type in callbacks:
                    bodybytes = jbuf.popleft(self._hdr.length)
                    m = DecodedMsg(self._hdr, bodybytes)
                    callbacks[self._hdr.type](m)
                elif self._log is not None:
                    jbuf.popleft(self._hdr.length, False)
                    self._log.warning("Unhandled message type=%d",
                                      self._hdr.type)
                self._hdr = None