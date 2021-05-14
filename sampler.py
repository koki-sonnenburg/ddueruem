#!/usr/bin/env python3
#------------------------------------------------------------------------------#

import argparse             
from copy import copy
import numpy as np
import random
import re

import statistics

from pprint import pprint

#------------------------------------------------------------------------------#

import config
from ddueruem import init
import adapters.Adapters as Adapters
import utils.IO as Utils
import utils.Logging as Logging

#------------------------------------------------------------------------------#

def satcount(adj_list, node2var, var2nodes, order, root):
    
    stack = []
    stack.append(root)

    while stack:
        node = stack.pop()

        # print(node)

        if node < 2:
            continue    

        low = adj_list[node][0]
        high = adj_list[node][1]

        visitLow = False
        visitHigh = False

        if adj_list[low][2] > 0 or low < 2:
            if low > 0:
                if low < 2:
                    child_index = len(order)
                else:
                    child_index = order.index(node2var[low])

                adj_list[node][2] = adj_list[low][2] * (1 << (child_index - order.index(node2var[node]) - 1))
        else:
            visitLow = True

        if adj_list[high][2] > 0 or high < 2:
            if high > 0:
                if high < 2:
                    child_index = len(order)
                else:
                    child_index = order.index(node2var[high])

                adj_list[node][2] += adj_list[high][2] * (1 << (child_index - order.index(node2var[node]) - 1))
        else:
            visitHigh = True

        if visitLow or visitHigh:
            stack.append(node)
            if visitLow:
                stack.append(low)

            if visitHigh:
                stack.append(high)

    return adj_list[root][2]

def get_commonality(adj_list, node2var, root, n_variables):
    count = 0
    counts = [0] * (n_variables + 1)

    stack = []
    stack.append((root, 0, []))

    while stack:
        node, depth, path = stack.pop()

        if node == 1:

            ccount = 1 << (n_variables - depth)
            count += ccount

            x = 1

            path = sorted(path, key = lambda x : abs(x))

            for j in range(0, len(path)):
                while x < abs(path[j]):
                    counts[x] += (ccount >> 1)
                    x += 1

                if path[j] > 0:
                    counts[x] += ccount
                
                x += 1

            while x < len(counts):
                counts[x] += (ccount >> 1)
                x += 1

        elif node != 0:

            lpath = copy(path)
            hpath = copy(path)

            lpath.append(-node2var[node])
            hpath.append(node2var[node])

            low = adj_list[node][0]
            high = adj_list[node][1]

            stack.append((low, depth +1, lpath))
            stack.append((high, depth +1, hpath))

    counts[0] = count

    return counts

def load_bdd_from_file(filename):

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

    adj_list = np.zeros((len(nodes)+2, 5), int)

    adj_list[1][:3] = 1

    k = 2

    old2new = {0:0, 1:1}

    for node in nodes:
        id, _, _, _, _, _ = node


        old2new[id] = k
        k += 1

    variables = set(range(1, int(data["n_vars"][0]) + 1))
    node2var = {}
    var2nodes = {}

    for node in nodes:
        id, var, lce, l, hce, h = node

        var += 1

        id = old2new[id]
        l = old2new[l]
        h = old2new[h]

        node2var[id] = var

        if var in var2nodes:
            var2nodes[var].append(id)
        else:
            var2nodes[var] = [id] 

        adj_list[id][0] = l
        adj_list[id][1] = h

    root = old2new[int(data["root"][1])]

    return adj_list, root, node2var, var2nodes, variables, data

def uniform_random_sample(adj_list, node2var, n_variables, n_sat, n = 10, valid = True, unqiue = True):

    if n == 0:
        return []

    if valid:
        start = 1
        Logging.log_info(f"Generating", Logging.highlight(f"{n}"), "distinct uniform random sample(s) of", Logging.highlight(f"{n_sat}"), "valid products.")
    else:
        start = 0
        Logging.log_info(f"Generating", Logging.highlight(f"{n}"), "distinct uniform random sample(s) of", Logging.highlight(f"{2**n_variables - n_sat}"),"invalid products.")

    lookup = dict()

    for i, array in enumerate(adj_list):
        low = array[0]
        high = array[1]
        lw = array[2]
        hw = array[3]

        if i == low or i == high:
            continue

        if lw > 0:
            if low in lookup:
                adjs, weights = lookup[low]
                adjs.append((-i, lw))
                lookup[low] = (adjs, weights + lw)
            else:
                lookup[low] = ([(-i, lw)], lw)

        if hw > 0:
            if high in lookup:
                adjs, weights = lookup[high]
                adjs.append((i, hw))
                lookup[high] = (adjs, weights + hw)
            else:
                lookup[high] = ([(i, hw)], hw)

    # print(lookup)
    
    if unqiue:
        samples = set()
        while len(samples) < n:
            walk = random_walk(lookup, node2var, n_variables, start)
            walk = [str(x) for x in walk]
            if walk:
                samples.update([(" ".join(walk))])

        samples = [[int(y) for y in re.split(r"\s", x)] for x in samples]

        samples = sorted(samples, key = lambda x : len(x))

    else:
        samples = []
        while len(samples) < n:
            walk = random_walk(lookup,node2var, n_variables, start)
            samples.append(walk)

        samples = sorted(samples, key = lambda x : len(x))

    return samples

