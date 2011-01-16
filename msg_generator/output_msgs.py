from generate import Fld, MsgClass

msgs = [
     
    MsgClass('Stdin', 'STDIN', 0, [Fld('bytes')]),
    MsgClass('Stdout', 'STDOUT', 1, [Fld('bytes')]),
    MsgClass('Stderr', 'STDERR', 2, [Fld('bytes')]),
    
    MsgClass('Except', 'EXCEPT', 10, [
        Fld('stderr'),                              
        Fld('stack', False),
        Fld('etype', False),
        Fld('value', False),
        Fld('syntax', False)
    ]),
     
    MsgClass('NeedStdin', 'NEED_STDIN', 90, [
        Fld('nbytes')
    ]),
    MsgClass('Done', 'DONE', 99),
]