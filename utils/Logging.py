from datetime import datetime
import os

from .IO import format, bulk_format, timestamp

logger = None

LL_ALL = 3
LL_INFO = 2
LL_WARNING = 1
LL_ERROR = 0
LL_OFF = -1

log_level_volatile = LL_INFO
log_level_persistent = LL_OFF


def highlight(x):
    return f"$${x}$$"

# logging

def log(*msgs):
    if log_level_persistent >= LL_ALL and logger:
        logger.log(timestamp(), "[#]", bulk_format(*msgs))

    if log_level_volatile >= LL_ALL:
        print(bulk_format(*msgs, color = "green"))

def log_info(*msgs):

    if log_level_persistent >= LL_INFO and logger:
        logger.log(timestamp(), "[I]", bulk_format(*msgs))

    if log_level_volatile >= LL_INFO:
        print(bulk_format(*msgs, color = "blue"))


def log_warning(*msgs):

    if log_level_persistent >= LL_WARNING and logger:
        logger.log(timestamp(), "[W]", bulk_format(*msgs))

    if log_level_volatile >= LL_WARNING:
        print(format("Warning", color = "red", attrs = ["bold"]), bulk_format(*msgs, color = "red"))


def log_error(*msgs, error_code = 1):

    if log_level_persistent >= LL_ERROR and logger:
        logger.log(timestamp(), "[W]", bulk_format(*msgs))

    print()
    print(format("ERROR", color = "red", bg = "on_white", attrs = ["bold"]), bulk_format(*msgs, color = "red"))
    print()

    exit(error_code)
#

def init(filename, volatile_log_level = None, persistent_log_level = None):
    global logger, log_level_volatile, log_level_persistent
    if volatile_log_level:
        log_level_volatile = volatile_log_level
    
    if persistent_log_level:
        log_level_persistent = persistent_log_level
    
    logger = Logger(filename)
    # log_info("info_set_volatile_loglevel", highlight(log_level_volatile))
    # log_info("info_set_persistent_loglevel", highlight(log_level_persistent))

def silence():
    global log_level_volatile, log_level_persistent

    log_level_volatile = LL_OFF
    log_level_persistent = LL_OFF

class Logger:
    def __init__(self, filename):
        self.logfile = filename

    def log(self, *msgs):
        with open(self.logfile, "a") as file:
            if len(msgs) == 1:
                file.write(msgs[0])
            else:
                file.write(" ".join(msgs))

            file.write(os.linesep)
