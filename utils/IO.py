from datetime import datetime, timedelta

import hashlib

import os

import requests

import tarfile
from termcolor import colored

import config


### Download

def untar(filepath):
    log_info(f"Unpacking {filepath}")

    with tarfile.open(filepath) as archive:
        archive.extractall(path = config.CACHE_DIR)   

def download(url, target):

    req = requests.get(url)

    with open(target, "wb") as file:
        file.write(req.content)

### Hashing

def hash_hex(filepath):    
    with open(filepath, "rb") as f:
        hash_is = hashlib.md5()
        while chunk := f.read(8192):
            hash_is.update(chunk)

    return hash_is.hexdigest()


def verify_hash(filepath, hash_should):

    hash_is = hash_hex(filepath)

    if hash_is == hash_should:
        return (True, "")
    else:
        return (False, f"Hash of {filepath} ({hash_is}) does not match expected hash ({hash_should})")

def prepend_input_file_signature(filename_to_hash, filename_to_store):
    with open(filename_to_store, "r") as file:
        contents = file.read()

    with open(filename_to_store, "w") as file:
        file.write(f"{filename_to_hash}:{hash(filename_to_hash)}{os.linesep}")
        file.write(contents)

### Time
