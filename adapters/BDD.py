import time

from utils.IO import basename, timestamp
from .Adapters import get_lib, get_meta


class BDD:

    def __init__(self, lib):
        self.lib = get_lib(lib)
        self.mgr = self.lib.Manager()
        self.meta = get_meta(self.lib)


    def __enter__(self):

        self.mgr.init()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        
        self.mgr.exit()


    def buildFrom(self, input, order = None):

        if input.get_stub() == "cnf":
            self.fromCNF(input, order)
        else:
            raise NotImplementedError

    def fromCNF(self, cnf, order = None):

        lib = self.lib
        mgr = self.mgr

        self.no_variables = cnf.get_no_variables()
        self.meta.update(cnf.get_meta())

        if lib.requires_variable_advertisement:
            mgr.set_no_variables(self.no_variables)

        varmod = 0
        if lib.has_zero_based_indizes:
            varmod = 1

        if order:
            mgr.set_order(order)

#         self.set_dynorder(dynorder)
#         buddy.bdd_setvarorder(arr)

        time_start = time.time()

        bdd = mgr.one_()

        for clause in cnf.clauses:

            clause_bdd = mgr.zero_()

            for x in clause:

                y = abs(x) - varmod
                
                if x < 0:
                    clause_bdd = mgr.or_(clause_bdd, mgr.nithvar_(y))
                else:
                    clause_bdd = mgr.or_(clause_bdd, mgr.ithvar_(y))

            bdd = mgr.and_(bdd, clause_bdd)

        time_stop = time.time()

        self.meta["lib-runtime"] = f"{time_stop - time_start} s"
        self.bdd = bdd

    def dump(self, filename = None):

        if filename is None:
            filename = f"{basename(self.meta['input-name'])}-{self.lib.stub}.bdd"

        self.mgr.dump(self.bdd, filename, no_variables = self.no_variables, meta = self.meta)