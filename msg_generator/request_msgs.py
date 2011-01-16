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
        Fld('cid', False, 0, doc="Cell id"),
        Fld('echo_stdin', False, True, doc='Output Stdin messages '
            'when Stdin is returned to the executing code'),
        Fld('displayhook', False, 'LAST', doc='''
            'LAST': only the last expression.
            'ALL': All expressions
            'NONE': nothing.'''),
        Fld('assignhook', False, 'NONE', doc='''
            'ALL': print results of all assignments.
            'NONE': nothing.'''),
        Fld('print_ast', False, False, doc='If True, print the '
            'abstract syntax tree before executing.'),
        Fld('except_msg', False, False, doc='If True, send an Except message '
            'when an exception occurs.  If False, print to stderr.'),
    ]),
    
    MsgClass('IsComputing', 'IS_COMPUTING', 130, doc="Returns Yes or No"),
    
    MsgClass('GetCompletions', 'GET_COMPLETIONS', 140, [
        Fld('text', doc='the text to complete'),
        Fld('format', False, 'TEXT')
    ]),
    
    MsgClass('Completions', 'COMPLETIONS', 141, [
        Fld('text'),
        Fld('format'),
        Fld('completions'),
    ]),
    
    MsgClass('GetDoc', 'GET_DOC', 142, [                                
        Fld('object'),
        Fld('format', False, 'TEXT'),
    ]),
    
    MsgClass('Doc', 'DOC', 143, [
        Fld('object'),
        Fld('format'),
        Fld('obj_found', False, False),
        Fld('doc', False, None),
    ]),
    
    MsgClass('GetSource', 'GET_SOURCE', 144, [
        Fld('object'),
        Fld('format', False, 'TEXT'),
    ]),
    
    MsgClass('Source', 'SOURCE', 145, [
        Fld('object'),
        Fld('format'),
        Fld('obj_found', False, False),
        Fld('source', False, None),
    ]),


]