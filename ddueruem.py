#!/usr/bin/env python3

#------------------------------------------------------------------------------#

import argparse             

import os
from os import path

import re

from pprint import pprint

#------------------------------------------------------------------------------#

import config
import utils.Caching as Caching
from utils.IO import bulk_format
import utils.Logging as Logging

import adapters.Adapters as Adapters

from adapters.BDD import BDD
from parsers.DIMACS_Parser import DIMACS_Parser
from svo import SVOutils as SVO

#------------------------------------------------------------------------------#

def parsing(input_file, flag_parser, flag_mode):

    parser = select_parser(input_file, flag_parser)

    Logging.log_info("Parser:", Logging.highlight(parser.name()))

    if flag_mode != "full" and parser.name() == "dimacs":
        Logging.log_error("dimacs does not segregate feature diagram and cross-tree constraints.")

    with parser(input_file) as parser:
        expr = parser.parse()

    return expr

def ordering(expr, flag_preorder):

    order = SVO.compute_default_order(expr)

    if flag_preorder != "off":
        preorder = SVO.select_svo(flag_preorder)
        Logging.log_info("SVO:", Logging.highlight(preorder.name()))
        with preorder(flag_preorder) as svo:
            order = svo.run(expr, order)
            if svo.provides_clause_ordering():
                expr.clauses = svo.order_clauses(expr.clauses, order)

    return order

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
            pass
            Logging.log("info_create_directory", Logging.highlight(path.abspath(dir)))
    else:
        pass
        Logging.log("info_use_directory", Logging.highlight(path.abspath(dir)))

### TODO: Move to parsers directory utility class
def select_parser(input_file, parser):

    if parser == "auto":

        if input_file.lower().endswith("dimacs"):
            return DIMACS_Parser
        elif input_file.lower().endswith("uvl"):
            return UVL_Parser
        else:
            Logging.log_error("Could not auto-detect input file format, please manually select the correct parser")

    elif parser == "dimacs":
        return DIMACS_Parser
    elif parser == "uvl":
        return UVL_Parser
    else:
        Logging.log_error("Unknown parser", Logging.highlight(parser))


def cli():    
    parser = argparse.ArgumentParser(description=bulk_format("cli_desc"))
    parser.add_argument("file", help = bulk_format("cli_file"))

    # Run Options
    parser.add_argument("--lib", help = bulk_format("cli--lib"), choices = config.LIBRARY_CHOICES, type = str.lower, default = config.LIB_DEFAULT)
    parser.add_argument("--parser", help = bulk_format("cli--parser"), choices = config.PARSER_CHOICES, type = str.lower, default = config.PARSER_DEFAULT)
    parser.add_argument("--mode", help = bulk_format("cli--mode"), choices = config.MODE_CHOICES, type = str.lower, default = config.MODE_DEFAULT)

    # Variable Ordering
    parser.add_argument("--preorder", help = bulk_format("cli--preorder"), choices = config.PREORDER_CHOICES, type = str.lower, default = config.SVO_DEFAULT)
    parser.add_argument("--dynorder", help = bulk_format("cli--dynorder"), type = str.lower, default = config.DVO_DEFAULT)
    
    # IO Toggles
    parser.add_argument("--silent", help = bulk_format("cli--silent"), dest = "silent", action = "store_true", default = False)
    parser.add_argument("--no-log", help = bulk_format("cli--no-log"), dest = "log", action = "store_false", default = True)
    parser.add_argument("--no-cache", help = bulk_format("cli--no-cache"), dest = "cache", action = "store_false", default = True)

    # Caching Toggles    
    parser.add_argument("--ignore-cached-order", help = bulk_format("cli--ignore-cached-order"), dest = "use_cached_order", action = "store_false", default = True)
    parser.add_argument("--ignore-cached-artifacts", help = bulk_format("cli--ignore-cached-artifacts"), dest = "use_cached_artifacts", action = "store_false", default = True)

    args = parser.parse_args()

    init()


    dvo = args.dynorder
    if dvo == "help":
        with BDD(args.lib) as bdd:
            bdd.list_available_dvo_options()

        exit(0)

    input_file = args.file

    Logging.log_info("Input:", Logging.highlight(input_file))

    if args.use_cached_artifacts and Caching.artifact_cache_exists(input_file, args.lib):
        Logging.log_info("Using cached BDD")
        raise NotImplementedError("Using cached BDD")
        # bdd = fromCache
    else:
        expr = parsing(input_file, args.parser, args.mode)
        Logging.log_info("Expression:", Logging.highlight(expr))

        if args.use_cached_order and Caching.order_cache_exists(input_file, args.preorder):
            Logging.log_info("Using cached variable order")
            raise NotImplementedError("Using cached VO")
            # order = fromCache
        else:
            order = ordering(expr, args.preorder)

        with BDD(args.lib) as bdd:
            Logging.log_info("Library:", Logging.highlight(bdd.lib.name))
                

            bdd.set_dvo(args.dynorder)
            Logging.log_info("DVO:", Logging.highlight(bdd.get_dvo()))

            bdd.buildFrom(expr, order)
            filename_bdd = bdd.dump()

#------------------------------------------------------------------------------#

if __name__ == "__main__":
    cli()