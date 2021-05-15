from datetime import datetime

from utils.IO import basename, timestamp, format_runtime, bulk_format
from .Adapters import get_lib, get_meta

import utils.Caching as Caching
import utils.Logging as Logging

class timeout:
    def __init__(self, seconds=1, error_message='Timeout'):
        self.seconds = seconds
        self.error_message = error_message
    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)
    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)
    def __exit__(self, type, value, traceback):
        signal.alarm(0)

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

        mgr.dvo = "off"

    def set_dvo(self, dvo_stub):
        if self.mgr is None:
            Logging.log_warning("BDD manager not initialized, not setting DVO.")
            return

        dvo_options = self.lib.dvo_options

        self.mgr.dvo = dvo_stub

        if dvo_stub == "off":
            self.mgr.disable_dvo()
        else:
            if dvo_stub in dvo_options:
                self.mgr.enable_dvo(dvo_options[dvo_stub])
            else:
                Logging.log_warning(f"Library {lib.name} does not support DVO {dvo_stub}")
                self.mgr.disable_dvo()

    def get_dvo(self):
        return self.mgr.dvo

    def list_available_dvo_options(self):
        ls = [x for x, _ in self.lib.dvo_options.items()]

        print(f"Available DVO options for {self.lib.name}:", bulk_format(Logging.highlight(", ".join(ls)), color = "blue"))

    def fromCNF(self, cnf, order = None):

        bdd = self.bdd
        lib = self.lib
        mgr = self.mgr

        if bdd is None:
            self.init(cnf.get_no_variables(), cnf.get_meta(), order)
            bdd = mgr.one_()

        time_start = datetime.now()

        for i, clause in enumerate(cnf.clauses):

            Logging.log_info(f"{i + 1} / {len(cnf.clauses)} ({100*(i+1)/len(cnf.clauses):3.1f}%)")

            clause_bdd = mgr.zero_()

            for x in clause:

                y = abs(x) - self.varmod
                
                if x < 0:
                    clause_bdd = mgr.or_(clause_bdd, mgr.nithvar_(y))
                else:
                    clause_bdd = mgr.or_(clause_bdd, mgr.ithvar_(y))


            try:
                bdd = mgr.and_(bdd, clause_bdd)            

            except StopIteration:
                print("Skipping clause", i + 1, "due to timeout")

        time_stop = datetime.now()

        self.meta["runtime-compilation"] = format_runtime(time_stop - time_start)
        self.bdd = bdd

    def dump(self, filename = None):

        if filename is None:
            filename = Caching.get_artifact_cache(self.meta['input-name'], self.lib.stub, self.mgr.dvo)

        Logging.log_info("Dumpfile:", Logging.highlight(filename))

        self.mgr.dump(self.bdd, filename, no_variables = self.no_variables, meta = self.meta)

        return filename