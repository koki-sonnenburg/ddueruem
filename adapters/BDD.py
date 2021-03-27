from .Adapters import get_lib

class BDD:

    def __init__(self, lib):
        self.lib = get_lib(lib)
        self.mgr = self.lib.Manager()

    def __enter__(self):

        self.mgr.init()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        
        self.mgr.exit()


    def fromCNF(self, cnf):

        lib = self.lib
        mgr = self.mgr

        if lib.requires_variable_advertisement:
            mgr.set_no_variables(cnf.get_no_variables())

        varmod = 0
        if lib.has_zero_based_indizes:
            varmod = 1

        bdd = mgr.one_()

        for clause in cnf.clauses:

            print(clause)

            clause_bdd = mgr.zero_()

            for x in clause:

                y = abs(x) - varmod
                
                if x < 0:
                    clause_bdd = mgr.or_(clause_bdd, mgr.nithvar_(y))
                else:
                    clause_bdd = mgr.or_(clause_bdd, mgr.ithvar_(y))

            bdd = mgr.and_(bdd, clause_bdd)

        self.bdd = bdd

    def dump(self, filename, no_variables = 0):
        self.mgr.dump(self.bdd, filename, no_variables = no_variables)