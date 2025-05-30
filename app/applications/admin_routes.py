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
    users_list = []
    for user_dict in users_cursor:
        user = User.from_dict(user_dict)
        user_id = user.get_id()

        gardens_count = mongo.db.gardens.count_documents({'user_id': user_id})
        
        beds_count = mongo.db.beds.count_documents({'user_id': user_id})
        
        care_logs_count = mongo.db.care_logs.count_documents({'user_id': user_id})

        user.gardens_count = gardens_count
        user.beds_count = beds_count
        user.care_logs_count = care_logs_count
        
        users_list.append(user)

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
        # Get user info
        user = mongo.db.users.find_one({'_id': ObjectId(garden['user_id'])})
        garden['user_email'] = user['email'] if user else 'N/A'
        garden['user_name'] = user['name'] if user else 'N/A'
        
        # Count related entities
        garden['beds_count'] = mongo.db.beds.count_documents({'garden_id': garden['_id']})
        garden['care_logs_count'] = mongo.db.care_logs.count_documents({'garden_id': garden['_id']})
        
        # Ensure area and location are present
        garden['area'] = garden.get('area', 'N/A')
        garden['location'] = garden.get('location', 'N/A')
        
        # Format creation time
        garden['created_at'] = garden.get('creation_time', garden.get('created_at', datetime.now()))
        
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
        # Get garden and user info
        garden = mongo.db.gardens.find_one({'_id': bed['garden_id']})
        user = mongo.db.users.find_one({'_id': ObjectId(bed['user_id'])})
        bed['garden_name'] = garden['name'] if garden else 'N/A'
        bed['user_email'] = user['email'] if user else 'N/A'
        bed['user_name'] = user['name'] if user else 'N/A'
        
        # Count care logs
        bed['care_logs_count'] = mongo.db.care_logs.count_documents({'bed_id': bed['_id']})
        
        # Ensure area and count_row are present
        bed['crop_name'] = bed.get('crop_name', 'N/A')
        bed['count_row'] = bed.get('count_row', 0)
        
        # Format creation time
        bed['created_at'] = bed.get('creation_time', bed.get('created_at', datetime.now()))
        
        beds_list.append(bed)

    return render_template('admin_view_beds.html', beds=beds_list, title="Manage Beds",
                         search_bed_name=search_bed_name, search_garden_name=search_garden_name,
                         search_user_email=search_user_email)

