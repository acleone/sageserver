
__all__ = ('Control',)

class Control(object):
    """
    The base class for a control on the interact canvas.

    Required Attributes:

    :cvar js_class: The javascript class that should be called with json_dict.
    """
    __slots__ = ()
    
    js_class = 'Control'
    """The javascript class name of this control"""

    def set_argname(self, argname):
        """
        Called to set the argname.
        """
        pass

    def json_dict(self):
        """
        Returns an object suitable for encoding with json.
        """
        raise NotImplementedError()

    def eval(self, json_obj):
        """
        Takes a decoded json object and returns the python value to be
        passed to the interact function.
        """
        raise NotImplementedError()
