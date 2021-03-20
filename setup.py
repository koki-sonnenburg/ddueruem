#!/usr/bin/env python3
#------------------------------------------------------------------------------#

import argparse             

#------------------------------------------------------------------------------#

import config
from ddueruem import init
from adapters import BUDDY, CUDD
import adapters.Adapter as Adapter
import utils.Logging as Logging

#------------------------------------------------------------------------------#

def get_lib(lib):
    if lib == "buddy":
        return BUDDY
    elif lib == "cudd":
        return CUDD
    else:
        Logging.log_error("Unknown lib", Logging.highlight(lib))

    return None

def cli():    
    parser = argparse.ArgumentParser(description=format("cli_setup_desc"))
    
    # IO Toggles
    parser.add_argument("--silent", help = format("cli--silent"), dest = "silent", action = "store_true", default = False)
    parser.add_argument("--clean", help = format("cli_setup--clean"), dest = "clean", action = "store_true", default = False)

    # Install Options
    parser.add_argument("libs", nargs = "+", choices = config.INSTALL_CHOICES, type = str.lower, help = format("cli_setup--install"), default = [])

    args = parser.parse_args()

    init(root_script = __file__, silent = args.silent)

    if args.clean:
        Logging.log(Logging.highlight("--clean"), "was supplied. Existing downloads, sources, and build results will be ignored.")

    libs = args.libs
    if "all" in libs:
        libs =  config.INSTALLABLE_LIBRARIES

    for lib in libs:
        lib = get_lib(lib)        
        lib.install(clean = args.clean)    

#------------------------------------------------------------------------------#

if __name__ == "__main__":
    cli()