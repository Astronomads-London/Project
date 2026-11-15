from flask import Blueprint, redirect, render_template, session, request
from datetime import datetime, timezone
from app.utils.birthday import birthday_error, birthday_limits
from app.utils.bloodpressure import (
    BLOOD_PRESSURE_ERROR,
    DIASTOLIC_RANGE,
    MIN_PULSE_PRESSURE,
    SYSTOLIC_RANGE,
)
from app.utils.charts import CHART_DAYS, build_charts
from app.utils.flags import vital_flags
from app.utils.greeting import get_gmt_greeting
from app.utils.messages import MESSAGE_ERRORS, MESSAGE_MAX_LENGTH, present_messages
from app.utils.validation import (
    CONVERSION_LIMITS,
    DAY_TOTAL_ERROR,
    MINUTES_PER_DAY,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    SETTINGS_NUMBER_FIELDS,
    TODAY_DATA_FIELDS,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
    launch_date_limits
)
import db

main_bp = Blueprint("main", __name__)

DASHBOARD_MESSAGES = 3  # latest flight surgeon messages shown on the dashboard
THREAD_MESSAGES = 100   # latest messages shown on the messages page


def _is_surgeon_session():
    """True when the logged-in account signed in as a flight surgeon.

    Only used to steer flight surgeons away from the astronaut pages; the
    flight surgeon pages check the account itself.
    """
    return session.get("role") == db.ROLE_FLIGHT_SURGEON


@main_bp.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")

@main_bp.route("/login", methods=["GET"])
def login():
    if "username" in session:
        return redirect("/dashboard")
    else:
        return render_template("login.html", error=request.args.get("error"))


@main_bp.route("/register", methods=["GET", "POST"])
def register():
    if "username" in session:
        return redirect("/dashboard")
    else:
        birthday_min, birthday_max = birthday_limits()
        return render_template(
            "register.html",
            error=request.args.get("error"),
            birthday_min=birthday_min.isoformat(),
            birthday_max=birthday_max.isoformat(),
            birthday_error=birthday_error(),
            username_length=(USERNAME_MIN_LENGTH, USERNAME_MAX_LENGTH),
            password_length=(PASSWORD_MIN_LENGTH, PASSWORD_MAX_LENGTH),
            is_surgeon=request.args.get("type") == db.ROLE_FLIGHT_SURGEON,
        )


@main_bp.route("/signup", methods=["GET", "POST"])
def signup():
    return redirect("/register")


@main_bp.route("/dashboard", methods=["GET"])
def dashboard():
    if "username" not in session:
        return redirect("/login")

    username = session["username"]
    user = db.get_user(username) or {}
    # The account decides the role, so a session from before a role change is corrected here.
    role = db.ROLE_FLIGHT_SURGEON if db.is_flight_surgeon(user) else db.ROLE_ASTRONAUT
    if session.get("role") != role:
        session["role"] = role
    if role == db.ROLE_FLIGHT_SURGEON:
        return redirect("/surgeon")

    is_female = str(user.get("sex", "")).strip().lower() in {"female", "f"}
    today_data = db.get_today_data(username)
    streak = db.get_current_streak(username)
    db.edit_user(username, "streak", streak)
    user["streak"] = streak
    today = datetime.now(timezone.utc).date()
    charts = build_charts(db.get_recent_data(CHART_DAYS, username), user, today)
    alerts = [
        f"Your {flag['name']} is {flag['status'].lower()}!"
        for flag in vital_flags(today_data or {})
    ]

    missing_fields = []
    health_data_items = [
        ("resting_heart_rate", "resting heart rate"),
        ("body_temp", "body temperature"),
        ("o2_level", "blood oxygen"),
        ("glucose_level", "glucose"),
        ("blood_pressure", "blood pressure"),
        ("breaths_per_min", "breaths per minute"),
        ("water", "water intake"),
        ("sleep_hours", "sleep"),
        ("exercise", "exercise"),
    ]
    aliases = {
        "resting_heart_rate": "heart_rate",
        "body_temp": "temperature",
        "o2_level": "blood_oxygen",
        "breaths_per_min": "breathing_rate",
    }
    for key, label in health_data_items:
        val = today_data.get(key) if today_data else None
        if (val is None or val == "") and key in aliases and today_data:
            val = today_data.get(aliases[key])
        if val is None or val == "":
            missing_fields.append(label)

    missing_health_data_alert = (
        f"Please enter {', '.join(missing_fields)} for today"
        if missing_fields
        else None
    )

    return render_template(
        "dashboard.html",
        username=username,
        greeting=get_gmt_greeting(),
        today_gmt=today.isoformat(),
        today_data=today_data,
        user=user,
        charts=charts,
        alerts=alerts,
        missing_health_data_alert=missing_health_data_alert,
        is_female=is_female,
        messages=present_messages(
            db.get_messages(
                astronaut=username,
                sender_role=db.ROLE_FLIGHT_SURGEON,
                limit=DASHBOARD_MESSAGES,
            ),
            db.ROLE_ASTRONAUT,
        ),
    )


