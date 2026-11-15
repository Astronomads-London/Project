def blood_oxygen(value):
    if value < 92:
        return "Critical"
    elif value < 95:
        return "Concerning"
    else:
        return "Normal"

def breathing_rate(value):
    if value < 12 or value > 18:
        return "Concerning"
    else:
        return ("Normal")

def heart_rate(value):
    if value < 60 or value > 100:
        return "Concerning"
    else:
        return "Normal"

def blood_pressure(value):
    value = value.split("/")
    systolic = int(value[0])
    diastolic = int(value[1])
    if systolic < 90 or systolic > 130 or diastolic < 60 or diastolic > 80:
        return "Concerning"
    else:
        return "Normal"

def temperature(value):
    if value < 35 or value > 38:
        return "Concerning"
    else:
        return "Normal"
