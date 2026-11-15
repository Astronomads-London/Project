import math
import re
from datetime import date, datetime, timezone

from flask import Blueprint, current_app, request, redirect, session, jsonify
from auth import auth_login, hash_password
from app.utils.unitconversion import height_to_cm, pounds_to_kg
from app.utils.uring import urine
import db


api_bp = Blueprint("api", __name__)

TEMP_REFCODE = "123456"  # Temporary referral code for testing purposes
TODAY_DATA_FIELDS = {
    "resting_heart_rate": (20, 250),
    "body_temp": (30, 45),
    "o2_level": (50, 100),
    "glucose_level": (20, 600),
    "breaths_per_min": (1, 80),
    "water": (0, 20000),
    "sleep_hours": (0, 24),
    "exercise": (0, 1440),
}
PVT_OUTCOMES = {"commission", "false_start", "response", "lapse", "omission", "truncated"}
URINE_FIELDS = ("ca", "ntx", "ctx1", "pyridinoline")
URINE_FIELD_LABELS = {
    "ca": "Calcium (CA)",
    "ntx": "N-telopeptide (NTX)",
    "ctx1": "C-telopeptide-1 (CTX1)",
    "pyridinoline": "Pyridinoline",
}


@api_bp.route("/urine-check", methods=["POST"])
def urine_check():
    username = session.get("username")
    if not username:
        return jsonify(error="Not authenticated."), 401
    if request.content_length is not None and request.content_length > 4096:
        return jsonify(error="Urine check payload is too large."), 413

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Provide urine check values as a JSON object."), 400

    user = db.get_user(username)
    if not user:
        return jsonify(error="User not found."), 404

    sex = str(user.get("sex", "")).strip().lower()
    if sex in {"male", "m"}:
        sex_code = "M"
        period = False
    elif sex in {"female", "f"}:
        sex_code = "F"
        period = data.get("period")
        if not isinstance(period, bool):
            return jsonify(error="Select whether you are currently on your period."), 400
    else:
        return jsonify(error="A valid sex is required in your profile to run this check."), 400

    values = {}
    for field in URINE_FIELDS:
        value = data.get(field)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or value < 0
            or value > 1_000_000
            or not math.isfinite(value)
        ):
            return jsonify(error=f"Enter a valid non-negative {field.upper()} value."), 400
        values[field] = value

    results = urine(
        sex_code,
        values["ca"],
        values["ntx"],
        values["ctx1"],
        values["pyridinoline"],
        period,
    )
    failed_tests = [
        URINE_FIELD_LABELS[field]
        for field, passed in zip(URINE_FIELDS, results)
        if not passed
    ]
    return jsonify(success=True, passed=not failed_tests, failed_tests=failed_tests)


def _percentile(values, percentile):
    ordered = sorted(values)
    if not ordered:
        return None
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def score_pvt_trials(trials):
    scored_trials = [trial for trial in trials if trial["outcome"] != "truncated"]
    response_times = [
        trial["reaction_time_ms"]
        for trial in scored_trials
        if trial["reaction_time_ms"] is not None and trial["reaction_time_ms"] >= 100
    ]
    reciprocal_times = [1000 / response_time for response_time in response_times]
    non_lapse_reciprocals = [
        1000 / trial["reaction_time_ms"]
        for trial in scored_trials
        if trial["reaction_time_ms"] is not None
        and 100 <= trial["reaction_time_ms"] <= 500
    ]
    fastest_count = max(1, math.ceil(len(response_times) * 0.1)) if response_times else 0
    fastest_reciprocals = [
        1000 / response_time for response_time in sorted(response_times)[:fastest_count]
    ]
    slowest_reciprocals = [
        1000 / response_time for response_time in sorted(response_times)[-fastest_count:]
    ]
    lapse_count = sum(trial["outcome"] in {"lapse", "omission"} for trial in scored_trials)
    omission_count = sum(trial["outcome"] == "omission" for trial in scored_trials)
    commission_count = sum(trial["outcome"] == "commission" for trial in scored_trials)
    false_start_count = sum(
        trial["outcome"] in {"commission", "false_start"} for trial in scored_trials
    )
    valid_stimuli = sum(
        trial["stimulus_onset_ms"] is not None for trial in scored_trials
    )

    return {
        "trial_count": len(scored_trials),
        "valid_stimulus_count": valid_stimuli,
        "average_response_time_ms": (
            sum(response_times) / len(response_times) if response_times else None
        ),
        "lapse_count": lapse_count,
        "omission_count": omission_count,
        "commission_count": commission_count,
        "false_start_count": false_start_count,
        "lapses_transformed": math.sqrt(lapse_count) + math.sqrt(lapse_count + 1),
        "false_rt_percent": (
            commission_count / valid_stimuli * 100 if valid_stimuli else None
        ),
        "overall_performance_score": (
            1 - (false_start_count + lapse_count) / len(scored_trials)
            if scored_trials else None
        ),
        "mean_reciprocal_rt_per_second": (
            sum(reciprocal_times) / len(reciprocal_times) if reciprocal_times else None
        ),
        "mean_reciprocal_rt500_per_second": (
            sum(non_lapse_reciprocals) / len(non_lapse_reciprocals)
            if non_lapse_reciprocals else None
        ),
        "reciprocal_rt_variability_per_second": (
            _percentile(reciprocal_times, 0.9) - _percentile(reciprocal_times, 0.1)
            if reciprocal_times else None
        ),
        "fastest_10_percent_reciprocal_rt_per_second": (
            sum(fastest_reciprocals) / len(fastest_reciprocals)
            if fastest_reciprocals else None
        ),
        "slowest_10_percent_reciprocal_rt_per_second": (
            sum(slowest_reciprocals) / len(slowest_reciprocals)
            if slowest_reciprocals else None
        ),
    }


