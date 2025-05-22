from flask import Blueprint, render_template, redirect, url_for, request, flash, send_from_directory, current_app
from flask_login import current_user, login_required
from datetime import datetime
from applications import mongo
from .utils import allowed_file, save_photo
from bson import ObjectId
import os

land_bp = Blueprint(
    "land_bp", __name__, template_folder="../../templates", static_folder="../../static"
)

SOIL_TYPES = ["", "Песчаная", "Суглинистая", "Глинистая", "Торфяная", "Чернозем", "Известняковая"]
TERRAIN_TYPES = ["", "Равнина", "Склон (южный)", "Склон (северный)", "Склон (восточный)", "Склон (западный)", "Холмистая", "Низина", "Террасированный"]
LIGHTING_OPTIONS = ["", "Солнечное (весь день)", "Утреннее солнце, дневная тень", "Дневное солнце, вечерняя тень", "Полутень (рассеянный свет)", "Тень"]

@land_bp.route('/gardens')
@login_required
def gardens():
    page = request.args.get('page', 1, type=int)
    per_page = 6

    filters = {'user_id': current_user.get_id()}
    total_all = mongo.db.gardens.count_documents({'user_id': current_user.get_id()})
    name_query = request.args.get('name_query', '')
    location_query = request.args.get('location_query', '')

    soil_type_query = request.args.get('soil_type_query', '')
    terrain_type_query = request.args.get('terrain_type_query', '')
    lighting_query = request.args.get('lighting_query', '')
    
    # Обработка фильтров по датам
    registration_date = request.args.get('registration_date', '')
    last_modified_date = request.args.get('last_modified_date', '')

    if name_query:
        filters['name'] = {'$regex': name_query, '$options': 'i'}
    if location_query:
        filters['location'] = {'$regex': location_query, '$options': 'i'}
    
    if soil_type_query and soil_type_query in SOIL_TYPES:
        filters['soil_type'] = soil_type_query
    if terrain_type_query and terrain_type_query in TERRAIN_TYPES:
        filters['terrain_type'] = terrain_type_query
    if lighting_query and lighting_query in LIGHTING_OPTIONS:
        filters['lighting'] = lighting_query

    # Фильтрация по дате регистрации
    if registration_date:
        try:
            date_obj = datetime.strptime(registration_date, '%Y-%m-%d')
            next_day = date_obj.replace(hour=23, minute=59, second=59)
            filters['registration_time'] = {
                '$gte': date_obj,
                '$lte': next_day
            }
        except ValueError:
            pass

    # Фильтрация по дате последнего изменения
    if last_modified_date:
        try:
            date_obj = datetime.strptime(last_modified_date, '%Y-%m-%d')
            next_day = date_obj.replace(hour=23, minute=59, second=59)
            filters['last_modified_time'] = {
                '$gte': date_obj,
                '$lte': next_day
            }
        except ValueError:
            pass

    sort_by = request.args.get('sort_by', 'registration_time')
    sort_order_str = request.args.get('sort_order', 'desc')
    sort_order = -1 if sort_order_str == 'desc' else 1
    
    valid_sort_fields = [
        'name', 'area', 'soil_type', 'terrain_type', 'lighting'
    ]
    if sort_by not in valid_sort_fields:
        sort_by = 'registration_time'  # По умолчанию сортируем по дате регистрации

    user_gardens_cursor = mongo.db.gardens.find(filters)\
                                .sort(sort_by, sort_order)\
                                .skip((page - 1) * per_page)\
                                .limit(per_page)
    user_gardens = list(user_gardens_cursor)
    
    total_gardens = mongo.db.gardens.count_documents(filters)
    total_pages = (total_gardens + per_page - 1) // per_page if per_page > 0 else 0

    return render_template('land.html',
                           gardens=user_gardens,
                           total_all=total_all,
                           current_page=page,
                           total_pages=total_pages,
                           name_query=name_query,
                           location_query=location_query,
                           soil_type_query=soil_type_query,
                           terrain_type_query=terrain_type_query,
                           lighting_query=lighting_query,
                           registration_date=registration_date,
                           last_modified_date=last_modified_date,
                           sort_by=sort_by,
                           sort_order_str=sort_order_str,
                           soil_types=SOIL_TYPES,
                           terrain_types=TERRAIN_TYPES,
                           lighting_options=LIGHTING_OPTIONS)

