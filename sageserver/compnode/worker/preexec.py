"""
Exec Command Pre-processing
===========================
This module defines the :func:`transform_source` and
:func:`transform_ast` functions, which take pre-processes code from
:class:`msg.Exec` instances before `exec`-ing.

Source Transformations (:func:`transform_source`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
These are transforms that act on the string source of the command, and return
the modified source.  These are generally hack-ish, so if you're adding a
transform, try to do it with an ast transform.

ast (Abstract Syntax Tree) Transformations (:func:`transform_ast`)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
These are transforms that act on the ast, and return the modified ast:
* :func:`displayhook_last` -- if the last node in an in-order traversal
  of the ast is an `Expr`(ession node), add a call to
  :func:`__displayhook__`.
* :class:`DisplayhookAll` -- a subclass of
  :class:`ast.NodeTransformer` that adds the displayhook to all
  :class:`ast.Expr` nodes.
* :class:`AssignhookAll` -- a subclass of
  :class:`ast.NodeTransformer` that prints out assignment statements.

"""
import ast

import astpp


def transform_source(exec_msg, globals_):
    """
    Called before the code is parsed into an AST.
    
    :param exec_msg: a :class:`msg.Exec` instance.
    :returns: a string to be parsed into an ast.
    """
    source = exec_msg.end_bytes
    source = parse_percent_directives(exec_msg, source, globals_)
    return source
    
    
def transform_ast(exec_msg, source_ast, source_lines, globals_):
    """
    Called after the code is parsed into an AST.
    
    :param exec_msg: a :class:`msg.Exec` instance.
    :param source_ast: the ast of the source
    :param source_lines: ``source.splitlines()``
    :returns: the transformed ast.
    """
    dh = exec_msg.dict.get('displayhook', 'last')
    if dh == 'last':
        source_ast = displayhook_last(source_ast)
    elif dh == 'all':
        source_ast = DisplayhookAll().visit(source_ast)
    ah = exec_msg.dict.get('assignhook', None)
    if ah == 'all':
        source_ast = AssignhookAll(source_lines).visit(source_ast)
    if exec_msg.dict.get('print_ast', False):
        print astpp.dump(source_ast)
    return source_ast
    
def parse_percent_directives(exec_msg, source, globals_):
    """
    Parses percent directives and changes exec_msg.opts.
    """
    lines = source.splitlines(True)
    for i in range(len(lines)):
        line = lines[i]
        if not line.startswith('%'):
            break
            
        d, s, v = line[1:].partition('=')
        d = d.strip()
        v = v.strip()
        exec_msg.dict[d] = eval(v, globals_)
        lines[i] = '#' + line
    return ''.join(lines)
    
def displayhook_expr(node):
    """
    Adds a call to :func:`__displayhook__` to an :class:`ast.Expr` node.
    
    :param node: an AST node.
    :returns: the modified node.
    
    EXAMPLES::
    
        >>> t = ast.parse("a = 4; a").body[1]
        >>> ast.dump(t)
        "Expr(value=Name(id='a', ctx=Load()))"
        >>> ast.dump(displayhook_expr(t))
        "Expr(value=Call(func=Name(id='__displayhook__', ctx=Load()), args=[Name(id='a', ctx=Load())], keywords=[], starargs=None, kwargs=None))"
    """
    if isinstance(node, ast.Expr):
        cl = ast.copy_location
        dh_Name = cl(ast.Name(id='__displayhook__', ctx=ast.Load()), node)
        dh_Call = cl(ast.Call(func=dh_Name, args=[node.value], keywords=[],
                              starargs=None, kwargs=None), node)
        node.value = dh_Call
    return node
    
        
def displayhook_last(node):
    """
    If the last node in an in-order traversal of the ast is an
    :class:`ast.Expr` node, add a call to :func:`__displayhook__`.
    
    :param node: an AST node.
    :returns: the modified node.
    
    EXAMPLES::
    
        >>> import sys
        >>> __displayhook__ = sys.displayhook
        >>> s = '''\\
        ... for i in range(1, 2):
        ...     for j in range(2, 3):
        ...         i * j'''
        >>> t = displayhook_last(ast.parse(s))
        >>> exec compile(t, '<string>', 'exec')
        2
    """
    if not isinstance(node, ast.Expr):
        children = list(ast.iter_child_nodes(node))
        if children:
            displayhook_last(children[-1])
    else:
        node = displayhook_expr(node)
    return node
    

class DisplayhookAll(ast.NodeTransformer):
    
    def visit_Expr(self, node):
        return displayhook_expr(node)
        
        
def assignhook(target, obj):
    """
    Prints ``{target} = repr({obj})`` and returns obj.
    
    EXAMPLES::
    
        >>> a = assignhook("a", 1)
        a = 1
    """
    print "%s = %r" % (target, obj)
    return obj
    
class AssignhookAll(ast.NodeTransformer):
    """
    Adds calls to :func:`__assignhook__` for all assignments (a = 1):
    
    EXAMPLES::
    
        >>> __assignhook__ = assignhook
        >>> s = '''\\
        ... a = 1
        ... b=2
        ... c=3; d = 4
        ... a,b    = [
        ... i for i in range(2)]
        ... a, (b, c) \\
        ... = (4, (5, 6))
        ... a, (b,
        ... c) = (4, (5, 6))'''
        >>> t = ast.parse(s)
        >>> t = AssignhookAll(s.splitlines()).visit(t)
        >>> exec compile(t, '<string>', 'exec')
        a = 1
        b = 2
        c = 3
        d = 4
        a,b = [0, 1]
        a, (b, c) = (4, (5, 6))
        a, (b, c) = (4, (5, 6))
    """

    def __init__(self, source_lines):
        self._source_lines = source_lines
        
    def visit_Assign(self, node):
        n1 = node.targets[0]
        n2 = node.value
        try:
            span = _get_source_span(self._source_lines, n1, n2)
            span = ' '.join(span.splitlines())
            eq_i = span.rfind('=')
            tar_str = span[:eq_i].rstrip()
            cl = ast.copy_location
            ah_Name = cl(ast.Name(id='__assignhook__', ctx=ast.Load()), n2)
            ah_Str = cl(ast.Str(s=tar_str), n2)
            ah_Call = cl(ast.Call(func=ah_Name, args=[ah_Str, n2], keywords=[],
                                  starargs=None, kwargs=None), n2)
            node.value = ah_Call
        except:
            pass
        return node
        

def _get_source_span(source_lines, n1, n2):
    """
    Returns source string between :class:`ast.Node` :obj:`n1` and :obj:`n2`.
    
    EXAMPLES::
        >>> s = 'a = 5; b = 6'
        >>> t = ast.parse(s)
        >>> _get_source_span(s.splitlines(), t.body[0], t.body[1])
        'a = 5; '
    """
    # NOTE: lineno is 1-indexed
    if n1.lineno != n2.lineno:
        r = [source_lines[n1.lineno - 1][n1.col_offset:]]
        for i in range(n1.lineno, n2.lineno - 1):
            r.append(source_lines[i])
        r.append(source_lines[n2.lineno - 1][:n2.col_offset])
        return '\n'.join(r)
    # else:
    return source_lines[n1.lineno - 1][n1.col_offset:n2.col_offset]    
    
if __name__ == '__main__':
    import doctest
    doctest.testmod()