@api_bp.route("/pvt-results", methods=["POST"])
def save_pvt_results():
    username = session.get("username")
    if not username:
        return jsonify(error="Not authenticated."), 401
    if request.content_length is not None and request.content_length > 512_000:
        return jsonify(error="PVT results payload is too large."), 413

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Provide PVT results as a JSON object."), 400
    if not db.user_exists(username):
        return jsonify(error="User not found."), 404

    try:
        started_at = datetime.fromisoformat(
            str(data["started_at"]).replace("Z", "+00:00")
        )
        if started_at.tzinfo is None:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        return jsonify(error="Provide a valid timezone-aware start time."), 400

    if data.get("duration_ms") != 180000:
        return jsonify(error="PVT-B runs must last exactly 180000 milliseconds."), 400
    trials = data.get("trials")
    if not isinstance(trials, list) or not 1 <= len(trials) <= 500:
        return jsonify(error="Provide between 1 and 500 trial records."), 400

    def valid_number(value, minimum, maximum):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False
        try:
            return math.isfinite(value) and minimum <= value <= maximum
        except OverflowError:
            return False

    cleaned_trials = []
    for index, trial in enumerate(trials, start=1):
        if not isinstance(trial, dict) or trial.get("trial_number") != index:
            return jsonify(error="Trial records must be ordered and numbered consecutively."), 400

        trial_start = trial.get("trial_start_ms")
        foreperiod = trial.get("foreperiod_ms")
        stimulus_onset = trial.get("stimulus_onset_ms")
        response_at = trial.get("response_ms")
        reaction_time = trial.get("reaction_time_ms")
        outcome = trial.get("outcome")
        if not valid_number(trial_start, 0, 180000):
            return jsonify(error=f"Trial {index} has an invalid start time."), 400
        if not valid_number(foreperiod, 0, 3000):
            return jsonify(error=f"Trial {index} has an invalid foreperiod."), 400
        if not isinstance(outcome, str) or outcome not in PVT_OUTCOMES:
            return jsonify(error=f"Trial {index} has an invalid outcome."), 400
        if stimulus_onset is not None and not valid_number(stimulus_onset, trial_start, 180000):
            return jsonify(error=f"Trial {index} has an invalid stimulus time."), 400
        if response_at is not None and not valid_number(response_at, trial_start, 180000):
            return jsonify(error=f"Trial {index} has an invalid response time."), 400
        if reaction_time is not None and not valid_number(reaction_time, 0, 30000):
            return jsonify(error=f"Trial {index} has an invalid reaction time."), 400

        has_response = response_at is not None
        if outcome == "commission":
            valid_trial = stimulus_onset is None and has_response and reaction_time is None
        elif outcome == "truncated":
            valid_trial = not has_response and reaction_time is None
        elif outcome == "omission":
            valid_trial = stimulus_onset is not None and not has_response and reaction_time is None
        else:
            valid_trial = (
                stimulus_onset is not None
                and has_response
                and reaction_time is not None
                and abs((response_at - stimulus_onset) - reaction_time) <= 1
            )
            if outcome == "false_start":
                valid_trial = valid_trial and reaction_time < 100
            elif outcome == "response":
                valid_trial = valid_trial and 100 <= reaction_time <= 500
            elif outcome == "lapse":
                valid_trial = valid_trial and 500 < reaction_time <= 30000
        if not valid_trial:
            return jsonify(error=f"Trial {index} has inconsistent timing and outcome data."), 400
        if (
            stimulus_onset is not None
            and stimulus_onset - trial_start < foreperiod - 1
        ):
            return jsonify(error=f"Trial {index} stimulus precedes its foreperiod."), 400

        cleaned_trials.append({
            "trial_number": index,
            "trial_start_ms": trial_start,
            "foreperiod_ms": foreperiod,
            "stimulus_onset_ms": stimulus_onset,
            "response_ms": response_at,
            "reaction_time_ms": reaction_time,
            "outcome": outcome,
        })

    scores = score_pvt_trials(cleaned_trials)
    if not db.save_pvt_result(username, started_at.astimezone(timezone.utc), cleaned_trials, scores):
        return jsonify(error="Could not save PVT results."), 500
    return jsonify(success=True, scores=scores)


