DDUERUEM_VERSION = "v2021-03"

LIB_DEFAULT     = "buddy"
PARSER_DEFAULT  = "auto"
MODE_DEFAULT    = "full"
SVO_DEFAULT     = "off"
DVO_DEFAULT     = "off"

# Directories
CACHE_DIR   = "_cache"
LOG_DIR     = "_log"
REPORT_DIR  = "_reports"

# CLI choices
PREORDER_CHOICES    = ["off", "force", "force-triage", "dbo"]

PARSER_CHOICES      = ["auto", "dimacs"]
MODE_CHOICES        = ["full", "only-ctcs", "only-fd"] # ignored for now

LOGLEVEL_CHOICES     = [("LL_OFF", 0), ("LL_ERROR", 1), ("LL_WARNING", 2), ("LL_INFO", 3), ("LL_ALL", 4)]
LL_VOLATILE_DEFAULT = LOGLEVEL_CHOICES[3]
LL_PERSISTENT_DEFAULT = LOGLEVEL_CHOICES[4]

LIBRARY_CHOICES         = ["buddy", "cudd"]
INSTALL_CHOICES         = ["all", "buddy", "cudd"]
INSTALLABLE_LIBRARIES   = ["buddy", "cudd"]