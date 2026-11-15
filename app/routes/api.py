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

@api_bp.route("/settings", methods=["POST"], endpoint="settings")
@api_bp.route("/update-settings", methods=["POST"], endpoint="update_settings")
@api_bp.route("/update_settings", methods=["POST"], endpoint="update_settings_underscore")
@api_bp.route("/edit_settings", methods=["POST"], endpoint="edit_settings_underscore")
@api_bp.route("/edit-settings", methods=["POST"], endpoint="edit_settings")
def edit_settings():
    username = session.get("username")
    if not username:
        if request.is_json or "application/json" in request.headers.get("Accept", ""):
            return jsonify(error="Not authenticated."), 401
        return redirect("/login")

    data = request.get_json(silent=True)
    if data is None:
        data = request.form.to_dict() if request.form else {}

    if not isinstance(data, dict):
        return jsonify(error="Provide settings as an object."), 400

    if not db.user_exists(username):
        return jsonify(error="User not found."), 404

    updates = {}

    if "sex" in data and data["sex"] is not None:
        updates["sex"] = str(data["sex"]).strip()

    if "birthday" in data and data["birthday"]:
        try:
            bday = date.fromisoformat(str(data["birthday"]).strip())
            if bday > date.today():
                return jsonify(error="Birthday cannot be in the future."), 400
            updates["birthday"] = bday.isoformat()
        except ValueError:
            return jsonify(error="Invalid birthday format."), 400

    if "height" in data and data["height"] not in (None, ""):
        try:
            height = float(data["height"])
            if not math.isfinite(height) or height < 0:
                raise ValueError
            updates["height"] = height
        except (TypeError, ValueError):
            return jsonify(error="Invalid height."), 400

    mass_val = data.get("mass") if "mass" in data else (data.get("body-mass") or data.get("body_mass") or data.get("weight"))
    if mass_val not in (None, ""):
        try:
            mass = float(mass_val)
            if not math.isfinite(mass) or mass < 0:
                raise ValueError
            updates["mass"] = mass
        except (TypeError, ValueError):
            return jsonify(error="Invalid mass."), 400

    if "water_target" in data and data["water_target"] not in (None, ""):
        try:
            water = float(data["water_target"])
            if not math.isfinite(water) or water < 0:
                raise ValueError
            updates["water_target"] = int(water) if water.is_integer() else water
        except (TypeError, ValueError):
            return jsonify(error="Invalid water target."), 400

    if "exercise_target" in data and data["exercise_target"] not in (None, ""):
        try:
            exercise = float(data["exercise_target"])
            if not math.isfinite(exercise) or exercise < 0:
                raise ValueError
            updates["exercise_target"] = int(exercise) if exercise.is_integer() else exercise
        except (TypeError, ValueError):
            return jsonify(error="Invalid exercise target."), 400

    if "sleep_target" in data and data["sleep_target"] not in (None, ""):
        try:
            sleep = float(data["sleep_target"])
            if not math.isfinite(sleep) or sleep < 0 or sleep > 24:
                raise ValueError
            updates["sleep_target"] = sleep
        except (TypeError, ValueError):
            return jsonify(error="Invalid sleep target."), 400

    reminder_val = data.get("hydration_reminders") if "hydration_reminders" in data else data.get("hydration_reminder")
    if reminder_val not in (None, ""):
        updates["hydration_reminders"] = str(reminder_val)
        updates["hydration_reminder"] = reminder_val

    if "environment" in data and data["environment"] not in (None, ""):
        updates["environment"] = str(data["environment"]).strip()

    launch_val = data.get("launch_date") if "launch_date" in data else data.get("mission_start")
    if launch_val not in (None, ""):
        updates["launch_date"] = str(launch_val).strip()
        updates["mission_start"] = str(launch_val).strip()

    mission_len = data.get("mission_length") if "mission_length" in data else data.get("mission_duration")
    if mission_len not in (None, ""):
        try:
            duration = float(mission_len)
            if not math.isfinite(duration) or duration < 1:
                raise ValueError
            updates["mission_length"] = int(duration) if duration.is_integer() else duration
            updates["mission_duration"] = int(duration) if duration.is_integer() else duration
        except (TypeError, ValueError):
            return jsonify(error="Invalid mission length."), 400

    if not updates:
        return jsonify(error="No valid settings to update."), 400

    # Apply updates using db.edit_user
    success = True
    for field, val in updates.items():
        if not db.edit_user(username, field, val):
            success = False

    if success:
        if request.is_json or "application/json" in request.headers.get("Accept", ""):
            return jsonify(success=True, message="Settings updated successfully.")
        return redirect("/settings?saved=true")
    else:
        return jsonify(error="Failed to update settings."), 500

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