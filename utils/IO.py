from datetime import datetime, timedelta

import hashlib

import i18n

import os

import re
import requests

import tarfile
from termcolor import colored

import config

# initialize i18n
i18n.load_path.append("i18n")
i18n.set('filename_format', '{locale}.{format}')

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

### Formatting

def format(*msgs, color = None, attrs = None, return_type = str, str_sep = " "):
    
    out = []

    for msg in msgs:
        msg = str(msg)
        msg = i18n.t(msg)
        if m := re.match(r"\$\$(?P<inner>[^$]+)\$\$", msg):
            msg = m["inner"]
            if color:
                if attrs:
                    msg = colored(msg, color, attrs=attrs)
                else:
                    msg = colored(msg, color)

        out.append(msg)

    if return_type == list:
        return out
    elif return_type == str:
        return str_sep.join(out)    
    else:
        raise TypeError("out must be list or str")