@main_bp.route("/messages", methods=["GET"])
def messages():
    if "username" not in session:
        return redirect("/login")
    if _is_surgeon_session():
        return redirect("/surgeon/treatment")

    username = session["username"]
    shown = present_messages(
        db.get_messages(astronaut=username, limit=THREAD_MESSAGES), db.ROLE_ASTRONAUT
    )
    # Opening this page is what marks the flight surgeons' messages as read.
    if any(message["new"] for message in shown):
        db.mark_messages_read(username, db.ROLE_FLIGHT_SURGEON)

    return render_template(
        "messages.html",
        username=username,
        messages=shown,
        error=MESSAGE_ERRORS.get(request.args.get("error")),
        sent=request.args.get("sent") == "true",
        max_length=MESSAGE_MAX_LENGTH,
    )


@main_bp.route("/pvt", methods=["GET"])
def pvt():
    if "username" not in session:
        return redirect("/login")
    if _is_surgeon_session():
        return redirect("/surgeon")
    return render_template("pvt.html", username=session["username"])


@main_bp.route("/today", methods=["GET"])
@main_bp.route("/edit-today", methods=["GET"])
def today_data():
    if "username" not in session:
        return redirect("/login")
    if _is_surgeon_session():
        return redirect("/surgeon")

    username = session["username"]
    return render_template(
        "today_data.html",
        username=username,
        today_data=db.get_today_data(username),
        user=db.get_user(username) or {},
        today_gmt=datetime.now(timezone.utc).date().isoformat(),
        saved=request.args.get("saved") == "true",
        error=request.args.get("error"),
        systolic_range=SYSTOLIC_RANGE,
        diastolic_range=DIASTOLIC_RANGE,
        min_pulse_pressure=MIN_PULSE_PRESSURE,
        blood_pressure_error=BLOOD_PRESSURE_ERROR,
        limits=TODAY_DATA_FIELDS,
        minutes_per_day=MINUTES_PER_DAY,
        day_total_error=DAY_TOTAL_ERROR,
    )


@main_bp.route("/settings", methods=["GET", "POST"])
def settings():
    if "username" not in session:
        return redirect("/login")
    if _is_surgeon_session():
        return redirect("/surgeon")

    user = db.get_user(session["username"]) or {}
    birthday_min, birthday_max = birthday_limits()
    launch_min, launch_max = launch_date_limits()

    return render_template(
        "settings.html",
        username=session["username"],
        user=user,
        today_gmt=datetime.now(timezone.utc).date().isoformat(),
        birthday_min=birthday_min.isoformat(),
        birthday_max=birthday_max.isoformat(),
        launch_min=launch_min.isoformat(),
        launch_max=launch_max.isoformat(),
        limits=SETTINGS_NUMBER_FIELDS,
    )



@main_bp.route("/aboutus", methods=["GET"])
@main_bp.route("/about", methods=["GET"])
def aboutus():
    return render_template("aboutus.html")


@main_bp.route("/privacy", methods=["GET"])
def privacy_redirect():
    return redirect("/policies/privacy")


@main_bp.route("/unitconversion", methods=["GET"])
@main_bp.route("/unit_conversion", methods=["GET"])
@main_bp.route("/conversion", methods=["GET"])
def unitconversion():
    return render_template("unitconversion.html", limits=CONVERSION_LIMITS)