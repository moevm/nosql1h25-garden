from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from applications import mongo
from bson import ObjectId
from datetime import datetime
from .choices import CARE_ACTION_TYPES
care_bp = Blueprint(
    "care_bp", 
    __name__, 
    template_folder="../../templates", 
    static_folder="../../static"
)

@care_bp.route('/api/gardens/<garden_id>/beds-for-dropdown', methods=['GET'])
@login_required
def beds_for_dropdown(garden_id):
    try:
        garden_object_id = ObjectId(garden_id)
    except Exception:
        return jsonify({'error': 'Invalid garden_id format'}), 400

    beds_cursor = mongo.db.beds.find(
        {'garden_id': garden_object_id, 'user_id': current_user.get_id()},
        {'name': 1, '_id': 1}
    ).sort('name', 1)
    
    beds = [{'id': str(bed['_id']), 'name': bed['name']} for bed in beds_cursor]
    return jsonify(beds)

@care_bp.route('/care-logs', methods=['GET'])
@login_required
def list_care_logs():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    filters = {'user_id': current_user.get_id()}
    
    # Filtering
    filter_garden_id = request.args.get('garden_id')
    filter_bed_id = request.args.get('bed_id')
    filter_action_type = request.args.get('action_type')
    filter_date_from_str = request.args.get('date_from')
    filter_date_to_str = request.args.get('date_to')

    # Получаем только существующие сады пользователя
    user_gardens = list(mongo.db.gardens.find({'user_id': current_user.get_id()}, {'name': 1, '_id': 1}).sort('name', 1))
    user_beds = []

    # Создаем список ID существующих садов для фильтрации
    existing_garden_ids = [garden['_id'] for garden in user_gardens]
    
    # Базовый фильтр: показывать записи только для существующих садов
    filters['garden_id'] = {'$in': existing_garden_ids} if existing_garden_ids else {'$exists': False}

    if filter_garden_id:
        try:
            garden_id_obj = ObjectId(filter_garden_id)
            if garden_id_obj in existing_garden_ids:
                filters['garden_id'] = garden_id_obj
                
                user_beds = list(mongo.db.beds.find(
                    {'user_id': current_user.get_id(), 'garden_id': garden_id_obj}, 
                    {'name': 1, '_id': 1}
                ).sort('name', 1))
                
                existing_bed_ids = [bed['_id'] for bed in user_beds]
                
                if filter_bed_id:
                    try:
                        bed_id_obj = ObjectId(filter_bed_id)
                        if bed_id_obj in existing_bed_ids:
                            filters['bed_id'] = bed_id_obj
                    except:
                        flash('Некорректный формат ID грядки', 'warning')
            else:
                flash('Указанный сад не существует или у вас нет к нему доступа', 'warning')
        except:
            flash('Некорректный формат ID сада', 'warning')
    
    if filter_action_type:
        filters['action_type'] = filter_action_type
    
    date_filter_conditions = {}
    if filter_date_from_str:
        try:
            date_filter_conditions['$gte'] = datetime.strptime(filter_date_from_str, '%Y-%m-%d')
        except ValueError:
            flash('Некорректный формат даты "с". Используйте YYYY-MM-DD.', 'warning')
    if filter_date_to_str:
        try:
            date_filter_conditions['$lte'] = datetime.strptime(filter_date_to_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        except ValueError:
            flash('Некорректный формат даты "по". Используйте YYYY-MM-DD.', 'warning')
    
    if date_filter_conditions:
        filters['log_date'] = date_filter_conditions

    # Sorting
    sort_by = request.args.get('sort_by', 'log_date')
    sort_order_str = request.args.get('sort_order', 'desc')
    sort_order = -1 if sort_order_str == 'desc' else 1
    
    valid_sort_fields = ['log_date', 'garden_name', 'bed_name', 'action_type']
    if sort_by not in valid_sort_fields:
        sort_by = 'log_date'

    care_logs_cursor = mongo.db.care_logs.find(filters).sort(sort_by, sort_order).skip((page - 1) * per_page).limit(per_page)
    
    display_logs = []
    for log in care_logs_cursor:
        garden = mongo.db.gardens.find_one({'_id': log['garden_id']})
        bed = mongo.db.beds.find_one({'_id': log['bed_id']})
        
        # Пропускаем записи для несуществующих садов/грядок
        if not garden or not bed:
            # Удаляем запись, если сад или грядка больше не существуют
            mongo.db.care_logs.delete_one({'_id': log['_id']})
            continue
            
        log['garden_name'] = garden['name']
        log['bed_name'] = bed['name']
        display_logs.append(log)

    # Пересчитываем общее количество записей после проверки существования
    total_logs = len(display_logs) if display_logs else 0
    if total_logs == 0:
        total_logs = mongo.db.care_logs.count_documents(filters)
    
    total_pages = (total_logs + per_page - 1) // per_page if total_logs > 0 else 1

    return render_template(
        'care_log_list.html', 
        care_logs=display_logs,
        current_page=page, total_pages=total_pages,
        user_gardens=user_gardens, user_beds=user_beds, # For filter dropdowns
        CARE_ACTION_TYPES=CARE_ACTION_TYPES,
        filters=request.args
    )

@care_bp.route('/care-logs/new', methods=['GET', 'POST'])
@login_required
def new_care_log():
    # Получаем параметр redirect_to из запроса
    redirect_to = request.args.get('redirect_to')
    # Получаем garden_id из запроса
    garden_id_from_args = request.args.get('garden_id')
    
    user_gardens = list(mongo.db.gardens.find({'user_id': current_user.get_id()}, {'name': 1, '_id': 1}).sort('name', 1))
    
    initial_beds = []
    if user_gardens:
        # Если есть garden_id в запросе, используем его, иначе берем первый сад
        first_garden_id = ObjectId(garden_id_from_args) if garden_id_from_args else user_gardens[0]['_id']
        initial_beds_cursor = mongo.db.beds.find(
            {'garden_id': ObjectId(first_garden_id), 'user_id': current_user.get_id()},
            {'name': 1, '_id': 1}
        ).sort('name', 1)
        initial_beds = [{'id': str(bed['_id']), 'name': bed['name']} for bed in initial_beds_cursor]

    if request.method == 'POST':
        data = request.form
        garden_id_str = data.get('garden_id')
        bed_id_str = data.get('bed_id')
        action_type = data.get('action_type')
        log_date_str = data.get('log_date')
        log_time_str = data.get('log_time')
        notes = data.get('notes', '')
        redirect_to = data.get('redirect_to')  # Get redirect_to from form data

        errors = []
        if not garden_id_str: errors.append("Garden is required.")
        if not bed_id_str: errors.append("Bed is required.")
        if not action_type: errors.append("Action type is required.")
        if action_type not in CARE_ACTION_TYPES: errors.append("Invalid action type selected.")
        if not log_date_str: errors.append("Log date is required.")
        if not log_time_str: errors.append("Log time is required.")

        log_datetime = None
        if log_date_str and log_time_str:
            try:
                log_datetime = datetime.strptime(f"{log_date_str} {log_time_str}", '%Y-%m-%d %H:%M')
            except ValueError:
                errors.append("Invalid date or time format.")
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('care_log_form.html', 
                                   form_data=data, 
                                   user_gardens=user_gardens, 
                                   initial_beds=initial_beds,
                                   CARE_ACTION_TYPES=CARE_ACTION_TYPES, 
                                   is_edit=False,
                                   redirect_to=redirect_to)
        
        garden_id = ObjectId(garden_id_str)
        bed_id = ObjectId(bed_id_str)

        care_log_doc = {
            'user_id': current_user.get_id(),
            'garden_id': garden_id,
            'bed_id': bed_id,
            'action_type': action_type,
            'log_date': log_datetime,
            'notes': notes,
            'created_at': datetime.now(),
            'linked_recommendation_id': None 
        }
        
        result = mongo.db.care_logs.insert_one(care_log_doc)
        care_log_id = result.inserted_id

        potential_recommendations = mongo.db.recommendations.find({
            'user_id': current_user.get_id(),
            'garden_id': garden_id,
            'bed_id': bed_id,
            'action_type': action_type,
            'is_completed': False,
            'due_date': {'$lte': log_datetime}
        }).sort('due_date', 1)

        recommendation_completed = False
        for rec in potential_recommendations:
            if rec['due_date'].date() <= log_datetime.date():
                 mongo.db.recommendations.update_one(
                    {'_id': rec['_id']},
                    {'$set': {
                        'is_completed': True, 
                        'completed_at': log_datetime,
                        'completed_by_care_log_id': care_log_id
                        }
                    }
                )
                 mongo.db.care_logs.update_one(
                     {'_id': care_log_id},
                     {'$set': {'linked_recommendation_id': rec['_id']}}
                 )
                 
                 # Update bed stats
                 mongo.db.beds.update_one(
                     {'_id': bed_id},
                     {
                         '$inc': {'stats.completed_recommendations': 1, 'stats.pending_recommendations': -1, 'stats.total_care_actions': 1},
                         '$set': {'stats.last_care_date': log_datetime}
                     }
                 )
                 flash(f"Recommendation '{rec['description'] if rec.get('description') else action_type}' marked as completed.", 'info')
                 recommendation_completed = True
                 break

        if not recommendation_completed:
            mongo.db.beds.update_one(
                 {'_id': bed_id},
                 {
                     '$inc': {'stats.total_care_actions': 1},
                     '$set': {'stats.last_care_date': log_datetime}
                 }
            )

        flash('Care log added successfully!', 'success')
        
        # Redirect based on the redirect_to parameter
        if redirect_to == 'garden_detail' and garden_id_str:
            return redirect(url_for('land_bp.garden_detail', garden_id=garden_id_str))
        else:
            return redirect(url_for('care_bp.list_care_logs'))

    # Предзаполнение формы, если передан garden_id
    form_data = {}
    if garden_id_from_args:
        form_data['garden_id'] = garden_id_from_args

    return render_template('care_log_form.html', 
                           form_data=form_data, 
                           user_gardens=user_gardens, 
                           initial_beds=initial_beds,
                           CARE_ACTION_TYPES=CARE_ACTION_TYPES, 
                           is_edit=False,
                           redirect_to=redirect_to)
                           
@care_bp.route('/care-logs/<care_log_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_care_log(care_log_id):
    # Получаем запись журнала ухода
    care_log = mongo.db.care_logs.find_one({'_id': ObjectId(care_log_id), 'user_id': current_user.get_id()})
    if not care_log:
        flash('Запись не найдена или у вас нет доступа к ней.', 'error')
        return redirect(url_for('care_bp.list_care_logs'))
    
    # Получаем параметр redirect_to из запроса
    redirect_to = request.args.get('redirect_to')
    
    user_gardens = list(mongo.db.gardens.find({'user_id': current_user.get_id()}, {'name': 1, '_id': 1}).sort('name', 1))
    
    # Получаем все грядки для выбранного участка
    user_beds = list(mongo.db.beds.find(
        {'garden_id': care_log['garden_id'], 'user_id': current_user.get_id()},
        {'name': 1, '_id': 1}
    ).sort('name', 1))
    
    # Преобразуем ObjectId в строки для передачи в шаблон
    user_beds = [{'id': str(bed['_id']), 'name': bed['name']} for bed in user_beds]
    
    if request.method == 'POST':
        data = request.form
        garden_id_str = data.get('garden_id')
        bed_id_str = data.get('bed_id')
        action_type = data.get('action_type')
        log_date_str = data.get('log_date')
        log_time_str = data.get('log_time')
        notes = data.get('notes', '')
        redirect_to = data.get('redirect_to')  # Get redirect_to from form data

        errors = []
        if not garden_id_str: errors.append("Участок обязателен.")
        if not bed_id_str: errors.append("Грядка обязательна.")
        if not action_type: errors.append("Тип действия обязателен.")
        if action_type not in CARE_ACTION_TYPES: errors.append("Выбран неверный тип действия.")
        if not log_date_str: errors.append("Дата записи обязательна.")
        if not log_time_str: errors.append("Время записи обязательно.")

        log_datetime = None
        if log_date_str and log_time_str:
            try:
                log_datetime = datetime.strptime(f"{log_date_str} {log_time_str}", '%Y-%m-%d %H:%M')
            except ValueError:
                errors.append("Неверный формат даты или времени.")
        
        if errors:
            for error in errors:
                flash(error, 'error')
            # Добавим данные формы в care_log для правильного отображения в форме
            for key, value in data.items():
                care_log[key] = value
            return render_template('care_log_form.html', 
                                   form_data=care_log, 
                                   user_gardens=user_gardens, 
                                   initial_beds=user_beds,
                                   CARE_ACTION_TYPES=CARE_ACTION_TYPES, 
                                   is_edit=True,
                                   care_log_id=care_log_id,
                                   redirect_to=redirect_to)
        
        garden_id = ObjectId(garden_id_str)
        bed_id = ObjectId(bed_id_str)
        
        # Если изменилась грядка, нужно обновить счетчик грядки
        old_bed_id = care_log['bed_id']
        
        # Обновляем запись журнала
        mongo.db.care_logs.update_one(
            {'_id': ObjectId(care_log_id)},
            {'$set': {
                'garden_id': garden_id,
                'bed_id': bed_id,
                'action_type': action_type,
                'log_date': log_datetime,
                'notes': notes
            }}
        )
        
        # Если грядка изменилась, обновляем статистику обеих грядок
        if str(old_bed_id) != bed_id_str:
            # Уменьшаем счетчик для старой грядки
            mongo.db.beds.update_one(
                {'_id': old_bed_id},
                {'$inc': {'stats.total_care_actions': -1}}
            )
            
            # Увеличиваем счетчик для новой грядки
            mongo.db.beds.update_one(
                {'_id': bed_id},
                {'$inc': {'stats.total_care_actions': 1},
                 '$set': {'stats.last_care_date': log_datetime}}
            )
        
        flash('Запись журнала успешно обновлена!', 'success')
        
        # Redirect based on the redirect_to parameter
        if redirect_to == 'garden_detail' and garden_id_str:
            return redirect(url_for('land_bp.garden_detail', garden_id=garden_id_str))
        else:
            return redirect(url_for('care_bp.list_care_logs'))
    
    # Форматируем данные для формы
    if care_log.get('log_date'):
        care_log['log_date_str'] = care_log['log_date'].strftime('%Y-%m-%d')
        care_log['log_time_str'] = care_log['log_date'].strftime('%H:%M')
    
    return render_template('care_log_form.html', 
                           form_data=care_log, 
                           user_gardens=user_gardens, 
                           initial_beds=user_beds,
                           CARE_ACTION_TYPES=CARE_ACTION_TYPES, 
                           is_edit=True,
                           care_log_id=care_log_id,
                           redirect_to=redirect_to)

@care_bp.route('/care-logs/<care_log_id>/delete', methods=['POST'])
@login_required
def delete_care_log(care_log_id):
    care_log = mongo.db.care_logs.find_one({'_id': ObjectId(care_log_id), 'user_id': current_user.get_id()})
    if not care_log:
        flash('Запись не найдена или у вас нет доступа к ней.', 'error')
        return redirect(url_for('care_bp.list_care_logs'))
    
    # Уменьшаем счетчик total_care_actions для соответствующей грядки
    mongo.db.beds.update_one(
        {'_id': care_log['bed_id']},
        {'$inc': {'stats.total_care_actions': -1}}
    )
    
    # Если запись связана с рекомендацией, обновляем статус рекомендации
    if care_log.get('linked_recommendation_id'):
        mongo.db.recommendations.update_one(
            {'_id': care_log['linked_recommendation_id']},
            {'$set': {
                'is_completed': False,
                'completed_at': None,
                'completed_by_care_log_id': None
            },
             '$inc': {'stats.completed_recommendations': -1, 'stats.pending_recommendations': 1}}
        )
    
    # Удаляем запись журнала
    mongo.db.care_logs.delete_one({'_id': ObjectId(care_log_id)})
    
    flash('Запись журнала успешно удалена!', 'success')
    return redirect(url_for('care_bp.list_care_logs'))