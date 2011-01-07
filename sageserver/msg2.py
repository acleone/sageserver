"""

This module defines the message format between:

1. (In the computation node) Manager Process to Worker Process.

The general structure of a message over the wire is::

   0         16          32       
   ------------------------
   |   type   |flags| sum |
   ------------------------
   |  length              |
   ------------------------
   | length octets        |
   | of data follow       |

Note: all integers are little-endian encoded.
  
* type {uint16_t} -- uint16_t - message type.
* flags {uint8_t} -- depends on context.
* sum {uint8_t} -- sum of all octets in the header (consider the sum octet to
                   be zero), then bitwise inverted (xor 0xff)
* length {uint32_t} -- number of octets of data that follow.
                       
In python struct format syntax, the header is represented as "<HBBI".

The sum is calculated as below::

    struct header {
        uint16_t type;
        uint8_t flags;
        uint8_t sum;
        uint32_t length;
    }
    
    /** type, flags, length must be set. */
    void set_sum(struct header *hdr) {
        hdr->sum = ((hdr->type >> 8) + (hdr->type & 0xff)
                    + hdr->flags
                    + (hdr->length >> 24) + ((hdr->length >> 16) & 0xff)
                    + ((hdr->length >> 8) & 0xff) + (hdr->length & 0xff)
                   ) ^ 0xff
    }

"""
from collections import namedtuple
import json


"""
Tuple for converting a message type integer into a string.

.. note:: Message type integers start at 1.  The zero element is invalid and is
   ``None``.
"""

TYPE_DICT = {}
"""Dictionary of integer message types to message classes."""

def _init_type_consts():
    """
    Adds all the message classes to the msg module, eg msg.Shutdown.
    """
    if __name__ != '__main__':
        import msg
        for i in range(1, len(TYPE_STRS)):
            setattr(msg, TYPE_STRS[i], i)
    else:
        for i in range(1, len(TYPE_STRS)):
            globals()[TYPE_STRS[i]] = i

_init_type_consts()


class MsgHeader(object):
    """
    Representation of a message header.
    
    """
    
    __slots__ = ("type", "flags", "length")
    
    def __init__(self):

    
class Msg(object):
    """
    Base class for all messages.

    :cvar type: unsigned integer - the message's type.
    
    :ivar end_bytes: the last bytes in the message (after any message specific
        fields).
    """
    __slots__ = ('end_bytes',)
    type = 0

    def __init__(self, end_bytes=''):
        self.end_bytes = _ensure_utf8(end_bytes)

    def encode(self):
        """
        :returns: this message encoded as a byte string.  See :func:`encode`.
        """
        return encode(self.type, self.end_bytes)

    @classmethod
    def decode(cls, bytes):
        """
        :param bytes: byte string that is the message body (type bytes and
            length bytes are not included).
        :returns: new message instance.
        """
        return cls(bytes)

    def __repr__(self):        
        end_bytes = getattr(self, self.__slots__[0])
        return "%s(%s)" % (self.__class__.__name__,
                           ', '.join(([repr(end_bytes)] if end_bytes else []) +
                                     ["%s=%r" % (n, getattr(self, n))
                                      for n in self.__slots__[1:]]) )
        

    def json_dict(self):
        """
        Returns a dict of this object suitable for encoding with JSON.
        """
        d = dict([(n, getattr(self, n)) for n in self.__slots__])
        d["type"] = self.__class__.__name__
        return d


###############################################################################
#                     Execution Requests
###############################################################################

