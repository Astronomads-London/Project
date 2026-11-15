import re
from datetime import date

# Oldest age a profile may claim. Birthdays must fall between this many years
# ago and today.
MAX_AGE_YEARS = 120

_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def birthday_limits(today=None):
    """Return the (earliest, latest) birthday accepted today."""
    today = today or date.today()
    try:
        earliest = today.replace(year=today.year - MAX_AGE_YEARS)
    except ValueError:  # 29 February in a non-leap target year
        earliest = today.replace(year=today.year - MAX_AGE_YEARS, day=28)
    return earliest, today


def parse_birthday(raw):
    """Return raw ("YYYY-MM-DD") as a date within birthday_limits(), or None."""
    if not isinstance(raw, str) or not _ISO_DATE.fullmatch(raw.strip()):
        return None
    try:
        birthday = date.fromisoformat(raw.strip())
    except ValueError:
        return None

    earliest, latest = birthday_limits()
    if not earliest <= birthday <= latest:
        return None
    return birthday
