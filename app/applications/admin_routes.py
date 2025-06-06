from flask import Blueprint, render_template, abort, redirect, url_for, request, flash
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
        'diary_entries': mongo.db.diary.count_documents({})
    }
    return render_template('admin_dashboard.html', title="Admin Dashboard", stats=stats)

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
        title="Управление пользователями",
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
        
        # Format creation time - ensure it's a datetime object
        creation_time = garden.get('creation_time', garden.get('created_at', datetime.now()))
        if isinstance(creation_time, str):
            try:
                garden['created_at'] = datetime.fromisoformat(creation_time.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                garden['created_at'] = datetime.now()
        elif isinstance(creation_time, datetime):
            garden['created_at'] = creation_time
        else:
            garden['created_at'] = datetime.now()
        
        gardens_list.append(garden)
    
    return render_template(
        'admin_view_gardens.html', 
        gardens=gardens_list, 
        title="Управление участками",
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
        
        # Ensure area and count_row are present        bed['crop_name'] = bed.get('crop_name', 'N/A')
        bed['count_row'] = bed.get('count_row', 0)
        
        # Format creation time - ensure it's a datetime object
        creation_time = bed.get('creation_time', bed.get('created_at', datetime.now()))
        if isinstance(creation_time, str):
            try:
                bed['created_at'] = datetime.fromisoformat(creation_time.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                bed['created_at'] = datetime.now()
        elif isinstance(creation_time, datetime):
            bed['created_at'] = creation_time
        else:
            bed['created_at'] = datetime.now()
        
        beds_list.append(bed)

    return render_template('admin_view_beds.html', beds=beds_list, title="Управление грядками",
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
        
        # Ensure log_date is a datetime object
        log_date = log.get('log_date')
        if isinstance(log_date, str):
            try:
                log['log_date'] = datetime.fromisoformat(log_date.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                log['log_date'] = None
        elif not isinstance(log_date, datetime):
            log['log_date'] = None
            
        care_logs_list.append(log)

    return render_template('admin_view_care_logs.html', care_logs=care_logs_list, title="Управление записями об уходе",
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
        
        # Ensure due_date is a datetime object
        due_date = rec.get('due_date')
        if isinstance(due_date, str):
            try:
                rec['due_date'] = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                rec['due_date'] = None
        elif not isinstance(due_date, datetime):
            rec['due_date'] = None
            
        recommendations_list.append(rec)

    return render_template('admin_view_recommendations.html', recommendations=recommendations_list,
                         title="Управление рекомендациями", search_action_type=search_action_type,
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

    entries_cursor = mongo.db.diary.find(filters)
    entries_list = []
    for entry in entries_cursor:
        user = mongo.db.users.find_one({'_id': ObjectId(entry['user_id'])})
        entry['user_email'] = user['email'] if user else 'N/A'
        entry['user_name'] = user['name'] if user else 'N/A'
        
        # Ensure creation dates are datetime objects
        creation_time = entry.get('creation_time')
        if isinstance(creation_time, str):
            try:
                entry['creation_time'] = datetime.fromisoformat(creation_time.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                entry['creation_time'] = datetime.now()
        elif not isinstance(creation_time, datetime):
            entry['creation_time'] = datetime.now()
            
        last_modified_time = entry.get('last_modified_time')
        if isinstance(last_modified_time, str):
            try:
                entry['last_modified_time'] = datetime.fromisoformat(last_modified_time.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                entry['last_modified_time'] = entry['creation_time']
        elif not isinstance(last_modified_time, datetime):
            entry['last_modified_time'] = entry['creation_time']
            
        entries_list.append(entry)

    return render_template('admin_view_diary.html', entries=entries_list, title="Управление записями в дневнике",
                         search_title=search_title, search_user_email=search_user_email,
                         date_from=date_from, date_to=date_to)

@admin_bp.route('/admin/gardens/<garden_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_garden(garden_id):
    """Admin can edit any garden"""
    from .land import SOIL_TYPES, TERRAIN_TYPES, LIGHTING_OPTIONS
    from .utils import save_photo
    
    garden_doc = mongo.db.gardens.find_one({'_id': ObjectId(garden_id)})
    if not garden_doc:
        flash('Garden not found.', 'error')
        return redirect(url_for('admin_bp.admin_view_gardens'))
    
    if request.method == 'POST':
        data = request.form
        update_data = {
            'name': data.get('name', garden_doc.get('name')),
            'location': data.get('location', garden_doc.get('location', '')),
            'area': float(data.get('area', garden_doc.get('area', 0.0))),
            'soil_type': data.get('soil_type', garden_doc.get('soil_type', '')),
            'terrain_type': data.get('terrain_type', garden_doc.get('terrain_type', '')),
            'lighting': data.get('lighting', garden_doc.get('lighting', '')),
            'last_modified_time': datetime.utcnow()
        }

        if update_data['soil_type'] not in SOIL_TYPES:
            flash('Invalid soil type selected.', 'error')
            return render_template('land_form.html', form_data=data, garden_id=garden_id, is_edit=True, is_admin=True, soil_types=SOIL_TYPES, terrain_types=TERRAIN_TYPES, lighting_options=LIGHTING_OPTIONS)
        
        if 'photo' in request.files:
            photo_file = request.files['photo']
            if photo_file.filename != '':
                saved_photo_path = save_photo(photo_file)
                if saved_photo_path:
                    if 'photo_file_paths' not in update_data:
                        update_data['photo_file_paths'] = garden_doc.get('photo_file_paths', [])
                    update_data['photo_file_paths'].append(saved_photo_path)

        mongo.db.gardens.update_one({'_id': ObjectId(garden_id)}, {'$set': update_data})
        flash('Garden updated successfully!', 'success')
        return redirect(url_for('admin_bp.admin_view_gardens'))
    
    return render_template('land_form.html', form_data=garden_doc, garden_id=garden_id, is_edit=True, is_admin=True, soil_types=SOIL_TYPES, terrain_types=TERRAIN_TYPES, lighting_options=LIGHTING_OPTIONS)

@admin_bp.route('/admin/gardens/<garden_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_garden(garden_id):
    """Admin can delete any garden"""
    import os
    from flask import current_app
    
    garden = mongo.db.gardens.find_one({'_id': ObjectId(garden_id)})
    if not garden:
        flash('Garden not found.', 'error')
        return redirect(url_for('admin_bp.admin_view_gardens'))

    # Find all beds of this garden
    beds = list(mongo.db.beds.find({'garden_id': ObjectId(garden_id)}))
    
    # Delete all care logs related to this garden
    mongo.db.care_logs.delete_many({'garden_id': ObjectId(garden_id)})
    mongo.db.recommendations.delete_many({'garden_id': ObjectId(garden_id)})
    
    # Delete all beds of this garden
    for bed in beds:
        if bed.get('photo_file_paths'):
            for photo_path in bed['photo_file_paths']:
                if photo_path:
                    photo_disk_path = os.path.join(current_app.static_folder, photo_path)
                    if os.path.exists(photo_disk_path):
                        try:
                            os.remove(photo_disk_path)
                        except Exception as e:
                            flash(f'Could not delete bed photo: {e}', 'warning')
    
    mongo.db.beds.delete_many({'garden_id': ObjectId(garden_id)})
    
    # Delete garden photos
    if garden.get('photo_file_paths'):
        for photo_path in garden['photo_file_paths']:
            if photo_path:
                photo_disk_path = os.path.join(current_app.static_folder, photo_path)
                if os.path.exists(photo_disk_path):
                    try:
                        os.remove(photo_disk_path)
                    except Exception as e:
                        flash(f'Could not delete garden photo: {e}', 'warning')
    
    # Delete the garden itself
    mongo.db.gardens.delete_one({'_id': ObjectId(garden_id)})
    
    flash('Garden deleted successfully!', 'success')
    return redirect(url_for('admin_bp.admin_view_gardens'))

@admin_bp.route('/admin/beds/<bed_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_bed(bed_id):
    """Admin can edit any bed"""
    from .land_beds import BED_TYPES, CROP_NAMES
    from .utils import save_photo
    
    bed_doc = mongo.db.beds.find_one({'_id': ObjectId(bed_id)})
    if not bed_doc:
        flash('Bed not found.', 'error')
        return redirect(url_for('admin_bp.admin_view_beds'))
    
    # Get the garden for this bed
    garden = mongo.db.gardens.find_one({'_id': bed_doc['garden_id']})
    if not garden:
        flash('Garden not found for this bed.', 'error')
        return redirect(url_for('admin_bp.admin_view_beds'))
    
    if request.method == 'POST':
        data = request.form
        
        # Parse planting date
        planting_date = None
        if data.get('planting_date'):
            try:
                planting_date = datetime.strptime(data['planting_date'], '%Y-%m-%d')
            except ValueError:
                flash('Invalid planting date format.', 'error')
                return render_template('bed_form.html', 
                                       form_data=data, 
                                       bed_id=bed_id, 
                                       garden_id=str(garden['_id']),
                                       garden=garden,
                                       is_edit=True, 
                                       is_admin=True, 
                                       bed_types=BED_TYPES,
                                       crop_names=CROP_NAMES)
        
        update_data = {
            'name': data.get('name', bed_doc.get('name')),
            'crop_name': data.get('crop_name', bed_doc.get('crop_name', '')),
            'planting_date': planting_date or bed_doc.get('planting_date'),
            'count_row': int(data.get('count_row', bed_doc.get('count_row', 1))),
            'length': float(data.get('length', bed_doc.get('length', 0.0))),
            'width': float(data.get('width', bed_doc.get('width', 0.0))),
            'bed_type': data.get('bed_type', bed_doc.get('bed_type', '')),
            'is_hothouse': data.get('is_hothouse') == 'on',
            'notes': data.get('notes', bed_doc.get('notes', '')),
            'last_modified_time': datetime.utcnow()
        }

        if 'photo' in request.files:
            photo_file = request.files['photo']
            if photo_file.filename != '':
                saved_photo_path = save_photo(photo_file)
                if saved_photo_path:
                    if 'photo_file_paths' not in update_data:
                        update_data['photo_file_paths'] = bed_doc.get('photo_file_paths', [])
                    update_data['photo_file_paths'].append(saved_photo_path)

        mongo.db.beds.update_one({'_id': ObjectId(bed_id)}, {'$set': update_data})
        flash('Bed updated successfully!', 'success')
        return redirect(url_for('admin_bp.admin_view_beds'))
    
    return render_template('bed_form.html', 
                           form_data=bed_doc, 
                           bed_id=bed_id, 
                           garden_id=str(garden['_id']),
                           garden=garden,
                           is_edit=True, 
                           is_admin=True, 
                           bed_types=BED_TYPES,
                           crop_names=CROP_NAMES)

@admin_bp.route('/admin/beds/<bed_id>/delete', methods=['POST'])
@login_required
@admin_required  
def admin_delete_bed(bed_id):
    """Admin can delete any bed"""
    import os
    from flask import current_app
    
    bed = mongo.db.beds.find_one({'_id': ObjectId(bed_id)})
    if not bed:
        flash('Bed not found.', 'error')
        return redirect(url_for('admin_bp.admin_view_beds'))

    # Delete related care logs and recommendations
    mongo.db.care_logs.delete_many({'bed_id': ObjectId(bed_id)})
    mongo.db.recommendations.delete_many({'bed_id': ObjectId(bed_id)})
    
    # Delete bed photos
    if bed.get('photo_file_paths'):
        for photo_path in bed['photo_file_paths']:
            if photo_path:
                photo_disk_path = os.path.join(current_app.static_folder, photo_path)
                if os.path.exists(photo_disk_path):
                    try:
                        os.remove(photo_disk_path)
                    except Exception as e:
                        flash(f'Could not delete bed photo: {e}', 'warning')
    
    # Update garden stats
    garden_id = bed.get('garden_id')
    if garden_id:
        remaining_beds = mongo.db.beds.count_documents({'garden_id': garden_id})
        mongo.db.gardens.update_one(
            {'_id': ObjectId(garden_id)},
            {'$set': {'stats.total_beds': remaining_beds, 'stats.active_beds': remaining_beds}}
        )
    
    # Delete the bed
    mongo.db.beds.delete_one({'_id': ObjectId(bed_id)})
    
    flash('Bed deleted successfully!', 'success')
    return redirect(url_for('admin_bp.admin_view_beds'))

@admin_bp.route('/admin/care-logs/<care_log_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_care_log(care_log_id):
    """Admin can edit any care log"""
    from .choices import CARE_ACTION_TYPES
    from datetime import datetime
    
    care_log_doc = mongo.db.care_logs.find_one({'_id': ObjectId(care_log_id)})
    if not care_log_doc:
        flash('Care log not found.', 'error')
        return redirect(url_for('admin_bp.admin_view_care_logs'))
    
    # Get all gardens and beds for admin view
    user_gardens = list(mongo.db.gardens.find({}).sort('name', 1))
    initial_beds = []
    
    if request.method == 'POST':
        data = request.form
        
        # Parse date and time
        log_date_str = data.get('log_date')
        log_time_str = data.get('log_time')
        
        log_datetime = None
        if log_date_str and log_time_str:
            try:
                log_datetime = datetime.strptime(f"{log_date_str} {log_time_str}", '%Y-%m-%d %H:%M')
            except ValueError:
                flash('Invalid date or time format.', 'error')
                care_log_doc.update(data)
                return render_template('care_log_form.html', 
                                       form_data=care_log_doc, 
                                       user_gardens=user_gardens, 
                                       initial_beds=initial_beds,
                                       CARE_ACTION_TYPES=CARE_ACTION_TYPES, 
                                       is_edit=True, 
                                       is_admin=True,
                                       care_log_id=care_log_id,
                                       today_date=datetime.utcnow().strftime('%Y-%m-%d'),
                                       current_time=datetime.utcnow().strftime('%H:%M'))
        
        update_data = {
            'garden_id': ObjectId(data.get('garden_id')) if data.get('garden_id') else care_log_doc.get('garden_id'),
            'bed_id': ObjectId(data.get('bed_id')) if data.get('bed_id') else care_log_doc.get('bed_id'),
            'action_type': data.get('action_type', care_log_doc.get('action_type')),
            'log_date': log_datetime or care_log_doc.get('log_date'),
            'notes': data.get('notes', care_log_doc.get('notes', '')),
            'updated_at': datetime.utcnow()
        }

        mongo.db.care_logs.update_one({'_id': ObjectId(care_log_id)}, {'$set': update_data})
        flash('Care log updated successfully!', 'success')
        return redirect(url_for('admin_bp.admin_view_care_logs'))
    
    # Format dates for the form
    if care_log_doc.get('log_date'):
        care_log_doc['log_date_str'] = care_log_doc['log_date'].strftime('%Y-%m-%d')
        care_log_doc['log_time_str'] = care_log_doc['log_date'].strftime('%H:%M')
    
    # Get beds for the current garden if available
    if care_log_doc.get('garden_id'):
        beds_cursor = mongo.db.beds.find({'garden_id': care_log_doc['garden_id']}).sort('name', 1)
        initial_beds = [{'id': str(bed['_id']), 'name': bed['name']} for bed in beds_cursor]
    
    return render_template('care_log_form.html', 
                           form_data=care_log_doc, 
                           user_gardens=user_gardens, 
                           initial_beds=initial_beds,
                           CARE_ACTION_TYPES=CARE_ACTION_TYPES, 
                           is_edit=True, 
                           is_admin=True,
                           care_log_id=care_log_id,
                           today_date=datetime.utcnow().strftime('%Y-%m-%d'),
                           current_time=datetime.utcnow().strftime('%H:%M'))

@admin_bp.route('/admin/care-logs/<care_log_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_care_log(care_log_id):
    """Admin can delete any care log"""
    care_log = mongo.db.care_logs.find_one({'_id': ObjectId(care_log_id)})
    if not care_log:
        flash('Care log not found.', 'error')
        return redirect(url_for('admin_bp.admin_view_care_logs'))

    # Update bed stats
    bed_id = care_log.get('bed_id')
    if bed_id:
        remaining_logs = mongo.db.care_logs.count_documents({'bed_id': bed_id})
        last_care_log = mongo.db.care_logs.find_one(
            {'bed_id': bed_id}, sort=[('log_date', -1)]
        )
        
        update_data = {'stats.total_care_actions': remaining_logs - 1}
        if last_care_log:
            update_data['stats.last_care_date'] = last_care_log.get('log_date')
        else:
            update_data['stats.last_care_date'] = None
            
        mongo.db.beds.update_one({'_id': ObjectId(bed_id)}, {'$set': update_data})
    
    # Delete the care log
    mongo.db.care_logs.delete_one({'_id': ObjectId(care_log_id)})
    
    flash('Care log deleted successfully!', 'success')
    return redirect(url_for('admin_bp.admin_view_care_logs'))

@admin_bp.route('/admin/users/<user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_user(user_id):
    """Admin can edit user details (except password)"""
    user_doc = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if not user_doc:
        flash('User not found.', 'error')
        return redirect(url_for('admin_bp.admin_view_users'))
    
    if request.method == 'POST':
        data = request.form
        
        # Check if email is already taken by another user
        existing_user = mongo.db.users.find_one({
            'email': data.get('email'),
            '_id': {'$ne': ObjectId(user_id)}
        })
        if existing_user:
            flash('Email already exists for another user.', 'error')
            return render_template('admin/admin_edit_user.html', form_data=data, user_id=user_id, is_edit=True)
        
        update_data = {
            'name': data.get('name', user_doc.get('name')),
            'email': data.get('email', user_doc.get('email')),
            'email_verified': data.get('email_verified') == 'on',
            'is_admin': data.get('is_admin') == 'on',
            'updated_at': datetime.utcnow()
        }
        
        # Update roles based on admin status
        if update_data['is_admin']:
            update_data['roles'] = ['admin']
        else:
            update_data['roles'] = ['user']

        mongo.db.users.update_one({'_id': ObjectId(user_id)}, {'$set': update_data})
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin_bp.admin_view_users'))
    
    return render_template('admin/admin_edit_user.html', form_data=user_doc, user_id=user_id, is_edit=True)

@admin_bp.route('/admin/users/<user_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    """Admin can delete any user (except themselves)"""
    import os
    from flask import current_app
    
    # Prevent admin from deleting themselves
    if user_id == current_user.get_id():
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin_bp.admin_view_users'))
    
    user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin_bp.admin_view_users'))

    # Delete all user data in correct order
    
    # 1. Delete care logs
    mongo.db.care_logs.delete_many({'user_id': user_id})
    
    # 2. Delete recommendations  
    mongo.db.recommendations.delete_many({'user_id': user_id})
    
    # 3. Delete diary entries
    mongo.db.diary.delete_many({'user_id': user_id})
    
    # 4. Delete beds and their photos
    beds = list(mongo.db.beds.find({'user_id': user_id}))
    for bed in beds:
        if bed.get('photo_file_paths'):
            for photo_path in bed['photo_file_paths']:
                if photo_path:
                    photo_disk_path = os.path.join(current_app.static_folder, photo_path)
                    if os.path.exists(photo_disk_path):
                        try:
                            os.remove(photo_disk_path)
                        except Exception as e:
                            pass  # Continue deletion even if photo removal fails
    mongo.db.beds.delete_many({'user_id': user_id})
    
    # 5. Delete gardens and their photos
    gardens = list(mongo.db.gardens.find({'user_id': user_id}))
    for garden in gardens:
        if garden.get('photo_file_paths'):
            for photo_path in garden['photo_file_paths']:
                if photo_path:
                    photo_disk_path = os.path.join(current_app.static_folder, photo_path)
                    if os.path.exists(photo_disk_path):
                        try:
                            os.remove(photo_disk_path)
                        except Exception as e:
                            pass  # Continue deletion even if photo removal fails
    mongo.db.gardens.delete_many({'user_id': user_id})
    
    # 6. Delete user profile photo
    if user.get('photo_path'):
        photo_disk_path = os.path.join(current_app.static_folder, user['photo_path'])
        if os.path.exists(photo_disk_path):
            try:
                os.remove(photo_disk_path)
            except Exception as e:
                pass  # Continue deletion even if photo removal fails
    
    # 7. Finally delete the user
    mongo.db.users.delete_one({'_id': ObjectId(user_id)})
    
    flash(f'User "{user.get("name", "Unknown")}" and all associated data deleted successfully!', 'success')
    return redirect(url_for('admin_bp.admin_view_users'))

@admin_bp.route('/admin/recommendations/<recommendation_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_recommendation(recommendation_id):
    """Admin can edit any recommendation"""
    from .choices import RECOMMENDATION_ACTION_TYPES
    from datetime import datetime
    
    recommendation_doc = mongo.db.recommendations.find_one({'_id': ObjectId(recommendation_id)})
    if not recommendation_doc:
        flash('Recommendation not found.', 'error')
        return redirect(url_for('admin_bp.admin_view_recommendations'))
    
    # Get all gardens and beds for admin view
    user_gardens = list(mongo.db.gardens.find({}).sort('name', 1))
    initial_beds = []
    
    if request.method == 'POST':
        data = request.form
        
        # Parse due date and time
        due_date_str = data.get('due_date')
        due_time_str = data.get('due_time')
        
        due_datetime = None
        if due_date_str and due_time_str:
            try:
                due_datetime = datetime.strptime(f"{due_date_str} {due_time_str}", '%Y-%m-%d %H:%M')
            except ValueError:
                flash('Invalid due date or time format.', 'error')
                recommendation_doc.update(data)
                return render_template('recommendation_form.html', 
                                       form_data=recommendation_doc, 
                                       user_gardens=user_gardens, 
                                       initial_beds=initial_beds,
                                       RECOMMENDATION_ACTION_TYPES=RECOMMENDATION_ACTION_TYPES, 
                                       is_edit=True, 
                                       is_admin=True,
                                       recommendation_id=recommendation_id,
                                       today_date=datetime.utcnow().strftime('%Y-%m-%d'),
                                       current_time=datetime.utcnow().strftime('%H:%M'))
        elif due_date_str:
            try:
                due_datetime = datetime.strptime(due_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid due date format.', 'error')
                recommendation_doc.update(data)
                return render_template('recommendation_form.html', 
                                       form_data=recommendation_doc, 
                                       user_gardens=user_gardens, 
                                       initial_beds=initial_beds,
                                       RECOMMENDATION_ACTION_TYPES=RECOMMENDATION_ACTION_TYPES, 
                                       is_edit=True, 
                                       is_admin=True,
                                       recommendation_id=recommendation_id,
                                       today_date=datetime.utcnow().strftime('%Y-%m-%d'),
                                       current_time=datetime.utcnow().strftime('%H:%M'))
        
        update_data = {
            'garden_id': ObjectId(data.get('garden_id')) if data.get('garden_id') else recommendation_doc.get('garden_id'),
            'bed_id': ObjectId(data.get('bed_id')) if data.get('bed_id') else recommendation_doc.get('bed_id'),
            'action_type': data.get('action_type', recommendation_doc.get('action_type')),
            'description': data.get('description', recommendation_doc.get('description', '')),
            'due_date': due_datetime or recommendation_doc.get('due_date'),
            'updated_at': datetime.utcnow()
        }
        
        # Handle completion status
        if data.get('is_completed') == 'on':
            update_data['is_completed'] = True
            update_data['completed_at'] = datetime.utcnow()
        else:
            update_data['is_completed'] = False
            update_data['completed_at'] = None

        mongo.db.recommendations.update_one({'_id': ObjectId(recommendation_id)}, {'$set': update_data})
        flash('Recommendation updated successfully!', 'success')
        return redirect(url_for('admin_bp.admin_view_recommendations'))
    
    # Format dates for the form
    if recommendation_doc.get('due_date'):
        recommendation_doc['due_date'] = recommendation_doc['due_date'].strftime('%Y-%m-%d')
        recommendation_doc['due_time'] = recommendation_doc['due_date'].strftime('%H:%M') if isinstance(recommendation_doc.get('due_date'), datetime) else '09:00'
    
    # Get beds for the current garden if available
    if recommendation_doc.get('garden_id'):
        beds_cursor = mongo.db.beds.find({'garden_id': recommendation_doc['garden_id']}).sort('name', 1)
        initial_beds = [{'id': str(bed['_id']), 'name': bed['name']} for bed in beds_cursor]
    
    return render_template('recommendation_form.html', 
                           form_data=recommendation_doc, 
                           user_gardens=user_gardens, 
                           initial_beds=initial_beds,
                           RECOMMENDATION_ACTION_TYPES=RECOMMENDATION_ACTION_TYPES, 
                           is_edit=True, 
                           is_admin=True,
                           recommendation_id=recommendation_id,
                           today_date=datetime.utcnow().strftime('%Y-%m-%d'),
                           current_time=datetime.utcnow().strftime('%H:%M'))

@admin_bp.route('/admin/recommendations/<recommendation_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_recommendation(recommendation_id):
    """Admin can delete any recommendation"""
    recommendation = mongo.db.recommendations.find_one({'_id': ObjectId(recommendation_id)})
    if not recommendation:
        flash('Recommendation not found.', 'error')
        return redirect(url_for('admin_bp.admin_view_recommendations'))

    # Update bed stats if recommendation is linked to a bed
    bed_id = recommendation.get('bed_id')
    if bed_id:
        remaining_recommendations = mongo.db.recommendations.count_documents({'bed_id': bed_id}) - 1
        pending_recommendations = mongo.db.recommendations.count_documents({
            'bed_id': bed_id, 'is_completed': False
        })
        
        mongo.db.beds.update_one(
            {'_id': ObjectId(bed_id)},
            {'$set': {
                'stats.pending_recommendations': max(0, pending_recommendations - 1) if not recommendation.get('is_completed') else pending_recommendations,
                'stats.completed_recommendations': mongo.db.recommendations.count_documents({
                    'bed_id': bed_id, 'is_completed': True
                }) - (1 if recommendation.get('is_completed') else 0)
            }}
        )
    
    # Delete the recommendation
    mongo.db.recommendations.delete_one({'_id': ObjectId(recommendation_id)})
    
    flash('Recommendation deleted successfully!', 'success')
    return redirect(url_for('admin_bp.admin_view_recommendations'))

@admin_bp.route('/admin/diary_entries/<entry_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_diary_entry(entry_id):
    """Admin can edit any diary entry"""
    entry_doc = mongo.db.diary.find_one({'_id': ObjectId(entry_id)})
    if not entry_doc:
        flash('Diary entry not found.', 'error')
        return redirect(url_for('admin_bp.admin_view_diary'))
    
    if request.method == 'POST':
        data = request.form
        
        update_data = {
            'title': data.get('title', entry_doc.get('title')),
            'content': data.get('content', entry_doc.get('content', '')),
            'last_modified_time': datetime.utcnow()
        }

        mongo.db.diary.update_one({'_id': ObjectId(entry_id)}, {'$set': update_data})
        flash('Diary entry updated successfully!', 'success')
        return redirect(url_for('admin_bp.admin_view_diary'))
    
    return render_template('entry_form.html', form_data=entry_doc, entry_id=entry_id, is_edit=True, is_admin=True)

@admin_bp.route('/admin/diary_entries/<entry_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_diary_entry(entry_id):
    """Admin can delete any diary entry"""
    entry = mongo.db.diary.find_one({'_id': ObjectId(entry_id)})
    if not entry:
        flash('Diary entry not found.', 'error')
        return redirect(url_for('admin_bp.admin_view_diary'))

    # Delete the diary entry
    mongo.db.diary.delete_one({'_id': ObjectId(entry_id)})
    
    flash('Diary entry deleted successfully!', 'success')
    return redirect(url_for('admin_bp.admin_view_diary'))
