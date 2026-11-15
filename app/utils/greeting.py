from datetime import datetime, timezone


def greeting_for_hour(hour):
    if not 0 <= hour <= 23:
        raise ValueError("Hour must be between 0 and 23.")
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


def get_gmt_greeting(now=None):
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    return greeting_for_hour(current_time.astimezone(timezone.utc).hour)