class Exec(MsgWithDict):
    """
    Something for the worker to exec.

    :cvar type: :obj:`EXEC`.
    
    :ivar end_bytes: the utf-8 encoded representation of the source code to
        execute.
    :ivar dict: a dict of options. Defaults to :attr:`Exec.DEFAULT_DICT`.
    :ivar id: a numeric id >= 0.
    
    Available execution options (:attr:`dict`):
    
    * :attr:`name` -- the :obj:`__name__` to use when executing the code.
      *Optional: defaults to* ``'__cell_%d__' % (id,)``.
    * :attr:`inline_stdin` -- send :class:`Stdin`'s back when returned
      from :func:`sys.stdin.read()`. *Optional: defaults to* ``True``.
    * :attr:`except_msg` -- *Optional: defaults to* ``False``:
    
      * ``True`` -- send exceptions as :class:`Except` messages.
      * ``False`` -- print a traceback to stderr.
      
    * :attr:`displayhook` -- *Optional: defaults to* ``'last'``:

      * ``'last'`` -- prints the last expression if not ``None``, like the
        standard command-line interpreter.
      * ``'all'`` -- prints all expressions if not ``None``.
      * ``None``.
      
    * :attr:`assignhook` -- *Optional: defaults to* ``None``:
    
      * ``'all'`` -- print all assignments, ala MATLAB::
            
            >>> a = 2 + 2 #doctest:+SKIP
            a = 4
            
      * ``None``.

    * :attr:`print_ast` -- print out the abstract syntax tree after all
      source and ast transformations.  *Optional: defaults to* ``False``.
    * :attr:`time` -- print timing information to stdout.  *Optional: defaults
      to* ``False``.
    
    :cvar DEFAULT_DICT:
    
        >>> from pprint import PrettyPrinter as PP
        >>> PP().pprint(Exec.DEFAULT_DICT)
        {'assignhook': None,
         'displayhook': 'last',
         'except_msg': False,
         'inline_stdin': True,
         'name': None,
         'time': False,
         'timeit': False}
    """
    __slots__ = MsgWithDict.__slots__
    DEFAULT_DICT = {
        'name': None,
        'inline_stdin': True,
        'except_msg': False,
        'displayhook': 'last',
        'assignhook': None,
        'print_ast': False,
        'time': False,
        'timeit': False,
    }
    type = EXEC

    def __init__(self, end_bytes=b'', dict={}, id=0):
        MsgWithDict.__init__(self, end_bytes, dict, id)
        if self.dict['name'] is None:
            self.dict['name'] = '__cell_%s__' % (id,)


class ExecInteract(MsgWithDict):
    """
    An interact execution request.
    
    :cvar type: :obj:`EXEC_INTERACT`.
    
    :ivar end_bytes: the utf-8 encoded interact name.
    :ivar dict: a dict of options. Defaults to :attr:`ExecInteract.DEFAULT_DICT`.
    :ivar id: a numeric id >= 0.
    """
    __slots__ = MsgWithDict.__slots__
    type = EXEC_INTERACT

class Eval(MsgWithDict):
    """
    :cvar type: :obj:`EVAL`.
    
    :ivar end_bytes: the utf-8 encoded representation of the source code to
        eval.
    :ivar dict: a dict of options. Defaults to :attr:`Eval.DEFAULT_DICT`.
    :ivar id: a numeric id >= 0.
    """
    __slots__ = MsgWithDict.__slots__
    type = EVAL


###############################################################################
#                    Execution Output
###############################################################################

class Stdout(MsgWithId):
    """
    The raw bytes from stdout of an ``exec``-ed computation.  The :attr:`id`
    will be the same as the :class:`Exec` message.
    """
    __slots__ = MsgWithId.__slots__
    type = STDOUT


class Stderr(MsgWithId):
    """
    The raw bytes from stderr of an ``exec``-ed computation.  The :attr:`id`
    will be the same as the :class:`Exec` message.
    """
    __slots__ = MsgWithId.__slots__
    type = STDERR


