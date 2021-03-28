from ctypes import CDLL

import os
from os import path

import re

import subprocess

from utils.IO import  download, untar, verify_hash, format
import utils.Logging as Logging

from . import Adapter_BUDDY as BUDDY
from . import Adapter_CUDD as CUDD

from config import DDUERUEM_VERSION

def get_lib(stub):

    stub = stub.lower()

    if stub == "buddy":
        return BUDDY
    elif stub == "cudd":
        return CUDD
    else:
        raise NotImplementedError(f"Library with stub \"{stub}\" is not hooked in.")

def get_meta(lib):
    return {
        "ddueruem-version": DDUERUEM_VERSION,
        "lib-name-stub":lib.stub,
        "lib-name":lib.name
    }

def install(lib, clean = False):

    if clean:
        Logging.log_info(f"Clean installing", Logging.highlight(lib.name))
    else:
        Logging.log_info(f"Installing", Logging.highlight(lib.name))
        
    if path.exists(lib.shared_lib):
        if clean:
            Logging.log_info(f"Ignoring existing shared library", Logging.highlight(lib.shared_lib))
        else: 
            Logging.log_info(Logging.highlight(lib.shared_lib), "already exists, skipping install")
            return 

    if clean or not path.exists(archive):    
        Logging.log("Downloading...")
        download(lib.url, lib.archive)

    if clean or not path.exists(lib.sources_dir):        
        valid, reason = verify_hash(lib.archive, lib.archive_md5)

        if not valid:
            Logging.log_error(reason)

        Logging.log_info(f"Unpacking", Logging.highlight(lib.archive))
        untar(lib.archive)

    if clean or not path.exists(shared_lib):            
        Logging.log("Configuring...")
        lib.configure()

        Logging.log("Building...")
        subprocess.run(['make', lib.stub, '-j4'], stdout=subprocess.PIPE).stdout.decode('utf-8')
    
    if path.exists(lib.shared_lib):
        Logging.log_info(f'{lib.name} build: {format("SUCCESS", color = "green", attrs = ["bold"])}')
    else:
        Logging.log_warning(f'{lib.name} build: {format("FAIL", color = "red", attrs = ["bold"])}')

# def fromCNF(lib, cnf)

#     if lib.requires_variable_advertisement:
#         lib.set_no_variables(cnf.get_no_variables())

#     varmod = 0
#     if lib.has_zero_based_indizes:
#         varmod = 1

#     bdd = lib.one_()

#     for clause in cnf.clauses:

#         clause_bdd = lib.one_()

#         for x in clause:

#             x = abs(x) - varmod
            
#             if x < 0:
#                 clause_bdd = lib.or_(clause_bdd, lib.nithvar_(x))
#             else:
#                 clause_bdd = lib.or_(clause_bdd, lib.ithvar_(x))

#     bdd = lib.and_(bdd, clause_bdd)



# def verify_load_lib(lib, hint_install):
#     if not path.exists(lib):
#         Logging.log_error(Logging.highlight(lib), "not found, please install first with", Logging.highlight(hint_install))
#     else:
#         return CDLL(f"./{lib}")


# def flavour_filename(filename, stub):
#     filename = re.sub(".dd$", f"-{stub}.dd", filename)
#     return filename

# def install(lib, clean = False):



# def install_library(name, stub, url, archive, archive_md5, sources, shared_lib, configure_params = "", clean = False):
