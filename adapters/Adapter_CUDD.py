from ctypes import CDLL, Structure, POINTER, c_uint, c_double, c_ulong, byref, c_int

import os
import re
import subprocess
import sys

from . import Adapter_Generic
from config import CACHE_DIR

name        = "CUDD 3.0.0"
stub        = "cudd"
url         = "https://davidkebo.com/source/cudd_versions/cudd-3.0.0.tar.gz"
archive     = f"{CACHE_DIR}/cudd-3.0.0.tar.gz"
archive_md5 = "4fdafe4924b81648b908881c81fe6c30"
sources_dir  = f"{CACHE_DIR}/cudd-3.0.0"
shared_lib  = "libcudd.so"

configure_settings = "CFLAGS=-fPIC -std=c99"

hint_install = "--install cudd"

reordering_algorithms = {
    "sift": 4,
    "sift-conv": 5
}

has_zero_based_indizes = True
requires_variable_advertisement = False

def configure():
    subprocess.run(['./configure', configure_settings], cwd = sources_dir, stdout=subprocess.PIPE).stdout.decode('utf-8')

def declare(f, argtypes, restype = None):
    x = f
    x.argtypes = argtypes

    if restype:
        x.restype = restype

    return x

#---- Utility Class -----------------------------------------------------------#

class STDOUT_Recorder():

    def __init__(self, filename):
        with open(filename, "w"):
            pass

        sys.stdout.flush()
        self._oldstdout_fno = os.dup(sys.stdout.fileno())
        self.sink = os.open(filename, os.O_WRONLY)

    def __enter__(self):
        self._newstdout = os.dup(1)
        os.dup2(self.sink, 1)
        os.close(self.sink)
        sys.stdout = os.fdopen(self._newstdout, 'w')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = sys.__stdout__
        sys.stdout.flush()

#---- CDLL Companion Classes --------------------------------------------------#

class DdNode(Structure):
    _fields_ = [
        ('index', c_uint),
        ('keys', c_uint)
    ]

class DdSubtable(Structure):
    _fields_ = [
        ('slots', c_uint),
        ('keys', c_uint)
    ]

class DdManager(Structure):
    _fields_ = [
        ('subtables', POINTER(DdSubtable)),
        ('keys', c_uint),
        ('dead', c_uint),
        ('cachecollisions', c_double),
        ('cacheinserts', c_double),
        ('cachedeletions', c_double)
    ]


class Manager(Adapter_Generic.Adapter_Generic):

#---- Initialization, Setup, Destruction---------------------------------------#

    def init(self):
        self.cudd = self.load_lib(shared_lib, hint_install)

        self._init = declare(self.cudd.Cudd_Init, [c_uint, c_uint, c_uint, c_uint, c_ulong], POINTER(DdManager))

        self.mgr = self._init(0,0, 256, 1<<20, 0)

        return self

    def exit(self):
        if not hasattr(self, "_exit"):
            self._exit = declare(self.cudd.Cudd_Quit, [POINTER(DdManager)])

        self._exit(self.mgr)

    def set_no_variables(self, no_variables):

        if not hasattr(self, "_newvar"):
            self._newvar = declare(self.cudd.Cudd_bddNewVar, [POINTER(DdManager), c_uint])

        for x in range(0, no_variables):
            self._newvar(self.mgr, x)

#---- Constants ---------------------------------------------------------------#

    def zero_(self):
        
        if not hasattr(self, "_zero"):
            self._zero = declare(self.cudd.Cudd_ReadLogicZero, [POINTER(DdManager)], POINTER(DdNode))

        return self._zero(self.mgr);

    def one_(self):

        if not hasattr(self, "_one"):
            self._one = declare(self.cudd.Cudd_ReadOne, [POINTER(DdManager)], POINTER(DdNode))

        return self._one(self.mgr);

#---- Variables ---------------------------------------------------------------#

    def ithvar_(self, varid):

        if not hasattr(self, "_ithvar"):
            self._ithvar = declare(self.cudd.Cudd_bddIthVar, [POINTER(DdManager), c_int], POINTER(DdNode))

        return self._ithvar(self.mgr, varid)

    def nithvar_(self, varid):
        return self.not_(self.ithvar_(varid))

#---- Unary Operators ---------------------------------------------------------#

    def not_(self, obj):
        return byref(obj.contents, 1)

#---- Binary Operators --------------------------------------------------------#

    def and_(self, lhs, rhs, free_factors = True):

        if not hasattr(self, "_and"):
            self._and = declare(self.cudd.Cudd_bddAnd, [POINTER(DdManager), POINTER(DdNode), POINTER(DdNode)], POINTER(DdNode))

        out = self._and(self.mgr, lhs, rhs)
        self.addref_(out)

        if free_factors:
            self.delref_(lhs)
            self.delref_(rhs)

        return out

    def or_(self, lhs, rhs, free_factors = True):

        if not hasattr(self, "_or"):
            self._or = declare(self.cudd.Cudd_bddOr, [POINTER(DdManager), POINTER(DdNode), POINTER(DdNode)], POINTER(DdNode))

        out = self._or(self.mgr, lhs, rhs)
        self.addref_(out)

        if free_factors:
            self.delref_(lhs)
            self.delref_(rhs)

        return out

    def xor_(self, lhs, rhs, free_factors = True):

        if not hasattr(self, "_xor"):
            self._xor = declare(self.cudd.Cudd_bddXor, [POINTER(DdManager), POINTER(DdNode), POINTER(DdNode)], POINTER(DdNode))

        out = self._xor(self.mgr, lhs, rhs)
        self.addref_(out)

        if free_factors:
            self.delref_(lhs)
            self.delref_(rhs)

        return out

