"""Health ranges for logged readings.

Every reading is "Normal", "Concerning" or "Critical". The dashboard alerts,
the flight surgeon's flags and the chart bar colours all come from the ranges
in this file, so they always agree.
"""
NORMAL = "Normal"
CONCERNING = "Concerning"
CRITICAL = "Critical"

# field: (critical below, normal from, normal to, critical above)
# A reading inside "normal from"-"normal to" is Normal, one beyond a critical
# limit is Critical and anything in between is Concerning. None means that
# side has no critical limit.
RANGES = {
    "o2_level": (92, 95, 100, None),          # %
    "breaths_per_min": (9, 12, 18, 24),       # breaths/min
    "resting_heart_rate": (40, 60, 100, 130),  # bpm
    "body_temp": (35, 35, 38, 39.5),          # °C
    "glucose_level": (54, 70, 140, 250),      # mg/dL
    "sleep_hours": (5, 7, 9, None),           # hours
}
# Blood pressure in mmHg; the reading takes the worse status of its two numbers.
SYSTOLIC_RANGE = (80, 90, 130, 180)
DIASTOLIC_RANGE = (50, 60, 80, 120)
# Water is judged against the account's daily goal: below these fractions of it.
WATER_CRITICAL_FRACTION = 0.5
WATER_CONCERNING_FRACTION = 0.8
DEFAULT_WATER_TARGET = 2500  # ml

_SEVERITY = {NORMAL: 0, CONCERNING: 1, CRITICAL: 2}


def _status(value, limits):
    critical_below, normal_from, normal_to, critical_above = limits
    if critical_below is not None and value < critical_below:
        return CRITICAL
    if critical_above is not None and value > critical_above:
        return CRITICAL
    if normal_from <= value <= normal_to:
        return NORMAL
    return CONCERNING


def blood_oxygen(value):
    return _status(value, RANGES["o2_level"])


def breathing_rate(value):
    return _status(value, RANGES["breaths_per_min"])


def heart_rate(value):
    return _status(value, RANGES["resting_heart_rate"])


def blood_pressure(value):
    """Return the status of a "systolic/diastolic" reading such as "120/80"."""
    value = value.split("/")
    systolic = int(value[0])
    diastolic = int(value[1])
    return max(
        _status(systolic, SYSTOLIC_RANGE),
        _status(diastolic, DIASTOLIC_RANGE),
        key=_SEVERITY.get,
    )


def temperature(value):
    return _status(value, RANGES["body_temp"])


def glucose(value):
    return _status(value, RANGES["glucose_level"])


def sleep(value):
    return _status(value, RANGES["sleep_hours"])


def water(value, target=None):
    """Return the status of a day's water intake (ml) against the daily goal."""
    try:
        target = float(target)
    except (TypeError, ValueError):
        target = 0
    if target <= 0:
        target = DEFAULT_WATER_TARGET
    if value < target * WATER_CRITICAL_FRACTION:
        return CRITICAL
    if value < target * WATER_CONCERNING_FRACTION:
        return CONCERNING
    return NORMAL


def reading_status(field, value, water_target=None):
    """Return the status of one logged reading, or None if it cannot be judged.

    None covers fields without a range, missing values and stored values that
    cannot be read as a number (or as "systolic/diastolic" for blood pressure).
    """
    if value is None or value == "":
        return None
    try:
        if field == "blood_pressure":
            return blood_pressure(str(value).strip())
        if field == "water":
            return water(float(value), water_target)
        if field in RANGES:
            return _status(float(value), RANGES[field])
    except (TypeError, ValueError, IndexError):
        pass
    return None
