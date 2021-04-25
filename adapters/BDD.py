from datetime import datetime

from config import CACHE_DIR
from utils.IO import basename, timestamp, format_runtime
from .Adapters import get_lib, get_meta
import utils.Logging as Logging

class BDD:

    def __init__(self, lib):
        self.bdd = None
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
        elif input.get_stub() == "fm":
            self.fromFM(input, order)
        else:
            raise NotImplementedError(f"\"{input.get_stub()}\"")

    def init(self, no_variables, meta = {}, order = None):
        lib = self.lib
        mgr = self.mgr

        self.no_variables = no_variables
        self.meta.update(meta)

        if lib.requires_variable_advertisement:
            mgr.set_no_variables(self.no_variables)

        self.varmod = 0
        if lib.has_zero_based_indizes:
            self.varmod = 1

        if order:
            mgr.set_order(order)


    def fromCNF(self, cnf, order = None):

        bdd = self.bdd
        lib = self.lib
        mgr = self.mgr

        if bdd is None:
            self.init(cnf.get_no_variables(), cnf.get_meta(), order)
            bdd = mgr.one_()

        time_start = datetime.now()

        for i, clause in enumerate(cnf.clauses):

            Logging.log_info(f"{i + 1} / {len(cnf.clauses)} ({100*(i+1)/len(cnf.clauses):.1f}%)")

            clause_bdd = mgr.zero_()

            for x in clause:

                y = abs(x) - self.varmod
                
                if x < 0:
                    clause_bdd = mgr.or_(clause_bdd, mgr.nithvar_(y))
                else:
                    clause_bdd = mgr.or_(clause_bdd, mgr.ithvar_(y))

            bdd = mgr.and_(bdd, clause_bdd)

        time_stop = datetime.now()

        if "lib-runtime" in self.meta:
            self.meta["lib-runtime"].append(format_runtime(time_stop - time_start))
        else:
            self.meta["lib-runtime"] = [format_runtime(time_stop - time_start)]

        self.bdd = bdd

    def dump(self, filename = None):

        if filename is None:
            filename = Caching.get_artifact_cache_filename(self.meta['input-name'], self.lib.stub)

        Logging.log_info("Dumpfile:", Logging.highlight(filename))

        self.mgr.dump(self.bdd, filename, no_variables = self.no_variables, meta = self.meta)

        return filename


    # def fromFM(self, fm, order = None):

    #     self.fromCNF(fm.expr_fd)

    #     for ast in fm.expr_ctcs:
    #         self.fromAST(ast)

    # def fromAST(self, ast, order = None):

    #     bdd = self.bdd
    #     lib = self.lib
    #     mgr = self.mgr

    #     if bdd is None:
    #         self.init(cnf.get_no_variables(), cnf.get_meta(), order)
    #         bdd = mgr.one_()

        
    #     time_start = datetime.now()

    #     for clause in cnf.clauses:

    #         clause_bdd = mgr.zero_()

    #         for x in clause:

    #             y = abs(x) - self.varmod
                
    #             if x < 0:
    #                 clause_bdd = mgr.or_(clause_bdd, mgr.nithvar_(y))
    #             else:
    #                 clause_bdd = mgr.or_(clause_bdd, mgr.ithvar_(y))

    #         bdd = mgr.and_(bdd, clause_bdd)

    #     time_stop = datetime.now()

    #     if "lib-runtime" in self.meta:
    #         self.meta["lib-runtime"].append(format_runtime(time_stop - time_start))
    #     else:
    #         self.meta["lib-runtime"] = [format_runtime(time_stop - time_start)]

    #     self.bdd = bdd
