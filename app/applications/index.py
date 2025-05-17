from flask import Blueprint, redirect

main_bp = Blueprint('main_bp', __name__, template_folder="../templates")
@main_bp.route('/')
def index():
    return redirect('/auth/login')