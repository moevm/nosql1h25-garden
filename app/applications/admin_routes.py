from flask import Blueprint, render_template, abort, redirect, url_for, request
from flask_login import current_user, login_required
from functools import wraps
from applications import mongo
from applications.schemas import User
from bson import ObjectId
from datetime import datetime

admin_bp = Blueprint(
    "admin_bp", 
    __name__, 
    template_folder="../templates/admin",
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
    # Get counts for each entity
    stats = {
        'users': mongo.db.users.count_documents({}),
        'gardens': mongo.db.gardens.count_documents({}),
        'beds': mongo.db.beds.count_documents({}),
        'care_logs': mongo.db.care_logs.count_documents({}),
        'recommendations': mongo.db.recommendations.count_documents({}),
        'diary_entries': mongo.db.diary_entries.count_documents({})
    }
    return render_template('admin_dashboard.html', title="Admin Dashboard", stats=stats)

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

    if search_user_email:
        matching_users = mongo.db.users.find({'email': {'$regex': search_user_email, '$options': 'i'}}, {'_id': 1})
        user_ids = [user['_id'] for user in matching_users]
        if user_ids:
            filters['user_id'] = {'$in': user_ids}
        else:
            filters['user_id'] = None

    gardens_cursor = mongo.db.gardens.find(filters)
    gardens_list = []
    for garden in gardens_cursor:
        user = mongo.db.users.find_one({'_id': ObjectId(garden['user_id'])})
        garden['user_email'] = user['email'] if user else 'N/A'
        garden['user_name'] = user['name'] if user else 'N/A'
        gardens_list.append(garden)
    
    return render_template(
        'admin_view_gardens.html', 
        gardens=gardens_list, 
        title="Manage Gardens",
        search_garden_name=search_garden_name,
        search_user_email=search_user_email
    )

@admin_bp.route('/admin/beds')
@login_required
@admin_required
def admin_view_beds():
    search_bed_name = request.args.get('search_bed_name', '')
    search_garden_name = request.args.get('search_garden_name', '')
    search_user_email = request.args.get('search_user_email', '')

    filters = {}
    if search_bed_name:
        filters['name'] = {'$regex': search_bed_name, '$options': 'i'}

    if search_garden_name:
        matching_gardens = mongo.db.gardens.find({'name': {'$regex': search_garden_name, '$options': 'i'}}, {'_id': 1})
        garden_ids = [garden['_id'] for garden in matching_gardens]
        if garden_ids:
            filters['garden_id'] = {'$in': garden_ids}
        else:
            filters['garden_id'] = None

    if search_user_email:
        matching_users = mongo.db.users.find({'email': {'$regex': search_user_email, '$options': 'i'}}, {'_id': 1})
        user_ids = [user['_id'] for user in matching_users]
        if user_ids:
            filters['user_id'] = {'$in': user_ids}
        else:
            filters['user_id'] = None

    beds_cursor = mongo.db.beds.find(filters)
    beds_list = []
    for bed in beds_cursor:
        garden = mongo.db.gardens.find_one({'_id': bed['garden_id']})
        user = mongo.db.users.find_one({'_id': ObjectId(bed['user_id'])})
        bed['garden_name'] = garden['name'] if garden else 'N/A'
        bed['user_email'] = user['email'] if user else 'N/A'
        bed['user_name'] = user['name'] if user else 'N/A'
        beds_list.append(bed)

    return render_template('admin_view_beds.html', beds=beds_list, title="Manage Beds",
                         search_bed_name=search_bed_name, search_garden_name=search_garden_name,
                         search_user_email=search_user_email)