class Stdin(MsgWithId):
    """
    Write something to the exec's stdin.  To send ``EOF``, send a
    :class:`Stdin` with an empty bytes string.
    
    .. note::
        
        If ``Exec.opts.inline_stdin``, then there will be a response of
        :class:`Stdin` from the worker whenever ``stdin.read()`` returns, with
        :attr:`id` equal to the :attr:`id` of the :class:`Exec`.  If
        ``stdin.read()`` returned because of an ``EOF`` or shutdown, then
        the response will also include an empty :class:`Stdin`.
    """
    __slots__ = MsgWithId.__slots__
    type = STDIN


class NeedStdin(MsgWithId):
    """
    Sent by the worker if the exec called ``stdin.read()`` and there isn't any
    :class:`Stdin` bytes left to send.  The :attr:`id` will be
    the same as the :class:`Exec` message.

    :attr:`end_bytes` will the ascii encoded integer of how many bytes were
      requested.
    """
    __slots__ = MsgWithId.__slots__
    type = NEED_STDIN


class Except(MsgWithDict):
    """
    Information about an exception generated from a :class:`Exec` with
    ``dict.except_msg = True``.

    :ivar end_bytes: the utf-8 encoded representation of the source code to
        execute.
    :ivar dict: a dict of info.
    :ivar id: a numeric id >= 0.
    
    :attr:`dict` has keys:
    
    * :attr:`stack` -- list of 4-tuples: ``(filename, lineno, func_name, text)``
    * :attr:`etype` -- Exception class name
    * :attr:`value` -- Exception value
    * :attr:`syntax` -- if the Exception is a :exc:`SyntaxError` or subclass,
      then ``(filename, lineno, offset, badline)``, otherwise ``None``.

    """
    __slots__ = MsgWithDict.__slots__
    type = EXCEPT

    def __init__(self, bytes=b'', dict={}, id=0):
        MsgWithId.__init__(self, bytes, id)
        self.dict = dict


class Done(MsgWithId):
    """
    Sent after a :class:`Exec` is finished and in response to a
    :class:`IsDone`, with the same :attr:`id` that the message is replying to.
    :attr:`bytes` is always empty.
    """
    __slots__ = MsgWithId.__slots__
    type = DONE


class Interact(MsgWithDict):
    """
    An interact canvas.
    """
    __slots__ = MsgWithDict.__slots__
    type = INTERACT


class Latex(MsgWithId):
    """
    A latex string.
    """
    __slots__ = MsgWithId.__slots__
    type = LATEX


class Html(MsgWithId):
    """
    An html string.
    """
    __slots__ = MsgWithId.__slots__
    type = HTML


class Javascript(MsgWithId):
    """
    A javascript string to execute.
    """
    __slots__ = MsgWithId.__slots__
    type = JAVASCRIPT


class Json(MsgWithId):
    """
    A Json string.
    """
    __slots__ = MsgWithId.__slots__
    type = JSON


###############################################################################
#                  Commands
###############################################################################

class Shutdown(Msg):
    """
    Shutdown the worker.  The worker will attempt to kill itself if it 
    can't interrupt the currently running computation.  :attr:`end_bytes` is
    always empty.
    """
    __slots__ = Msg.__slots__
    type = SHUTDOWN


class Interrupt(MsgWithId):
    """
    Interrupt the worker.  Possible Responses (with id set to the
    :class:`Interrupt` id):
    
    * :class:`Yes` -- interrupt was done successfully.
    * :class:`No` -- could not interrupt.
    """
    __slots__ = MsgWithId.__slots__
    type = INTERRUPT


class IsComputing(MsgWithId):
    """
    Checks if the worker is currently computing.  Possible responses
    (with :attr:`id` set to the :class:`IsComputing` :attr:`id`):
    
    * :class:`Yes`
    * :class:`No`
    """
    __slots__ = MsgWithId.__slots__
    type = IS_COMPUTING


class GetStatus(MsgWithId):
    """
    Requests the status of the worker.
    """
    __slots__ = MsgWithId.__slots__
    type = GET_STATUS


class Status(MsgWithDict):
    """
    A dict of information about the worker.
    """
    __slots__ = MsgWithId.__slots__
    type = STATUS


