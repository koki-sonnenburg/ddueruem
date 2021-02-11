#!/usr/bin/env python3
import argparse

from copy import copy

from ctypes import *
import ctypes

from datetime import datetime, timedelta

import hashlib

import os.path
from os import path

import pprint

from random import shuffle
import re
import requests

import subprocess

import tarfile
from termcolor import colored

BUDDY_URL = "https://sourceforge.net/projects/buddy/files/buddy/BuDDy%202.4/buddy-2.4.tar.gz/download"
BUDDY_FILENAME = "buddy-2.4.tar.gz"
BUDDY_MD5 = "3b59cb073bcb3f26efdb851d617ef2ed"
BUDDY_SOURCES = "buddy-2.4"
BUDDY_SHAREDLIB = "./libbuddy.so"

#CUDD_URL = "https://davidkebo.com/source/cudd_versions/cudd-3.0.0.tar.gz"
#CUDD_FILENAME = "cudd-3.0.0.tar.gz"
#CUDD_MD5 = "4fdafe4924b81648b908881c81fe6c30"
#CUDD_SOURCES = "cudd-3.0.0"
#CUDD_SHAREDLIB = "./libcudd.so"

LIB_DEFAULT = "BUDDY"

verbose = False

### Log

def log_error(msg, *msgs):    
    print()
    print(colored("[ERROR]", "red", "on_white", attrs = ["bold"]), msg, *msgs)
    print()

def log_info(msg, *msgs):
    if verbose:
        print(colored("[INFO]", "blue", attrs = ["bold"]), msg, *msgs)

def log_warning(msg, *msgs):
    print(colored("[WARNING]", "yellow", attrs = ["bold"]), msg, *msgs)

### Download

def verify_hash(filepath, hash_should):
    with open(filepath, "rb") as f:
        hash_is = hashlib.md5()
        while chunk := f.read(8192):
            hash_is.update(chunk)

    hash_is = hash_is.hexdigest()

    if hash_is == hash_should:
        return True
    else:
        log_warning(f"Hash of {filepath} ({hash_is}) does not match expected hash ({hash_should})")

def untar(filepath):
    log_info(f"Unpacking {filepath}")

    with tarfile.open(filepath) as archive:
        archive.extractall(path = ".cache")        

### BDD general

class CNF:

    def __init__(self, filename, nvars, var_descs, clauses):
        self.filename = filename
        self.nvars = nvars
        self.var_descs = var_descs
        self.clauses = clauses

def satcount(top, nodes, cnf):
    
    count = 0

    stack = []
    stack.append((top, 0))

    while stack:
        node, depth = stack.pop()

        if node == 0:
            continue
        elif node == 1:
            count += 1 << (cnf.nvars - depth)
        else:
            _, low, high = nodes[node]
            stack.append((low, depth +1))
            stack.append((high, depth +1))

    return count

def force_compute_cog(clause, order):

    cog = sum([order.index(abs(x)) for x in clause])

    return cog / len(clause)


def force_compute_span(clauses, order):

    span = []
    #FIXME inefficient
    for clause in clauses:
        lspan = 0
        
        indizes = [order.index(abs(x)) for x in clause]
        lspan = max(indizes) - min(indizes)

        span.append(lspan)

    return sum(span)


def force(cnf, time_limit = 60, order = None):
    clauses = copy(cnf.clauses)  

    if order is None:
        order = list(range(1, cnf.nvars + 1))
        shuffle(order)

    span = force_compute_span(clauses, order)
    log_info(f"[FORCE] span = {span}")

    now = datetime.now()

    while datetime.now() - now < timedelta(seconds = time_limit):
        cogs_v = {}
        span_old = span

        for i, clause in enumerate(clauses):
            cogs = force_compute_cog(clause, order)

            for x in clause:
                x = abs(x)
                if x in cogs_v:
                    a,b = cogs_v[x]
                    cogs_v[x] = (a+cogs, b+1)
                else:
                    cogs_v[x] = (cogs, 1)

        tlocs = []
        for key, value in cogs_v.items():
            center, n = value
            tlocs.append((key, center / n))


        tlocs = sorted(tlocs, key = lambda x: x[1])

        order_old = copy(order)
        order = [x[0] for x in tlocs]

        span = force_compute_span(clauses, order)
        log_info(f"[FORCE] span = {span}")

        if span_old == span:
            break;

    return (order, span)


def force_triage(cnf, n1 = 32):

    orders = []

    for i in range(0, n1):
        log_info(f"Seeding ({i + 1}/{n1})")
        orders.append(force(cnf, 30))

    while len(orders) > 1:

        span_avg = sum([x for _,x in orders]) / len(orders)

        old_length = len(orders)

        orders = [(x,y) for x,y in orders if y <= span_avg]
        
        if len(orders) == old_length:
            break

        if verbose:
            print()
            print("[FORCE]", f"{span_avg:.3f}", f"{len(orders)}")
            print()

        orders2 = []

        for (order, span) in orders:
            orders2.append(force(cnf, 15, order))

        orders = orders2

    return orders[0]

