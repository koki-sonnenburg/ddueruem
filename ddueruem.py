#!/usr/bin/env python3
import i18n

import os
from os import path

import config
import utils.Logging as Logging

def init(root_script = __file__):

    # move to directory of the executed script
    os.chdir(os.path.dirname(os.path.realpath(root_script)))

    # initialize logging
    log_dir = config.LOG_DIR
    logfile = f"{log_dir}/log-{Logging.timestamp('-', '-')}.log"
    
    with open(logfile, "w+") as file:
        pass

    Logging.init(logfile)

    # verify existence of the folders (cache, log, report)
    cache_dir = config.CACHE_DIR
    report_dir = config.REPORT_DIR

    verify_create(cache_dir)
    verify_create(report_dir)


def verify_create(dir):
    if not path.exists(dir):
        try:
            os.mkdir(dir)
        except OSError as ose:
            Logging.log_error("error_failed_create_directory", Logging.highlight(dir))
        else:
            Logging.log_info("info_creating_directory", Logging.highlight(path.abspath(dir)))
    else:
        Logging.log_info("info_using_directory", Logging.highlight(path.abspath(dir)))


init()