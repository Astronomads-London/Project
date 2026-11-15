import hmac
import math
from datetime import datetime, timezone

from flask import Blueprint, current_app, request, redirect, session, jsonify
from auth import auth_login, hash_password
from app.utils.unitconversion import height_to_cm, pounds_to_kg, cm_to_feet_and_inches, kg_to_pounds
from app.utils.birthday import birthday_error, parse_birthday
from app.utils.bloodpressure import BLOOD_PRESSURE_ERROR, parse_blood_pressure
from app.utils.unitconversion import height_to_cm, pounds_to_kg
from app.utils.messages import clean_message
from app.utils.uring import urine
from app.utils.validation import (
    CONVERSION_LIMITS,
    DAY_TOTAL_ERROR,
    ENVIRONMENT_CHOICES,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    PROFILE_LIMIT_ERRORS,
    SEX_CHOICES,
    TODAY_DATA_FIELDS,
    USERNAME_PATTERN,
    check_height_conversion,
    day_total_ok,
    is_hydration_choice,
    launch_date_error,
    parse_launch_date,
    parse_number,
    parse_profile_measurement,
    parse_settings_number,
    pvt_start_time_ok,
    settings_number_error,
    today_data_error,
)
import db


api_bp = Blueprint("api", __name__)

TEMP_REFCODE = "123456"  # Temporary referral code for testing purposes
PVT_OUTCOMES = {"commission", "false_start", "response", "lapse", "omission", "truncated"}
URINE_FIELDS = ("ca", "ntx", "pyridinoline")
URINE_FIELD_LABELS = {
    "ca": "Calcium (CA)",
    "ntx": "N-telopeptide (NTX)",
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

    birthday = parse_birthday(user.get("birthday", ""))
    if birthday is None:
        return jsonify(error="A valid birthday is required in your profile to run this check."), 400
    today = datetime.now(timezone.utc).date()
    age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
    results = urine(
        sex_code,
        values["ca"],
        values["ntx"],
        values["pyridinoline"],
        period,
        age,
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
    if not pvt_start_time_ok(started_at):
        return jsonify(error="The test start time must be within the last 24 hours."), 400

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
    for field, (minimum, maximum, decimals) in TODAY_DATA_FIELDS.items():
        value = data.get(field)
        if value in (None, ""):
            continue
        number = parse_number(value, minimum, maximum, decimals)
        if number is None:
            if is_json_request:
                return jsonify(error=today_data_error(field)), 400
            return redirect("/today?error=invalid")
        updates[field] = number

    # Sleep and exercise have to fit in one day, counting what is already logged.
    if "sleep_hours" in updates or "exercise" in updates:
        logged = db.get_today_data(username) or {}
        sleep_hours = updates.get("sleep_hours", logged.get("sleep_hours"))
        exercise_minutes = updates.get("exercise", logged.get("exercise"))
        if not day_total_ok(sleep_hours, exercise_minutes):
            if is_json_request:
                return jsonify(error=DAY_TOTAL_ERROR), 400
            return redirect("/today?error=day_total")

    blood_pressure = data.get("blood_pressure")
    if blood_pressure not in (None, ""):
        reading = parse_blood_pressure(blood_pressure)
        if reading is None:
            if is_json_request:
                return jsonify(error=BLOOD_PRESSURE_ERROR), 400
            return redirect("/today?error=blood_pressure")
        updates["blood_pressure"] = reading

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
    if "centimetres" in data and "cm" not in data:
        data["cm"] = data["centimetres"]
    if "kilograms" in data and "kg" not in data:
        data["kg"] = data["kilograms"]

    values = {}

    required_fields = {
        "height": ("feet", "inches"),
        "height_reverse": ("cm",),
        "cm_to_feet": ("cm",),
        "cm_to_feet_and_inches": ("cm",),
        "cm": ("cm",),
        "weight": ("pounds",),
        "weight_reverse": ("kg",),
        "kg_to_pounds": ("kg",),
        "kg": ("kg",),
    }
    if conversion not in required_fields:
        return jsonify(error="Choose a supported conversion."), 400

    for field in required_fields[conversion]:
        low, high = CONVERSION_LIMITS[field]
        value = parse_number(data.get(field), low, high)
        if value is None:
            return jsonify(error=f"{field.capitalize()} must be between {low} and {high}, with no leading zeros."), 400
        values[field] = value

    if conversion == "height":
        problem = check_height_conversion(values["feet"], values["inches"])
        if problem:
            return jsonify(error=problem), 400
        result = height_to_cm(values["feet"], values["inches"])
        return jsonify(result=f"{result:.2f} cm")

    if conversion in ("height_reverse", "cm_to_feet", "cm_to_feet_and_inches", "cm"):
        feet, inches = cm_to_feet_and_inches(values["cm"])
        feet_int = int(feet) if hasattr(feet, "is_integer") and feet.is_integer() else int(feet)
        return jsonify(result=f"{feet_int} feet and {inches} inches")

    if conversion in ("weight_reverse", "kg_to_pounds", "kg"):
        result = kg_to_pounds(values["kg"])
        return jsonify(result=f"{result:.2f} pounds")

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

    if data.get("sex") not in (None, ""):
        sex = data["sex"].strip() if isinstance(data["sex"], str) else None
        if sex not in SEX_CHOICES:
            return jsonify(error="Sex must be Male or Female."), 400
        updates["sex"] = sex

    if "birthday" in data and data["birthday"]:
        bday = parse_birthday(data["birthday"])
        if bday is None:
            return jsonify(error=birthday_error()), 400
        updates["birthday"] = bday.isoformat()

    if "height" in data and data["height"] not in (None, ""):
        height = parse_profile_measurement("height", data["height"])
        if height is None:
            return jsonify(error=PROFILE_LIMIT_ERRORS["height"]), 400
        updates["height"] = height

    mass_val = data.get("mass") if "mass" in data else (data.get("body-mass") or data.get("body_mass") or data.get("weight"))
    if mass_val not in (None, ""):
        mass = parse_profile_measurement("mass", mass_val)
        if mass is None:
            return jsonify(error=PROFILE_LIMIT_ERRORS["mass"]), 400
        updates["mass"] = mass

    for field in ("water_target", "exercise_target", "sleep_target"):
        if data.get(field) in (None, ""):
            continue
        target = parse_settings_number(field, data[field])
        if target is None:
            return jsonify(error=settings_number_error(field)), 400
        updates[field] = float(target) if field == "sleep_target" else target

    reminder_val = data.get("hydration_reminders") if "hydration_reminders" in data else data.get("hydration_reminder")
    if reminder_val not in (None, ""):
        if not is_hydration_choice(reminder_val):
            return jsonify(error="Choose one of the listed hydration reminder options."), 400
        updates["hydration_reminders"] = str(reminder_val)
        updates["hydration_reminder"] = reminder_val

    if data.get("environment") not in (None, ""):
        environment = data["environment"].strip().lower() if isinstance(data["environment"], str) else None
        if environment not in ENVIRONMENT_CHOICES:
            return jsonify(error="Environment must be ISS, Mars or Moon."), 400
        updates["environment"] = environment

    launch_val = data.get("launch_date") if "launch_date" in data else data.get("mission_start")
    if launch_val not in (None, ""):
        launch = parse_launch_date(launch_val)
        if launch is None:
            return jsonify(error=launch_date_error()), 400
        updates["launch_date"] = launch.isoformat()
        updates["mission_start"] = launch.isoformat()

    mission_len = data.get("mission_length") if "mission_length" in data else data.get("mission_duration")
    if mission_len not in (None, ""):
        duration = parse_settings_number("mission_length", mission_len)
        if duration is None:
            return jsonify(error=settings_number_error("mission_length")), 400
        updates["mission_length"] = duration
        updates["mission_duration"] = duration

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

def _codes_match(entered, expected):
    """Compare an entered invite code with a configured one; an unset code matches nothing."""
    if not expected or not isinstance(entered, str):
        return False
    return hmac.compare_digest(entered.encode(), expected.encode())


@api_bp.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    exists = db.user_exists(username)  # Check if the user exists in the database

    if exists:
        is_valid = auth_login(username, username, password, db.return_user_hash(username))
        if is_valid:
            session["username"] = username
            if db.is_flight_surgeon(db.get_user(username)):
                session["role"] = db.ROLE_FLIGHT_SURGEON
                return redirect("/surgeon")
            session["role"] = db.ROLE_ASTRONAUT
            return redirect("/dashboard")
        else:
            return redirect("/login?error=invalid")
    else:
        return redirect("/login?error=not_found")


@api_bp.route("/register", methods=["POST"])
def register():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    invitecode = request.form.get("invite_code")
    expected_invite_code = current_app.config.get("INVITE_CODE")
    # The sign-up form's Astronaut / Flight surgeon switch.
    is_surgeon = request.form.get("account_type") == db.ROLE_FLIGHT_SURGEON

    def fail(error):
        # Keep the switch on the same side when the form is shown again.
        kind = "type=flight_surgeon&" if is_surgeon else ""
        return redirect(f"/register?{kind}error={error}")

    if not expected_invite_code:
        current_app.logger.error("INVITE_CODE is not configured.")
        return fail("invite_unavailable")

    # Each kind of account has its own invite code. A flight surgeon code that
    # is identical to the astronaut code is refused, so the astronaut code can
    # never hand out flight surgeon access.
    if is_surgeon:
        code_ok = (
            _codes_match(invitecode, current_app.config.get("SURGEON_INVITE_CODE"))
            and not _codes_match(invitecode, expected_invite_code)
        )
    else:
        code_ok = _codes_match(invitecode, expected_invite_code)
    if not code_ok:
        return fail("invalid_invitecode")

    if not USERNAME_PATTERN.fullmatch(username):
        return fail("invalid_username")

    if not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
        return fail("invalid_password")

    if is_surgeon:
        # Flight surgeons do not log health data, so they have no profile.
        role = db.ROLE_FLIGHT_SURGEON
        birthday = height = mass = sex = None
    else:
        role = db.ROLE_ASTRONAUT
        sex = request.form.get("sex")
        if sex not in SEX_CHOICES:
            return fail("invalid_sex")

        birthday = parse_birthday(request.form.get("birthday", ""))
        if birthday is None:
            return fail("invalid_birthday")
        birthday = birthday.isoformat()

        # Every profile field is required for astronauts, so a blank value is rejected too.
        height = parse_profile_measurement("height", request.form.get("height"))
        if height is None:
            return fail("invalid_height")

        mass = parse_profile_measurement("mass", request.form.get("mass") or request.form.get("body-mass"))
        if mass is None:
            return fail("invalid_mass")

    if db.user_exists(username):
        return fail("username_exists")

    hashed_password = hash_password(password)
    success = db.new_user(username, hashed_password, birthday, height, mass, sex, role)
    if success:
        session["username"] = username
        session["role"] = role
        return redirect("/surgeon" if is_surgeon else "/dashboard")
    else:
        return fail("database_error")

@api_bp.route("/messages", methods=["POST"])
def send_message():
    """Add an astronaut's reply to their conversation with the flight surgeons."""
    username = session.get("username")
    user = db.get_user(username) if username else None
    if not user:
        return redirect("/login")
    if db.is_flight_surgeon(user):
        # Flight surgeons write from the treatment page, to a chosen astronaut.
        return redirect("/surgeon/treatment")

    text, error = clean_message(request.form.get("message"))
    if error is None and not db.add_message(username, username, db.ROLE_ASTRONAUT, text):
        error = "save"
    if error:
        return redirect(f"/messages?error={error}")
    return redirect("/messages?sent=true")


@api_bp.route("/logout", methods=["GET"])
def logout():
    session.pop("username", None)
    session.pop("role", None)
    return redirect("/")