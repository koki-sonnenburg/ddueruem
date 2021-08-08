import random

from svo.FORCE import FORCE

def compute_default_order(expr):
    return [x + 1 for x in range(0, expr.get_no_variables())]

def compute_random_order(expr):
    order = [x + 1 for x in range(0, expr.get_no_variables())]
    random.shuffle(order)

    return order

def select_svo(stub):
    if stub == "off":
        return None
    if "force" in stub.lower():
        return FORCE
    else:
        raise NotImplementedError(stub)
