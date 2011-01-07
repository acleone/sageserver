from msgbase import *
from msgints import *

__all__ = ("No", "Yes",
           "ExecCell",
           "Shutdown", "Interrupt",
           "IsComputing")

No = simplemsg('No', NO)
Yes = simplemsg('Yes', YES)

ExecCell = simplemsg('ExecCell', EXEC_CELL,
                     [Fld(name='code', reqd=True, dflt=None)])

Shutdown = simplemsg('Shutdown', SHUTDOWN,
                     [Fld(name='before_int', reqd=False, dflt=0.5),
                      Fld(name='int_poll', reqd=False, dflt=0.5),
                      Fld(name='int_retries', reqd=False, dflt=1)])

Interrupt = simplemsg('Interrupt', INTERRUPT,
                      [Fld(name='retries', reqd=False, dflt=2),
                       Fld(name='poll_for', reqd=False, dflt=0.5)])


IsComputing = simplemsg('IsComputing', IS_COMPUTING)
