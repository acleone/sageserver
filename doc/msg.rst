:mod:`msg` --- Messages
***********************

.. automodule:: sageserver.msg

:class:`Msg` Classes
====================

Base Classes
------------

The base class for all messages is the :class:`Msg` class:

:class:`Msg`
^^^^^^^^^^^^

.. autoclass:: Msg
    :members: encode, decode, dict
    
:class:`MsgWithId`
^^^^^^^^^^^^^^^^^^

Most messages subclass :class:`MsgWithId`, which also provides an :attr:`id`
field so that the manager can keep track of responses.

.. autoclass:: MsgWithId

Requests
--------

These are generally sent to the worker process.

:class:`Shutdown`
^^^^^^^^^^^^^^^^^

.. autoclass:: Shutdown

:class:`Interrupt`
^^^^^^^^^^^^^^^^^^

.. autoclass:: Interrupt

:class:`IsDone`
^^^^^^^^^^^^^^^

.. autoclass:: IsDone

:class:`Exec`
^^^^^^^^^^^^^

.. autoclass:: Exec

:class:`Stdin`
^^^^^^^^^^^^^^

.. autoclass:: Stdin

:class:`GetCompletions`
^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: GetCompletions

:class:`GetDoc`
^^^^^^^^^^^^^^^

.. autoclass:: GetDoc

:class:`GetSource`
^^^^^^^^^^^^^^^^^^

.. autoclass:: GetSource

:class:`InteractExec`
^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: InteractExec

Responses
---------

These are generally sent to the manager process.

:class:`Done`
^^^^^^^^^^^^^

.. autoclass:: Done

:class:`NotDone`
^^^^^^^^^^^^^^^^

.. autoclass:: NotDone

:class:`Stdout`
^^^^^^^^^^^^^^^

.. autoclass:: Stdout

:class:`Stderr`
^^^^^^^^^^^^^^^

.. autoclass:: Stderr

:class:`NeedStdin`
^^^^^^^^^^^^^^^^^^

.. autoclass:: NeedStdin

:class:`Except`
^^^^^^^^^^^^^^^

.. autoclass:: Except

:class:`Completions`
^^^^^^^^^^^^^^^^^^^^

.. autoclass:: Completions

:class:`Doc`
^^^^^^^^^^^^

.. autoclass:: Doc

:class:`Source`
^^^^^^^^^^^^^^^

.. autoclass:: Source

:class:`InteractCanvas`
^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: InteractCanvas

:class:`Error`
^^^^^^^^^^^^^^

.. autoclass:: Error

Message Parsing
===============

:class:`FeedParser` --- parse messages a few bytes at a time
------------------------------------------------------------

.. autoclass:: FeedParser
    :members:
    
.. autoclass:: Fps
    :members: NEED_TYPE, NEED_LENGTH, NEED_BYTES

.. _binary-encoding:

Binary Encoding
===============

All messages have the form::

    --------------------------------------------------------
    |  1 byte: msg_type  |  n bytes: len(bytes)  |  bytes  |
    --------------------------------------------------------

where:

* :attr:`msg_type` -- message type byte, usually uppercase ascii for a
  command and lowercase for a response.
* :attr:`len(bytes)` -- a variable-length encoded unsigned integer (highest
  bit set means another byte of the integer follows - see
  :func:`vlq_encode` and :func:`vlq_decode`).  This is the number of bytes
  following.
* :attr:`bytes` -- a sequence of bytes with length equal to `len(bytes)`

.. seealso::
    
    :func:`msg_encode`
        A utility function that encodes a message.

Examples
--------

The simplest message defined is the :class:`Shutdown` message, which tells
the worker process to shutdown.  It is an empty message with no :attr:`bytes`,
so the entire message is two bytes: the :attr:`msg_type` byte ('S' for
Shutdown) and a zero byte that means that zero bytes follow::

    >>> from msg import *
    >>> Shutdown().encode()
    'S\x00'
    
Another simple message is a :class:`Stdout` message, which now has a message
body:

* :attr:`id` -- an unsigned integer (``i >= 0``) that is used by the manager
  to differentiate between different execution request's output.
* :attr:`bytes` -- the bytes written when something executing calls
  :func:`sys.stdout.write`.
  
::

    >>> from msg import *
    >>> Stdout('Hello World!', id=7).encode()
    'o\r\x07Hello World!'
    
Utility Functions
=================

.. autofunction:: msg_encode

.. autofunction:: vlq_encode

.. autofunction:: vlq_decode

.. autofunction:: utf8_str_encode

.. autofunction:: utf8_str_decode
