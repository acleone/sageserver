"""
Generates the python code for messages in sageserver/msg/...
"""

from bson import SON, _dict_to_bson # to make sure the user has pymongo

class Fld(object):
    """
    A field is a component in the body of the message, retrieved by
    msg['fieldname'].  This class helps create message classes that are
    nicely documented.
    """
    
    def __init__(self, name, required=True, default=None, doc=None):
        self.name = name
        self.required = required
        self.default = default
        self.doc = doc
        
class MsgClass(object):
    
    def __init__(self, clsname, typename, typeval, flds=[], doc=None):
        self.clsname = clsname
        self.typename = typename
        self.typeval = typeval
        self.flds = flds
        self.doc = doc
        
    def gen_code(self):
        """
        Returns a string that is the source code for the class.
        """
        flddocs = []
        for fld in self.flds:
            doc = '{fld.name} -- {fld.doc}'.format(fld=fld)
            if not fld.required:
                doc += ' (default: {fld.default})'.format(fld=fld)
            flddocs.append(doc)
            
        flddocs = '\n\t\t'.join(flddocs)
        
        if self.doc:
            docstr = '\n\t' + self.doc + '\n\t'
        else:
            docstr = '\n\t{self.clsname} Message\n\t'.format(**locals())
        if flddocs:
            docstr += '\n\tMessage Arguments:\n\t\t' + flddocs + '\n\t'
            
        args = (['self'] +
                [fld.name for fld in self.flds if fld.required] +
                ["%s=%r" % (fld.name, fld.default) for fld in self.flds
                    if not fld.required])
        argsstr = ', '.join(args)
        
        body_inserts = []
        for fld in self.flds:
            body_inserts.append(
                    'self[{fld.name!r}] = {fld.name}'.format(fld=fld))
            
        body_inserts = '\n\t\t'.join(body_inserts)
        
        template = '''class {self.clsname}(SON):
    """{docstr}"""
    type = {self.typeval!r}
    
    def __init__({argsstr}):
        SON.__init__(self)
        self.hdr = Hdr({self.typeval!r}, 0, 0, 0)
        self.type = {self.typeval!r}
        self['t'] = {self.typeval!r}
        {body_inserts}
        
    def encode(self):
        """
        Returns the encoded representation of this message.
        """
        bodybytes = _dict_to_bson(self, False)
        self.hdr.length = len(bodybytes)
        return self.hdr.encode() + bodybytes
        '''.format(**locals()).replace('\t', '    ')
        
        return template


def generate_cls_file(path, msgclasses):
    """
    Writes the message class code to path.
    
    Returns a list of strings 'MSGTYPE = MSGVAL' to be put into msgints.py
    """
    
    # some simple checking to make sure that each message has a unique typeval
    typevals = {}
    error = False
    for msgcls in msgclasses:
        if msgcls.typeval in typevals:
            print "Error: %r has the same typeval as %r!" % (
                    msgcls.clsname, typevals[msgcls.typeval])
            error = True
        else:
            typevals[msgcls.typeval] = msgcls.clsname
    if error:
        return None
    
    print "Generating", repr(path)
    cls_strs = '\n\n'.join(msgcls.gen_code() for msgcls in msgclasses)
    template = """
###############################################################################
# THIS FILE IS GENERATED BY msg_generator/generate.py!!!                      #
# *** DO NOT EDIT DIRECTLY ***                                                #
###############################################################################

from bson import SON, _dict_to_bson

from hdr import Hdr

{cls_strs}
""".format(**locals())

    f = open(path, 'w')
    f.write(template)
    f.close()
    
    return ['%s = %r' % (msgcls.typename, msgcls.typeval) for msgcls
             in msgclasses]
 
def main():
    import sys
    from os.path import dirname, join, isdir
    import request_msgs
    import output_msgs
    msgdir = join(dirname(__file__), '..', 'sageserver', 'msg')
    if not isdir(msgdir):
        print "Error: %r is not a directory (should be sageserver/msg/)" % (
                                                                    msgdir,)
        return 1
        
    reqints = generate_cls_file(join(msgdir, 'request_msgs.py'),
                                request_msgs.msgs)
    if reqints is None:
        return 1
    outints = generate_cls_file(join(msgdir, 'output_msgs.py'),
                                output_msgs.msgs)
    if outints is None:
        return 1

    reqints = '\n'.join(reqints)
    outints = '\n'.join(outints)

    template = """
###############################################################################
# THIS FILE IS GENERATED BY msg_generator/generate.py!!!                      #
# *** DO NOT EDIT DIRECTLY ***                                                #
###############################################################################

'''
Request message types
'''

{reqints}


'''
Output message types
'''

{outints}
""".format(**locals())

    typespath = join(msgdir, 'msgtypes.py')
    print "Generating", repr(typespath)
    f = open(typespath, 'w')
    f.write(template)
    f.close()
    
    return 0


if __name__ == '__main__':
    main()
        
    