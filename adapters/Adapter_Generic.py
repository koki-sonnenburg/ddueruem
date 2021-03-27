from ctypes import CDLL
from os import path


class Adapter_Generic:

#---- Constants ---------------------------------------------------------------#

    def zero_(self, mgr = None):
        raise NotImplementedError()

    def one_(self, mgr = None):
        raise NotImplementedError()

#---- Unary Operators ---------------------------------------------------------#

    def not_(self, obj, mgr = None):
        raise NotImplementedError()

#---- Binary Operators --------------------------------------------------------#

    def and_(self, lhs, rhs, free_factors = True, mgr = None):
        raise NotImplementedError()

    def or_(self, lhs, rhs, free_factors = True, mgr = None):
        raise NotImplementedError()

    def xor_(self, lhs, rhs, free_factors = True, mgr = None):
        raise NotImplementedError()

#---- Utility -----------------------------------------------------------------#

    def load_lib(self, shared_lib, hint_install):
        if not path.exists(shared_lib):
            Logging.log_error(Logging.highlight(shared_lib), "not found, please install first with", Logging.highlight(hint_install))
        else:
            return CDLL(f"./{shared_lib}")

    def dump(self, bdd, filename, mgr = None):
        raise NotImplementedError()
   
