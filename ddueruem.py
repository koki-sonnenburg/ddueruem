#!/usr/bin/env python3
import argparse

from copy import copy

from ctypes import *
import ctypes

from datetime import datetime, timedelta

import hashlib

import os
from os import path

from pprint import pprint

from random import shuffle
import re
import requests

import subprocess

from termcolor import colored

import tarfile

from adapters import BUDDY, CUDD
import config

from utils.CNF import CNF

from utils.VariableOrdering import compute_default_order, force, force_triage, sort_clauses_by_span
from utils.IO import log_info, log_warning, log_error, blue, verify_hash, hash_hex

class FeatureDiagram:

    def __init__(self, root):
        self.root = root



DYNORDER_CHOICES = ["off", "sift", "sift-conv"]
INSTALL_CHOICES = ["buddy", "cudd", "sylvan"]
PREORDER_CHOICES = ["force", "force-triage"]


CLI_HELP = {
    "file": "The DIMACS/UVL file to construct the BDD for",

    "--silent": "Disable all output (libraries may have unsuppressible output).",
    "--verbose": "Enable verbose output.",

    "--buddy": "Uses BuDDy to build the BDD.",
    "--cudd": "Uses CUDD to build the BDD. (Default)",

    "--preorder": "The preorder algorithm to use",
    "--ignore-cache": "Do not use cached variable order or BDD",

    "--dynorder": "The dynamic reordering algorithm to use",

    "--install": "Download and install the chosen libraries.",
    "--clean-install": "Forces download and install of the chosen libraries."
}

#

def enumerate_features(root, id = 1, id2feature = {}, feature2id = {}):
    feature, _, _, children = root

    id2feature[id] = feature
    feature2id[feature] = id
    id += 1

    for child in children:
        id2feature, feature2id, id = enumerate_features(child, id, id2feature, feature2id)

    return id2feature, feature2id, id

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

def fd2constraints(root, feature2id):

    constraints = []

    feature, _, _, _ = root
    constraints.append([feature2id[feature]])

    constraints = gather_constraints(root, constraints, feature2id)    

    print(len(constraints))
    print(constraints)

    return []

def parse_uvl(filename):
    with open(filename) as file:
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

    fd_constraints = fd2constraints(root, feature2id)

    ctc_cnf_constraints = []

    ctc_nt_constraints = []

    for line in lines[index:]:
        d, content = line

        if content in ["", "constraints"]:
            continue

        raw = re.split(r"\s+", content)

        lhs = []
        rhs = []
        toLHS = True

        lhs_ops = []
        rhs_ops = []

        for x in raw:
            if x == "=>":
                toLHS = False
                continue

            negated = False

            if x[0] == "!":
                x = x[1:]
                negated = True

            if x in feature2id:
                x = feature2id[x]
                if negated:
                    x = -x
            else:
                if toLHS:
                    lhs_ops.append(x)
                else:
                    rhs_ops.append(x)

            if toLHS:
                lhs.append(x)
            else:
                rhs.append(x)

        if not lhs_ops and not rhs_ops:
            lhs = [-int(x) for x in lhs]
            rhs = [int(x) for x in rhs]

            clause = lhs
            clause.extend(rhs)

            log_info("Clause", blue(content), "contains no operator")
            log_info("Adding", blue(clause))

            ctc_cnf_constraints.append(clause)
        else:
            print("Non trivial constraint", blue(content))
            print(lhs, rhs)
            print(lhs_ops, rhs_ops)

            lhs = to_ast(lhs, lhs_ops)
            rhs = to_ast(rhs, rhs_ops)

            constraint = ("|", ("!", lhs), rhs)

            print("-->", blue(constraint))
            ctc_nt_constraints.append(constraint)

    return root, fd_constraints, ctc_cnf_constraints, ctc_nt_constraints

def to_ast(formula, formula_ops):
    for x in formula:
        if x in ["(", ")"]:
            raise ValueError("Non flat constraints are currently not supported, please open a feature requst, if you require this feature")

    if not formula_ops:
        return ("&", formula)
    else:
        if formula_ops.count(formula_ops[0]) == len(formula_ops):
            op = formula_ops[0]
            formula = [x for x in formula if x != op]
            return (op, formula)


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

###
def get_lib(lib_name):
    if lib_name == "buddy":
        return BUDDY
    elif lib_name == "cudd":
        return CUDD

    return None

def read_cache_from_file(filename):

    with open(filename) as file:
        content = file.read()

    lines = re.split("[\n\r]", content)

    data = {}

    for line in lines:
        raw = re.split(":", line)
        key = raw[0]
        value = raw[1:]
        data[key] = value



    # sanitize order
    if "order" in data:
        data["order"] = [int(x) for x in re.split(r",", data["order"][0])]

    return data

