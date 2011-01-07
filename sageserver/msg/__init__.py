"""

This module defines the message format between:

1. (In the computation node) Manager Process to Worker Process.

The general structure of a message over the wire is::

  0         16         32
  -----------------------
  |   type   |   sid    |
  -----------------------
  |      length         |
  -----------------------
  |flags|csum|
  ------------

Note: all integers are little-endian encoded.
  
* type {uint16_t} -- message type
* sid {uint16_t} -- stream id
* length {uint32_t} -- number of octets of message body that follow the header
* flags {uint8_t} -- bit field:

  * 0x80 -- sopen -- stream open
  * 0x40 -- sclose -- stream close
  * 0x20 - 0x01 -- reserved for future use -- set to zero

* csum {uint8_t} -- sum of the first 8 octets in the header, then bitwise
                    inverted (xor 0xff).
                       
In python struct format syntax, the header is represented as "<HHIBB".

"""

from msgints import *
from hdr import *
from msgbase import *

def _gen_type_strs():
    import msgints
    return dict([(getattr(msgints, k), k)
                 for k in dir(msgints)
                 if k.isupper()])
    
TYPE_STRS = _gen_type_strs()

def _gen_type_dict():
    import msgs_outputs
    import msgs_requests
    type_dict = {}
    for k, v in TYPE_STRS.iteritems():
        clsname = ''.join( map(str.capitalize, v.split('_')) )
        cls = None
        if hasattr(msgs_outputs, clsname):
            cls = getattr(msgs_outputs, clsname)
        elif hasattr(msgs_requests, clsname):
            cls = getattr(msgs_requests, clsname)
        else:
            #print "Warning: no %s(Msg) defined for type %s!" % (clsname, v)
            continue
        type_dict[k] = cls
    return type_dict

TYPE_DICT = _gen_type_dict()
    
from msgs_outputs import *
from msgs_requests import *