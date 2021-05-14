from copy import copy

import networkx as nx

from datetime import datetime, timedelta
from random import shuffle
from utils.Logging import log

class DBO:

    @staticmethod
    def name():
        return f"DBO"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __init__(self, variant = None):
        self.variant = variant

    def run(self, expr, order):
        return dbo(expr)

    def provides_clause_ordering(self):
        return True

    def order_clauses(self, clauses, order):
        
        return clauses
        
        n_variables = len(order)

        var2clauses = [[] for x in range(0, n_variables + 1)]

        for i, clause in enumerate(clauses):

            y = min([abs(z) for z in clause])

            for x in clause:
                var2clauses[abs(x)].append(i)

        G = nx.Graph()

        for i in range(1, n_variables + 1):
            G.add_node(i)

        for i, group in enumerate(var2clauses):
            for x in group:
                for y in group:
                    if x >= y:
                        continue

                    G.add_edge(x, y)

        order = list(G.degree())
        order = sorted(order, key = lambda x : -x[1])

        order = [x for x,_ in order]

        H = nx.DiGraph()
        ls = [order[0]]
        done = set()

        while ls:
            x = ls.pop()
            if x in done:
                continue
            else:
                done.update([x])

            ns = list(G.neighbors(x))

            for y in ns:
                if H.has_edge(x,y) or H.has_edge(y,x):
                    continue

                if G.degree[x] < G.degree[y]:
                    H.add_edge(y,x)
                else:
                    H.add_edge(x,y)

            ls.extend(ns)

        order = list(nx.topological_sort(H))

        out = []

        for x in order:
            out.append(clauses[x])

        return out

def dbo(expr):

    n_variables = expr.get_no_variables()
    clauses = expr.clauses

    var_groups = [[] for x in range(0, n_variables + 1)]

    for i, clause in enumerate(clauses):

        y = min([abs(z) for z in clause])

        for x in clause:
            var_groups[y].append(abs(x))

    G = nx.Graph()

    for i in range(1, n_variables + 1):
        G.add_node(i)

    for group in var_groups:
        for x in group:
            for y in group:
                if x >= y:
                    continue

                G.add_edge(x,y)

    order = list(G.degree())
    order = sorted(order, key = lambda x : -x[1])

    order = [x for x,_ in order]

    H = nx.DiGraph()

    ls = [order[0]]
    done = set()

    while ls:
        x = ls.pop()
        if x in done:
            continue
        else:
            done.update([x])

        ns = list(G.neighbors(x))

        for y in ns:

            if H.has_edge(x,y) or H.has_edge(y,x):
                continue

            if G.degree[x] < G.degree[y]:
                H.add_edge(y,x)
            else:
                H.add_edge(x,y)

        ls.extend(ns)

    return list(nx.topological_sort(H))