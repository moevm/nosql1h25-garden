from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user, login_required

main_bp = Blueprint(
    "main_bp", __name__, template_folder="../../templates", static_folder="../../static"
)

@main_bp.route("/")
def index():
    return render_template("register.html")

@main_bp.route("/home")
@login_required
def home():
    return render_template("home.html")

# Add other routes here as needed