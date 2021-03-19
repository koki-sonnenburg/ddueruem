import copy
import re

from .IO import hash_hex, timestamp
from .Expression import Expression

from .UnicodeCharacterMap import u_bool_and as u8and
from .UnicodeCharacterMap import u_bool_or as u8or

class CNF(Expression):
    __slots__ = "meta", "clauses", "var2desc"

    def __init__(self, clauses, var2desc, meta = {}):
        self.meta = meta
        self.clauses = clauses
        self.var2desc = var2desc

    def __str__(self):
        out = copy(clauses)
        out = [f"({f' {u8or} '.join(c)})" for c in out]

        return f" {b8and} ".join(out)

    def get_no_variables(self):
        return len(self.var2desc)

    @staticmethod
    def from_DIMACS(filename):
        var2desc = {}

        nvars = 0
        nclauses = 0

        clauses = []

        with open(filename) as file:
            lines = file.readlines()

        for line in lines:
            m = re.match(r"(?P<type>[cp]) (?P<content>.*)", line)

            if m is None:
                line = re.sub(r"[\n\r]", "", line)
                clause = re.split(r"\s+", line)
                clause = [int(x) for x in clause if x != '0']
                
                clauses.append(clause)

            elif m["type"] == "c":
                m = re.match(r"\s*(?P<id>[1-9][0-9]*) (?P<desc>\w+)", m["content"])

                if m is not None:
                    var2desc[m["id"]] = m["desc"]

            elif m["type"] == "p":
                m = re.match(r"\s*(?P<type>\w+) (?P<nvars>\d+) (?P<nclauses>\d+)", m["content"])

                if m["type"] != "cnf":
                    print(f"[ERROR] Only CNFs are supported at this point, but type is ({m['type']})")

                nvars = int(m["nvars"])
                nclauses= int(m["nclauses"])

        if nclauses != len(clauses):
            print(f"[WARNING] Specified number of clauses ({nclauses}) differs from number of parsed ones ({len(clauses)}).")

        meta = {
            "filename": filename,
            "filename_hash": hash_hex(filename),
            "timestamp": timestamp()
        }

        return CNF(clauses, var2desc, meta)