class GetFile(MsgWithId):
    """
    Gets the specified file.

    The response will be a series of :class:`File` messages followed by a
    :class:`Done` message.  All messages will have :attr:`id` set to the
    :class:`GetFile` :attr:`id`.
    """
    __slots__ = MsgWithId.__slots__
    type = GET_FILE

class File(MsgWithId):
    __slots__ = MsgWithId.__slots__
    type = FILE


################################################################################
#                             Introspection
################################################################################

class GetCompletions(MsgWithId):
    """
    Get all the completions of text with rlcompleter.  The response will be a
    :class:`Completions` message.
    """
    __slots__ = MsgWithId.__slots__
    type = GET_COMPLETIONS


class Completions(MsgWithId):
    """
    The response to a :class:`GetCompletions` message.
    """
    __slots__ = MsgWithId.__slots__
    type = COMPLETIONS


class GetDoc(MsgWithId):
    """
    Gets the docstring for the specified text.  The response will be a
    :class:`Doc` message if documentation was found, otherwise a
    :class:`NotDone`.
    """
    __slots__ = MsgWithId.__slots__
    type = GET_DOC


class Doc(MsgWithId):
    """
    The response to a :class:`GetDoc` message.
    """
    __slots__ = MsgWithId.__slots__
    type = DOC


class GetSource(MsgWithId):
    """
    Gets the source of the specified text.  The response will be a
    :class:`Source` message if the source was found, otherwise a
    :class:`NotDone`.
    """
    __slots__ = MsgWithId.__slots__
    type = GET_SOURCE


class Source(MsgWithId):
    """
    The response to a :class:`GetSource` message.
    """
    __slots__ = MsgWithId.__slots__
    type = SOURCE


class Yes(MsgWithId):
    __slots__ = MsgWithId.__slots__
    type = YES


class No(MsgWithId):
    __slots__ = MsgWithId.__slots__
    type = NO


###############################################################################
#                      Message Parsers
###############################################################################
    
class Fps:
    """
    FeedParserState.
    """
    
    NEED_TYPE = 0
    """Just finished parsing a message (or just initialized)."""
    
    NEED_LENGTH = 1
    """Still parsing the message length."""
    
    NEED_BYTES = 2
    """Still buffering the message body."""