def sort_clauses_by_span(clauses, order):
    
    spans = []
    order = [x + 1 for x in order]

    for clause in clauses:
        spans.append((clause, force_compute_span([clause], order) / (len(clause))))

    spans = sorted(spans, key = lambda x : x[1])

    return [x for x, _ in spans]

### IO

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

def init():

    # check if the .cache directory exists and create it otherwise
    if not path.exists(".cache"):
        try:
            os.mkdir(".cache")
        except OSError as ose:
            log_error("[ERROR] Creating of directory", colored(".cache", "blue"), "failed")
            pprint(ose)
        else:
            log_info(f"Created cache directory at {path.abspath('.cache')}")

    if not path.exists("reports"):
        try:
            os.mkdir("reports")
        except OSError as ose:
            log_error("[ERROR] Creating of directory", colored("reports", "blue"), "failed")
            pprint(ose)
        else:
            log_info(f"Created reports directory at {path.abspath('reports')}")

### BuDDy

def buddy_check():

    if not path.exists(BUDDY_SHAREDLIB):
        log_error("libbuddy.so not found, please execute", colored("setup.py --install-buddy", "blue"), "first.")
        return False

    buddy = CDLL(BUDDY_SHAREDLIB)

    buddy.bdd_init(1000, 1000)
    buddy.bdd_setvarnum(10)

    x = buddy.bdd_ithvar(0)
    y = buddy.bdd_ithvar(1)

    z = buddy.bdd_addref(buddy.bdd_and(x, y))

    success = buddy.bdd_nodecount(z) == 2
        
    buddy.bdd_done()

    return success

def buddy_download():

    archive = f".cache/{BUDDY_FILENAME}"

    req = requests.get(BUDDY_URL)

    with open(archive, "wb") as file:
        file.write(req.content)

    log_info(f"Downloaded BuDDy to", colored(archive, "blue"))

def buddy_setup():    
    sources = f".cache/{BUDDY_SOURCES}/"
    archive = f".cache/{BUDDY_FILENAME}"

    if path.exists(BUDDY_SHAREDLIB):
        log_info(colored(BUDDY_SHAREDLIB, "blue"), "already exists, skipping install")
        return 

    # verify if sources already exist
    if path.exists(sources):
        log_info("BuDDy sources exist")

        log_info("Configuring BuDDy sources")
        subprocess.run(['./configure', "CFLAGS=-fPIC -std=c99"], cwd = sources, stdout=subprocess.PIPE).stdout.decode('utf-8')

        log_info("Building BuDDy")
        subprocess.run(['make', 'buddy'], stdout=subprocess.PIPE).stdout.decode('utf-8')

        if buddy_check():
            log_info("BuDDy build:", colored("SUCCESS", "green", attrs = ["bold"]))
        else:
            log_info("BuDDy build failed", colored("FAIL", "red", attrs = ["bold"]))
    else:        
        log_info("BuDDy sources not found, looking for archive")
        if path.exists(archive):
            if verify_hash(archive, BUDDY_MD5):
                log_info("BuDDy archive found, unpacking")
                untar(archive)
                buddy_setup()
            else:
                log_info("Pass the", colored("--clean", "blue"), "flag to redownload")
        else:
            log_info("BuDDy archive not found, downloading")
            buddy_download()
            buddy_setup()


def buddy_build(cnf, order = None):

    if not path.exists(BUDDY_SHAREDLIB):
        log_error(colored(BUDDY_SHAREDLIB, "red"), "not found, please supply", colored("--install-buddy", "blue"))
        exit(1)

    buddy = CDLL("./libbuddy.so")

    increase = 100000
    buddy.bdd_init(1000000, 10000000)
    buddy.bdd_setvarnum(cnf.nvars)
    buddy.bdd_setminfreenodes(33)
    buddy.bdd_setmaxincrease(ctypes.c_int(increase))

    if order is None:            
        order = [x for x in range(0, cnf.nvars)]
    else:
        order = [x-1 for x in order]        
        arr = (ctypes.c_int * len(order))(*order)
        buddy.bdd_setvarorder(arr)

    clauses = sort_clauses_by_span(cnf.clauses, order)

    buddy.bdd_autoreorder(4)

    full = None
    n = 0

    for clause in clauses:
        n+=1

        if full:
            increase = int(max(increase, buddy.bdd_nodecount(full) / 10))
            increase = min(increase, 1000000)
            buddy.bdd_setmaxincrease(ctypes.c_int(increase))

        log_info(clause, f"({n} / {len(cnf.clauses)})")
        
        cbdd = None

        for x in clause:
            if x < 0:
                x = abs(x) - 1
                if cbdd is None:
                    cbdd = buddy.bdd_nithvar(x)
                else:
                    old = cbdd
                    cbdd = buddy.bdd_addref(buddy.bdd_or(cbdd, buddy.bdd_nithvar(x)))
                    buddy.bdd_delref(old)
            else:
                x -= 1
                if cbdd is None:
                    cbdd = buddy.bdd_ithvar(x)
                else:
                    old = cbdd
                    cbdd = buddy.bdd_addref(buddy.bdd_or(cbdd, buddy.bdd_ithvar(x)))
                    buddy.bdd_delref(old)

        if full is None:
            full = cbdd
        else:
            old = full
            full = buddy.bdd_addref(buddy.bdd_and(full, cbdd))

            buddy.bdd_delref(cbdd)
            buddy.bdd_delref(old)

    output_filename = f".cache/{os.path.basename(cnf.filename).split('.')[0]}.dd"
    buddy.bdd_fnsave(ctypes.c_char_p(output_filename.encode("utf-8")), full)

    buddy.bdd_done()

