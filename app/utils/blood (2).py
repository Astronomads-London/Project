# Normal ranges for bone turnover blood markers.
# Units assumed: CTX in pg/mL, TRAP5b in U/L - check these match your lab's report.


def ctx(ismale, value):
    """Return True if the CTX1 value (pg/mL) is within the normal range, otherwise False."""
    value = float(value)
    if ismale:
        return 100 <= value <= 580
    return 100 <= value <= 600


def trap5b(value):
    """Return True if the TRAP5b value (U/L) is within the normal range, otherwise False."""
    value = float(value)
    return 1.5 <= value <= 4.8