def full(adj_list, node2var, variables, valid = True):

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


    products = []

    if valid:
        stack = [(1, [], [])]
    else:
        stack = [(0, [], [])]


    k = 0
    while stack:
        k += 1
        node, selected, deselected = stack.pop()

        if node in lookup:
            lows, highs = lookup[node]

            for low in lows:
                deselected2 = copy(deselected)
                deselected2.append(node2var[low])
                stack.append((low, selected, deselected2))

            for high in highs:
                selected2 = copy(selected)
                selected2.append(node2var[high])
                stack.append((high, selected2, deselected))
        else:
            bound = copy(selected)
            bound.extend(deselected)
            free = list(set(variables) - set(bound))
            products.append((sorted(selected), sorted(deselected), sorted(free)))

    return products

def random_walk(lookup, node2var, n_variables, node):

    walk = []
    free_variables = list(range(1, n_variables + 1))

    while node in lookup:

        adjs, weights = lookup[node]

        pos = random.randint(0, weights)

        #FIXME: Replace by binary search and increasing weights
        acc = 0
        for x in adjs:
            node, weight = x
            
            acc += weight

            if pos <= acc:
                break

        isLow = node < 0
        node = abs(node)

        if isLow:
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

def generate_XML_header(n_samples, n_variables):
    header = []

    for var in range(0, n_variables + 1):
        cells = []
        for x in range(0, n_samples):
            cells.append(f"//@rows.{x}/@cells.{var}")

        cells = " ".join(cells)

        if var < n_variables:
            header.append(f"    <ports xsi:type=\"InputPort\" name = \"{var + 1}\" cells = \"{cells}\" />")
        else:
            header.append(f"    <ports xsi:type=\"OutputPort\" name = \"out\" cells = \"{cells}\" />")

    return "\n".join(header) + "\n"

def generate_XML_content(samples, n_variables, cell_out_value = "true"):

    out = []

    for sample in samples:
        selected, deselected, free = sample

        cells = []

        for x in selected:
            cells.append((x, "true"))

        for x in deselected:
            cells.append((x, "false"))

        cells = [f'        <cells value = "{x[1]}" port = "//@ports.{i}/" />' for i, x in enumerate(cells)]
        cells.append(f'        <cells value = "{cell_out_value}" port = "//@ports.{n_variables}/" />')
        cells = "\n".join(cells)

        row = f"    <rows>\n{cells}\n    </rows>"

        out.append(row)

    return "\n".join(out)

def filter(samples, fixed_true, variables):

    out = []

    variables = set(copy(variables) - fixed_true)
    variables = sorted(list(variables))

    old2new = {}

    for i in range(1, len(variables)+1):
        old2new[variables[i-1]] = i

    # print(old2new)

    for sample in samples:
        
        sel, de, free = sample

        keep = True

        for x in fixed_true:
            if x in de:
                keep = False
                break

        if not keep:
            continue

        sel = set(sel)
        free = set(free)

        free = list(free - fixed_true)

        print(sel)
        print(fixed_true)
        sel = list(sel - fixed_true)
        print(sel)

        sel = [old2new[x] for x in sel]
        de = [old2new[x] for x in de]
        free = [old2new[x] for x in free]

        out.append((sel, de, free))

    return out

def get_core_features(ls, variables):

    counter = [0] * (len(variables) + 1)

    for sample in ls:
        sel, _, _ = sample

        for x in sel:
            counter[x] += 1

    cores = [i for i, x in enumerate(counter) if x == len(ls)]
    true_choices = [i for i, x in enumerate(counter) if x > 0 and x != len(ls)]

    return cores, true_choices

def r_score(samples, commonality):

    occ = [0] * len(commonality)

    occ[0] = len(samples)

    for sample in samples:
        for x in sample:
            if x > 0:
                occ[x] += 1


    deltas = []

    for i in range(1, len(occ)):

        sample_ratio = occ[i] / occ[0]
        commonality_ratio = commonality[i] / commonality[0]

        delta = commonality_ratio - sample_ratio
        deltas.append(delta)

        print(i, f"{100 * sample_ratio:3.2f}%", f"{100 * commonality_ratio:3.2f}%", f"{100 * (delta):3.2f}%")

    print("-" * 32)
    print(f"Avg:\t{100 * sum(deltas) / len(deltas):2.4f}% +/- {100*statistics.stdev(deltas):2.4f}%")


