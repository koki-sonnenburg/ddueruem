from copy import copy
import re
#------------------------------------------------------------------------------#

u8neg = u"\u00AC"
u8and = u"\u2227"
u8or = u"\u2228"

class FM:
    """Contains expressions representing the feature diagram and the cross-tree constraints"""

    def __init__(self, expr_fd, expr_ctcs):
        self.expr_fd = expr_fd
        self.expr_ctcs = expr_ctcs

class Expression:
    
    def __init__(self, clauses, var2desc = {}, meta = {}):
        self.meta = meta
        self.clauses = clauses
        self.var2desc = var2desc

    def toAST(self):
        pass

    def toCNF(self):
        pass

    def toDNF(self):
        pass

    def get_meta(self):
        return self.meta

class CNF(Expression):

    def __str__(self):
        out = []

        for clause in self.clauses:
            h = []
            for x in clause:
                if x < 0:
                    h.append(f"{u8neg}{abs(x)}")
                else:
                    h.append(str(x))

            h = f" {u8or} ".join(h)
            out.append(f"({h})")

        return f" {u8and} ".join(out)

    def verbose(self):        
        out = str(self)

        for k,v in self.var2desc.items():
            out = re.sub(str(k), v, out)

        return out

    def get_no_variables(self):
        return len(self.var2desc)

class DNF(Expression):
    pass

class AST(Expression):
    pass
