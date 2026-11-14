from flask import Blueprint

api_bp = Blueprint("api", __name__)

@api_bp.route("/login", methods=["GET", "POST"])
def login():
    return "Login functionality goes here!"