def compute_edges(adj_list, root, node2var, n_variables):

    stack = []
    stack.append((root, 0, [], True))

    while stack:
        node, depth, path, wasHigh = stack.pop()

        if node == 1:

            ccount = n_variables - depth

            npath = copy(path)

            if wasHigh:
                npath.append(1)
            else:
                npath.append(-1)

            for i in range(0, len(npath) - 1):
                u = abs(npath[i])
                v = npath[i+1]

                if v < 0:
                    adj_list[u][2] += ccount
                else:
                    adj_list[u][3] += ccount

        elif node != 0:

            npath = copy(path)

            if wasHigh:
                npath.append(node)
            else:
                npath.append(-node)

            low = adj_list[node][0]
            high = adj_list[node][1]

            stack.append((low, depth +1, npath, False))
            stack.append((high, depth +1, npath, True))

    return adj_list


#------------------------------------------------------------------------------#

def cli():
    parser = argparse.ArgumentParser(description=format("cli_setup_desc"))
    
    # IO Toggles

    parser.add_argument("file", help = "file to compute samples for", type = str)
    parser.add_argument("--silent", help = format("cli--silent"), dest = "silent", action = "store_true", default = False)    

    args = parser.parse_args()

    init(root_script = __file__, silent = args.silent)

    adj_list, root, node2var, var2nodes, variables, data = load_bdd_from_file(args.file)

    order = data["order"]
    order = [int(x) for x in re.split(r",", order[0])]
   
    print("Loaded")

    n_variables = len(variables)
    n_sat = satcount(adj_list, node2var, var2nodes, order, root)

    print(n_sat)
    # adj_list = compute_edges(adj_list, root, node2var, n_variables)

    # commonality = get_commonality(adj_list, node2var, root, n_variables)
    samples = uniform_random_sample(adj_list, node2var, n_variables, n_sat, n = 10000, valid = True, unqiue = False)

    # pprint(samples)

    # r_score(samples, commonality)
    # pprint(samples)

#------------------------------------------------------------------------------#

if __name__ == "__main__":
    cli()


    # # n_sat = satcount(adj_list, root, len(variables))

    # # fixed_true = set(random.sample(list(variables), 12))
    # # fixed_false = set(random.sample(list(fixed_true), 6))
    # # fixed_true = fixed_true - fixed_false

    # valids = full(adj_list, node2var, variables)
    # valids = sorted(valids, key = lambda x : len(x[0]))

    # cores, true_choices = get_core_features(valids, variables)

    # fixed_true = cores
    # fixed_true.extend(random.sample(list(set(variables) - set(cores)), n - len(cores)))
    # fixed_true = set(fixed_true)

    # fixed_false = set()

    # print(cores)
    # print(true_choices)

    # print(fixed_true)

    # invalids = full(adj_list, node2var, variables, False)
    # invalids = sorted(invalids, key = lambda x : len(x[0]))

    # valids = filter(valids, fixed_true, variables)
    # invalids = filter(invalids, fixed_true, variables)

    # basename = Utils.basename(data['input-name'][0])
    # appendix = "_".join([str(x) for x in sorted(list(fixed_true))])

    # outfile = f"{config.CACHE_DIR}/{basename}-T_{appendix}-{len(valids)}-{len(invalids)}.xml"

    # out = []
    # out.append(f'<?xml version="1.0" encoding="ISO-8859-1"?>')
    # out.append(f'<TruthTable xmi:version="2.0" xmlns:xmi="http://www.omg.org/XMI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="TT" name="{basename}-T_{appendix}">')
    # out.append(generate_XML_header(len(valids) + len(invalids), len(variables) - len(fixed_true) - len(fixed_false)))

    # out.append(generate_XML_content(valids, len(variables) - len(fixed_true) - len(fixed_false)))
    # out.append(generate_XML_content(invalids, len(variables) - len(fixed_true) - len(fixed_false), "false"))

    # out.append("</TruthTable>")

    # out = "\n".join(out) + "\n"

# # 
#     parser.add_argument("--valid", help = "Number of Samples for valid products", default = 1, type = int)
#     parser.add_argument("--invalid", help = "Number of Samples for invalid products", default = 0, type = int)
    # n_samples = min(args.valid + args.invalid, n_sat)

    # outfile = f"{config.CACHE_DIR}/{basename}-{n_samples}-{args.valid}-{args.invalid}.xml"

    # vsamples = sample(adj_list, node2var, n_variables, n_sat, args.valid, True)
    # isamples = sample(adj_list, node2var, n_variables, n_sat, args.invalid, False)

    # vsamples = sorted(vsamples, key = lambda x : len(x))
    # isamples = sorted(isamples, key = lambda x : len(x))

    # Logging.log_info("Done! Samples stored to:", Logging.highlight(f"{outfile}"))

    # out = []
    # out.append(f'<?xml version="1.0" encoding="ISO-8859-1"?>')
    # out.append(f'<TruthTable xmi:version="2.0" xmlns:xmi="http://www.omg.org/XMI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="TT" name="{basename}-{n_samples}-{args.valid}-{args.invalid}">')
    # out.append(generate_XML_header(n_samples, n_variables))

    
    # if isamples:
    #     out.append(generate_XML_content(isamples, n_variables, "false"))

    # out.append("</TruthTable>")

    # out = "\n".join(out) + "\n"

    # with open(outfile, "w+") as file:
    #     file.write(out)