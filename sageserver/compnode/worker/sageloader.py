"""
Import hook.

See PEP302 and the py3k documentation for importlib.
"""

class SageLoader(object):
    """
    Should be a subclass of importlib.abc.Loader and importlib.abc.Finder
    (py3k).
    
    EXAMPLES:
        >>> import sys
        >>> sl = SageLoader(sys=sys, append=True, log=None)
        >>> any([isinstance(m, SageLoader) for m in sys.meta_path])
        True
    """
    
    __slots__ = ('__log', '__source', '__code', '__sys')
    
    def __init__(self, sys=None, append=True, log=None):
        """
        :param sys: (default: None) what to use as the sys module. If None,
            import sys and use that.
        :param append: (default: True) append this loader to
            :obj:`sys.meta_path`.
        :param log: a Logger instance to log to.
        """
        if sys is None:
            import sys as _sys
            sys = _sys
        self.__sys = sys
        if append:
            self.__sys.meta_path.append(self)
        if log is None:
            import logging
            log = logging.getLogger("SageLoader")
        self.__log = log

        self.__source = {}
        self.__code = {}
        
    def set_source(self, name, source):
        self.__source[name] = source
        
    def get_source(self, fullname):
        self.__log.debug("get_source(%r)", fullname)
        self.__log.debug("current_sources: %r", self.__source)
        try:
            return self.__source[fullname]
        except KeyError:
            raise ImportError("Cannot find module %r" % (fullname,))

    def is_package(self, fullname):
        self.__log.debug("is_package(%r)", fullname)
        return False

    def set_code(self, fullname, code):
        self.__code[fullname] = code

    def get_code(self, fullname):
        self.__log.debug("get_code(%r)", fullname)
        return self.__code[fullname]
        
    def find_module(self, fullname, path=None):
        self.__log.debug("find_module(%r, %r)", fullname, path)
        return None
        
    def load_module(self, fullname):
        self.__log.debug("load_module(%r)", fullname)
        try:
            return self.__sys.modules[fullname]
        except KeyError:
            pass
        if fullname not in self.__code:
            raise ImportError('No module named %s' % (fullname,))
        code = self.__code[fullname]
        mod = self.new_module(fullname)
        exec code in mod.__dict__
        return mod

    def new_module(self, fullname):
        from imp import new_module
        mod = self.__sys.modules.setdefault(fullname, new_module(fullname))
        mod.__file__ = fullname
        mod.__loader__ = self
        return mod
        
    def clear(self):
        self.__source = {}
        
    def reload(self, mod):
        """
        Calls :func:`__reload__` (set by worker.py to the actual reload func).
        """
        self.__log.debug("reload(%r)", mod)
        if mod.__name__ == 'sys':
            sout = self.__sys.stdout
            serr = self.__sys.stderr
            sin = self.__sys.stdin
        __reload__(mod)
        if mod.__name__ == 'sys':
            mod.stdout = sout
            mod.stderr = serr
            mod.stdin = sin
        

if __name__ == '__main__':
    import doctest
    doctest.testmod()