def validate_cache(cache, filename):
    if not cache:
        return (False, "Cache damaged")

    if not "file_md5" in cache:
        return (False, "Cache contains no hash")

    hash_should = cache["file_md5"][0]

    return verify_hash(filename, hash_should)

def satcount(root_ce, root, nodes, cnf):
    count = 0

    stack = []
    stack.append((root, 0, root_ce == 1))

    while stack:
        node, depth, complemented = stack.pop()

        if (node == 0 and complemented) or (node == 1 and not complemented):
            count += 1 << (cnf.get_no_variables() - depth)
        elif node != 0 and node != 1:
            _, low_ce, low, high_ce, high = nodes[node]

            stack.append((low, depth +1, complemented ^ low_ce))
            stack.append((high, depth +1, complemented ^ high_ce))

    return count

def run_preorder(cnf, preorder):

    if preorder == "force":
        order, span = force(cnf)
    elif preorder == "force-triage":        
        log_info()
        log_info("Beginning variable ordering with triaged FORCE")
        order, span = force_triage(cnf)
        log_info("Triaged FORCE has finished")
    else:
        log_warning(blue(preoder), "currently not implemented")
        order = compute_default_order(cnf)

    return order

def run_lib(lib, cnf, order, dynorder, filename_bdd):
    log_info("Building BDD for", colored(cnf.meta["filename"], "blue"), "using", f"{colored(lib.name(), 'blue')}.")

    with lib() as bdd:
        filename_bdd = bdd.from_cnf(cnf, order, dynorder, filename_bdd)

    return filename_bdd

def report(cnf, filename_bdd, filename_report_ts, filename_report):

    if not path.exists(filename_bdd):
        log_error("No cached BDD found for", colored(cnf.meta["filename"], "blue"))
        exit(1)

    with open(filename_bdd) as file:
        lines = re.split("[\n\r]", file.read())

    m = 0

    data = {}

    for i, line in enumerate(lines):
        if line == "----":
            m = i
            break

        line = re.split(":", line)
        data[line[0]] = line[1:]

    if not "root" in data:
        log_error(f"Cannot compile report, as {filename_bdd} is broken (root missing)")
        exit(1)
    else:
        root_ce = int(data["root"][0])
        root = int(data["root"][1])

    if not "n_nodes" in data:
        log_error(f"Cannot compile report, as {filename_bdd} is broken (n_nodes missing)")
        exit(1)
    else:
        n_nodes = int(data["n_nodes"][0])

    if "order" in data:
        order = data["order"]
    else:
        order = ""

    nodes = {}
    for line in lines[m+1:]:
        m = re.match(r"(?P<id>\d+) (?P<var>\d+) (?P<low_ce>\d):(?P<low>\d+) (?P<high_ce>\d):(?P<high>\d+)", line)
        if m:
            nodes[int(m["id"])] = (int(m["var"]), int(m["low_ce"]) == 1, int(m["low"]), int(m["high_ce"]) == 1, int(m["high"]))

    ssat = satcount(root_ce, root, nodes, cnf)

    print("--------------------------------")
    print(f"Results for {colored(cnf.meta['filename'], 'blue')}:")
    print("#SAT:", ssat, sep = "\t")
    print("Nodes:", n_nodes, sep = "\t")
    print("--------------------------------")

    contents = [
        f"file:{cnf.meta['filename']}",
        f"file_md5:{hash_hex(cnf.meta['filename'])}",
        f"bdd:{filename_bdd}",
        f"bdd_md5:{hash_hex(filename_bdd)}",
        f"order:{','.join([str(x) for x in order])}",
        f"#SAT:{ssat}",
        f"#nodes:{n_nodes}"
    ]

    content = os.linesep.join(contents)

    with open(filename_report_ts, "w") as file:
        file.write(content)
        file.write(os.linesep)

    with open(filename_report, "w") as file:
        file.write(content)
        file.write(os.linesep)

def report_order(cnf, order, filename_report):

    contents = [
        f"file:{cnf.meta['filename']}",
        f"file_md5:{hash_hex(cnf.meta['filename'])}",
        f"order:{','.join([str(x) for x in order])}"
    ]

    content = os.linesep.join(contents)

    with open(filename_report, "w") as file:
        file.write(content)
        file.write(os.linesep)

