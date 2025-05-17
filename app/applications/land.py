from flask import Blueprint, render_template, redirect, url_for, request, flash, send_from_directory, current_app
from flask_login import current_user, login_required
from datetime import datetime
from applications import mongo
from .utils import allowed_file, save_photo

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
    name_query = request.args.get('name_query', '')
    location_query = request.args.get('location_query', '')

    soil_type_query = request.args.get('soil_type_query', '')
    terrain_type_query = request.args.get('terrain_type_query', '')
    lighting_query = request.args.get('lighting_query', '')

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

    sort_by = request.args.get('sort_by', 'registration_time')
    sort_order_str = request.args.get('sort_order', 'desc')
    sort_order = -1 if sort_order_str == 'desc' else 1
    
    valid_sort_fields = [
        'name', 'registration_time', 'last_modified_time', 
        'area', 'soil_type', 'terrain_type', 'lighting'
    ]
    if sort_by not in valid_sort_fields:
        sort_by = 'registration_time'

    user_gardens_cursor = mongo.db.gardens.find(filters)\
                                .sort(sort_by, sort_order)\
                                .skip((page - 1) * per_page)\
                                .limit(per_page)
    user_gardens = list(user_gardens_cursor)
    
    total_gardens = mongo.db.gardens.count_documents(filters)
    total_pages = (total_gardens + per_page - 1) // per_page if per_page > 0 else 0

    return render_template('land.html',
                           gardens=user_gardens,
                           current_page=page,
                           total_pages=total_pages,
                           name_query=name_query,
                           location_query=location_query,
                           soil_type_query=soil_type_query,
                           terrain_type_query=terrain_type_query,
                           lighting_query=lighting_query,
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
                                           soil_types=SOIL_TYPES, terrain_types=TERRAIN_TYPES, lighting_options=LIGHTING_OPTIONS)
        
        if not data.get('name'):
            flash('Garden name is required.', 'error')
            return render_template('land_form.html', form_data=data,
                                   soil_types=SOIL_TYPES, terrain_types=TERRAIN_TYPES, lighting_options=LIGHTING_OPTIONS)
        
        if data.get('soil_type') not in SOIL_TYPES:
            flash('Invalid soil type selected.', 'error')
            return render_template('land_form.html', form_data=data, soil_types=SOIL_TYPES, terrain_types=TERRAIN_TYPES, lighting_options=LIGHTING_OPTIONS)
        if data.get('terrain_type') not in TERRAIN_TYPES:
            flash('Invalid terrain type selected.', 'error')
            return render_template('land_form.html', form_data=data, soil_types=SOIL_TYPES, terrain_types=TERRAIN_TYPES, lighting_options=LIGHTING_OPTIONS)
        if data.get('lighting') not in LIGHTING_OPTIONS:
            flash('Invalid lighting option selected.', 'error')
            return render_template('land_form.html', form_data=data, soil_types=SOIL_TYPES, terrain_types=TERRAIN_TYPES, lighting_options=LIGHTING_OPTIONS)

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
                                   soil_types=SOIL_TYPES, terrain_types=TERRAIN_TYPES, lighting_options=LIGHTING_OPTIONS)
    
    return render_template('land_form.html', form_data={},
                           soil_types=SOIL_TYPES, terrain_types=TERRAIN_TYPES, lighting_options=LIGHTING_OPTIONS)

@land_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(os.path.join(current_app.static_folder, 'uploads'), filename.split('/')[-1])

