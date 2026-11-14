def urine(s, ca, ntx, ctx1, pyridinoline):
    normal_ca = False
    normal_ntx = False
    normal_ctx1 = False
    normal_pyridinoline = False
    if 100 <= ca <= 250:
        normal_ca = True

    if s == "M":
        if 15<=ntx<=65:
            normal_ntx = True
    else:
        if 15<=ntx<=75:
            normal_ntx = True

    if 100<=ctx1<=500:
        normal_ctx1 = True

    if 15<=pyridinoline<=40:
        normal_pyridinoline = True

    return normal_ca, normal_ntx, normal_ctx1, normal_pyridinoline