class FeedParser(object):
    """
    Decodes a binary stream of messages.  Useful for non-blocking io.
    """
    __slots__ = ('_state', '_type', '_length', '_bytes')
    
    def __init__(self):
        self.reset()

    @property
    def state(self):
        """
        Current state of the parser.  See :class:`Fps` for states.

        EXAMPLES::
        
            >>> f = FeedParser()
            >>> f.state == Fps.NEED_TYPE
            True
            >>> f.feed(vlq_encode(SHUTDOWN)); f.state == Fps.NEED_LENGTH
            []
            True
            >>> f.feed('\\x00'); f.state == Fps.NEED_TYPE
            [(1, '')]
            True
            >>> f.feed(vlq_encode(INTERRUPT) + b'\\x01')
            []
            >>> f.state == Fps.NEED_BYTES
            []
        """
        return self._state

    def feed(self, bytes, decode=True):
        """
        Add more bytes to the parser.

        If `decode` is ``True`` (the default), Returns a list of named tuples.

        If `decode` is ``False``, returns a list of two-tuples,
        ``(type int, byte string)``.

        EXAMPLES::
        
            >>> f = FeedParser()
            >>> f.feed(encode(SHUTDOWN, ''))
            [(SHUTDOWN, '')]
            >>> bytes = encode(STDOUT, 'Hello World!')
            >>> f.feed(bytes[0])
            []
            >>> [f.feed(b) for b in bytes[1:-1]] == [[]] * (len(bytes) - 2)
            True
            >>> f.feed(bytes[-1])
            [(STDOUT, 'Hello World!')]
            >>> f.feed(encode(INTERRUPT, 'hi') + encode(SHUTDOWN, ''))
            [(INTERRUPT, 'hi'), (SHUTDOWN, '')]
        """
        i = 0
        L = len(bytes)
        vdb = self._vlq_decode_byte
        msgs = []
        while i < L:
            if self._state == Fps.NEED_TYPE:
                self._type, more = vdb(bytes[i], self._type)
                i += 1
                if not more:
                    self._state = Fps.NEED_LENGTH
                    self._length = 0
                    
            elif self._state == Fps.NEED_LENGTH:
                self._length, more = vdb(bytes[i], self._length)
                i += 1
                if not more:
                    if self._length == 0:
                        msgs.append(self._decode(decode, self._type, b''))
                        self.reset()
                        continue
                    self._state = Fps.NEED_BYTES
                    self._bytes = []
                    
            elif self._state == Fps.NEED_BYTES:
                # self._length is number of bytes remaining
                end_i = min(L, i + self._length)
                self._bytes.append(bytes[i:end_i])
                self._length -= end_i - i
                i = end_i
                if self._length == 0:
                    msgs.append(self._decode(decode, self._type,
                                             b''.join(self._bytes)) )
                    del self._bytes # to release all the string parts to the gc
                    self.reset()
                    continue
                
        return msgs

    def _decode(self, should_decode, type, bytes):
        if not should_decode:
            return (type, bytes)
        # else: return a message class instance
        cls = TYPE_DICT.get(type, None)
        if cls is None:
            return Unrecognized(bytes, type, len(bytes), '')
        try:
            return cls.decode(bytes)
        except:
            from traceback import format_exc
            return DecodeError(bytes, type, len(bytes), format_exc())
        
    def _vlq_decode_byte(self, byte_char, var):
        """
        Returns ``(new_var, more)``.
        """
        byte = ord(byte_char)
        var = (var << 7) | (byte & 0x7f)
        return (var, bool(byte & 0x80))

    def reset(self):
        """
        Resets the parser.
        """
        self._state = Fps.NEED_TYPE
        self._type = 0
        if hasattr(self, '_bytes'):
            del self._bytes


###############################################################################
#                            Misc Functions
###############################################################################

def encode(type, bytes):
    """
    Encodes a message in the binary encoding described in
    :ref:`binary-encoding`.

    :param type: unsigned integer type.
    :param bytes: the sequence of bytes that is the message body.
    :returns: A byte string of the encoded message.

    Examples::

        >>> encode(1, 'Hello World!')
        '\\x01\\x0cHello World!'
        >>> encode(2, '')
        '\\x02\\x00'
    """
    return b''.join( (vlq_encode(type), vlq_encode(len(bytes)), bytes) )


def vlq_encode(i):
    """
    Encodes an integer i >= 0 in a variable number of bytes [#]_.
    Opposite of :func:`vlq_decode`.

    :param i: unsigned integer (``i >= 0``) to encode.
    :raises: :exc:`ValueError` if ``i < 0``.

    EXAMPLES::
    
        >>> vlq_encode(0) == '\\x00'
        True
        >>> vlq_encode(0x80) == '\\x81\\x00'
        True
        
    .. [#] http://en.wikipedia.org/wiki/Variable-length_quantity
    """
    if i < 0:
        raise ValueError("i must be >= 0! (%r)" % (i,))
    r = chr(i & 0x7f)
    while i > 0x7f:
        i >>= 7
        r = chr(0x80 | (i & 0x7f)) + r
    return r


