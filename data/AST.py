class Node:
    def __init__(self, op, lhs, rhs = None):
        self.op = op
        self.lhs = lhs
        self.rhs = rhs

    def __str__(self):
        return f"({self.op}, {self.lhs}, {self.rhs})"

class AST:
    def __init__(self, root):
        self.root = root