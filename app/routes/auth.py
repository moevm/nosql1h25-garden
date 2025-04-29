from flask import (
    Blueprint, render_template
)

auth_bp = Blueprint("auth_bp", __name__, template_folder=".templates")

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')


