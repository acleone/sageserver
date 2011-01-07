import bson
from collections import namedtuple

from hdr import Hdr

__all__ = ("Msg", "Fld", "simplemsg")

class Msg(object):
    
    type = None
    typekey = False
    
    def __init__(self, _hdr=None, _bodybytes=None):
        """
        See .init for the public constructor.
        """
        self.hdr = _hdr
        if _hdr is not None:
            self.type = _hdr.type
        self._body = None
        self._bodybytes = _bodybytes
        
    def _decode_body(self, bodybytes):
        """
        Returns a body object.
        """
        return bson.BSON(bodybytes).decode(as_class=bson.SON)
        
    def _encode_body(self, body):
        """
        Returns the bytes that will be sent as the message body.
        """
        return bson.BSON.encode(body)
        
    def init(self, kvs=[]):
        """
        The public constructor.  Put any fields here.
        """
        self.hdr = Hdr(self.type, 0, 0, 0)
        self._body = bson.SON()
        if self.typekey:
            self._body['t'] = self.type
        for k, v in kvs:
            self._body[k] = v
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
    
    def changed(self):
        """
        Should be called when the body is changed, an the object has already
        been encoded.
        """
        self.ensure_decoded()
        self._bodybytes = self._encode_body(self._body)
        self.hdr.length = len(self._bodybytes)
            
    def encode(self):
        """
        Returns a string.
        """
        if self._bodybytes is None:
            self.changed()
        return self.hdr.encode() + self._bodybytes
    
    def __repr__(self):
        if self._body is None:
            pstr = 'bodybytes=' + repr(self._bodybytes)
        else:
            pstr = ', '.join('%s=%r' % (k, v)
                             for k, v in self._body.iteritems())
        return "%s(%s)" % (self.__class__.__name__, pstr)


Fld = namedtuple('Fld', 'name reqd dflt')
    
def simplemsg(clsname, mtype, flds=[], typekey=False, docstr="",
              verbose=False):
    """
    Returns a new subclass of Msg.
    """
    args = ([fld.name for fld in flds if fld.reqd] +
            ["%s=%r" % (fld.name, fld.dflt) for fld in flds
             if not fld.reqd])
    argstr = ', '.join(args)
    if argstr:
        argstr = ', ' + argstr
    kvs = ', '.join("(%r, %s)" % (fld.name, fld.name) for fld in flds)
    if kvs:
        kvs = ', (' + kvs + ',)'
    if not docstr:
        docstr = "Subclass %s of Msg" % (clsname,)
    template = """class %(clsname)s(Msg):
        '''%(docstr)s'''
        type = %(mtype)r
        typekey = %(typekey)r
        
        def init(self%(argstr)s):
            return Msg.init(self%(kvs)s)""" % locals()
    if verbose:
        print template
        
    exec template
    return eval(clsname)
        
    # copied from namedtuple:
        
    # Execute the template string in a temporary namespace and
    # support tracing utilities by setting a value for frame.f_globals['__name__']
    namespace = dict(Msg=Msg, __name__='simplemsg_%s' % (clsname,))
    try:
        exec template in globals(), namespace
    except SyntaxError, e:
        raise SyntaxError(e.message + ':\n' + template)
    result = namespace[clsname]

    return result
    
    