@land_bp.route('/gardens/new', methods=['GET', 'POST'])
@login_required
def new_garden():
    if request.method == 'POST':
        data = request.form
        photo_paths = []

        if 'photo' in request.files:
            photo_file = request.files['photo']
            if photo_file.filename != '':
                saved_photo_path = save_photo(photo_file)
                if saved_photo_path:
                    photo_paths.append(saved_photo_path)
                else:
                    return render_template('land_form.html', form_data=data, 
                                           soil_types=SOIL_TYPES, terrain_types=TERRAIN_TYPES, lighting_options=LIGHTING_OPTIONS, is_edit=False)
        
        if not data.get('name'):
            flash('Garden name is required.', 'error')
            return render_template('land_form.html', form_data=data,
                                   soil_types=SOIL_TYPES, terrain_types=TERRAIN_TYPES, lighting_options=LIGHTING_OPTIONS, is_edit=False)
        
        if data.get('soil_type') not in SOIL_TYPES:
            flash('Invalid soil type selected.', 'error')
            return render_template('land_form.html', form_data=data, soil_types=SOIL_TYPES, terrain_types=TERRAIN_TYPES, lighting_options=LIGHTING_OPTIONS, is_edit=False)
        if data.get('terrain_type') not in TERRAIN_TYPES:
            flash('Invalid terrain type selected.', 'error')
            return render_template('land_form.html', form_data=data, soil_types=SOIL_TYPES, terrain_types=TERRAIN_TYPES, lighting_options=LIGHTING_OPTIONS, is_edit=False)
        if data.get('lighting') not in LIGHTING_OPTIONS:
            flash('Invalid lighting option selected.', 'error')
            return render_template('land_form.html', form_data=data, soil_types=SOIL_TYPES, terrain_types=TERRAIN_TYPES, lighting_options=LIGHTING_OPTIONS, is_edit=False)

        new_garden_doc = {
            'user_id': current_user.get_id(),
            'name': data['name'],
            'location': data.get('location', ''),
            'area': float(data.get('area', 0.0)) if data.get('area') else 0.0,
            'soil_type': data.get('soil_type', ''),
            'terrain_type': data.get('terrain_type', ''),
            'lighting': data.get('lighting', ''),
            'registration_time': datetime.utcnow(),
            'last_modified_time': datetime.utcnow(),
            'photo_file_paths': photo_paths,
            'stats': {
                'total_beds': 0,
                'active_beds': 0,
                'total_crops': 0
            }
        }

        try:
            mongo.db.gardens.insert_one(new_garden_doc)
            flash('Garden created successfully!', 'success')
            return redirect(url_for('land_bp.gardens'))
        except Exception as e:
            flash(f'Error creating garden: {e}', 'error')
            return render_template('land_form.html', form_data=data,
                                   soil_types=SOIL_TYPES, terrain_types=TERRAIN_TYPES, lighting_options=LIGHTING_OPTIONS, is_edit=False)
    
    return render_template('land_form.html', form_data={},
                           soil_types=SOIL_TYPES, terrain_types=TERRAIN_TYPES, lighting_options=LIGHTING_OPTIONS, is_edit=False)

@land_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.static_folder, filename)

