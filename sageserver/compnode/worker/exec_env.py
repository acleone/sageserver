"""
The execution environment.
"""

from ast import parse as ast_parse
import logging
import os
from Queue import Queue
from time import time as _time, sleep as _sleep


import sageserver.msg as msg
from transforms import transform_source, transform_ast, assignhook
from queuefile import QueueFileOut, QueueFileIn
#from sageloader import SageLoader

class ExecEnv(object):

    def __init__(self, msgr):
        """
        Sets up this execution session's environment.
        """
        self._send_q = msgr.get_send_queue()
        
        msgr.recv_handlers.update({
            msg.STDIN: self._recv_Stdin,
            msg.GET_COMPLETIONS: self._recv_GetCompletions,
            msg.GET_DOC: self._recv_GetDoc,
            msg.GET_SOURCE: self._recv_GetSource,
        })

        self._log = logging.getLogger(
            "%s[pid=%s]" % (self.__class__.__name__, os.getpid()) )
        self._globals = {}

        self.MAIN_HANDLERS = {
            msg.EXEC_CELL: self._main_ExecCell,
            #msg.EXEC_INTERACT: self.exec_,
        }
            
        
        exec """\
import sys
import time

import sageserver.msg as msg

#from interacts.interacts import InteractManager
#_interact_manager = InteractManager()
#interact = _interact_manager.interact
""" in self._globals
        # keep a refence to these so they aren't deleted
        self._mod_sys = self._globals["sys"]
        self._mod_time = self._globals["time"]
        self._mod_msg = self._globals["msg"]
        #self._interact_manager = self._globals["_interact_manager"]
        del self._globals["sys"]
        del self._globals["time"]
        del self._globals["msg"]
        #del self._globals["InteractManager"]
        #del self._globals["_interact_manager"]

        # replace time.sleep with _fake_sleep
        self._mod_time.__sleep__ = self._mod_time.sleep
        self._mod_time.sleep = _fake_sleep

        self._globals["__displayhook__"] = self._mod_sys.displayhook
        self._globals["__assignhook__"] = assignhook

        #self._loader = SageLoader(sys=self._mod_sys, append=True,
        #       log=logging.getLogger("SageLoader[pid=%d]" % (os.getpid(),) ) )
        #b = self._globals["__builtins__"]
        #assert "__reload__" not in b
        #b["__reload__"] = b["reload"]
        #b["reload"] = self._loader.reload

    def _main_ExecCell(self, exec_msg):
        """
        Executes a multi-line block of code.
        """
        sid = exec_msg.hdr.sid
        send_q = self._send_q
        
        self._mod_msg._send_q = send_q
        self._mod_msg._exec_id = id
        
        self._stdout = QueueFileOut(send_q, msg.Stdout, sid)
        self._stderr = QueueFileOut(send_q, msg.Stderr, sid)
        self._stdin_q = Queue()
        self._stdin = QueueFileIn(self._stdin_q, send_q, sid,
                                  exec_msg['echo_stdin'])

        self._mod_sys.stdout = self._stdout
        self._mod_sys.stderr = self._stderr
        self._mod_sys.stdin = self._stdin

        #name = exec_msg["name", "__cell_%s__" % (id,))
        #mod = self._loader.new_module(name)
        #self._globals.update(mod.__dict__)
        fname = 'cell_%d.py' % (exec_msg['cid'],)

        try:
            # apply source and ast transformations
            source = transform_source(exec_msg, self._globals)
            
            # write to file so that introspection works
            f = open(fname, 'w')
            f.write(source)
            f.close()
            
            #self._loader.set_source(name, source)
            source_ast = ast_parse(source, filename=fname, mode='exec')
            source_ast = transform_ast(exec_msg, source_ast, source,
                                       self._globals)
            # compile and execute
            code = compile(source_ast, fname, 'exec')
            #self._loader.set_code(name, code)
            exec_msg['transformed_source'] = source
            self._globals["__exec_msg__"] = exec_msg
            exec code in self._globals
        except:
            send_q.put(_get_except_msg(exec_msg))
        finally:
            send_q.put(msg.Done().as_reply_to(exec_msg))

    @property
    def waiting_on_stdin(self):
        return hasattr(self, '_stdin_q') and self._stdin.waiting

    def interrupt_stdin(self):
        if self.waiting_on_stdin:
            self._stdin_q.put(msg.Interrupt())
        return False
    

    def _recv_Stdin(self, m):
        if hasattr(self, '_stdin_q'):
            self._stdin_q.put(m)
        else:
            self._log.warning("[recv_Stdin] unhandled Stdin (%r)!", m)
        return None

    def _recv_GetCompletions(self, m):
        """
        Returns a :class:`msg.Completions` message instance.
        """
        return (msg.Completions(m['text'], m['format'],
                                _complete(m['text'], self._globals))
                    .as_reply_to(m))

    def _recv_GetDoc(self, m):
        """
        Returns a :class:`msg.Doc` or :class:`msg.NotDone` instance.
        """
        from inspect import getdoc
        objt = _get_obj(m['object'], self._globals)
        doc = None
        rm = msg.Doc(m['object'], m['format']).as_reply_to(m)
        if objt:
            doc = getdoc(objt[0])
            if m['format'] == 'TEXT':
                rm['doc'] = doc
            else:
                self._log.error("Unknown doc format %r", m['format'])
        self._msgr.sendmsg(rm)
    
    def _recv_GetSource(self, m):
        """
        Returns a :class:`msg.Source` or :class:`msg.NotDone` instance.
        """
        from inspect import getsource
        objt = _get_obj(m['object'], self._globals)
        rm = (msg.Source(m['object'], m['format'], obj_found=bool(objt))
                    .as_reply_to(m))
        try:
            if objt:
                source = getsource(objt[0])
                if source:
                    rm['source'] = source
        except IOError:
            pass
        except TypeError: # maybe a builtin?
            if m['object'] in self._globals['__builtins__']:
                rm['source'] = '(builtin object %r)' % (m['object'],)
        self._msgr.sendmsg(rm)


