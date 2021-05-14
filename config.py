DDUERUEM_VERSION = "2021-03"

LIB_DEFAULT     = "buddy"
PARSER_DEFAULT  = "auto"
MODE_DEFAULT    = "full"
SVO_DEFAULT     = "off"
DVO_DEFAULT     = "lib-default"

# Directories
CACHE_DIR   = "_cache"
LOG_DIR     = "log"
REPORT_DIR  = "reports"

# CLI choices
PREORDER_CHOICES    = ["off", "force", "force-triage", "dbo"]
DYNORDER_CHOICES    = ["off", "lib-default", "sift", "sift-conv"]

PARSER_CHOICES      = ["auto", "dimacs", "uvl"]
MODE_CHOICES        = ["full", "only-ctcs", "only-fd"]

LIBRARY_CHOICES         = ["buddy", "cudd"]
INSTALL_CHOICES         = ["all", "buddy", "cudd"]
INSTALLABLE_LIBRARIES   = ["buddy", "cudd"]