### CLI

def report(cnf, order):
    filename = f".cache/{os.path.basename(cnf.filename).split('.')[0]}.dd"

    if not path.exists(filename):
        log_error("No cached BDD found for", colored(cnf, "blue"))
        exit(1)

    with open(filename) as file:
        lines = file.readlines()
        lines = [re.sub(r"[\n\r]", "", x) for x in lines]

    nodes = {}
    last = None

    for line in lines[2:]:
        m = re.match(r"(?P<id>\d+) (?P<var>\d+) (?P<low>\d+) (?P<high>\d+)", line)
        nodes[int(m["id"])] = (int(m["var"]), int(m["low"]), int(m["high"]))
        last = int(m["id"])

    ssat = satcount(last, nodes, cnf)

    print("--------------------------------")
    print(f"Results for {colored(cnf.filename, 'blue')}:")
    print("#SAT:", ssat, sep = "\t")
    print("Nodes:", len(lines) - 2, sep = "\t")
    print("Order:", order, sep = "\t")
    print("--------------------------------")

    report_filename = f"reports/{os.path.basename(cnf.filename).split('.')[0]}.rep"

    with open(report_filename, "w") as file:
        file.write(f"{cnf.filename}{os.linesep}")
        file.write(f"#SAT:{ssat}{os.linesep}")
        file.write(f"#NODES:{len(nodes)}{os.linesep}")
        file.write(f"Order:{','.join([str(x) for x in order])}{os.linesep}")

def cli():
    global verbose

    parser = argparse.ArgumentParser(description="Wrapper for BuDDy and CUDD.")
    parser.add_argument("file", nargs = "?", default=None)
    parser.add_argument("--install-buddy", help = "Install BuDDy.", dest = "lib_install", action = "append_const", const = "BUDDY", default=[])
    parser.add_argument("--install-cudd", help = f"Install CUDD. {colored('[Currently disabled]', 'red')}", dest = "lib_install", action = "append_const", const = "CUDD", default=[])
    parser.add_argument("--verbose", help = "Enable verbose output", dest = "verbose", action = "store_true", default = False)
    parser.add_argument("--order-force", help = "Order the variables with FORCE algorithm for <= 60 seconds.", dest = "order_force", action = "store_true", default = False)
    parser.add_argument("--order-force-triage", help = "Order the variables with FORCE algorithm and triage heuristic (~630 seconds)", dest = "order_triage", action = "store_true", default = False)
    parser.add_argument("--order-clean", help = "Do not use cached order", dest = "order_clean", action = "store_true", default = False)

    args = parser.parse_args()
    verbose = args.verbose    
    lib_install = args.lib_install

    _verbose = verbose
    verbose = True
    for lib in lib_install:
        log_info(f"Installing {lib}")

        if lib == "CUDD":
            log_error("Support for CUDD not available")
            exit(1)
        elif lib == "BUDDY":
            buddy_setup()
        else:
            log_warning(f"{lib} unknown, ignoring")    
    verbose = _verbose

    if args.file is None:
        return

    filename = args.file

    filename_cache = f".cache/{os.path.basename(filename).split('.')[0]}.ddueruem"

    if not path.exists(filename):
        log_error("File", colored(filename, "red"), "not found. Aborting.")
        exit(1)

    cnf = parse_dimacs(filename)
  
    order = [x+1 for x in range(0, cnf.nvars)]
    
    if path.exists(filename_cache) and not args.order_clean:
        
        if args.order_force or args.order_triage:
            log_warning("Using cached order, as", colored("--order-clean"), "was not supplied")

        raw = []

        with open(filename_cache) as file:
            raw = file.readlines()

        order = re.split(";", re.sub(r"[\r\n]", "", raw[1]))
        order = [int(x) for x in order]

    else:
        if args.order_force or args.order_triage:
            if args.order_force and args.order_triage:
                log_error("Both the", colored("--order-force", "red"), "and", colored("--order-force-triage", "red"), "flags are present. Please remove one.")
                exit(1)

            if args.order_force:
                order, span = force(cnf)
            elif args.order_triage:
                order, span = force_triage(cnf)

            with open(filename_cache, "w") as file:
                file.write(f"{span}{os.linesep}")
                file.write(";".join([str(x) for x in order]))
                file.write(f"{os.linesep}")

    buddy_build(cnf, order)
    report(cnf, order)

init()
cli()