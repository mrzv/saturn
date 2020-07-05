import ast
import sys

# From: https://stackoverflow.com/questions/33908794/get-value-of-last-expression-in-exec-call
# exec, but return the value of the last expression
def exec_eval(script, globals=None, locals=None, name=''):
    '''Execute a script and return the value of the last expression'''
    stmts = list(ast.iter_child_nodes(ast.parse(script)))
    if not stmts:
        return None
    if isinstance(stmts[-1], ast.Expr):
        # the last one is an expression and we will try to return the results
        # so we first execute the previous statements
        if len(stmts) > 1:
            if sys.version_info >= (3, 8):
                mod = ast.Module(stmts[:-1], [])
            else:
                mod = ast.Module(stmts[:-1])
            exec(compile(mod, filename=name, mode="exec"), globals, locals)
        # then we eval the last one
        return eval(compile(ast.Expression(body=stmts[-1].value), filename=name, mode="eval"), globals, locals)
    else:
        # otherwise we just execute the entire code
        return exec(compile(script, filename=name, mode="exec"), globals, locals)

def eval_expression(expr, locals_):
    return eval(expr, locals_, locals_)