@land_bp.route('/gardens/<garden_id>', methods=['GET'])
def garden_detail(garden_id):
    try:
        garden_object_id = ObjectId(garden_id)
    except Exception:
        flash('Некорректный формат ID участка', 'error')
        return redirect(url_for('land_bp.gardens'))
    
    garden = mongo.db.gardens.find_one({'_id': garden_object_id, 'user_id': current_user.get_id()})
    
    if not garden:
        flash('Участок не найден или у вас нет доступа к нему', 'error')
        return redirect(url_for('land_bp.gardens'))
    
    # Pagination for beds
    bed_page = request.args.get('bed_page', 1, type=int)
    bed_per_page = 6
    
    # Filtering and sorting beds
    bed_name_query = request.args.get('bed_name_query', '')
    bed_crop_query = request.args.get('bed_crop_query', '')
    bed_sort_by = request.args.get('bed_sort_by', 'creation_time')
    bed_sort_order_str = request.args.get('bed_sort_order', 'desc')
    bed_sort_order = -1 if bed_sort_order_str == 'desc' else 1
    
    bed_filters = {'garden_id': garden_object_id, 'user_id': current_user.get_id()}
    
    if bed_name_query:
        bed_filters['name'] = {'$regex': bed_name_query, '$options': 'i'}
    if bed_crop_query:
        bed_filters['crop_name'] = {'$regex': bed_crop_query, '$options': 'i'}
    
    
    beds_cursor = mongo.db.beds.find(bed_filters).sort(bed_sort_by, bed_sort_order).skip((bed_page - 1) * bed_per_page).limit(bed_per_page)
    beds = list(beds_cursor)
    total_beds = mongo.db.beds.count_documents(bed_filters)
    total_bed_pages = (total_beds + bed_per_page - 1) // bed_per_page if total_beds > 0 else 1
    
    # Get garden care logs
    garden_care_logs_limit = 5  # Show only 5 most recent logs on the garden detail page
    garden_care_logs_cursor = mongo.db.care_logs.find(
        {'garden_id': garden_object_id, 'user_id': current_user.get_id()}
    ).sort('log_date', -1).limit(garden_care_logs_limit)
    
    # Convert cursor to list and enrich with bed names
    garden_care_logs = []
    for log in garden_care_logs_cursor:
        bed = mongo.db.beds.find_one({'_id': log['bed_id']})
        if bed:  # Only include logs where the bed still exists
            log['bed_name'] = bed['name']
            garden_care_logs.append(log)

    garden_care_logs_count = mongo.db.care_logs.count_documents({
        'garden_id': garden_object_id, 
        'user_id': current_user.get_id()
    })
    
    # Get garden recommendations instead of tasks
    garden_recommendations_limit = 5  # Show only 5 most recent recommendations
    garden_recommendations_cursor = mongo.db.recommendations.find(
        {'garden_id': garden_object_id, 'user_id': current_user.get_id(), 'is_completed': False}
    ).sort('due_date', 1).limit(garden_recommendations_limit)
    
    # Convert cursor to list and enrich with bed names
    garden_recommendations = []
    for rec in garden_recommendations_cursor:
        bed = mongo.db.beds.find_one({'_id': rec['bed_id']})
        if bed:  # Only include recommendations where the bed still exists
            rec['bed_name'] = bed['name']
            rec['is_overdue'] = rec['due_date'] < datetime.utcnow() if not rec['is_completed'] else False
            garden_recommendations.append(rec)

    garden_recommendations_count = mongo.db.recommendations.count_documents({
        'garden_id': garden_object_id, 
        'user_id': current_user.get_id(),
        'is_completed': False
    })
    
    return render_template('land_detail.html', 
                          garden=garden,
                          beds=beds,
                          current_bed_page=bed_page,
                          total_bed_pages=total_bed_pages,
                          bed_name_query=bed_name_query,
                          bed_crop_query=bed_crop_query,
                          bed_sort_by=bed_sort_by,
                          bed_sort_order_str=bed_sort_order_str,
                          garden_care_logs=garden_care_logs,
                          garden_care_logs_count=garden_care_logs_count,
                          garden_recommendations=garden_recommendations,
                          garden_recommendations_count=garden_recommendations_count,
                          datetime=datetime)

