from flask import Blueprint, request, redirect, session
from auth import auth_login
import db
api_bp = Blueprint("api", __name__)

TEMP_REFCODE = "123456"  # Temporary referral code for testing purposes

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
    age = request.form.get("age")
    height = request.form.get("height")
    mass = request.form.get("mass")
    sex = request.form.get("sex")
    refcode = request.form.get("refcode")

    if refcode != TEMP_REFCODE:
        return redirect("/register?error=invalid_refcode")

    success = db.new_user(username, password, age, height, mass, sex)
    if success:
        session["username"] = username
        return redirect("/dashboard")
    else:
        return redirect("/register?error=database_error")