@api_bp.route("/edit-today", methods=["POST"])
def edit_today():
    username = session.get("username")
    is_json_request = request.is_json or "application/json" in request.headers.get("Accept", "")
    if not username:
        if is_json_request:
            return jsonify(error="Not authenticated."), 401
        return redirect("/login")

    data = request.get_json(silent=True)
    if data is None:
        data = request.form.to_dict() if request.form else {}
    if not isinstance(data, dict):
        return jsonify(error="Provide today's data as an object."), 400
    if "streak" in data:
        message = "Your streak is calculated automatically from consecutive days with logged health data."
        if is_json_request:
            return jsonify(error=message), 400
        return redirect("/today?error=streak")
    if not db.user_exists(username):
        return jsonify(error="User not found."), 404

    updates = {}
    for field, (minimum, maximum) in TODAY_DATA_FIELDS.items():
        value = data.get(field)
        if value in (None, ""):
            continue
        try:
            number = float(value)
            if not math.isfinite(number) or not minimum <= number <= maximum:
                raise ValueError
            updates[field] = int(number) if number.is_integer() else number
        except (TypeError, ValueError):
            message = f"Enter a valid {field.replace('_', ' ')} value."
            if is_json_request:
                return jsonify(error=message), 400
            return redirect("/today?error=invalid")

    blood_pressure = data.get("blood_pressure")
    if blood_pressure not in (None, ""):
        match = re.fullmatch(r"\s*(\d{2,3})\s*/\s*(\d{2,3})\s*", str(blood_pressure))
        if not match:
            message = "Enter blood pressure as systolic/diastolic, for example 120/80."
            if is_json_request:
                return jsonify(error=message), 400
            return redirect("/today?error=invalid")
        systolic, diastolic = (int(value) for value in match.groups())
        if not 40 <= systolic <= 300 or not 20 <= diastolic <= 200 or systolic <= diastolic:
            message = "Enter a valid systolic/diastolic blood pressure reading."
            if is_json_request:
                return jsonify(error=message), 400
            return redirect("/today?error=invalid")
        updates["blood_pressure"] = f"{systolic}/{diastolic}"

    if not updates:
        message = "Enter at least one value to update."
        if is_json_request:
            return jsonify(error=message), 400
        return redirect("/today?error=empty")

    for field, value in updates.items():
        if not db.edit_today_data(username, field, value):
            if is_json_request:
                return jsonify(error="Failed to save today's health data."), 500
            return redirect("/today?error=save")

    streak = db.get_current_streak(username)
    if not db.edit_user(username, "streak", streak):
        if is_json_request:
            return jsonify(error="Failed to save your streak."), 500
        return redirect("/today?error=save")

    if is_json_request:
        return jsonify(success=True, message="Today's data updated.")
    return redirect("/today?saved=true")

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