#---- Utility -----------------------------------------------------------------#
    
    def addref_(self, obj):

        if not hasattr(self, "_addref"):
            self._addref = declare(self.cudd.Cudd_Ref, [POINTER(DdNode)])

        self._addref(obj)

    def delref_(self, obj):

        if not hasattr(self, "_delref"):
            self._delref = declare(self.cudd.Cudd_RecursiveDeref, [POINTER(DdManager), POINTER(DdNode)])

        self._delref(self.mgr, obj)

    def dump(self, bdd, filename, no_variables = 0):

        if not hasattr(self, "_dump"):
            self._dump = declare(self.cudd.Cudd_PrintDebug, [POINTER(DdManager), POINTER(DdNode), c_int, c_int])

        with STDOUT_Recorder(filename):
            self._dump(self.mgr, bdd, no_variables, 3)





























# class DdNode(Structure):
#     _fields_ = [
#         ('index', c_uint),
#         ('keys', c_uint)
#     ]

# class DdSubtable(Structure):
#     _fields_ = [
#         ('slots', c_uint),
#         ('keys', c_uint)
#     ]

# class DdManager(Structure):
#     _fields_ = [
#         ('subtables', POINTER(DdSubtable)),
#         ('keys', c_uint),
#         ('dead', c_uint),
#         ('cachecollisions', c_double),
#         ('cacheinserts', c_double),
#         ('cachedeletions', c_double)
#     ]

# class STDOUT_Recorder():

#     def __init__(self, filename):
#         with open(filename, "w"):
#             pass

#         sys.stdout.flush()
#         self._oldstdout_fno = os.dup(sys.stdout.fileno())
#         self.sink = os.open(filename, os.O_WRONLY)

#     def __enter__(self):
#         self._newstdout = os.dup(1)
#         os.dup2(self.sink, 1)
#         os.close(self.sink)
#         sys.stdout = os.fdopen(self._newstdout, 'w')
#         return self

#     def __exit__(self, exc_type, exc_val, exc_tb):
#         sys.stdout = sys.__stdout__
#         sys.stdout.flush()
#         os.dup2(self._oldstdout_fno, 1)


# class CUDD_Adapter():

#     def __init__(self):
#         cudd = verify_load_lib(shared_lib, hint_install)

#         self.cudd_init = declare(cudd.Cudd_Init, [c_uint, c_uint, c_uint, c_uint, c_ulong], POINTER(DdManager))

#         self.cudd_ref = declare(cudd.Cudd_Ref, [POINTER(DdNode)])
#         self.cudd_deref = declare(cudd.Cudd_RecursiveDeref, [POINTER(DdManager), POINTER(DdNode)])

#         self.cudd_zero = declare(cudd.Cudd_ReadLogicZero, [POINTER(DdManager)], POINTER(DdNode))
#         self.cudd_one = declare(cudd.Cudd_ReadOne, [POINTER(DdManager)], POINTER(DdNode))
#         self.cudd_ithvar = declare(cudd.Cudd_bddIthVar, [POINTER(DdManager), c_int], POINTER(DdNode))

#         self.cudd_and = declare(cudd.Cudd_bddAnd, [POINTER(DdManager), POINTER(DdNode), POINTER(DdNode)], POINTER(DdNode))
#         self.cudd_or = declare(cudd.Cudd_bddOr, [POINTER(DdManager), POINTER(DdNode), POINTER(DdNode)], POINTER(DdNode))
#         self.cudd_nor = declare(cudd.Cudd_bddNor, [POINTER(DdManager), POINTER(DdNode), POINTER(DdNode)], POINTER(DdNode))

#         self.cudd_info = declare(cudd.Cudd_PrintDebug, [POINTER(DdManager), POINTER(DdNode), c_int, c_int])

#         self.cudd_enable_dynorder = declare(cudd.Cudd_AutodynEnable, [POINTER(DdManager), c_int])
#         self.cudd_disable_dynorder = declare(cudd.Cudd_AutodynDisable, [POINTER(DdManager)])

#         self.cudd_n_reorders = declare(cudd.Cudd_ReadReorderings, [POINTER(DdManager)])

#         self.cudd_setorder  = declare(cudd.Cudd_ShuffleHeap, [POINTER(DdManager), POINTER(c_uint)])
#         self.cudd_bddnewvar = declare(cudd.Cudd_bddNewVar, [POINTER(DdManager)])

#         self.cudd_quit = declare(cudd.Cudd_Quit, [POINTER(DdManager)])

