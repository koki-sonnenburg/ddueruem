from ctypes import CDLL

import os
from os import path

import re

import subprocess

from utils.IO import  download, untar, verify_hash, format
import utils.Logging as Logging

def declare(f, argtypes, restype = None):
    x = f
    x.argtypes = argtypes

    if restype:
        x.restype = restype

    return x

def verify_load_lib(lib, hint_install):
    if not path.exists(lib):
        Logging.log_error(Logging.highlight(lib), "not found, please install first with", Logging.highlight(hint_install))
    else:
        return CDLL(f"./{lib}")


def flavour_filename(filename, stub):
    filename = re.sub(".dd$", f"-{stub}.dd", filename)
    return filename

def install_library(name, stub, url, archive, archive_md5, sources, shared_lib, configure_params = "", clean = False):

    if clean:
        Logging.log_info(f"Clean installing", Logging.highlight(name))
    else:
        Logging.log_info(f"Installing", Logging.highlight(name))
        
    if path.exists(shared_lib):
        if clean:
            Logging.log_info(f"Ignoring existing shared library", Logging.highlight(shared_lib))
        else: 
            Logging.log_info(Logging.highlight(shared_lib), "already exists, skipping install")
            return 

    if clean or not path.exists(archive):    
        Logging.log("Downloading...")
        download(url, archive)

    if clean or not path.exists(sources):        
        valid, reason = verify_hash(archive, archive_md5)

        if not valid:
            Logging.log_error(reason)

        Logging.log_info(f"Unpacking", Logging.highlight(archive))
        untar(archive)

    if clean or not path.exists(shared_lib):            
        Logging.log("Configuring...")
        subprocess.run(['./configure', configure_params], cwd = sources, stdout=subprocess.PIPE).stdout.decode('utf-8')

        Logging.log("Building...")
        subprocess.run(['make', stub, '-j4'], stdout=subprocess.PIPE).stdout.decode('utf-8')

    if path.exists(shared_lib):        
        if path.exists(shared_lib):
            Logging.log_info(f'{name} build: {format("SUCCESS", color = "green", attrs = ["bold"])}')
        else:
            Logging.log_warning(f'{name} build: {format("FAIL", color = "red", attrs = ["bold"])}')