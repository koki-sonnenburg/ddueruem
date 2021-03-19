logger = None

LL_ALL = 3
LL_INFO = 2
LL_WARNING = 1
LL_ERROR = 0

log_level_volatile = ALL
log_level_persistent = ALL

# styling
def timestamp():
    return datetime.now().strftime('%Y-%m-%d:%H-%M-%S')

def clean(msgs, highlight_op):

    out = []

    for msg in msgs:
        if msg isinstance(Highlight):
            out.append(highlight_op(msg))
        else:
            out.append(msg)

    return out

# logging
def log_info(*msgs):

    if log_level_persistent >= LL_INFO and logger:
        logger.log("[E]", timestamp(), clean(msgs, lambda x: x.strip()))

    if log_level_volatile >= LL_INFO:
        msgs = clean(msgs, lambda x: x.style("blue"))
        print(*msgs)


def init(filename, volatile_level = None, persistent_level = None):
    if volatile_level:
        log_level_volatile = volatile_level
    
    if persistent_level:
        log_level_persistent = persistent_level
    
    logger = Logger(filename)

class Highlight:
    def __init__(self, content):
        self.content = content

    def strip(self):
        return content

    def style(self, color, attrs):
        return colored(self.content, color, attrs = attrs)

class Logger:
    def __init__(self, filename):
        self.logfile = filename

    def log(self, *msgs):
        with open(self.logfile, "a") as file:
            file.write(" ".join(msgs))
