from struct import calcsize, pack_into, unpack_from

__all__ = ("HDR_LEN", "HDRF_SOPEN", "HDRF_SCLOSE",
           "Hdr", "HdrDecodeError")

_HDR_STRUCT_FMT = "<HHIBH"

HDR_LEN = calcsize(_HDR_STRUCT_FMT)

_N_CSUM_BYTES = 8
_CSUM_MASK = 0xffff

HDRF_SOPEN = 0x80
HDRF_SCLOSE = 0x40

class Hdr(object):
    """
    Representation of a header struct.
    
    TESTS::
    
       >>> h1 = Hdr(3, 4, 5, 6)
       >>> (h1.type, h1.sid, h1.length, h1.flags)
       (3, 4, 5, 6)
       >>> Hdr.decode(h1.encode())
       Hdr(type=3, sid=4, length=5, flags=6)
       >>> h1err = h1.encode()
       >>> h1err[_HDR_SUM_IDX] = 47
       >>> h3 = Hdr.decode(h1err)
       Traceback (most recent call last):
       ...
       RuntimeError: header sum incorrect (got 0x2f exp 0xf3)
       >>> sum(repr(Hdr.decode(Hdr(i,1,2,3).encode())) ==
       ...     "Hdr(type=%d, sid=1, length=2, flags=3)" % (i,)
       ...     for i in range(512))
       512
                     
    """
    __slots__ = ("type", "sid", "length", "flags")
    
    def __init__(self, type, sid, length, flags):
        self.type = type
        self.sid = sid
        self.length = length
        self.flags = flags      
        
    def encode(self):
        """
        Returns a bytearray representing this object.
        """
        bytes = bytearray(HDR_LEN)
        pack_into(_HDR_STRUCT_FMT, bytes, 0,
                  self.type, self.sid,
                  self.length,
                  self.flags, 0)
        csum = (sum(bytes[:_N_CSUM_BYTES]) & _CSUM_MASK) ^ _CSUM_MASK
        pack_into(_HDR_STRUCT_FMT, bytes, 0,
                  self.type, self.sid,
                  self.length,
                  self.flags, csum)
        return bytes
        
    @classmethod
    def decode(cls, bytearr, offset=0):
        t, s, l, f, csum = unpack_from(_HDR_STRUCT_FMT, buffer(bytearr), offset)
        # calculate expected checksum
        esum = (sum(
                    bytearray(buffer(bytearr, offset, _N_CSUM_BYTES))
                ) & _CSUM_MASK) ^ _CSUM_MASK
        if esum != csum:
            raise HdrDecodeError("header sum incorrect (got 0x%02x exp 0x%02x)"
                                 % (csum, esum))
        return cls(t, s, l, f)
    
    def __repr__(self):
        return "".join((self.__class__.__name__, "(",
                       ", ".join("%s=%s" % (k, getattr(self, k))
                                 for k in self.__slots__), ")"))


class HdrDecodeError(Exception):
    """
    Error thrown when decoding fails.
    """