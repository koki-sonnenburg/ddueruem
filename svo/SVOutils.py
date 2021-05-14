from svo.FORCE import FORCE
from svo.DBO import DBO

def compute_default_order(expr):
    return [x + 1 for x in range(0, expr.get_no_variables())]

def select_svo(stub):
    if stub == "off":
        return None
    if "force" in stub.lower():
        return FORCE
    if "dbo" in stub.lower():
        return DBO
    else:
        raise NotImplementedError(stub)
