from flask import Blueprint, redirect, render_template, session, request
from datetime import datetime, timedelta, timezone
from app.utils.greeting import get_gmt_greeting
from app.utils.vital_signs import (
    blood_oxygen,
    breathing_rate,
    heart_rate,
    blood_pressure,
    temperature,
)
import db

main_bp = Blueprint("main", __name__)


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
        return render_template("register.html", error=request.args.get("error"))


@main_bp.route("/signup", methods=["GET", "POST"])
def signup():
    return redirect("/register")


@main_bp.route("/dashboard", methods=["GET"])
def dashboard():
    if "username" not in session:
        return redirect("/login")

    username = session["username"]
    user = db.get_user(username) or {}
    today_data = db.get_today_data(username)
    streak = db.get_current_streak(username)
    db.edit_user(username, "streak", streak)
    user["streak"] = streak
    today = datetime.now(timezone.utc).date()
    dates = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    chart_definitions = (
        ("sleep_hours", "Sleep", "hours", user.get("sleep_target", 8)),
        ("resting_heart_rate", "Resting heart rate", "bpm", None),
        ("glucose_level", "Glucose", "mg/dL", None),
        ("blood_pressure", "Blood pressure · systolic", "mmHg", None),
        ("water", "Water intake", "ml", user.get("water_target", 2500)),
        ("breaths_per_min", "Breaths per minute", "breaths/min", None),
        ("o2_level", "Blood oxygen", "%", None),
        ("body_temp", "Body temperature", "°C", None),
    )
    charts = []
    for field, title, unit, target in chart_definitions:
        records = db.get_last_7_days_data(username, field)
        values_by_date = {record["date"]: record.get(field) for record in records}
        points = []
        for day in dates:
            value = values_by_date.get(day.isoformat())
            if field == "blood_pressure":
                value = str(value).strip() if value is not None else None
            elif value is not None:
                try:
                    value = float(value)
                except (TypeError, ValueError):
                    value = None
            points.append({"label": day.strftime("%a"), "value": value})
        charts.append({
            "field": field,
            "title": title,
            "unit": unit,
            "target": target,
            "points": points,
        })

    alerts = []
    if today_data:
        vitals_checks = [
            ("blood oxygen", today_data.get("o2_level") if today_data.get("o2_level") is not None else today_data.get("blood_oxygen"), blood_oxygen, float),
            ("breathing rate", today_data.get("breaths_per_min") if today_data.get("breaths_per_min") is not None else today_data.get("breathing_rate"), breathing_rate, float),
            ("heart rate", today_data.get("resting_heart_rate") if today_data.get("resting_heart_rate") is not None else today_data.get("heart_rate"), heart_rate, float),
            ("blood pressure", today_data.get("blood_pressure"), blood_pressure, str),
            ("temperature", today_data.get("body_temp") if today_data.get("body_temp") is not None else today_data.get("temperature"), temperature, float),
        ]
        for name, val, func, cast in vitals_checks:
            if val is not None and val != "":
                try:
                    status = func(cast(val) if cast is not str else str(val).strip())
                    if status and status.lower() != "normal":
                        alerts.append(f"Your {name} is {status.lower()}!")
                except Exception:
                    pass

    return render_template(
        "dashboard.html",
        username=username,
        greeting=get_gmt_greeting(),
        today_gmt=today.isoformat(),
        today_data=today_data,
        user=user,
        charts=charts,
        alerts=alerts,
    )


@main_bp.route("/pvt", methods=["GET"])
def pvt():
    if "username" not in session:
        return redirect("/login")
    return render_template("pvt.html", username=session["username"])


@main_bp.route("/today", methods=["GET"])
@main_bp.route("/edit-today", methods=["GET"])
def today_data():
    if "username" not in session:
        return redirect("/login")

    username = session["username"]
    return render_template(
        "today_data.html",
        username=username,
        today_data=db.get_today_data(username),
        user=db.get_user(username) or {},
        today_gmt=datetime.now(timezone.utc).date().isoformat(),
        saved=request.args.get("saved") == "true",
        error=request.args.get("error"),
    )


@main_bp.route("/settings", methods=["GET", "POST"])
def settings():
    if "username" not in session:
        return redirect("/login")

    user = db.get_user(session["username"]) or {}

    return render_template(
        "settings.html",
        username=session["username"],
        user=user,
        today_gmt=datetime.now(timezone.utc).date().isoformat(),
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
    return render_template("unitconversion.html")