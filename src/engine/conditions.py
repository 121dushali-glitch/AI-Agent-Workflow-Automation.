import operator
OPS = {'<': operator.lt, '<=': operator.le, '>': operator.gt, '>=': operator.ge, '==': operator.eq, '!=': operator.ne}

def compare(left, op, right):
    return OPS[op](left, right)
