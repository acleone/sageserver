

import bson
from collections import namedtuple
from struct import calcsize, pack_into, unpack_from


    
class Msg(object):
    """
    A Message Header and it's body.
    
    A message can be created two ways:
    
    1. From the sub-class message constructor.
    2. From a Hdr object and a bytearray (i.e. the body hasn't been decoded).
    
    :ivar hdr: The header object.
    :ivar body: The body object.
    
    """
    
    def __init__(self, hdr, bodybytes):
        pass
        
    
    def encode(self):
        """
        Encodes the message to a bytestring.
        """

    
class ExecCell(Msg):
    
    def __init__(self, code, cell_id=None, cell_name=None,
                 echo_stdin=True, err2out=False,
                 displayhook='last', assignhook=None,
                 print_ast=False, time=False, timeit=False):
        pass

class Shutdown(Msg):
    
    def __init__(self):
        pass



"""

    >>> Chdir().init(path='blah')
    
    vs
    
    >>> Chdir(hdr, bodybytes)

"""

    
class Stdout(Msg):
    
    def __init__(self, bytes):
        pass
    
    
        

if __name__ == '__main__':
    import doctest
    doctest.testmod()
            