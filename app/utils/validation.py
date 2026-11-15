"""Shared input rules.

The forms are rendered with these same limits, so the browser and the server
agree on what counts as a sensible value.
"""
import math
import re
from datetime import date, datetime, timedelta, timezone

from app.utils.birthday import years_before

# Plain decimal only: no leading zeros, signs or exponents ("0072", "+70", "1e2").
_PLAIN_NUMBER = re.compile(r"(?:0|[1-9]\d*)(?:\.\d+)?")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def parse_number(raw, low, high, decimals=None):
    """Return raw as a number within [low, high], or None if it is not acceptable.

    Text must be a plain decimal. decimals caps the decimal places allowed
    (0 means whole numbers only).
    """
    if isinstance(raw, bool):
        return None
    try:
        if isinstance(raw, (int, float)):
            value = float(raw)
        elif isinstance(raw, str) and _PLAIN_NUMBER.fullmatch(raw.strip()):
            value = float(raw.strip())
        else:
            return None
    except OverflowError:
        return None

    if not math.isfinite(value) or not low <= value <= high:
        return None
    if decimals is not None and round(value, decimals) != value:
        return None
    return int(value) if value.is_integer() else value


def range_error(label, low, high, decimals=None, unit=""):
    """Return the message shown when a number is outside its range."""
    kind = "a whole number " if decimals == 0 else ""
    unit = f" {unit}" if unit else ""
    places = ""
    if decimals:
        places = f" and at most {decimals} decimal place{'s' if decimals > 1 else ''}"
    return f"{label} must be {kind}between {low} and {high}{unit}, with no leading zeros{places}."


# ---------- Sign-up ----------
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 30
# Letters, numbers, dot, underscore and dash. The sign-up form's pattern
# attribute repeats this character set.
USERNAME_PATTERN = re.compile(
    r"[A-Za-z0-9._-]{%d,%d}" % (USERNAME_MIN_LENGTH, USERNAME_MAX_LENGTH)
)
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
SEX_CHOICES = ("Male", "Female")

# Height in cm, body mass in kg.
PROFILE_LIMITS = {
    "height": (100, 250),
    "mass": (30, 250),
}
PROFILE_LIMIT_ERRORS = {
    "height": "Height must be between 100 and 250 cm, with no leading zeros.",
    "mass": "Body mass must be between 30 and 250 kg, with no leading zeros.",
}


def parse_profile_measurement(field, raw):
    """Return raw as a float within PROFILE_LIMITS[field], or None if it is not acceptable."""
    value = parse_number(raw, *PROFILE_LIMITS[field])
    return None if value is None else float(value)


# ---------- Settings ----------
# field: (minimum, maximum, decimal places, label, unit)
SETTINGS_NUMBER_FIELDS = {
    "water_target": (500, 10000, 0, "Water target", "ml"),
    "exercise_target": (0, 480, 0, "Exercise target", "minutes"),
    "sleep_target": (4, 12, 2, "Sleep target", "hours"),
    "mission_length": (1, 2000, 0, "Mission length", "days"),
}
ENVIRONMENT_CHOICES = ("iss", "mars", "moon")
HYDRATION_CHOICES = ("disabled", "1h", "2h")
# Older accounts store the reminder as 0 (off), 1 (hourly) or 2 (every 2 hours).
_LEGACY_HYDRATION_CHOICES = (0, 1, 2, "0", "1", "2")
# A launch date may be this many years before or after today.
LAUNCH_WINDOW_YEARS = 10


def parse_settings_number(field, raw):
    low, high, decimals = SETTINGS_NUMBER_FIELDS[field][:3]
    return parse_number(raw, low, high, decimals)


def settings_number_error(field):
    low, high, decimals, label, unit = SETTINGS_NUMBER_FIELDS[field]
    return range_error(label, low, high, decimals, unit)


def is_hydration_choice(raw):
    if isinstance(raw, bool):
        return False
    return raw in HYDRATION_CHOICES or raw in _LEGACY_HYDRATION_CHOICES


def launch_date_limits(today=None):
    """Return the (earliest, latest) launch date accepted today (UTC)."""
    today = today or datetime.now(timezone.utc).date()
    return years_before(today, LAUNCH_WINDOW_YEARS), years_before(today, -LAUNCH_WINDOW_YEARS)


def launch_date_error():
    earliest, latest = launch_date_limits()
    return f"Launch date must be between {earliest.isoformat()} and {latest.isoformat()}."


def parse_launch_date(raw):
    """Return raw ("YYYY-MM-DD") as a date within launch_date_limits(), or None."""
    if not isinstance(raw, str) or not _ISO_DATE.fullmatch(raw.strip()):
        return None
    try:
        launch = date.fromisoformat(raw.strip())
    except ValueError:
        return None

    earliest, latest = launch_date_limits()
    if not earliest <= launch <= latest:
        return None
    return launch


# ---------- Log Today ----------
# field: (minimum, maximum, decimal places)
TODAY_DATA_FIELDS = {
    "resting_heart_rate": (30, 200, 0),   # bpm
    "body_temp": (34, 42, 1),             # °C
    "o2_level": (70, 100, 0),             # %
    "glucose_level": (40, 500, 0),        # mg/dL
    "breaths_per_min": (6, 60, 0),        # breaths/min
    "water": (0, 10000, 0),               # ml
    "sleep_hours": (0, 20, 2),            # hours
    "exercise": (0, 600, 0),              # minutes
}
MINUTES_PER_DAY = 24 * 60
DAY_TOTAL_ERROR = "Sleep and exercise together cannot add up to more than 24 hours."


def today_data_error(field):
    low, high, decimals = TODAY_DATA_FIELDS[field]
    return range_error(field.replace("_", " ").capitalize(), low, high, decimals)


def day_total_ok(sleep_hours, exercise_minutes):
    """Return False when sleep and exercise would need more than one day."""
    try:
        total = float(sleep_hours or 0) * 60 + float(exercise_minutes or 0)
    except (TypeError, ValueError):
        return True  # an unreadable stored value is not this request's fault
    return total <= MINUTES_PER_DAY


# ---------- Unit conversion ----------
# field: (minimum, maximum)
CONVERSION_LIMITS = {
    "feet": (0, 9),
    "inches": (0, 108),
    "pounds": (1, 600),
}
MAX_HEIGHT_INCHES = 108  # 9 ft


def check_height_conversion(feet, inches):
    """Return an error message for an impossible feet/inches pair, or None."""
    if feet > 0 and inches >= 12:
        return "When feet are entered, inches must be below 12."
    total = feet * 12 + inches
    if not 0 < total <= MAX_HEIGHT_INCHES:
        return "Height must be more than 0 and no more than 9 ft (108 in)."
    return None


# ---------- Reaction test ----------
PVT_MAX_AGE = timedelta(hours=24)
PVT_CLOCK_TOLERANCE = timedelta(minutes=5)


def pvt_start_time_ok(started_at, now=None):
    """Return True when a timezone-aware start time is recent and not in the future."""
    now = now or datetime.now(timezone.utc)
    return now - PVT_MAX_AGE <= started_at <= now + PVT_CLOCK_TOLERANCE
