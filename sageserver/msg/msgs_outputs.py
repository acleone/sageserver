from msgbase import *
from msgints import *

__all__ = ("Stdin", "Stdout", "Stderr", "Except")


class Stdin(Msg):
    type = STDIN
    def init(self, o):
        return Msg.init(o=o)
    
class Stdout(Msg):
    type = STDOUT
    def init(self, o):
        return Msg.init(o=o)
    
class Stderr(Msg):
    type = STDERR
    def init(self, o):
        return Msg.init(o=o)
    


class Except(Msg):
    type = EXCEPT
    def init(self, o):
        return Msg.init(o=o)