def vlq_decode(bytes, i=0):
    r"""
    Opposite of :func:`vlq_encode`.

    :param bytes: a sequence of bytes to decode.
    :param i: starting index.
    :returns: (decoded_int, i) where decoded_int is >= 0 and i is the index
        after all the vlq bytes.
    
    :raises: :exc:`ValueError` if we ran out of bytes.

    EXAMPLES::
    
        >>> vlq_decode('\x00') == (0, 1)
        True
        >>> vlq_decode('\x81\x00') == (0x80, 2)
        True
        >>> vlq_decode('\x81') #doctest:+ELLIPSIS
        Traceback (most recent call last):
        ...
        ValueError: Not enough bytes!
    """
    r = 0
    bi = 0x80
    while i < len(bytes):
        bi = ord(bytes[i])
        i += 1
        r = (r << 7) | (bi & 0x7f)
        if not bi & 0x80:
            break
    else:
        if bi & 0x80:
            raise ValueError("Not enough bytes!")
    return (r, i)

def utf8_str_encode(s):
    r"""
    Encodes a (unicode) string by encoding in utf-8 and appending a null byte.
    Opposite of :func:`utf8_str_decode`.

    :param s: a string
    :returns: a byte string
    :raises: :exc:`ValueError` if `s` has any null bytes.

    EXAMPLES::
    
        >>> utf8_str_encode('hi')
        'hi\x00'
        >>> utf8_str_encode(u'\u0100')
        '\xc4\x80\x00'
    """
    if not isinstance(s, basestring):
        s = str(s)
    if isinstance(s, unicode):
        s = s.encode('utf-8', 'replace')
    if b'\x00' in s:
        raise ValueError("String contains a null byte!")
    return s + b'\x00'

def utf8_str_decode(bytes, i=0):
    r"""
    Opposite of :func:`utf8_str_encode`.

    :param bytes: the sequence of bytes to decode
    :param i: [default: 0] starting index
    :returns: (str, i) where str is a unicode instance and i is the index
        after the null byte.
    
    :raises: :exc:`ValueError` if there were no null bytes in `bytes`.

    EXAMPLES::
    
        >>> utf8_str_decode('\x00') == ('', 1)
        True
        >>> utf8_str_decode('a\x00') == ('a', 2)
        True
        >>> utf8_str_decode('\xc4\x80\x00') == (u'\u0100', 3)
        True
        >>> utf8_str_decode('asdf') #doctest:+ELLIPSIS
        Traceback (most recent call last):
        ...
        ValueError: No null byte!
    """
    end_i = bytes.find(b'\x00', i)
    if end_i == -1:
        raise ValueError('No null byte!')
    return (bytes[i:end_i].decode('utf-8', 'replace'), end_i + 1)


def _ensure_utf8(s):
    if isinstance(s, unicode):
        return s.encode('utf-8', 'replace')
    return s


COMBINABLE = (STDOUT, STDERR)

def combine_and_encode(msgs):
    lastm = msgs[0]
    encoded = []
    i = 1
    while i < len(msgs):
        m = msgs[i]
        i += 1
        if lastm.type == m.type and lastm.id == m.id and m.type in COMBINABLE:
            lastm = lastm + m
        else:
            encoded.append(lastm.encode())
            lastm = m
    encoded.append(lastm.encode())
    return b''.join(encoded)


_exec_id = 0
"""Set by :class:`ExecEnv` for sending things."""

_send_q = None
"""Set by :class:`ExecEnv` for sending things."""

def send(m):
    if not isinstance(m, MsgWithId):
        raise ValueError("Message must be a subclass instance of MsgWithId! "
                         "Got %r!" % (m,))
    m.id = _exec_id
    _send_q.put(m)


def _init_type_dict():
    TYPE_DICT.clear()
    for i in range(1, len(TYPE_STRS)):
        t = TYPE_STRS[i]
        class_name = t.replace('_', ' ').title().replace(' ', '')
        if class_name not in globals():
            raise RuntimeError("%r is not a class name for %r!" % (
                                 class_name, t))
        TYPE_DICT[i] = globals()[class_name]

_init_type_dict()

if __name__ == '__main__':
    import doctest
    doctest.testmod()