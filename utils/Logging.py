from datetime import datetime

import i18n

import os
import re
from termcolor import colored

logger = None

LL_ALL = 3
LL_INFO = 2
LL_WARNING = 1
LL_ERROR = 0

log_level_volatile = LL_ALL
log_level_persistent = LL_ALL


# styling
def format(msgs, color = None, attrs = None):
    
    out = []

    for msg in msgs:
        msg = str(msg)
        msg = i18n.t(msg)
        if m := re.match(r"\$\$(?P<inner>[^$]+)\$\$", msg):
            msg = m["inner"]
            if color:
                if attrs:
                    msg = colored(msg, color, attrs)
                else:
                    msg = colored(msg, color)

        out.append(msg)

    return out    

def highlight(x):
    return f"$${x}$$"

def timestamp(sep = "", splitsep = ":"):
    return datetime.now().strftime(f"%Y{sep}%m{sep}%d{splitsep}%H{sep}%M{sep}%S")

# logging
def log_info(*msgs):

    if log_level_persistent >= LL_INFO and logger:
        logger.log("[I]", timestamp(), *format(msgs))

    if log_level_volatile >= LL_INFO:
        print(*format(msgs, "blue"))


def init(filename, volatile_level = None, persistent_level = None):
    global logger, log_level_volatile, log_level_persistent
    if volatile_level:
        log_level_volatile = volatile_level
    
    if persistent_level:
        log_level_persistent = persistent_level
    
    # initialize i18n
    i18n.load_path.append("i18n")
    i18n.set('filename_format', '{locale}.{format}')
    
    logger = Logger(filename)
    log_info("Setting volatile log level to:", highlight(log_level_volatile))
    log_info("Setting persistent level to:", highlight(log_level_persistent))

class Logger:
    def __init__(self, filename):
        self.logfile = filename

    def log(self, *msgs):
        with open(self.logfile, "a") as file:
            file.write(" ".join(msgs))
            file.write(os.linesep)