#     def __enter__(self):
#         # From the CUDD manual
#         manager = self.cudd_init(0,0, 256, 1<<20, 0)

#         self.manager = manager

#         return self

#     def __exit__(self, exc_type, exc_val, exc_tb):
#         manager = self.manager
#         self.cudd_quit(manager)

#     def name():
#         return name

#     def set_dynorder(self, dynorder):
#         manager = self.manager
#         if dynorder == "off" or dynorder not in reordering_algorithms:
#             if dynorder != "off":
#                 log_warning(f"CUDD: Reordering algorithm not supported ({blue(dynorder)}).")

#             log_info(f"CUDD: Disabled automatic reordering")
#             self.cudd_disable_dynorder(manager)

#         if dynorder in reordering_algorithms:
#             log_info(f"CUDD: Enabled automatic reordering ({blue(dynorder)})")
#             self.cudd_enable_dynorder(manager, reordering_algorithms[dynorder])

#     def cudd_not(self, pointer):

#         return byref(pointer.contents, 1)

#     @staticmethod
#     def install(clean = False):
#         install_library(name, stub, url, archive, archive_md5, source_dir, shared_lib, configure_params, clean)

#     def from_cnf(self, cnf, order, dynorder,filename_bdd):

#         filename_bdd = flavour_filename(filename_bdd, stub)

#         manager = self.manager

#         self.cudd_disable_dynorder(manager)

#         # Normalize as CUDD indexes from 0
#         order = [x - 1 for x in order] 
#         arr = (c_uint * len(order))(*order)

#         for x in range(0, cnf.get_no_variables()):
#             self.cudd_bddnewvar(manager, x)

#         self.cudd_setorder(manager, arr)

#         self.set_dynorder(dynorder)

#         full = self.cudd_one(manager)
#         self.cudd_ref(full)
#         for n, clause in enumerate(cnf.clauses):
#             log_info(clause, f"({n+1} / {len(cnf.clauses)})")

#             cbdd = self.cudd_zero(manager)
#             self.cudd_ref(cbdd)
#             for x in clause:
#                 var = abs(x) - 1
#                 f = self.cudd_ithvar(manager, var)

#                 if x < 0:
#                     tmp = self.cudd_or(manager, self.cudd_not(f), cbdd)
#                     self.cudd_ref(tmp)
#                 else:
#                     tmp = self.cudd_or(manager, f, cbdd)
#                     self.cudd_ref(tmp)

#                 self.cudd_deref(manager, cbdd)
#                 cbdd = tmp

#             tmp = self.cudd_and(manager, cbdd, full)
#             self.cudd_ref(tmp)
#             self.cudd_deref(manager, full)
#             self.cudd_deref(manager, cbdd)
#             full = tmp

#         with STDOUT_Recorder(filename_bdd):
#             self.cudd_info(manager, full, cnf.get_no_variables(), 3)

#         self.format_cache(cnf, filename_bdd, order)  
#         log_info("BDD saved to", blue(filename_bdd))
#         return filename_bdd 

#     def format_cache(self, cnf, filename_bdd, order):        
#         with open(filename_bdd, "r") as file:
#             content = file.read()

#         lines = re.split("[\n\r]",content)

#         m = re.match(r"^:\s+(?P<n_nodes>\d+)\s+nodes\s+\d+\s+leaves\s+(?P<ssat>[^\s]+)\s+minterms\s*$", lines[0])

#         n_nodes = int(m["n_nodes"])
#         root = re.split(r"\s+", lines[1])[2]

#         root_ce = 0
#         if root[0] == '!':
#             root_ce = 1
#             root = int(root[1:], 16)
#         else:
#             root = int(root, 16)

#         filename_cnf = cnf.meta["filename"]

#         content = [
#             f"input_file:{filename_cnf}",
#             f"input_hash:{hash_hex(filename_cnf)}",
#             f"order:{','.join([str(x + 1) for x in order])}",
#             f"n_vars:{cnf.get_no_variables()}",
#             f"n_nodes:{n_nodes}",
#             f"root:{root_ce}:{root}"
#         ]

#         content.append("----")

#         for line in lines[1:]:
#             if not line.startswith("ID"):
#                 continue

#             fields = re.split(r"\s+", line)

#             if fields[2][0] == "!":
#                 node_id = int(fields[2][1:], 16)
#             else:
#                 node_id = int(fields[2], 16)

#             var_index = int(fields[5])

#             high = fields[8]
#             high_ce = 0
#             if high[0] == '!':
#                 high_ce = 1
#                 node_high = int(high[1:], 16)
#             else:
#                 node_high = int(high[0:], 16)

#             low = fields[11]
#             low_ce = 0
#             if low[0] == '!':
#                 low_ce = 1
#                 node_low = int(low[1:], 16)
#             else:
#                 node_low = int(low[0:], 16)

#             content.append(f"{node_id} {var_index} {low_ce}:{node_low} {high_ce}:{node_high}")

#         with open(filename_bdd, "w") as file:
#             file.write(f"{os.linesep}".join(content))
#             file.write(os.linesep)