def run(filename, lib, preorder, dynorder, caching):

    if not path.exists(filename):
        log_error(f"Could not find", blue(filename),f"aborting.{os.linesep}Either give the absolute path to the file or the relative path wrt", blue(os.path.realpath(__file__)))
        exit(1)

    filename_base = os.path.basename(filename).split('.')[0]
    filename_report = f"{config.REPORT_DIR}/{filename_base}.ddrep"
    filename_report_ts = f"{config.REPORT_DIR}/{filename_base}-{datetime.now().strftime('%Y%m%d%H%M%S')}.ddrep"
    filename_bdd = f"{config.CACHE_DIR}/{filename_base}.dd" 

    cnf = CNF.from_DIMACS(filename)

    cache = None
    if path.exists(filename_report) and caching:
        log_info(f"Found cache for", blue(filename), f"({os.path.relpath(filename_report)})")
        cache = read_cache_from_file(filename_report)
        valid, reason = validate_cache(cache, filename)

        if not valid:
            log_warning(reason)
            cache = None

    order = None
    if cache:
        if "order" in cache:
            log_info("Found", blue("variable order"), "in cache")
            order = cache["order"]
        else:
            log_info("Cache contains no", blue("variable order"))

    computed_order = False
    if order and preorder:
        log_warning("Ignoring flag", blue(f"--preorder {preorder}"), "as cache exists and flag", blue("--ignore-cache"), "was not supplied")
    else:
        if order is None:
            if preorder is None:
                order = compute_default_order(cnf)
            else:
                computed_order = True
                order = run_preorder(cnf, preorder)

    if computed_order:
        report_order(cnf, order, filename_report)

    cnf.clauses = sort_clauses_by_span(cnf.clauses, order)

    filename_bdd = run_lib(lib, cnf, order, dynorder, filename_bdd)
    report(cnf, filename_bdd, filename_report_ts, filename_report)


def cli():

    lib_default = config.LIB_DEFAULT

    parser = argparse.ArgumentParser(description="Wrapper for BuDDy and CUDD.")
    parser.add_argument("file", nargs = "?", help = CLI_HELP["file"], default = None)

    # IO options
    parser.add_argument("--silent", help = CLI_HELP["--silent"], dest = "silent", action = "store_true", default = False)
    parser.add_argument("--verbose", help = CLI_HELP["--verbose"], dest = "verbose", action = "store_true", default = False)

    # Run options
    parser.add_argument("--buddy", help = CLI_HELP["--buddy"], dest = "lib", action = "store_const", const = "buddy", default = lib_default)
    parser.add_argument("--cudd", help = CLI_HELP["--cudd"], dest = "lib", action = "store_const", const = "cudd", default = lib_default)

    # Preorder
    parser.add_argument("--preorder", help = CLI_HELP["--preorder"], choices = PREORDER_CHOICES, type = str.lower, default = None)
    parser.add_argument("--ignore-cache", help =CLI_HELP["--ignore-cache"], dest = "caching", action = "store_false", default = True)

    # Reorder
    parser.add_argument("--dynorder", help = CLI_HELP["--dynorder"], choices = DYNORDER_CHOICES, type = str.lower, default = "sift-conv")

    # Install options
    parser.add_argument("--install", nargs = "+", choices = INSTALL_CHOICES, type = str.lower, help = CLI_HELP["--install"], default = [])
    parser.add_argument("--clean-install", nargs = "+", choices = INSTALL_CHOICES, type = str.lower, help = CLI_HELP["--clean-install"], default = [])

    args = parser.parse_args()

    # Perform clean installs:
    libs_clean_install = args.clean_install
    libs_install = args.install

    if libs_clean_install or libs_install:
        config.verbose = True
        log_info("Install requested, ignoring remaining parameters and flags")

    for lib in libs_clean_install:
        lib = get_lib(lib)
        lib.install(clean = True)

    # Perform  installs:
    for lib in libs_install:
        lib = get_lib(lib)
        lib.install(clean = False)

    if libs_clean_install or libs_install:
        exit(0)

    # Set toggles
    config.verbose = args.verbose
    config.silent = args.silent

    if config.verbose and config.silent:
        log_warning("Both", blue("--verbose"), "and", blue("--silent"), "are present, ignoring both.")
        config.verbose = False
        config.silent = False

    filename = args.file

    if filename is None:
        log_error("No filename given and not in setup mode. Exiting.")
        parser.print_help()
        exit()

    preorder = args.preorder
    caching  = args.caching
    dynorder = args.dynorder

    lib = get_lib(args.lib)

    run(filename, lib, preorder, dynorder, caching)

def init():    

    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    cache_dir = config.CACHE_DIR
    report_dir = config.REPORT_DIR

    if not path.exists(cache_dir):
        try:
            os.mkdir(cache_dir)
        except OSError as ose:
            log_error("[ERROR] Creating of directory", colored(cache_dir, "blue"), "failed")
        else:
            log_info(f"Created cache directory at {path.abspath(cache_dir)}")

    if not path.exists(report_dir):
        try:
            os.mkdir(report_dir)
        except OSError as ose:
            log_error("[ERROR] Creating of directory", colored(report_dir, "blue"), "failed")
        else:
            log_info(f"Created report directory at {path.abspath(report_dir)}")

init()
cli()