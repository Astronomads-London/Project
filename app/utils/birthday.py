import re
from datetime import date

# Account holders must be at least MIN_AGE_YEARS old and may claim to be at
# most MAX_AGE_YEARS old, so birthdays fall between those two points.
MIN_AGE_YEARS = 18
MAX_AGE_YEARS = 120

_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def years_before(day, years):
    try:
        return day.replace(year=day.year - years)
    except ValueError:  # 29 February in a non-leap target year
        return day.replace(year=day.year - years, day=28)


def birthday_limits(today=None):
    """Return the (earliest, latest) birthday accepted today."""
    today = today or date.today()
    return years_before(today, MAX_AGE_YEARS), years_before(today, MIN_AGE_YEARS)


def birthday_error():
    """Return the message shown when a birthday is outside birthday_limits()."""
    earliest, latest = birthday_limits()
    # Kept short: the sign-up card only has room for one line of error text.
    return (
        f"Enter a birthday from {earliest.isoformat()} to {latest.isoformat()} "
        f"(age {MIN_AGE_YEARS} or over)."
    )


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
