import re

#------------------------------------------------------------------------------#

from data.AST import Node

from utils.InputFormats import FM, CNF
from utils.IO import hash_hex

#------------------------------------------------------------------------------#

tokenizer_specs = [
    ("LFT", r"\("),
    ("RGT", r"\)"),
    ("NEG", r"[!]"),
    ("AND", r"[&]"),
    ("OR", r"[|]"),
    ("IMP", r"=>"),
    ("EQV", r"\<=\>"),
    ("VAR", r"[\w/+]+"),
    ("WSP", r"\s"),
    ("ERR", r".+")
]

tokenizer_regex = '|'.join([f"(?P<{name}>{regex})" for name, regex in tokenizer_specs])

#------------------------------------------------------------------------------#

def parse_features_rec(lines, index):
    d, name = lines[index]

    children_type = None

    m = re.match(r"(?P<feature>[\w/+]+)(\s+(?P<modifier>[{}\w]+))?", name)

    if not m:
        raise ValueError(f"Malformed entry ({name})")

    feature_depth = d
    children = []
    while index in range(0, len(lines) - 1):
        index += 1

        d, name = lines[index]

        if name in [""]:
            continue

        if d <= feature_depth or name == "constraints":
            index -= 1
            break

        if name in ["mandatory", "optional", "or", "alternative"]:
            children_type = name
            continue

        child_feature, index = parse_features_rec(lines, index)
        c_feature, c_modifier, _, c_children = child_feature

        child_feature = (c_feature, c_modifier, children_type, c_children)

        children.append(child_feature)

    return (m["feature"], m["modifier"], None, children), index

def enumerate_features(root, id = 1, id2feature = {}, feature2id = {}):
    feature, _, _, children = root

    id2feature[id] = feature
    feature2id[feature] = id
    id += 1

    for child in children:
        id2feature, feature2id, id = enumerate_features(child, id, id2feature, feature2id)

    return id2feature, feature2id, id

def fd2constraints(root, feature2id):

    constraints = []

    feature, _, _, _ = root
    constraints.append([feature2id[feature]])

    constraints = gather_constraints(root, constraints, feature2id)    

    return constraints

def gather_constraints(root, constraints, feature2id):

    feature_name, _, _, children = root

    group_processed = False
    for child in children:
        child_name, _, child_type, _ = child

        #child => parent (not(child) /\ parent)
        constraints.append([-feature2id[child_name], feature2id[feature_name]])

        if child_type == "optional":
            pass
        elif child_type == "mandatory":
            #parent => child (not(parent) /\ child)
            constraints.append([-feature2id[feature_name], feature2id[child_name]])
        elif child_type == "or" and not group_processed:
            group_processed = True

            clause = [-feature2id[feature_name]]
            for x, _, _, _ in children:
                clause.append(feature2id[x])

            constraints.append(clause)

        elif child_type == "alternative" and not group_processed:       
            group_processed = True

            clause = [-feature2id[feature_name]]
            for x, _, _, _ in children:
                clause.append(feature2id[x])

            constraints.append(clause)

            for x, _, _, _ in children: 
                for y, _, _, _ in children:
                    if x == y:
                        break

                    constraints.append([-feature2id[feature_name], -feature2id[x], -feature2id[y]])

        constraints = gather_constraints(child, constraints, feature2id)

    return constraints

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

def find_ops_at_depth(depth, tokens):

    ops = []

    for i, token in enumerate(tokens):
        d, t, _ = token

        if d > depth:
            continue

        if t in ["NEG", "AND", "OR", "IMP", "EQV"]:
            ops.append((i, t))

    return ops

def add_brackets(tokens):
    ops = find_ops_at_depth(0, tokens)

    while ops:
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
            start = find_group_start(pos - 1, 0, tokens)

        end = find_group_end(pos + 1, 0, tokens)

        if start == 0 and end == len(tokens):
            break

        for i in range(start, end):
            d, t, c = tokens[i]
            tokens[i] = (d + 1, t, c)

        tokens.insert(end, (0, "RGT", ")"))
        tokens.insert(start, (0, "LFT", "("))

        ops = find_ops_at_depth(0, tokens)

    return tokens

def build(tokens, feature2id):
    ops = find_ops_at_depth(0, tokens)

    if len(ops) == 0:
        if len(tokens) == 1:
            _, _, c = tokens[0]
            return feature2id[c]

        _, t1, _ = tokens[0]
        _, t2, _ = tokens[len(tokens) - 1]

        if t1 == "LFT" and t2 == "RGT":
            tokens.pop(0)
            tokens.pop()

            for i in range(0, len(tokens)):
                d,t,c = tokens[i]
                tokens[i] = (d-1,t,c)

            tokens = add_brackets(tokens)

            return build(tokens, feature2id)
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

def recursive_expand(node, feature2id):
    op, ls = node

    if op == "?":
        node = build(ls, feature2id)
        if type(node) == int or type(node) == str:
            return node

        return recursive_expand(node, feature2id)

    for i in range(0, len(ls)):
        x = ls[i]

        if type(x) == int or type(x) == str:
            continue

        ls[i] = recursive_expand(x, feature2id)

    return (op, ls)

def expr2ast(string, feature2id):
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

    tokens = add_brackets(tokens)

    root = build(tokens, feature2id)

    root = recursive_expand(root, feature2id)

    return root

def parse_ctcs(lines, index, feature2id):
    lines = lines[index:]

    nconstraints = 0
    for line in lines:
        d, _ = line
        if d > 0:
            nconstraints += 1

    print(f"#CTCs:\t{nconstraints}")

    out = []

    for depth, line in lines:
        if depth == 0:
            continue

        out.append(expr2ast(line, feature2id))

    return out

class UVL_Parser: 

    @staticmethod
    def name():
        return "uvl"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __init__(self, filename):
        self.filename = filename

    def parse(self):
        expr_fd = None
        expr_ctcs = None

        with open(self.filename) as file:
            lines = file.readlines()

        for i, line in enumerate(lines):
            indent = 0
            if m := re.search(r"[^\n\r\s]", line):
                indent = m.start()

            lines[i] = (indent, line.strip())

        start = 0

        for i, x in enumerate(lines):
            d, name = x
            if d == 1:
                start = i
                break

        root, index = parse_features_rec(lines, start)

        id2feature, feature2id, _ = enumerate_features(root)

        expr_fd = fd2constraints(root, feature2id)
        expr_ctcs = parse_ctcs(lines, index + 1, feature2id)

        meta = {
            "input-name": self.filename,
            "input-hash": hash_hex(self.filename)
        }

        return FM(CNF(expr_fd), expr_ctcs, id2feature, meta)