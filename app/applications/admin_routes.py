from flask import Blueprint, render_template, abort, redirect, url_for
from flask_login import current_user, login_required
from functools import wraps

admin_bp = Blueprint(
    "admin_bp", 
    __name__, 
    template_folder="../../templates/admin",  # Keep admin templates separate
    static_folder="../../static"
)

# Decorator for admin-only access
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html', title="Admin Dashboard")

# Placeholder for viewing all users - we'll expand this later
@admin_bp.route('/admin/users')
@login_required
@admin_required
def admin_view_users():
    # This will eventually fetch and display users
    users = [] # mongo.db.users.find() 
    return render_template('admin_view_users.html', users=users, title="Manage Users")

# Add more routes here for other entities (gardens, beds, care_logs, etc.) 