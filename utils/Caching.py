import os
from os import path

from utils.IO import basename
from config import CACHE_DIR

def get_artifact_cache(input_file_name, lib_stub):
    return f"{CACHE_DIR}/{basename(input_file_name)}-{lib_stub}.bdd"

def artifact_cache_exists(input_file, flag_lib):
    filename = get_artifact_cache(input_file, flag_lib)
    return path.exists(filename)

def order_cache_exists(input_file, preorder):
    return False