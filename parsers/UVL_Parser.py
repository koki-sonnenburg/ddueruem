import re

#------------------------------------------------------------------------------#

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
    ("EQV", r"<=>"),
    ("VAR", r"\w+"),
    ("WSP", r"\s"),
    ("ERR", r".+")
]

tokenizer_regex = '|'.join([f"(?P<{name}>{regex})" for name, regex in tokenizer_specs])

#------------------------------------------------------------------------------#

def parse_features_rec(lines, index):
    d, name = lines[index]

    children_type = None

    m = re.match(r"(?P<feature>\w+)(\s+(?P<modifier>[{}\w]+))?", name)

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


class UVL_Parser: 
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __init__(self, filename):
        self.filename = filename

    def parse2fm(self):
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

        return FM(CNF(expr_fd), expr_ctcs)


