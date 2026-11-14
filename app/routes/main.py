from flask import Blueprint, redirect, render_template, session, request

main_bp = Blueprint("main", __name__)


@main_bp.route("/", methods=["GET", "POST"])
def index():
    return "Hello World!"

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


@main_bp.route("/dashboard", methods=["GET"])
def dashboard():
    if "username" not in session:
        return redirect("/login")

    return render_template("dashboard.html", username=session["username"])