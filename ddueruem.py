#!/usr/bin/env python3
import Logging

def init(root_script):

    # move to directory of the executed script
    os.chdir(os.path.dirname(os.path.realpath(root_script)))

    cache_dir = config.CACHE_DIR
    verify_create(cache_dir)
    
    # initialize logging
        

    # verify existence of the folders (cache, log, report)

    log_dir = config.LOG_DIR
    report_dir = config.REPORT_DIR

    verify_create(log_dir)
    verify_create(report_dir)


def verify_create(dir):
    if not path.exists(dir):
        os.mkdir(dir)
    except OSError as ose:

    else:
        log_info(f"Created cache directory at {path.abspath(cache_dir)}")


init()