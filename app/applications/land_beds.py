from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import current_user, login_required
from datetime import datetime
from bson import ObjectId
import os

from applications import mongo
from .utils import save_photo

bed_bp = Blueprint(
    "bed_bp", __name__, 
    template_folder="../../templates", 
    static_folder="../../static",
    url_prefix='/gardens/<garden_id>/beds'
)

BED_TYPES = ["", "Поднятая грядка", "Контейнер", "Высокая грядка (глубокая)", "Традиционная (в грунте)", "Вертикальная", "Гидропоника", "Другое"]

@bed_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_bed(garden_id):
    parent_garden = mongo.db.gardens.find_one({'_id': ObjectId(garden_id), 'user_id': current_user.get_id()})
    if not parent_garden:
        flash('Garden not found or access denied.', 'error')
        return redirect(url_for('land_bp.gardens')) # Redirect to main garden list

    if request.method == 'POST':
        data = request.form
        
        if not data.get('name'):
            flash('Bed name is required.', 'error')
            return render_template('bed_form.html', garden=parent_garden, garden_id=garden_id, form_data=data, bed_types=BED_TYPES, is_edit=False)

        photo_paths = []
        if 'photo' in request.files:
            photo_file = request.files['photo']
            if photo_file.filename != '':
                saved_photo_path = save_photo(photo_file)
                if saved_photo_path:
                    photo_paths.append(saved_photo_path)
                else:
                    return render_template('bed_form.html', garden=parent_garden, garden_id=garden_id, form_data=data, bed_types=BED_TYPES, is_edit=False)
        
        try:
            planting_date_val = datetime.strptime(data['planting_date'], '%Y-%m-%d') if data.get('planting_date') else None
        except ValueError:
            flash('Invalid planting date format. Please use YYYY-MM-DD.', 'error')
            return render_template('bed_form.html', garden=parent_garden, garden_id=garden_id, form_data=data, bed_types=BED_TYPES, is_edit=False)


        bed_doc = {
            'garden_id': ObjectId(garden_id),
            'user_id': current_user.get_id(),
            'name': data['name'],
            'crop_name': data.get('crop_name', ''),
            'planting_date': planting_date_val,
            'creation_time': datetime.utcnow(),
            'last_modified_time': datetime.utcnow(),
            'photo_file_paths': photo_paths,
            'recommendations': [],
            'care_actions': [],
            'count_row': int(data.get('count_row', 0)) if data.get('count_row') else 0,
            'length': float(data.get('length', 0.0)) if data.get('length') else 0.0,
            'width': float(data.get('width', 0.0)) if data.get('width') else 0.0,
            'bed_type': data.get('bed_type', ''),
            'is_hothouse': data.get('is_hothouse') == 'on', # HTML checkbox sends 'on' if checked
            'notes': data.get('notes', ''),
            'stats': {
                'total_care_actions': 0,
                'last_care_date': None,
                'pending_recommendations': 0,
                'completed_recommendations': 0
            }
        }
        
        if bed_doc['bed_type'] not in BED_TYPES:
            flash('Invalid bed type selected.', 'error')
            return render_template('bed_form.html', garden=parent_garden, garden_id=garden_id, form_data=data, bed_types=BED_TYPES, is_edit=False)

        mongo.db.beds.insert_one(bed_doc)

        mongo.db.gardens.update_one(
            {'_id': ObjectId(garden_id)},
            {
                '$inc': {'stats.total_beds': 1, 'stats.active_beds': 1},
                '$set': {'last_modified_time': datetime.utcnow()}
            }
        )
        flash('Bed created successfully!', 'success')
        return redirect(url_for('land_bp.garden_detail', garden_id=garden_id))

    return render_template('bed_form.html', garden=parent_garden, garden_id=garden_id, form_data={}, bed_types=BED_TYPES, is_edit=False)

