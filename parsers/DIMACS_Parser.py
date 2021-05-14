import re

#------------------------------------------------------------------------------#

import utils.Logging as Logging

from utils.InputFormats import CNF
from utils.IO import hash_hex

#------------------------------------------------------------------------------#

class DIMACS_Parser: 

    @staticmethod
    def name():
        return "dimacs"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __init__(self, filename):
        self.filename = filename

    def parse(self):

        var_descs = {}

        nvars = 0
        nclauses = 0

        clauses = []

        with open(self.filename) as file:
            for line in file.readlines():
                m = re.match(r"(?P<type>[cp]) (?P<content>.*)", line)

                if m is None:
                    line = re.sub(r"[\n\r]", "", line)
                    clause = re.split(r"\s+", line)
                    clause = sorted([int(x) for x in clause if x != '0'], key = lambda x : abs(x))

                    isTautology = False

                    for i in range(0, len(clause)-1):
                        if clause[i] + clause[i+1] == 0:
                            Logging.log("Removed tautological clause", clause)
                            isTautology = True
                            break

                    if not isTautology:
                        clauses.append(clause)

                elif m["type"] == "c":
                    m = re.match(r"\s*(?P<id>[1-9][0-9]*) (?P<desc>\w+)", m["content"])

                    if m is not None:
                        var_descs[int(m["id"])] = m["desc"]

                elif m["type"] == "p":
                    m = re.match(r"\s*(?P<type>\w+) (?P<nvars>\d+) (?P<nclauses>\d+)", m["content"])

                    if m["type"] != "cnf":
                        print(f"[ERROR] Only CNFs are supported at this point, but type is ({m['type']})")

                    nvars = int(m["nvars"])
                    nclauses= int(m["nclauses"])

        if nclauses != len(clauses):
            print(f"[WARNING] Specified number of clauses ({nclauses}) differs from number of parsed ones ({len(clauses)}).")

        meta = {
            "input-name": self.filename,
            "input-hash": hash_hex(self.filename),
            "n_vars": nvars
        }

        return CNF(clauses, var_descs, meta)


