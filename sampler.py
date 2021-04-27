#!/usr/bin/env python3
#------------------------------------------------------------------------------#

import argparse             

import numpy as np
import random
import re

from pprint import pprint

#------------------------------------------------------------------------------#

import config
from ddueruem import init
import adapters.Adapters as Adapters
import utils.IO as Utils
import utils.Logging as Logging

#------------------------------------------------------------------------------#

def satcount(adj_list, root, n_variables):
    count = 0

    stack = []
    stack.append((root, 0))

    while stack:
        node, depth = stack.pop()

        if node == 1:
            count += 1 << (n_variables - depth)
        elif node != 0:
            low = adj_list[node][0]
            high = adj_list[node][1]

            stack.append((low, depth +1))
            stack.append((high, depth +1))

    return count

def load_bdd_from_file(filename):

    #FIXME: No support for complement edges => USE BUDDY

    with open(filename) as file:
        lines = re.split("[\n\r]", file.read())

    m = 0

    data = {}

    for i, line in enumerate(lines):
        if line == "----":
            m = i
            break

        line = re.split(":", line)
        data[line[0]] = line[1:]

    nodes = []    

    for line in lines[m+1:]:
        m = re.match(r"(?P<id>\d+) (?P<var>\d+) (?P<low_ce>\d):(?P<low>\d+) (?P<high_ce>\d):(?P<high>\d+)", line)
        if m:
            nodes.append((int(m["id"]), int(m["var"]), int(m["low_ce"]) == 1, int(m["low"]), int(m["high_ce"]) == 1, int(m["high"])))

    adj_list = np.zeros((len(nodes)+2, 2), int)
    adj_list[1][:] = 1

    k = 2

    old2new = {0:0, 1:1}

    for node in nodes:
        id, _, _, _, _, _ = node


        old2new[id] = k
        k += 1

    variables = set()
    node2var = {}

    for node in nodes:
        id, var, lce, l, hce, h = node

        variables.update([var])

        id = old2new[id]
        l = old2new[l]
        h = old2new[h]

        node2var[id] = var + 1

        adj_list[id][0] = l
        adj_list[id][1] = h

    root = old2new[int(data["root"][1])]

    return adj_list, root, node2var, len(variables), data

def sample(adj_list, node2var, n_variables, n_sat, n = 10):

    Logging.log_info(f"Generating", Logging.highlight(f"{n}"), "distinct sample(s) of", Logging.highlight(f"{n_sat}"), "valid products.")

    lookup = dict()

    for i, array in enumerate(adj_list):
        low = array[0]
        high = array[1]
        
        if i == low or i == high:
            continue

        if low in lookup:
            lows, highs = lookup[low]
            lows.append(i)
            lookup[low] = (lows, highs)
        else:
            lookup[low] = ([i], [])

        if high in lookup:
            lows, highs = lookup[high]
            highs.append(i)
            lookup[high] = (lows, highs)
        else:
            lookup[high] = ([], [i])

    samples = set()
    while len(samples) < n:
        walk = random_walk(lookup,node2var, n_variables, 1)
        walk = [str(x) for x in walk]
        samples.update([(" ".join(walk))])

    return samples

def random_walk(lookup, node2var, n_variables, node):

    walk = []
    free_variables = list(range(1, n_variables + 1))

    while node in lookup:

        lows, highs = lookup[node]

        if lows and highs:
            if random.randint(0,1) == 0:
                ls = lows
            else:
                ls = highs
        else:
            if lows:
                ls = lows
            else:
                ls = highs

        node = ls[random.randint(0, len(ls) - 1)]

        if ls == lows:
            walk.append(-node2var[node])
        else:
            walk.append(node2var[node])

    used_variables = [abs(x) for x in walk]
    free_variables = sorted(list(set(free_variables) - set(used_variables)))

    if len(free_variables) != 0:
        n = random.randint(0, len(free_variables))
        free_variables = sorted(random.sample(free_variables, n))

        walk.extend(free_variables)

    walk = sorted([x for x in walk if x > 0])

    return walk

#------------------------------------------------------------------------------#

def cli():
    parser = argparse.ArgumentParser(description=format("cli_setup_desc"))
    
    # IO Toggles

    parser.add_argument("file", help = "file to compute samples for", type = str)
    parser.add_argument("--n", help = "Number of Samples", default = 1, type = int)
    parser.add_argument("--silent", help = format("cli--silent"), dest = "silent", action = "store_true", default = False)    

    args = parser.parse_args()

    init(root_script = __file__, silent = args.silent)

    adj_list, root, node2var, n_variables, data = load_bdd_from_file(args.file)

    n_sat = satcount(adj_list, root, n_variables)

    n_samples = min(args.n, n_sat)

    if n_samples == 0:
        n_samples = n_sat

    outfile = f"{Utils.basename(data['input-name'][0])}-{n_samples}.samples"

    samples = sample(adj_list, node2var, n_variables, n_sat, n_samples)

    samples = sorted(samples, key = lambda x : len(x))

    Logging.log_info("Done! Samples stored to:", Logging.highlight(f"{outfile}"))

    samples = "\n".join(samples) + "\n"

    with open(outfile, "w+") as file:
        file.write(samples)

#------------------------------------------------------------------------------#

if __name__ == "__main__":
    cli()