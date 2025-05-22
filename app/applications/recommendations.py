from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from applications import mongo
from bson import ObjectId
from datetime import datetime
from .choices import RECOMMENDATION_ACTION_TYPES

recommendation_bp = Blueprint(
    "recommendation_bp", 
    __name__, 
    template_folder="../../templates", 
    static_folder="../../static"
)

@recommendation_bp.route('/recommendations', methods=['GET'])
@login_required
def list_recommendations():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    filters = {'user_id': current_user.get_id(), 'is_completed': False}
    
    # Filtering
    filter_garden_id = request.args.get('garden_id')
    filter_bed_id = request.args.get('bed_id')
    filter_action_type = request.args.get('action_type')
    filter_due_date_from_str = request.args.get('due_date_from')
    filter_due_date_to_str = request.args.get('due_date_to')

    user_gardens = list(mongo.db.gardens.find({'user_id': current_user.get_id()}, {'name': 1, '_id': 1}).sort('name', 1))
    user_beds = [] # For populating bed filter based on selected garden

    if filter_garden_id:
        filters['garden_id'] = ObjectId(filter_garden_id)
        user_beds = list(mongo.db.beds.find({'user_id': current_user.get_id(), 'garden_id': ObjectId(filter_garden_id)}, {'name': 1, '_id': 1}).sort('name', 1))
        if filter_bed_id:
            filters['bed_id'] = ObjectId(filter_bed_id)
    
    if filter_action_type:
        filters['action_type'] = filter_action_type
    
    due_date_filter_conditions = {}
    if filter_due_date_from_str:
        try:
            due_date_filter_conditions['$gte'] = datetime.strptime(filter_due_date_from_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid "due date from" format. Please use YYYY-MM-DD.', 'warning')
    if filter_due_date_to_str:
        try:
            due_date_filter_conditions['$lte'] = datetime.strptime(filter_due_date_to_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        except ValueError:
            flash('Invalid "due date to" format. Please use YYYY-MM-DD.', 'warning')
    
    if due_date_filter_conditions:
        filters['due_date'] = due_date_filter_conditions

    # Sorting
    sort_by = request.args.get('sort_by', 'due_date')
    sort_order_str = request.args.get('sort_order', 'asc') # Default to ascending for due dates
    sort_order = 1 if sort_order_str == 'asc' else -1
    
    valid_sort_fields = ['due_date', 'garden_name', 'bed_name', 'action_type'] # Adjust as needed
    if sort_by not in valid_sort_fields:
        sort_by = 'due_date'

    recommendations_cursor = mongo.db.recommendations.find(filters).sort(sort_by, sort_order).skip((page - 1) * per_page).limit(per_page)
    
    display_recommendations = []
    for rec in recommendations_cursor:
        garden = mongo.db.gardens.find_one({'_id': rec['garden_id']})
        bed = mongo.db.beds.find_one({'_id': rec['bed_id']})
        rec['garden_name'] = garden['name'] if garden else 'N/A'
        rec['bed_name'] = bed['name'] if bed else 'N/A'
        rec['is_overdue'] = rec['due_date'] < datetime.utcnow() if not rec['is_completed'] else False
        display_recommendations.append(rec)

    total_recommendations = mongo.db.recommendations.count_documents(filters)
    total_pages = (total_recommendations + per_page - 1) // per_page

    return render_template(
        'recommendations_list.html',
        recommendations=display_recommendations,
        current_page=page, total_pages=total_pages,
        total_recommendations=total_recommendations,
        user_gardens=user_gardens, user_beds=user_beds, # For filter dropdowns
        RECOMMENDATION_ACTION_TYPES=RECOMMENDATION_ACTION_TYPES,
        filters=request.args # Pass current filters back to template
    )

@recommendation_bp.route('/recommendations/<recommendation_id>/complete', methods=['POST'])
@login_required
def complete_recommendation(recommendation_id):
    redirect_to = request.form.get('redirect_to')
    garden_id = request.form.get('garden_id')
    
    recommendation = mongo.db.recommendations.find_one({
        '_id': ObjectId(recommendation_id), 
        'user_id': current_user.get_id(),
        'is_completed': False
    })
    
    if not recommendation:
        flash('Рекомендация не найдена или уже выполнена.', 'error')
        if redirect_to == 'garden_detail' and garden_id:
            return redirect(url_for('land_bp.garden_detail', garden_id=garden_id))
        else:
            return redirect(url_for('recommendation_bp.list_recommendations'))
    
    # Mark recommendation as completed
    completed_time = datetime.utcnow()
    mongo.db.recommendations.update_one(
        {'_id': ObjectId(recommendation_id)},
        {'$set': {
            'is_completed': True,
            'completed_at': completed_time
        }}
    )
    
    # Create a care log entry for this completion
    care_log_doc = {
        'user_id': current_user.get_id(),
        'garden_id': recommendation['garden_id'],
        'bed_id': recommendation['bed_id'],
        'action_type': recommendation['action_type'],
        'log_date': completed_time,
        'notes': f"Автоматически создано при выполнении рекомендации: {recommendation.get('description', '')}",
        'created_at': completed_time,
        'linked_recommendation_id': recommendation['_id']
    }
    
    care_log_id = mongo.db.care_logs.insert_one(care_log_doc).inserted_id
    
    # Update recommendation with the care log that completed it
    mongo.db.recommendations.update_one(
        {'_id': ObjectId(recommendation_id)},
        {'$set': {'completed_by_care_log_id': care_log_id}}
    )
    
    # Update bed stats
    mongo.db.beds.update_one(
        {'_id': recommendation['bed_id']},
        {
            '$inc': {'stats.completed_recommendations': 1, 'stats.pending_recommendations': -1, 'stats.total_care_actions': 1},
            '$set': {'stats.last_care_date': completed_time}
        }
    )
    
    flash('Рекомендация отмечена как выполненная!', 'success')
    
    if redirect_to == 'garden_detail' and garden_id:
        return redirect(url_for('land_bp.garden_detail', garden_id=garden_id))
    else:
        return redirect(url_for('recommendation_bp.list_recommendations'))

@recommendation_bp.route('/recommendations/<recommendation_id>/delete', methods=['POST'])
@login_required
def delete_recommendation(recommendation_id):
    redirect_to = request.form.get('redirect_to')
    garden_id = request.form.get('garden_id')
    
    recommendation = mongo.db.recommendations.find_one({
        '_id': ObjectId(recommendation_id), 
        'user_id': current_user.get_id()
    })
    
    if not recommendation:
        flash('Рекомендация не найдена.', 'error')
        if redirect_to == 'garden_detail' and garden_id:
            return redirect(url_for('land_bp.garden_detail', garden_id=garden_id))
        else:
            return redirect(url_for('recommendation_bp.list_recommendations'))
    
    # Update bed stats to decrease pending recommendations
    if not recommendation.get('is_completed', False):
        mongo.db.beds.update_one(
            {'_id': recommendation['bed_id']},
            {'$inc': {'stats.pending_recommendations': -1}}
        )
    
    # Delete recommendation
    mongo.db.recommendations.delete_one({'_id': ObjectId(recommendation_id)})
    
    flash('Рекомендация успешно удалена!', 'success')
    
    if redirect_to == 'garden_detail' and garden_id:
        return redirect(url_for('land_bp.garden_detail', garden_id=garden_id))
    else:
        return redirect(url_for('recommendation_bp.list_recommendations'))

@recommendation_bp.route('/recommendations/new', methods=['GET', 'POST'])
@login_required
def new_recommendation():
    # Get the redirect_to parameter from the request
    redirect_to = request.args.get('redirect_to')
    garden_id_from_args = request.args.get('garden_id')
    
    user_gardens = list(mongo.db.gardens.find({'user_id': current_user.get_id()}, {'name': 1, '_id': 1}).sort('name', 1))
    
    initial_beds = []
    selected_garden_id_for_beds = request.form.get('garden_id') # on POST error
    if not selected_garden_id_for_beds: # on initial GET
        selected_garden_id_for_beds = garden_id_from_args if garden_id_from_args else (str(user_gardens[0]['_id']) if user_gardens else None)

    if selected_garden_id_for_beds:
        try:
            initial_beds_cursor = mongo.db.beds.find(
                {'garden_id': ObjectId(selected_garden_id_for_beds), 'user_id': current_user.get_id()},
                {'name': 1, '_id': 1}
            ).sort('name', 1)
            initial_beds = [{'id': str(bed['_id']), 'name': bed['name']} for bed in initial_beds_cursor]
        except Exception as e:
            flash(f'Error loading beds for selected garden: {e}', 'warning')

    if request.method == 'POST':
        data = request.form
        garden_id_str = data.get('garden_id')
        bed_id_str = data.get('bed_id')
        action_type = data.get('action_type')
        description = data.get('description', '')
        due_date_str = data.get('due_date')
        due_time_str = data.get('due_time')
        redirect_to = data.get('redirect_to')  # Get from form post data

        errors = []
        if not garden_id_str: errors.append("Garden is required.")
        if not bed_id_str: errors.append("Bed is required.")
        if not action_type: errors.append("Action type is required.")
        if action_type not in RECOMMENDATION_ACTION_TYPES: errors.append("Invalid action type selected.")
        if not due_date_str: errors.append("Due date is required.")
        if not due_time_str: errors.append("Due time is required.")

        due_datetime = None
        if due_date_str and due_time_str:
            try:
                due_datetime = datetime.strptime(f"{due_date_str} {due_time_str}", '%Y-%m-%d %H:%M')
            except ValueError:
                errors.append("Invalid due date or time format. Use YYYY-MM-DD and HH:MM.")
        
        if errors:
            for error in errors:
                flash(error, 'error')

            current_form_garden_id = data.get('garden_id')
            current_beds_for_form = []
            if current_form_garden_id:
                try:
                    beds_c = mongo.db.beds.find(
                        {'garden_id': ObjectId(current_form_garden_id), 'user_id': current_user.get_id()},
                        {'name': 1, '_id': 1}
                    ).sort('name', 1)
                    current_beds_for_form = [{'id': str(b['_id']), 'name': b['name']} for b in beds_c]
                except Exception:
                    pass
            
            return render_template('recommendation_form.html',
                                   form_data=data,
                                   user_gardens=user_gardens,
                                   initial_beds=current_beds_for_form,
                                   RECOMMENDATION_ACTION_TYPES=RECOMMENDATION_ACTION_TYPES,
                                   today_date=datetime.utcnow().strftime('%Y-%m-%d'),
                                   current_time=datetime.utcnow().strftime('%H:%M'),
                                   redirect_to=redirect_to)

        garden_id = ObjectId(garden_id_str)
        bed_id = ObjectId(bed_id_str)

        recommendation_doc = {
            'user_id': current_user.get_id(),
            'garden_id': garden_id,
            'bed_id': bed_id,
            'action_type': action_type,
            'description': description,
            'due_date': due_datetime,
            'is_completed': False,
            'completed_at': None,
            'completed_by_care_log_id': None,
            'source': 'manual', # Indicates it was manually created by user
            'created_at': datetime.utcnow()
        }
        
        try:
            mongo.db.recommendations.insert_one(recommendation_doc)
            # Increment pending recommendations count in the bed's stats
            mongo.db.beds.update_one(
                {'_id': bed_id, 'user_id': current_user.get_id()},
                {'$inc': {'stats.pending_recommendations': 1}}
            )
            flash('Recommendation created successfully!', 'success')
            
            # Redirect based on the redirect_to parameter
            if redirect_to == 'garden_detail' and garden_id_str:
                return redirect(url_for('land_bp.garden_detail', garden_id=garden_id_str))
            else:
                return redirect(url_for('recommendation_bp.list_recommendations'))
        except Exception as e:
            flash(f'Error creating recommendation: {e}', 'error')

    # Create a form_data object with the garden_id if it was provided
    form_data = {}
    if garden_id_from_args:
        form_data['garden_id'] = garden_id_from_args
    
    return render_template('recommendation_form.html', 
                           form_data=form_data,
                           user_gardens=user_gardens, 
                           initial_beds=initial_beds,
                           RECOMMENDATION_ACTION_TYPES=RECOMMENDATION_ACTION_TYPES,
                           today_date=datetime.utcnow().strftime('%Y-%m-%d'),
                           current_time=datetime.utcnow().strftime('%H:%M'),
                           redirect_to=redirect_to)