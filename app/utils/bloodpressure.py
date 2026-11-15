import re

# Accepted blood pressure readings, in mmHg. The log-today form reads these
# limits too, so the browser and the server apply the same rule.
SYSTOLIC_RANGE = (70, 250)
DIASTOLIC_RANGE = (40, 150)
# Systolic must be higher than diastolic by at least this much.
MIN_PULSE_PRESSURE = 10

BLOOD_PRESSURE_ERROR = (
    "Enter blood pressure as systolic/diastolic, for example 120/80. "
    f"Systolic must be {SYSTOLIC_RANGE[0]}-{SYSTOLIC_RANGE[1]}, "
    f"diastolic {DIASTOLIC_RANGE[0]}-{DIASTOLIC_RANGE[1]} "
    f"and at least {MIN_PULSE_PRESSURE} below systolic."
)

# Two or three digits each side, no leading zeros ("099/080" is rejected).
_READING = re.compile(r"\s*([1-9]\d{1,2})\s*/\s*([1-9]\d{1,2})\s*")


def parse_blood_pressure(raw):
    """Return raw as a normalised "systolic/diastolic" string, or None if it is not sensible."""
    if not isinstance(raw, str):
        return None
    match = _READING.fullmatch(raw)
    if not match:
        return None

    systolic, diastolic = (int(value) for value in match.groups())
    if not SYSTOLIC_RANGE[0] <= systolic <= SYSTOLIC_RANGE[1]:
        return None
    if not DIASTOLIC_RANGE[0] <= diastolic <= DIASTOLIC_RANGE[1]:
        return None
    if systolic - diastolic < MIN_PULSE_PRESSURE:
        return None
    return f"{systolic}/{diastolic}"
