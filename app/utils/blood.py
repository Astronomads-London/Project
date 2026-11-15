# Normal ranges for bone turnover blood markers.
# Units assumed: CTX in pg/mL, TRAP5b in U/L - check these match your lab's report.

def blood(ismale, ctx1, trap5b,period,age):
    """Return True if the CTX1 value (pg/mL) is within the normal range, otherwise False."""
    normal_ctx1 = False
    """Return True if the TRAP5b value (U/L) is within the normal range, otherwise False."""
    normal_trap5b = False
    if ismale:
        if (242 <= ctx1 <= 2457 and 0<=age<=17) or (238<=ctx1<=1019 and 18<=age<=29) or (182<=ctx1<=936 and 30<=age<=49) or (118<=ctx1<=776 and 50<=age):
            normal_ctx1 = True
        if (3.03 <= trap5b <= 4.57 and age<=54) or (3.41<=trap5b<=5.31 and age>=55):
            normal_trap5b = True
    else:
        if period:
            if (146 <= ctx1 <= 1776 and 0<=age<=17) or (148<=ctx1<=967 and 18<=age<=29) or (131<=ctx1<=670 and 30<=age<=49) or (183<=ctx1<=1060 and 50<=age<=59) or (152<=ctx1<=970 and 60<=age):
                normal_ctx1 = True
            if 2.45 <= trap5b <= 4.03:
                normal_trap5b = True
        else:
            if 177 <= ctx1 <= 1015:
                normal_ctx1 = True
            if 3.07 <= trap5b <= 5.31:
                normal_trap5b = True

    return normal_ctx1 and normal_trap5b