@admin_bp.route('/admin/care-logs')
@login_required
@admin_required
def admin_view_care_logs():
    search_action_type = request.args.get('search_action_type', '')
    search_garden_name = request.args.get('search_garden_name', '')
    search_bed_name = request.args.get('search_bed_name', '')
    search_user_email = request.args.get('search_user_email', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    filters = {}
    if search_action_type:
        filters['action_type'] = {'$regex': search_action_type, '$options': 'i'}

    if search_garden_name:
        matching_gardens = mongo.db.gardens.find({'name': {'$regex': search_garden_name, '$options': 'i'}}, {'_id': 1})
        garden_ids = [garden['_id'] for garden in matching_gardens]
        if garden_ids:
            filters['garden_id'] = {'$in': garden_ids}
        else:
            filters['garden_id'] = None

    if search_bed_name:
        matching_beds = mongo.db.beds.find({'name': {'$regex': search_bed_name, '$options': 'i'}}, {'_id': 1})
        bed_ids = [bed['_id'] for bed in matching_beds]
        if bed_ids:
            filters['bed_id'] = {'$in': bed_ids}
        else:
            filters['bed_id'] = None

    if search_user_email:
        matching_users = mongo.db.users.find({'email': {'$regex': search_user_email, '$options': 'i'}}, {'_id': 1})
        user_ids = [user['_id'] for user in matching_users]
        if user_ids:
            filters['user_id'] = {'$in': user_ids}
        else:
            filters['user_id'] = None

    if date_from or date_to:
        date_filter = {}
        if date_from:
            date_filter['$gte'] = datetime.strptime(date_from, '%Y-%m-%d')
        if date_to:
            date_filter['$lte'] = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        filters['log_date'] = date_filter

    care_logs_cursor = mongo.db.care_logs.find(filters)
    care_logs_list = []
    for log in care_logs_cursor:
        garden = mongo.db.gardens.find_one({'_id': log['garden_id']})
        bed = mongo.db.beds.find_one({'_id': log['bed_id']})
        user = mongo.db.users.find_one({'_id': ObjectId(log['user_id'])})
        log['garden_name'] = garden['name'] if garden else 'N/A'
        log['bed_name'] = bed['name'] if bed else 'N/A'
        log['user_email'] = user['email'] if user else 'N/A'
        log['user_name'] = user['name'] if user else 'N/A'
        care_logs_list.append(log)

    return render_template('admin_view_care_logs.html', care_logs=care_logs_list, title="Manage Care Logs",
                         search_action_type=search_action_type, search_garden_name=search_garden_name,
                         search_bed_name=search_bed_name, search_user_email=search_user_email,
                         date_from=date_from, date_to=date_to)

@admin_bp.route('/admin/recommendations')
@login_required
@admin_required
def admin_view_recommendations():
    search_action_type = request.args.get('search_action_type', '')
    search_garden_name = request.args.get('search_garden_name', '')
    search_bed_name = request.args.get('search_bed_name', '')
    search_user_email = request.args.get('search_user_email', '')
    is_completed = request.args.get('is_completed', '')
    due_date_from = request.args.get('due_date_from', '')
    due_date_to = request.args.get('due_date_to', '')

    filters = {}
    if search_action_type:
        filters['action_type'] = {'$regex': search_action_type, '$options': 'i'}

    if search_garden_name:
        matching_gardens = mongo.db.gardens.find({'name': {'$regex': search_garden_name, '$options': 'i'}}, {'_id': 1})
        garden_ids = [garden['_id'] for garden in matching_gardens]
        if garden_ids:
            filters['garden_id'] = {'$in': garden_ids}
        else:
            filters['garden_id'] = None

    if search_bed_name:
        matching_beds = mongo.db.beds.find({'name': {'$regex': search_bed_name, '$options': 'i'}}, {'_id': 1})
        bed_ids = [bed['_id'] for bed in matching_beds]
        if bed_ids:
            filters['bed_id'] = {'$in': bed_ids}
        else:
            filters['bed_id'] = None

    if search_user_email:
        matching_users = mongo.db.users.find({'email': {'$regex': search_user_email, '$options': 'i'}}, {'_id': 1})
        user_ids = [user['_id'] for user in matching_users]
        if user_ids:
            filters['user_id'] = {'$in': user_ids}
        else:
            filters['user_id'] = None

    if is_completed:
        filters['is_completed'] = (is_completed == 'yes')

    if due_date_from or due_date_to:
        date_filter = {}
        if due_date_from:
            date_filter['$gte'] = datetime.strptime(due_date_from, '%Y-%m-%d')
        if due_date_to:
            date_filter['$lte'] = datetime.strptime(due_date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        filters['due_date'] = date_filter

    recommendations_cursor = mongo.db.recommendations.find(filters)
    recommendations_list = []
    for rec in recommendations_cursor:
        garden = mongo.db.gardens.find_one({'_id': rec['garden_id']})
        bed = mongo.db.beds.find_one({'_id': rec['bed_id']})
        user = mongo.db.users.find_one({'_id': ObjectId(rec['user_id'])})
        rec['garden_name'] = garden['name'] if garden else 'N/A'
        rec['bed_name'] = bed['name'] if bed else 'N/A'
        rec['user_email'] = user['email'] if user else 'N/A'
        rec['user_name'] = user['name'] if user else 'N/A'
        recommendations_list.append(rec)

    return render_template('admin_view_recommendations.html', recommendations=recommendations_list,
                         title="Manage Recommendations", search_action_type=search_action_type,
                         search_garden_name=search_garden_name, search_bed_name=search_bed_name,
                         search_user_email=search_user_email, is_completed=is_completed,
                         due_date_from=due_date_from, due_date_to=due_date_to)

@admin_bp.route('/admin/diary')
@login_required
@admin_required
def admin_view_diary():
    search_title = request.args.get('search_title', '')
    search_user_email = request.args.get('search_user_email', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    filters = {}
    if search_title:
        filters['title'] = {'$regex': search_title, '$options': 'i'}

    if search_user_email:
        matching_users = mongo.db.users.find({'email': {'$regex': search_user_email, '$options': 'i'}}, {'_id': 1})
        user_ids = [user['_id'] for user in matching_users]
        if user_ids:
            filters['user_id'] = {'$in': user_ids}
        else:
            filters['user_id'] = None

    if date_from or date_to:
        date_filter = {}
        if date_from:
            date_filter['$gte'] = datetime.strptime(date_from, '%Y-%m-%d')
        if date_to:
            date_filter['$lte'] = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        filters['created_at'] = date_filter

    entries_cursor = mongo.db.diary_entries.find(filters)
    entries_list = []
    for entry in entries_cursor:
        user = mongo.db.users.find_one({'_id': ObjectId(entry['user_id'])})
        entry['user_email'] = user['email'] if user else 'N/A'
        entry['user_name'] = user['name'] if user else 'N/A'
        entries_list.append(entry)

    return render_template('admin_view_diary.html', entries=entries_list, title="Manage Diary Entries",
                         search_title=search_title, search_user_email=search_user_email,
                         date_from=date_from, date_to=date_to)
