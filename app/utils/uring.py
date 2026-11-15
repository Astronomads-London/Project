def urine(s, ca, ntx, ctx1, pyridinoline,period):
    normal_ca = False
    normal_ntx = False
    normal_ctx1 = False
    normal_pyridinoline = False

    if s == "M":
        if 100 <= ca <= 300:
            normal_ca = True
        if 21<=ntx<=92:
            normal_ntx = True
        if 150 <= ctx1 <= 300:
            normal_ctx1 = True
        if 20 <= pyridinoline <= 61:
            normal_pyridinoline = True
    else:
        if 100 <= ca <= 250:
            normal_ca = True
        if not period:
            if 150 <= ctx1 <= 400:
                normal_ctx1 = True
            if 5<=ntx<=65:
                normal_ntx = True
            if 22 <= pyridinoline <= 89:
                normal_pyridinoline = True
        else:
            if 20<=ntx<=144:
                normal_ntx = True
            if 300 <= ctx1 <= 700:
                normal_ctx1 = True
            if 38 <= pyridinoline <= 89:
                normal_pyridinoline = True


    return normal_ca, normal_ntx, normal_ctx1, normal_pyridinoline

