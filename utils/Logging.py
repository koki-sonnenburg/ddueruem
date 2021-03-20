from datetime import datetime
import os

from .IO import format

logger = None

LL_ALL = 3
LL_INFO = 2
LL_WARNING = 1
LL_ERROR = 0

log_level_volatile = LL_ALL
log_level_persistent = LL_ALL


def highlight(x):
    return f"$${x}$$"

def timestamp(sep = "", splitsep = ":"):
    return datetime.now().strftime(f"%Y{sep}%m{sep}%d{splitsep}%H{sep}%M{sep}%S")

# logging

def log(*msgs):
    if log_level_persistent >= LL_ALL and logger:
        logger.log(timestamp(), "[#]", format(*msgs))

    if log_level_volatile >= LL_ALL:
        print(format(*msgs, color = "green"))

def log_info(*msgs):

    if log_level_persistent >= LL_INFO and logger:
        logger.log(timestamp(), "[I]", format(*msgs))

    if log_level_volatile >= LL_INFO:
        print(format(*msgs, color = "blue"))


def log_warning(*msgs):

    if log_level_persistent >= LL_WARNING and logger:
        logger.log(timestamp(), "[W]", format(*msgs))

    if log_level_volatile >= LL_WARNING:
        print(format("$$Warning$$", color = "red", attrs = ["bold"]), format(*msgs, color = "red"))


def init(filename, volatile_level = None, persistent_level = None):
    global logger, log_level_volatile, log_level_persistent
    if volatile_level:
        log_level_volatile = volatile_level
    
    if persistent_level:
        log_level_persistent = persistent_level
    
    logger = Logger(filename)
    log_info("info_set_volatile_loglevel", highlight(log_level_volatile))
    log_info("info_set_persistent_loglevel", highlight(log_level_persistent))

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
