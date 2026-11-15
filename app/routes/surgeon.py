"""Flight surgeon pages: the crew list and one astronaut's record."""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from functools import wraps

from flask import Blueprint, abort, redirect, render_template, request, session, url_for

from app.utils.charts import build_charts
from app.utils.flags import vital_flags
from app.utils.greeting import get_gmt_greeting
from app.utils.messages import MESSAGE_ERRORS, MESSAGE_MAX_LENGTH, clean_message, present_messages
import db

surgeon_bp = Blueprint("surgeon", __name__)

FLAG_WINDOW_DAYS = 7    # flags are listed for readings logged in this many days
LOG_HISTORY_DAYS = 30   # days of self-reported data shown for one astronaut
PVT_HISTORY_LIMIT = 10  # most recent PVT results shown for one astronaut
DASHBOARD_MESSAGES = 5  # latest messages shown on the crew dashboard
RECENT_MESSAGES = 50    # latest messages shown on the treatment page for the whole crew
THREAD_MESSAGES = 100   # latest messages shown for one astronaut's conversation

# (field, column heading, unit)
LOG_COLUMNS = (
    ("resting_heart_rate", "Heart rate", "bpm"),
    ("blood_pressure", "Blood pressure", "mmHg"),
    ("body_temp", "Temperature", "°C"),
    ("o2_level", "Blood oxygen", "%"),
    ("breaths_per_min", "Breathing rate", "breaths/min"),
    ("glucose_level", "Glucose", "mg/dL"),
    ("water", "Water", "ml"),
    ("sleep_hours", "Sleep", "hours"),
    ("exercise", "Exercise", "min"),
)
ENVIRONMENT_NAMES = {"iss": "ISS", "mars": "Mars", "moon": "Moon"}
MISSING = "—"


def flight_surgeon_required(view):
    """Only let a logged-in flight surgeon reach the view.

    The role is read from the account on every request, not from the session.
    """
    @wraps(view)
    def wrapper(*args, **kwargs):
        username = session.get("username")
        if not username:
            return redirect("/login")
        if not db.is_flight_surgeon(db.get_user(username)):
            return redirect("/dashboard")
        if session.get("role") != db.ROLE_FLIGHT_SURGEON:
            session["role"] = db.ROLE_FLIGHT_SURGEON
        return view(*args, **kwargs)
    return wrapper


def _display(value):
    """Return a stored reading as text, without a trailing ".0"."""
    if value is None or value == "":
        return MISSING
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _with_unit(value, unit):
    return MISSING if value in (None, "") else f"{_display(value)} {unit}"


def _parse_day(text):
    try:
        return date.fromisoformat(str(text)[:10])
    except ValueError:
        return None


def _day_label(text, today):
    day = _parse_day(text)
    if day is None:
        return MISSING
    if day == today:
        return "Today"
    if day == today - timedelta(days=1):
        return "Yesterday"
    return f"{day.day} {day:%b %Y}"


def _has_readings(record):
    return any(record.get(field) is not None for field, _, _ in LOG_COLUMNS)


def _recent_flags(records, today):
    """Return the flags raised by logs from the last FLAG_WINDOW_DAYS days.

    Newest day first, critical readings before concerning ones.
    """
    earliest = (today - timedelta(days=FLAG_WINDOW_DAYS - 1)).isoformat()
    flags = []
    for record in records:
        day = record.get("date")
        if not isinstance(day, str) or day < earliest:
            continue
        for flag in vital_flags(record):
            flags.append({
                "username": record.get("username"),
                "date": day,
                "day": _day_label(day, today),
                "name": flag["name"].capitalize(),
                "reading": _with_unit(flag["value"], flag["unit"]),
                "status": flag["status"],
                "critical": flag["status"].lower() == "critical",
            })
    return _sorted_flags(flags)


def _sorted_flags(flags):
    by_name = sorted(flags, key=lambda flag: str(flag["username"]))
    return sorted(by_name, key=lambda flag: (flag["date"], flag["critical"]), reverse=True)


def _last_logged(records, today):
    """Describe the newest day with readings; records are newest first."""
    for record in records:
        if _has_readings(record):
            label = _day_label(record.get("date"), today)
            if label == "Today":
                return "Logged today"
            return f"Last logged {label.lower() if label == 'Yesterday' else label}"
    return f"No logs in the last {FLAG_WINDOW_DAYS} days"


def _age(birthday, today):
    born = _parse_day(birthday)
    if born is None:
        return None
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def _profile(account, today):
    """Return the (label, value) facts shown about an astronaut. Never includes the password hash."""
    age = _age(account.get("birthday"), today)
    environment = str(account.get("environment") or "").strip()
    launch = _parse_day(account.get("launch_date") or account.get("mission_start"))
    mission_days = account.get("mission_duration") or account.get("mission_length")
    return [
        ("Age", MISSING if age is None else str(age)),
        ("Sex", _display(account.get("sex"))),
        ("Height", _with_unit(account.get("height"), "cm")),
        ("Body mass", _with_unit(account.get("mass"), "kg")),
        ("Environment", ENVIRONMENT_NAMES.get(environment.lower(), environment or MISSING)),
        ("Launch date", launch.isoformat() if launch else MISSING),
        ("Mission length", _with_unit(mission_days, "days")),
        ("Water target", _with_unit(account.get("water_target"), "ml")),
        ("Sleep target", _with_unit(account.get("sleep_target"), "hours")),
        ("Exercise target", _with_unit(account.get("exercise_target"), "min")),
    ]


