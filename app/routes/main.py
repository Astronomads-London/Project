from flask import Blueprint, redirect, render_template, session

main_bp = Blueprint("main", __name__)


@main_bp.route("/", methods=["GET", "POST"])
def index():
    return "Hello World!"

@main_bp.route("/login", methods=["GET", "POST"])
def login():
    return render_template("login.html")


@main_bp.route("/register", methods=["GET", "POST"])
def register():
    return render_template("register.html")

@main_bp.route("/dashboard", methods=["GET"])
def dashboard():
    if "username" not in session:
        return redirect("/login")

    return render_template("dashboard.html", username=session["username"])