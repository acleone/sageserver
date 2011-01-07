"""
Move most of the interact stuff into javascript.

The decorator adds an InteractCanvas to the output

[
    Stdout('Hello World!\n'),
    Interact([
        InputBox(asjfasfjasfdkjasf)
        Selector(items=[...])
        ColorPicker(asdflf
        AxesPicker(...)
    ])
"""

from inspect import isroutine, getargspec
from sys import displayhook

from control import Control
import msg

__all__ = ('interact',)

class InteractManager(object):
    def __init__(self):
        self._interacts = {}

    def interact(self, *args, **kwargs):
        """
        If the interact decorator is called without parameters, then
        use the defaults.
        """
        if not kwargs and len(args) == 1 and isroutine(args[0]):
            # empty decorator, f = args[0]
            i = InteractDecorator(self)
            return i(args[0])
        else:
            # decorator with params
            return InteractDecorator(self, *args, **kwargs)
        
    def add(self, opts, f, controls):

        id = repr(f)
        iobj = {
            'id': id,
            'controls': [c.json_dict() for c in controls]
        }
        iobj.update(opts)
        self._interacts[id] = (f, controls)
        msg.send(msg.Interact(dict=iobj))

    def eval(self, id, control_vals, displayhook):
        f, controls = self._interacts[id]
        assert len(controls) == len(control_vals)
        displayhook(f(*[c.eval(v) for c, v in zip(controls, control_vals)]))
        

        
class InteractDecorator(object):
    """
    :obj:`DEFAULT_OPTS`:
    
    * :attr:`update_timeout` -- the timeout after a change to re-evaluate the
      interact, in milliseconds.  If ``None``, then do manual updates with an
      'Update' button.
    """
    DEFAULT_OPTS = {
        'update_timeout': 200,
    }
    
    def __init__(self, manager, *args, **kwargs):
        self._manager = manager
        self._opts = self.DEFAULT_OPTS.copy()
        self._opts.update(kwargs)
        
    def __call__(self, f):
        (args, varargs, varkw, defaults) = getargspec(f)
        print "args: %r\nvarargs: %r\nvarkw: %r\ndefaults: %r" % (
            args, varargs, varkw, defaults)
    
        if defaults is None:
            defaults = []

        n = len(args) - len(defaults)
        controls = [automatic_control(arg, defaults[i-n] if i >= n else None)
                    for i, arg in enumerate(args)]
        self._manager.add(self._opts, f, controls)
        return f

def automatic_control(argname, default):
    if isinstance(default, Control):
        default.set_argname(argname)
        return default
    from inputbox import InputBox
    i = InputBox(default=default, type=eval)
    i.set_argname(argname)
    return i
    

