from flask import Blueprint, redirect, render_template, session, request
from datetime import datetime, timezone
from app.utils.greeting import get_gmt_greeting
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

    return render_template(
        "dashboard.html",
        username=session["username"],
        greeting=get_gmt_greeting(),
        today_gmt=datetime.now(timezone.utc).date().isoformat(),
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



@main_bp.route("/privacy", methods=["GET"])
def privacy_redirect():
    return redirect("/policies/privacy")


@main_bp.route("/unitconversion", methods=["GET"])
@main_bp.route("/unit_conversion", methods=["GET"])
@main_bp.route("/conversion", methods=["GET"])
def unitconversion():
    return render_template("unitconversion.html")