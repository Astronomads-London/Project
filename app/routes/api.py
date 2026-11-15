import math
from datetime import date

from flask import Blueprint, current_app, request, redirect, session, jsonify
from auth import auth_login, hash_password
from app.utils.unitconversion import height_to_cm, pounds_to_kg
import db


api_bp = Blueprint("api", __name__)

TEMP_REFCODE = "123456"  # Temporary referral code for testing purposes

@api_bp.route("/unit-conversion", methods=["POST"])
def unit_conversion():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify(error="Provide conversion values as an object."), 400

    conversion = data.get("conversion")
    values = {}

    required_fields = {
        "height": ("feet", "inches"),
        "weight": ("pounds",),
    }
    if conversion not in required_fields:
        return jsonify(error="Choose a supported conversion."), 400

    try:
        for field in required_fields[conversion]:
            value = float(data[field])
            if not math.isfinite(value) or value < 0:
                raise ValueError
            values[field] = value
    except (KeyError, TypeError, ValueError):
        return jsonify(error="Enter valid non-negative numbers."), 400

    if conversion == "height":
        result = height_to_cm(values["feet"], values["inches"])
        return jsonify(result=f"{result:.2f} cm")

    result = pounds_to_kg(values["pounds"])
    return jsonify(result=f"{result:.2f} kg")

@api_bp.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    exists = db.user_exists(username)  # Check if the user exists in the database

    if exists:
        is_valid = auth_login(username, username, password, db.return_user_hash(username))
        if is_valid:
            session["username"] = username
            return redirect("/dashboard")
        else:
            return redirect("/login?error=invalid")
    else:
        return redirect("/login?error=not_found")


@api_bp.route("/register", methods=["POST"])
def register():
    username = request.form.get("username")
    password = request.form.get("password")
    birthday_value = request.form.get("birthday", "")
    height = request.form.get("height")
    mass = request.form.get("mass") or request.form.get("body-mass")
    sex = request.form.get("sex")
    invitecode = request.form.get("invite_code")
    expected_invite_code = current_app.config.get("INVITE_CODE")

    if not expected_invite_code:
        current_app.logger.error("INVITE_CODE is not configured.")
        return redirect("/register?error=invite_unavailable")

    if invitecode != expected_invite_code:
        return redirect("/register?error=invalid_invitecode")

    try:
        birthday = date.fromisoformat(birthday_value)
        if birthday > date.today():
            raise ValueError
    except ValueError:
        return redirect("/register?error=invalid_birthday")

    if db.user_exists(username):
        return redirect("/register?error=username_exists")

    hashed_password = hash_password(password)
    success = db.new_user(username, hashed_password, birthday.isoformat(), height, mass, sex)
    if success:
        session["username"] = username
        return redirect("/dashboard")
    else:
        return redirect("/register?error=database_error")

@api_bp.route("/logout", methods=["GET"])
def logout():
    session.pop("username", None)
    return redirect("/")