"""Health flags: logged vital signs that fall outside their normal range."""
from app.utils.vital_signs import (
    blood_oxygen,
    blood_pressure,
    breathing_rate,
    heart_rate,
    temperature,
)

# (name, stored field, older field name, unit, check, type the check expects)
_VITAL_CHECKS = (
    ("blood oxygen", "o2_level", "blood_oxygen", "%", blood_oxygen, float),
    ("breathing rate", "breaths_per_min", "breathing_rate", "breaths/min", breathing_rate, float),
    ("heart rate", "resting_heart_rate", "heart_rate", "bpm", heart_rate, float),
    ("blood pressure", "blood_pressure", None, "mmHg", blood_pressure, str),
    ("temperature", "body_temp", "temperature", "°C", temperature, float),
)


def vital_flags(record):
    """Return a flag for each vital sign in a day's log that is not "Normal".

    Each flag is {"name", "field", "status", "value", "unit"}; status is the
    check's own wording, e.g. "Concerning" or "Critical".
    """
    flags = []
    for name, field, old_field, unit, check, kind in _VITAL_CHECKS:
        value = record.get(field)
        if value is None and old_field:
            value = record.get(old_field)
        if value is None or value == "":
            continue
        try:
            status = check(str(value).strip() if kind is str else float(value))
        except (TypeError, ValueError, IndexError):
            continue  # an unreadable stored value cannot be judged
        if status and status.lower() != "normal":
            flags.append({
                "name": name,
                "field": field,
                "status": status,
                "value": value,
                "unit": unit,
            })
    return flags
