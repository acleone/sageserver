from generate import Fld, MsgClass

msgs = [
        
    MsgClass('No', 'NO', 100, doc='No response'),
    MsgClass('Yes', 'YES', 101, doc='Yes response'),
    
    
    MsgClass('Interrupt', 'INTERRUPT', 110, [
        Fld('timeout', False, 1.0,
            doc="Time in seconds to wait before responding No"),
    ], doc='Interrupt a computation'),
    
    MsgClass('Shutdown', 'SHUTDOWN', 111),
    
    
    MsgClass('ExecCell', 'EXEC_CELL', 120, [
        Fld('source', doc='Source code of the cell to execute'),
    ]),


]