def _fake_sleep(t, sleep_time=0.25):
    """
    Replaces a long ``time.sleep(t)`` with repeated calls to
    ``time.sleep(0.25)``, because ``time.sleep(t)`` is uninterruptable with
    ``thread.interrupt_main()``.
    """
    while t > sleep_time:
        _sleep(sleep_time)
        t -= sleep_time
    _sleep(t)


def _get_except_msg(exec_msg):
    """
    Returns either:
        - `msg.Except` if exec_msg.dict.except_msg is True, or
        - `msg.Stderr` if exec_msg.dict.except_msg is False.
    
    EXAMPLES:
        >>> def a():
        ...     b()
        >>> def b():
        ...     raise ValueError('ack!')
        >>> try:
        ...     a()
        ... except:
        ...     e_stderr = _get_except_msg(msg.Exec())
        ...     e_except = _get_except_msg(msg.Exec(opts={'except_msg':True}))
        >>> isinstance(e_stderr, msg.Stderr)
        True
        >>> isinstance(e_except, msg.Except)
        True
        >>> e_stderr.bytes == e_except.bytes
        True
        >>> print e_except.bytes, #doctest:+ELLIPSIS
        Traceback (most recent call last):
          File "...", line 2, in a
            b()
          File "...", line 2, in b
            raise ValueError('ack!')
        ValueError: ack!
        >>> e_except.info['etype']
        'ValueError'
        >>> e_except.info['value']
        'ack!'
    """
    from sys import exc_info
    import traceback
    etype, value, tb = exc_info()
    stack_list = traceback.extract_tb(tb)
    
    s = b''.join(['Traceback (most recent call last):\n'] + 
                   traceback.format_list(stack_list) +
                   traceback.format_exception_only(etype, value) )
    if not exec_msg['except_msg']:
        return msg.Stderr(s, _hsid=exec_msg.hdr.sid)
        
    syntax = None
    try:
        if issubclass(etype, SyntaxError):
            _, syntax = value.args
        valuestr = str(value)

        return msg.Except(stderr=s, stack=stack_list, etype=etype.__name__,
                          value=valuestr, syntax=syntax,
                          _hsid=exec_msg.hdr.sid)
    except:
        pass
    return msg.Except(stderr=s, _hsid=exec_msg.hdr.sid)


def _complete(text, globals_):
    """
    Gets the completions for text from the exec globals.  Returns a sorted
    list.
    """
    from rlcompleter import Completer
    ctr = Completer(globals_)
    i = 0
    comps = []
    while 1:
        c = ctr.complete(text, i)
        if c is None:
            break
        comps.append(c)
        i += 1
    comps = tuple(sorted(frozenset(comps)))
    return comps


def _get_obj(text, globals_):
    """
    Gets the object for text from the exec globals.  Returns ``()`` if the
    object couldn't be found or ``(obj,)`` if it was.
    """
    # TODO: fix this hack to see if an object exists
    comps = _complete(text, globals_)
    if not (text in comps or text + '(' in comps):
        return ()
    try:
        obj = eval(text, globals_)
    except SyntaxError:
        return ()
    return (obj,)

