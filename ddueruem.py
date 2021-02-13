#!/usr/bin/env python3
import argparse

from copy import copy

from ctypes import *
import ctypes

from datetime import datetime, timedelta

import hashlib

import os
from os import path

from random import shuffle
import re
import requests

import subprocess

from termcolor import colored

import tarfile

from adapters import BUDDY
import config

from utils.VariableOrdering import compute_default_order, force
from utils.IO import log_info,log_warning, blue, verify_hash

class CNF:

    def __init__(self, filename, nvars, var_descs, clauses):
        self.filename = filename
        self.nvars = nvars
        self.var_descs = var_descs
        self.clauses = clauses


INSTALL_CHOICES = ["buddy", "cudd", "sylvan"]
PREORDER_CHOICES = ["force", "force-triage"]

CLI_HELP = {
    "file": "The DIMACS file to construct the BDD for",

    "--silent": "Disable all output (libraries may have unsuppressible output).",
    "--verbose": "Enable verbose output.",

    "--buddy": "Uses BuDDy to build the BDD.",
    "--cudd": "Uses CUDD to build the BDD. (Default)",

    "--preorder": "The preorder algorithm to use",
    "--ignore-cache": "Do not use cached variable order or BDD",

    "--install": "Download and install the chosen libraries.",
    "--clean-install": "Forces download and install of the chosen libraries."
}

#

def parse_dimacs(filename):

    var_descs = {}

    nvars = 0
    nclauses = 0

    clauses = []

    with open(filename) as file:
        for line in file.readlines():
            m = re.match(r"(?P<type>[cp]) (?P<content>.*)", line)

            if m is None:
                line = re.sub(r"[\n\r]", "", line)
                clause = re.split(r"\s+", line)
                clause = [int(x) for x in clause if x != '0']
                
                clauses.append(clause)

            elif m["type"] == "c":
                m = re.match(r"\s*(?P<id>[1-9][0-9]*) (?P<desc>\w+)", m["content"])

                if m is not None:
                    var_descs[m["id"]] = m["desc"]

            elif m["type"] == "p":
                m = re.match(r"\s*(?P<type>\w+) (?P<nvars>\d+) (?P<nclauses>\d+)", m["content"])

                if m["type"] != "cnf":
                    print(f"[ERROR] Only CNFs are supported at this point, but type is ({m['type']})")

                nvars = int(m["nvars"])
                nclauses= int(m["nclauses"])

    if nclauses != len(clauses):
        print(f"[WARNING] Specified number of clauses ({nclauses}) differs from number of parsed ones ({len(clauses)}).")

    return CNF(filename, nvars, var_descs, clauses)

###
def get_lib(lib_name):
    if lib_name == "buddy":
        return BUDDY
    elif lib_name == "cudd":
        return CUDD

    return None

def read_cache_from_file(filename):

    out = dict()

    with open(filename) as file:
        content = file.read()

    lines = re.split("[\n\r]", content)

    try:
        filename = re.split(r"[:]", lines[0])[1]
        filehash = re.split(r"[:]", lines[1])[1]
    except (ValueError, IndexError):
        return None

    out["filename"] = filename.strip()
    out["md5"] = filehash.strip()
    out["order"] = re.split(r"[:]", lines[2])[1].strip()

    # sanitize order
    if "order" in out:
        out["order"] = [int(x) for x in re.split(r",", out["order"])]

    return out

def validate_cache(cache, filename):
    if not cache:
        return (False, "Cache damaged")

    if not "md5" in cache:
        return (False, "Cache contains no hash")

    hash_should = cache["md5"]

    return verify_hash(filename, hash_should)

def satcount(top, nodes, cnf):
    
    count = 0

    stack = []
    stack.append((top, 0, False))

    while stack:
        node, depth, complemented = stack.pop()

        if node == 0 and not complemented:
            continue
        elif node == 1 or complemented:
            count += 1 << (cnf.nvars - depth)
        else:
            _, low_ce, low, high_ce, high = nodes[node]
            stack.append((low, depth +1, not complemented and low_ce))
            stack.append((high, depth +1, not complemented and high_ce))

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

