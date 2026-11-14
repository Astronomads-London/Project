from flask import Blueprint, request, redirect

api_bp = Blueprint("api", __name__)

@api_bp.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")


    return f"username: {username}, password: {password}"


@api_bp.route("/register", methods=["POST"])
def register():
    username = request.form.get("username")
    password = request.form.get("password")

    return f"username: {username}, password: {password}"