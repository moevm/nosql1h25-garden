from flask import Blueprint, render_template, abort, redirect, url_for, request
from flask_login import current_user, login_required
from functools import wraps
from applications import mongo # Import mongo
from applications.schemas import User # Import User schema for type hinting if needed
from bson import ObjectId # Add ObjectId import

admin_bp = Blueprint(
    "admin_bp", 
    __name__, 
    template_folder="../templates/admin",  # Keep admin templates separate
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
    search_query = request.args.get('search_query', '')
    admin_filter = request.args.get('admin_filter', '') # 'yes', 'no', or '' (all)

    filters = {}
    if search_query:
        filters['$or'] = [
            {'name': {'$regex': search_query, '$options': 'i'}},
            {'email': {'$regex': search_query, '$options': 'i'}}
        ]
    
    if admin_filter == 'yes':
        filters['is_admin'] = True
    elif admin_filter == 'no':
        filters['is_admin'] = False

    users_cursor = mongo.db.users.find(filters)
    users_list = [User.from_dict(u) for u in users_cursor]
    return render_template(
        'admin_view_users.html', 
        users=users_list, 
        title="Manage Users",
        search_query=search_query,
        admin_filter=admin_filter
    )

@admin_bp.route('/admin/gardens')
@login_required
@admin_required
def admin_view_gardens():
    search_garden_name = request.args.get('search_garden_name', '')
    search_user_email = request.args.get('search_user_email', '')

    filters = {}
    if search_garden_name:
        filters['name'] = {'$regex': search_garden_name, '$options': 'i'}

    user_ids_for_filter = []
    if search_user_email:
        # Find users matching the email search
        matching_users = mongo.db.users.find({'email': {'$regex': search_user_email, '$options': 'i'}}, {'_id': 1})
        user_ids_for_filter = [user['_id'] for user in matching_users]
        if not user_ids_for_filter: # If no users match email, no gardens will match this part of the filter
            filters['user_id'] = {'$in': []} # effectively no results for user email
        else:
            filters['user_id'] = {'$in': user_ids_for_filter}


    gardens_cursor = mongo.db.gardens.find(filters)
    gardens_list = []
    for g in gardens_cursor:
        # Try to get user email for display
        user = mongo.db.users.find_one({'_id': ObjectId(g['user_id'])})
        g['user_email'] = user['email'] if user else 'N/A'
        g['user_name'] = user['name'] if user else 'N/A'
        gardens_list.append(g)
    
    return render_template(
        'admin_view_gardens.html', 
        gardens=gardens_list, 
        title="Manage Gardens",
        search_garden_name=search_garden_name,
        search_user_email=search_user_email
    )

# Add more routes here for other entities (gardens, beds, care_logs, etc.) 