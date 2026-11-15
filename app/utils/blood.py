# Normal ranges for bone turnover blood markers.
# Units assumed: CTX in pg/mL, TRAP5b in U/L - check these match your lab's report.

def blood(ismale, ctx1, trap5b,period):
    """Return True if the CTX1 value (pg/mL) is within the normal range, otherwise False."""
    normal_ctx1 = False
    """Return True if the TRAP5b value (U/L) is within the normal range, otherwise False."""
    normal_trap5b = False
    if ismale:
        if 60 <= ctx1 <= 700:
            normal_ctx1 = True
        if 1.1 <= trap5b <= 5.9:
            normal_trap5b = True
    else:
        if period:
            if 40 <= ctx1 <= 635:
                normal_ctx1 = True
            if 1.2 <= trap5b <= 4.8:
                normal_trap5b = True
        else:
            if 104 <= ctx1 <= 1037:
                normal_ctx1 = True
            if 1.1 <= trap5b <= 7.6:
                normal_trap5b = True

    return normal_ctx1 and normal_trap5b