def run_lib(lib, cnf, order, filename_bdd):
    log_info("Building BDD for", colored(cnf.filename, "blue"), "using", f"{colored(lib.name(), 'blue')}.")

    with lib() as bdd:
        bdd.from_cnf(cnf, order, filename_bdd)

def report(cnf, filename_bdd, filename_report):

    if not path.exists(filename_bdd):
        log_error("No cached BDD found for", colored(cnf, "blue"))
        exit(1)

    with open(filename_bdd) as file:
        lines = re.split("[\n\r]", file.read())

    nodes = {}
    last = None

    for line in lines[4:]:
        m = re.match(r"(?P<id>\d+) (?P<var>\d+) (?P<low_ce>\d):(?P<low>\d+) (?P<high_ce>\d):(?P<high>\d+)", line)
        if m:
            nodes[int(m["id"])] = (int(m["var"]), int(m["high_ce"]) == 1, int(m["low"]), int(m["high_ce"]) == 1, int(m["high"]))
            last = int(m["id"])

    ssat = satcount(last, nodes, cnf)

    print("--------------------------------")
    print(f"Results for {colored(cnf.filename, 'blue')}:")
    print("#SAT:", ssat, sep = "\t")
    print("Nodes:", len(nodes), sep = "\t")
    print("--------------------------------")

    with open(filename_report, "w") as file:
        file.write(f"{cnf.filename}:{hash(cnf.filename)}{os.linesep}")
        file.write(f"BDD:{filename_bdd}{os.linesep}")
        file.write(f"#SAT:{ssat}{os.linesep}")
        file.write(f"#NODES:{len(nodes)}{os.linesep}")

def run(filename, lib, preorder, caching):

    if not path.exists(filename):
        log_error("Could not find", blue(filename),"aborting.")
        exit(1)

    filename_base = os.path.basename(filename).split('.')[0]
    filename_report = f"{config.REPORT_DIR}/{filename_base}-{datetime.now().strftime('%Y%m%d%H%M')}.ddrep"
    filename_bdd = f"{config.CACHE_DIR}/{filename_base}.dd" 

    cnf = parse_dimacs(filename)

    cache = None
    if path.exists(filename_bdd) and caching:
        log_info(f"Found cache for", blue(filename), f"({os.path.relpath(filename_bdd)})")
        cache = read_cache_from_file(filename_bdd)
        valid, reason = validate_cache(cache, filename)

        if not valid:
            log_warning(reason)
            cache = None

    order = None
    if cache:
        if "order" in cache:
            log_info("Found", blue("variable order"), "in cache")
            order = cache["order"]

    if order and preorder:
        log_warning("Ignoring flag", blue(f"--preorder {preorder}"), "as cache exists and flag", blue("--ignore-cache"), "was not supplied")
    else:
        if order is None:
            if preorder is None:
                order = compute_default_order(cnf)
            else:
                order = run_preorder(cnf, preorder)

    run_lib(lib, cnf, order, filename_bdd)
    report(cnf, filename_bdd, filename_report)


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
    parser.add_argument("--preorder", help = CLI_HELP["--preorder"], nargs = "?", choices = PREORDER_CHOICES, type = str.lower, default = None)
    parser.add_argument("--ignore-cache", help =CLI_HELP["--ignore-cache"], dest = "caching", action = "store_false", default = True)

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
    preorder = args.preorder
    caching  = args.caching

    lib = get_lib(args.lib)

    run(filename, lib, preorder, caching)

def init():    
    # check if the .cache directory exists and create it otherwise
    if not path.exists(".cache"):
        try:
            os.mkdir(".cache")
        except OSError as ose:
            log_error("[ERROR] Creating of directory", colored(".cache", "blue"), "failed")
        else:
            log_info(f"Created cache directory at {path.abspath('.cache')}")

    if not path.exists("reports"):
        try:
            os.mkdir("reports")
        except OSError as ose:
            log_error("[ERROR] Creating of directory", colored("reports", "blue"), "failed")
        else:
            log_info(f"Created reports directory at {path.abspath('reports')}")

init()
cli()