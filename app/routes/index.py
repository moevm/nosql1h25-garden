from flask import Blueprint, redirect

main_bp = Blueprint('main_bp', __name__)
@main_bp.route('/')
def index():
    return redirect('/auth/login')