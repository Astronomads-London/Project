import math
import re


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


def chart_status(field, value, target=None):
    """Return a display status using this app's existing reference ranges."""
    if value is None:
        return "neutral"

    if field == "blood_pressure":
        match = re.fullmatch(r"\s*(\d{2,3})\s*/\s*(\d{2,3})\s*", str(value))
        if not match:
            return "neutral"
        systolic, diastolic = (int(part) for part in match.groups())
        return (
            "concerning"
            if systolic < 90 or systolic > 130 or diastolic < 60 or diastolic > 80
            else "good"
        )

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "neutral"
    if not math.isfinite(numeric):
        return "neutral"

    if field == "o2_level":
        status = blood_oxygen(numeric).lower()
        return "good" if status == "normal" else status
    if field == "breaths_per_min":
        return "concerning" if breathing_rate(numeric) != "Normal" else "good"
    if field == "resting_heart_rate":
        return "concerning" if heart_rate(numeric) != "Normal" else "good"
    if field == "body_temp":
        return "concerning" if temperature(numeric) != "Normal" else "good"
    if field in {"sleep_hours", "water"}:
        try:
            goal = float(target)
        except (TypeError, ValueError):
            return "neutral"
        if not math.isfinite(goal) or goal <= 0:
            return "neutral"
        return "good" if numeric >= goal else "concerning"

    return "neutral"