@land_bp.route('/gardens/<garden_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_garden(garden_id):
    garden_doc = mongo.db.gardens.find_one({'_id': ObjectId(garden_id), 'user_id': current_user.get_id()})
    if not garden_doc:
        flash('Garden not found or access denied.', 'error')
        return redirect(url_for('land_bp.gardens'))
    
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
            return render_template('land_form.html', form_data=data, garden_id=garden_id, is_edit=True, soil_types=SOIL_TYPES, terrain_types=TERRAIN_TYPES, lighting_options=LIGHTING_OPTIONS)
        if update_data['terrain_type'] not in TERRAIN_TYPES:
            flash('Invalid terrain type selected.', 'error')
            return render_template('land_form.html', form_data=data, garden_id=garden_id, is_edit=True, soil_types=SOIL_TYPES, terrain_types=TERRAIN_TYPES, lighting_options=LIGHTING_OPTIONS)
        if update_data['lighting'] not in LIGHTING_OPTIONS:
            flash('Invalid lighting option selected.', 'error')
            return render_template('land_form.html', form_data=data, garden_id=garden_id, is_edit=True, soil_types=SOIL_TYPES, terrain_types=TERRAIN_TYPES, lighting_options=LIGHTING_OPTIONS)
        
        if 'photo' in request.files:
            photo_file = request.files['photo']
            if photo_file.filename != '':
                saved_photo_path = save_photo(photo_file)
                if saved_photo_path:
                    current_photo_paths = garden_doc.get('photo_file_paths', [])
                    if current_photo_paths and current_photo_paths[0]:
                        old_photo_disk_path = os.path.join(current_app.static_folder, current_photo_paths[0])
                        if os.path.exists(old_photo_disk_path):
                            try:
                                os.remove(old_photo_disk_path)
                            except Exception as e:
                                flash(f'Could not delete old photo: {e}', 'warning')
                    update_data['photo_file_paths'] = [saved_photo_path]
                else:
                    return render_template('land_form.html', form_data=garden_doc, garden_id=garden_id, is_edit=True, soil_types=SOIL_TYPES, terrain_types=TERRAIN_TYPES, lighting_options=LIGHTING_OPTIONS)

        mongo.db.gardens.update_one(
            {'_id': ObjectId(garden_id)},
            {'$set': update_data}
        )
        flash('Garden updated successfully!', 'success')
        return redirect(url_for('land_bp.garden_detail', garden_id=garden_id))
    
    return render_template('land_form.html', form_data=garden_doc, garden_id=garden_id, is_edit=True, 
                           soil_types=SOIL_TYPES, terrain_types=TERRAIN_TYPES, lighting_options=LIGHTING_OPTIONS)

@land_bp.route('/gardens/<garden_id>/delete', methods=['POST'])
@login_required
def delete_garden(garden_id):
    garden = mongo.db.gardens.find_one({'_id': ObjectId(garden_id), 'user_id': current_user.get_id()})
    if not garden:
        flash('Участок не найден или у вас нет доступа.', 'error')
        return redirect(url_for('land_bp.gardens'))

    # Находим все грядки этого участка
    beds = list(mongo.db.beds.find({'garden_id': ObjectId(garden_id)}))
    
    # Удаляем все записи журнала ухода, связанные с этим участком
    mongo.db.care_logs.delete_many({'garden_id': ObjectId(garden_id)})
    mongo.db.recommendations.delete_many({'garden_id': ObjectId(garden_id)})
    
    # Удаляем все грядки этого участка
    for bed in beds:
        if bed.get('photo_file_paths'):
            for photo_path in bed['photo_file_paths']:
                if photo_path:
                    photo_disk_path = os.path.join(current_app.static_folder, photo_path)
                    if os.path.exists(photo_disk_path):
                        try:
                            os.remove(photo_disk_path)
                        except Exception as e:
                            flash(f'Не удалось удалить фото грядки: {e}', 'warning')
    
    # Удаляем все грядки участка
    mongo.db.beds.delete_many({'garden_id': ObjectId(garden_id)})
    
    # Удаляем фото самого участка
    if garden.get('photo_file_paths'):
        for photo_path in garden['photo_file_paths']:
            if photo_path:
                photo_disk_path = os.path.join(current_app.static_folder, photo_path)
                if os.path.exists(photo_disk_path):
                    try:
                        os.remove(photo_disk_path)
                    except Exception as e:
                        flash(f'Не удалось удалить фото участка: {e}', 'warning')
    
    # Удаляем сам участок
    mongo.db.gardens.delete_one({'_id': ObjectId(garden_id)})
    
    flash('Участок успешно удален!', 'success')
    return redirect(url_for('land_bp.gardens'))