def _log_rows(records):
    """Return one table row per logged day, marking the readings that raised a flag."""
    rows = []
    for record in records:
        if not _has_readings(record):
            continue
        flagged = {flag["field"]: flag["status"] for flag in vital_flags(record)}
        rows.append({
            "date": record.get("date") or MISSING,
            "cells": [
                {"text": _display(record.get(field)), "status": flagged.get(field)}
                for field, _, _ in LOG_COLUMNS
            ],
        })
    return rows


def _number(value, pattern="{:.0f}"):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return MISSING
    return pattern.format(value)


def _pvt_rows(results):
    rows = []
    for result in results:
        scores = result.get("scores") or {}
        completed = result.get("completed_at")
        performance = scores.get("overall_performance_score")
        rows.append({
            "completed": completed.strftime("%Y-%m-%d %H:%M") if isinstance(completed, datetime) else MISSING,
            "average": _number(scores.get("average_response_time_ms")),
            "lapses": _number(scores.get("lapse_count")),
            "false_starts": _number(scores.get("false_start_count")),
            "performance": (
                _number(performance * 100) + "%"
                if isinstance(performance, (int, float)) and not isinstance(performance, bool)
                else MISSING
            ),
            "trials": _number(scores.get("trial_count")),
        })
    return rows


@surgeon_bp.route("", methods=["GET"], strict_slashes=False)
@flight_surgeon_required
def crew():
    today = datetime.now(timezone.utc).date()
    logs_by_astronaut = defaultdict(list)
    for record in db.get_recent_data(FLAG_WINDOW_DAYS):
        logs_by_astronaut[record.get("username")].append(record)

    astronauts = []
    flags = []
    for account in db.get_astronauts():
        username = account.get("username")
        logs = logs_by_astronaut.get(username, [])
        own_flags = _recent_flags(logs, today)
        flags.extend(own_flags)
        astronauts.append({
            "username": username,
            "last_logged": _last_logged(logs, today),
            "flag_count": len(own_flags),
            "critical": any(flag["critical"] for flag in own_flags),
        })

    return render_template(
        "surgeon.html",
        username=session["username"],
        greeting=get_gmt_greeting(),
        astronauts=astronauts,
        flags=_sorted_flags(flags),
        messages=present_messages(
            db.get_messages(limit=DASHBOARD_MESSAGES), db.ROLE_FLIGHT_SURGEON
        ),
        flagged_count=sum(1 for astronaut in astronauts if astronaut["flag_count"]),
        flag_days=FLAG_WINDOW_DAYS,
    )


@surgeon_bp.route("/astronaut", methods=["GET"])
@flight_surgeon_required
def astronaut():
    username = request.args.get("username", "")
    account = db.get_user(username)
    if not account or db.is_flight_surgeon(account):
        abort(404)

    today = datetime.now(timezone.utc).date()
    logs = db.get_recent_data(LOG_HISTORY_DAYS, username)
    return render_template(
        "surgeon_astronaut.html",
        astronaut=username,
        profile=_profile(account, today),
        streak=db.get_current_streak(username),
        flags=_recent_flags(logs, today),
        flag_days=FLAG_WINDOW_DAYS,
        charts=build_charts(logs, account, today),
        pvt_rows=_pvt_rows(db.get_pvt_results(username, PVT_HISTORY_LIMIT)),
        pvt_limit=PVT_HISTORY_LIMIT,
        log_columns=LOG_COLUMNS,
        log_rows=_log_rows(logs),
        log_days=LOG_HISTORY_DAYS,
    )


def _astronaut_account(username):
    """Return the astronaut's account, or None if there is no such astronaut."""
    account = db.get_user(username) if username else None
    if not account or db.is_flight_surgeon(account):
        return None
    return account


@surgeon_bp.route("/treatment", methods=["GET", "POST"])
@flight_surgeon_required
def treatment():
    if request.method == "POST":
        target = request.form.get("astronaut", "")
        if _astronaut_account(target) is None:
            return redirect(url_for("surgeon.treatment", error="astronaut"))
        text, error = clean_message(request.form.get("message"))
        if error is None and not db.add_message(
            target, session["username"], db.ROLE_FLIGHT_SURGEON, text
        ):
            error = "save"
        if error:
            return redirect(url_for("surgeon.treatment", username=target, error=error))
        return redirect(url_for("surgeon.treatment", username=target, sent="true"))

    # With ?username= the page shows that astronaut's conversation, otherwise
    # the latest messages of the whole crew.
    selected = request.args.get("username") or None
    if selected is not None:
        if _astronaut_account(selected) is None:
            abort(404)
        messages = present_messages(
            db.get_messages(astronaut=selected, limit=THREAD_MESSAGES), db.ROLE_FLIGHT_SURGEON
        )
        # Opening the conversation is what marks the astronaut's replies as read.
        if any(message["new"] for message in messages):
            db.mark_messages_read(selected, db.ROLE_ASTRONAUT)
    else:
        messages = present_messages(
            db.get_messages(limit=RECENT_MESSAGES), db.ROLE_FLIGHT_SURGEON
        )

    return render_template(
        "surgeon_treatment.html",
        astronauts=[account.get("username") for account in db.get_astronauts()],
        selected=selected,
        messages=messages,
        error=MESSAGE_ERRORS.get(request.args.get("error")),
        sent=request.args.get("sent") == "true",
        max_length=MESSAGE_MAX_LENGTH,
    )
