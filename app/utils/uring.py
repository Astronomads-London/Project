def urine(s, ca, ntx, pyridinoline,period,age):
    normal_ca = False
    normal_ntx = False
    normal_pyridinoline = False

    if s == "M":
        if 100 <= ca <= 300:
            normal_ca = True
        if (152<=ntx<=578 and 0<=age<=12) or (103<=ntx<=776 and 13<=age<=15) or (34<=ntx<=313 and 16<=age<=17) or (21<=ntx<=83 and age>=18):
            normal_ntx = True
        if 5.0<=pyridinoline<=21.8:
            normal_pyridinoline = True
    else:
        if 100 <= ca <= 250:
            normal_ca = True
        if period:
            if (173<=ntx<=728 and 0<=age<=12) or (38<=ntx<=515 and 13<=age<=15) or (20<=ntx<=144 and 16<=age<=17) or (17<=ntx<=94 and age>=18):
                normal_ntx = True
            if 7.8 <= pyridinoline <= 21.2:
                normal_pyridinoline = True
        else:
            if 26<=ntx<=124:
                normal_ntx = True
            if 7.1 <= pyridinoline <= 31.8:
                normal_pyridinoline = True


    return normal_ca, normal_ntx, normal_pyridinoline