@bed_bp.route('/<bed_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_bed(garden_id, bed_id):
    parent_garden = mongo.db.gardens.find_one({'_id': ObjectId(garden_id), 'user_id': current_user.get_id()})
    if not parent_garden:
        flash('Parent garden not found or access denied.', 'error')
        return redirect(url_for('land_bp.gardens'))

    bed_doc = mongo.db.beds.find_one({'_id': ObjectId(bed_id), 'garden_id': ObjectId(garden_id), 'user_id': current_user.get_id()})
    if not bed_doc:
        flash('Bed not found or access denied.', 'error')
        return redirect(url_for('land_bp.garden_detail', garden_id=garden_id))

    if request.method == 'POST':
        data = request.form
        update_fields = {
            'name': data.get('name', bed_doc.get('name')),
            'crop_name': data.get('crop_name', bed_doc.get('crop_name', '')),
            'last_modified_time': datetime.utcnow(),
            'count_row': int(data.get('count_row', bed_doc.get('count_row',0))) if data.get('count_row') else bed_doc.get('count_row',0),
            'length': float(data.get('length', bed_doc.get('length',0.0))) if data.get('length') else bed_doc.get('length',0.0),
            'width': float(data.get('width', bed_doc.get('width',0.0))) if data.get('width') else bed_doc.get('width',0.0),
            'bed_type': data.get('bed_type', bed_doc.get('bed_type','')),
            'is_hothouse': data.get('is_hothouse') == 'on',
            'notes': data.get('notes', bed_doc.get('notes', '')),
        }
        
        try:
            update_fields['planting_date'] = datetime.strptime(data['planting_date'], '%Y-%m-%d') if data.get('planting_date') else bed_doc.get('planting_date')
        except ValueError:
            flash('Invalid planting date format. Please use YYYY-MM-DD.', 'error')
            return render_template('bed_form.html', form_data=data, garden_id=garden_id, bed_id=bed_id, bed_types=BED_TYPES, is_edit=True, garden=parent_garden)

        if update_fields['bed_type'] not in BED_TYPES:
            flash('Invalid bed type selected.', 'error')
            return render_template('bed_form.html', form_data=data, garden_id=garden_id, bed_id=bed_id, bed_types=BED_TYPES, is_edit=True, garden=parent_garden)

        if 'photo' in request.files:
            photo_file = request.files['photo']
            if photo_file.filename != '':
                saved_photo_path = save_photo(photo_file)
                if saved_photo_path:
                    current_photo_paths = bed_doc.get('photo_file_paths', [])
                    if current_photo_paths and current_photo_paths[0]:
                        old_photo_disk_path = os.path.join(current_app.static_folder, current_photo_paths[0])
                        if os.path.exists(old_photo_disk_path):
                            try:
                                os.remove(old_photo_disk_path)
                            except Exception as e:
                                flash(f'Could not delete old photo: {e}', 'warning')
                    update_fields['photo_file_paths'] = [saved_photo_path] # Replace/set the first photo
                else:
                    return render_template('bed_form.html', form_data=bed_doc, garden_id=garden_id, bed_id=bed_id, bed_types=BED_TYPES, is_edit=True, garden=parent_garden)
        
        mongo.db.beds.update_one({'_id': ObjectId(bed_id)}, {'$set': update_fields})
        flash('Bed updated successfully!', 'success')
        return redirect(url_for('land_bp.garden_detail', garden_id=garden_id))

    # For GET request, prefill form_data
    return render_template('bed_form.html', form_data=bed_doc, garden_id=garden_id, bed_id=bed_id, bed_types=BED_TYPES, is_edit=True, garden=parent_garden)

@bed_bp.route('/<bed_id>/delete', methods=['POST'])
@login_required
def delete_bed(garden_id, bed_id):
    parent_garden = mongo.db.gardens.find_one({'_id': ObjectId(garden_id), 'user_id': current_user.get_id()})
    if not parent_garden:
        flash('Parent garden not found or access denied.', 'error')
        return redirect(url_for('land_bp.gardens'))

    bed = mongo.db.beds.find_one({'_id': ObjectId(bed_id), 'garden_id': ObjectId(garden_id), 'user_id': current_user.get_id()})
    if bed:
        if bed.get('photo_file_paths'):
            for photo_path_from_db in bed['photo_file_paths']:
                if photo_path_from_db:
                    actual_photo_disk_path = os.path.join(current_app.static_folder, photo_path_from_db)
                    if os.path.exists(actual_photo_disk_path):
                        try:
                            os.remove(actual_photo_disk_path)
                        except Exception as e:
                             flash(f'Could not delete bed photo {photo_path_from_db}: {e}', 'warning')
        
        mongo.db.beds.delete_one({'_id': ObjectId(bed_id)})
        
        # Update garden stats
        mongo.db.gardens.update_one(
            {'_id': ObjectId(garden_id)},
            {'$inc': {'stats.total_beds': -1, 'stats.active_beds': -1}}
        )
        flash('Bed deleted successfully!', 'success')
    else:
        flash('Bed not found or access denied.', 'error')
    
    return redirect(url_for('land_bp.garden_detail', garden_id=garden_id)) 