import re

tokenizer_specs = [
    ("LFT", r"\("),
    ("RGT", r"\)"),
    ("NEG", r"[!]"),
    ("AND", r"[&]"),
    ("OR", r"[|]"),
    ("IMP", r"=>"),
    ("EQV", r"<=>"),
    ("VAR", r"\w+"),
    ("WSP", r"\s"),
    ("ERR", r".+")
]

tokenizer_regex = '|'.join([f"(?P<{name}>{regex})" for name, regex in tokenizer_specs])

class Node:
    __slots__ = "val", "children"

    def __init__(self, val, children = []):
        self.val = val
        self.children = children

    def __str__(self):
        if type(self.val) == int:
            return f"({int(self.val)})"
        
        return f"({self.val}, {[str(x) for x in self.children]})"

class AST:

    def __init__(self, root):
        self.root = root

    @classmethod
    def from_string(cls, string):
        print(string)

        tokens = []
        depth = 0
        for m in re.finditer(tokenizer_regex, string):
            kind = m.lastgroup

            content = m.group()

            if kind == "WSP":
                continue
            elif kind == "RGT":
                depth -= 1

            tokens.append((depth, kind, content))

            if kind == "LFT":
                depth += 1

        tokens = AST.add_brackets(tokens)

        root = AST.build(tokens)

        root = AST.recursive_expand(root)

        print(root)

    @staticmethod
    def build(tokens):
        ops = AST.find_ops_at_depth(0, tokens)

        if len(ops) == 0:
            if len(tokens) == 1:
                _, _, c = tokens[0]
                return c

            _, t1, _ = tokens[0]
            _, t2, _ = tokens[len(tokens) - 1]


            if t1 == "LFT" and t2 == "RGT":
                tokens.pop(0)
                tokens.pop()

                for i in range(0, len(tokens)):
                    d,t,c = tokens[i]
                    tokens[i] = (d-1,t,c)

                tokens = AST.add_brackets(tokens)

                return AST.build(tokens)
            else:
                raise ValueError(f"No operator at depth 0 and outermost tokens are not brackets {tokens}")
        elif len(ops) > 1:
            raise ValueError(f"Multiple operators at depth 0 {tokens}")            

        i, op = ops[0]

        left = ("?", tokens[:i])
        right = ("?", tokens[i+1:])

        if op == "NEG":
            root = (op, [right])
        else:
            root = (op, [left, right])

        return root

    @staticmethod
    def recursive_expand(node):
        op, ls = node

        if op == "?":
            node = AST.build(ls)
            if type(node) == int or type(node) == str:
                return node

            return AST.recursive_expand(node)

        for i in range(0, len(ls)):
            x = ls[i]

            if type(x) == int or type(x) == str:
                continue

            ls[i] = AST.recursive_expand(x)

        return (op, ls)


    @staticmethod
    def add_brackets(tokens):
        ops = AST.find_ops_at_depth(0, tokens)

        while ops:
            print(ops)
            ops_only = [x for _, x in ops]

            start = -1
            pos = -1
            if "NEG" in ops_only:
                pos, _ = ops[ops_only.index("NEG")]
                start = pos
            elif "AND" in ops_only:             
                pos, _ = ops[ops_only.index("AND")]
            elif "OR" in ops_only:
                pos, _ = ops[ops_only.index("OR")]
            elif "IMP" in ops_only:
                pos, _ = ops[ops_only.index("IMP")]
            elif "EQV" in ops_only:
                pos, _ = ops[ops_only.index("EQV")]

            if pos == -1:
                break


            if start == -1:
                start = AST.find_group_start(pos - 1, 0, tokens)

            end = AST.find_group_end(pos + 1, 0, tokens)

            print(start, pos, end)

            if start == 0 and end == len(tokens):
                break

            for i in range(start, end):
                d, t, c = tokens[i]
                tokens[i] = (d + 1, t, c)

            tokens.insert(end, (0, "RGT", ")"))
            tokens.insert(start, (0, "LFT", "("))

            print(tokens)

            ops = AST.find_ops_at_depth(0, tokens)

        return tokens

    @staticmethod
    def find_ops_at_depth(depth, tokens):

        ops = []

        for i, token in enumerate(tokens):
            d, t, _ = token

            if d > depth:
                continue

            if t in ["NEG", "AND", "OR", "IMP", "EQV"]:
                ops.append((i, t))

        return ops

    @staticmethod
    def find_group_start(start, depth, tokens):

        end = -1
        for i in reversed(range(0, start + 1)):
            d, t, c = tokens[i]

            if d > 0:
                continue

            if t == "VAR" or t == "LFT":
                return i

            if t in ["OR", "AND", "IMP", "EQV"]:
                return i + 1


        return 0

    @staticmethod
    def find_group_end(start, depth, tokens):

        end = -1
        for i, token in enumerate(tokens[(start):]):
            d, t, c = token

            if d > 0:
                continue

            if t == "VAR" or t == "RGT":
                return i + start + 1

            if t in ["OR", "AND", "IMP", "EQV"]:
                return i + start - 1


        return len(tokens) - 1
