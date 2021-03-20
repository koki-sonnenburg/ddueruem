#!/usr/bin/env python3

#------------------------------------------------------------------------------#

import argparse             

import os
from os import path

#------------------------------------------------------------------------------#

import config
from utils.IO import format
import utils.Logging as Logging

#------------------------------------------------------------------------------#

def init(root_script = __file__, silent = False):

    # move to directory of the executed script
    os.chdir(os.path.dirname(os.path.realpath(root_script)))

    if silent:
        Logging.silence()

    # initialize logging
    log_dir = config.LOG_DIR
    verify_create(log_dir)

    logfile = f"{log_dir}/log-{Logging.timestamp('-', '-')}.log"
    
    with open(logfile, "w+") as file:
        pass

    Logging.init(logfile)

    # verify existence of the folders cache & report
    cache_dir = config.CACHE_DIR
    report_dir = config.REPORT_DIR

    verify_create(cache_dir)
    verify_create(report_dir)


def verify_create(dir):
    """Creates the directory dir if it does not already exist."""

    if not path.exists(dir):
        try:
            os.mkdir(dir)
        except OSError as ose:
            Logging.log_error("error_create_directory_failed", Logging.highlight(dir))
        else:
            Logging.log("info_create_directory", Logging.highlight(path.abspath(dir)))
    else:
        Logging.log("info_use_directory", Logging.highlight(path.abspath(dir)))

def cli():    
    parser = argparse.ArgumentParser(description=format("cli_desc"))
    parser.add_argument("file", nargs = "?", help = format("cli_file"), default = None)

    # Run Options
    parser.add_argument("--lib", help = format("cli--lib"), choices = config.LIBRARY_CHOICES, type = str.lower, default = config.LIB_DEFAULT)
    parser.add_argument("--parser", help = format("cli--parser"), choices = config.PARSER_CHOICES, type = str.lower, default = config.PARSER_DEFAULT)

    # Variable Ordering
    parser.add_argument("--preorder", help = format("cli--preorder"), choices = config.PREORDER_CHOICES, type = str.lower, default = config.SVO_DEFAULT)
    parser.add_argument("--dynorder", help = format("cli--dynorder"), choices = config.DYNORDER_CHOICES, type = str.lower, default = config.DVO_DEFAULT)
    
    # IO Toggles
    parser.add_argument("--silent", help = format("cli--silent"), dest = "silent", action = "store_true", default = False)
    parser.add_argument("--no-log", help = format("cli--no-log"), dest = "log", action = "store_false", default = True)
    parser.add_argument("--no-cache", help = format("cli--no-cache"), dest = "cache", action = "store_false", default = True)

    # Caching Toggles    
    parser.add_argument("--ignore-cached-order", help = format("cli--ignore-cached-order"), dest = "use_cached_order", action = "store_false", default = True)
    parser.add_argument("--ignore-cached-results", help = format("cli--ignore-cached-results"), dest = "use_cached_results", action = "store_false", default = True)

    args = parser.parse_args()

    init()

if __name__ == "__main__":
    cli()