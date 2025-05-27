from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import current_user, login_required
from datetime import datetime
from applications import mongo
from bson import ObjectId
import os
from .utils import allowed_file, save_photo

diary_bp = Blueprint(
    "diary_bp", __name__, template_folder="../../templates", static_folder="../../static"
)

PRIVACY_OPTIONS = ["", "Публичная", "Приватная"]


@diary_bp.route('/entries')
@login_required
def entries():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    filters = {'user_id': current_user.get_id()}
    total_all = mongo.db.diary.count_documents({'user_id': current_user.get_id()})

    title_query = request.args.get('title_query', '')
    creation_date = request.args.get('creation_date', '')
    modification_date = request.args.get('modification_date', '')
    privacy_query = request.args.get('privacy_query', '')

    if title_query:
        filters['title'] = {'$regex': title_query, '$options': 'i'}

    if creation_date:
        try:
            date_obj = datetime.strptime(creation_date, '%Y-%m-%d')
            next_day = date_obj.replace(hour=23, minute=59, second=59)
            filters['creation_time'] = {
                '$gte': date_obj,
                '$lte': next_day
            }
        except ValueError:
            pass

    if modification_date:
        try:
            date_obj = datetime.strptime(modification_date, '%Y-%m-%d')
            next_day = date_obj.replace(hour=23, minute=59, second=59)
            filters['last_modified_time'] = {
                '$gte': date_obj,
                '$lte': next_day
            }
        except ValueError:
            pass

    if privacy_query == "Публичная":
        filters['is_private'] = False
    elif privacy_query == "Приватная":
        filters['is_private'] = True

    sort_by = request.args.get('sort_by', 'creation_time')
    sort_order_str = request.args.get('sort_order', 'desc')
    sort_order = -1 if sort_order_str == 'desc' else 1

    valid_sort_fields = ['title', 'creation_time', 'last_modified_time']
    if sort_by not in valid_sort_fields:
        sort_by = 'creation_time'

    entries_cursor = mongo.db.diary.find(filters) \
        .sort(sort_by, sort_order) \
        .skip((page - 1) * per_page) \
        .limit(per_page)
    entries = list(entries_cursor)

    total_entries = mongo.db.diary.count_documents(filters)
    total_pages = (total_entries + per_page - 1) // per_page if per_page > 0 else 0

    return render_template('diary.html',
                           entries=entries,
                           total_all=total_all,
                           current_page=page,
                           total_pages=total_pages,
                           title_query=title_query,
                           creation_date=creation_date,
                           modification_date=modification_date,
                           privacy_query=privacy_query,
                           sort_by=sort_by,
                           sort_order_str=sort_order_str,
                           privacy_options=PRIVACY_OPTIONS)


@diary_bp.route('/entries/new', methods=['GET', 'POST'])
@login_required
def new_entry():
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
                    return render_template('entry_form.html', form_data=data, is_edit=False)

        if not data.get('title'):
            flash('Заголовок обязателен', 'error')
            return render_template('entry_form.html', form_data=data, is_edit=False)

        new_entry_doc = {
            'user_id': current_user.get_id(),
            'title': data['title'],
            'content': data.get('content', ''),
            'is_private': data.get('is_private') == 'true',
            'photo_file_paths': photo_paths,
            'creation_time': datetime.now(),
            'last_modified_time': datetime.now()
        }

        try:
            mongo.db.diary.insert_one(new_entry_doc)
            flash('Запись успешно создана!', 'success')
            return redirect(url_for('diary_bp.entries'))
        except Exception as e:
            flash(f'Ошибка при создании записи: {e}', 'error')
            return render_template('entry_form.html', form_data=data, is_edit=False)

    return render_template('entry_form.html', form_data={}, is_edit=False)


@diary_bp.route('/entries/<entry_id>')
@login_required
def entry_detail(entry_id):
    entry = mongo.db.diary.find_one({'_id': ObjectId(entry_id), 'user_id': current_user.get_id()})
    if not entry:
        flash('Запись не найдена или доступ запрещен', 'error')
        return redirect(url_for('diary_bp.entries'))

    return render_template('entry_detail.html', entry=entry)


@diary_bp.route('/entries/<entry_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_entry(entry_id):
    entry_doc = mongo.db.diary.find_one({'_id': ObjectId(entry_id), 'user_id': current_user.get_id()})
    if not entry_doc:
        flash('Запись не найдена или доступ запрещен', 'error')
        return redirect(url_for('diary_bp.entries'))

    if request.method == 'POST':
        data = request.form
        update_data = {
            'title': data.get('title', entry_doc.get('title')),
            'content': data.get('content', entry_doc.get('content', '')),
            'is_private': data.get('is_private') == 'true',
            'last_modified_time': datetime.now()
        }

        if 'photo' in request.files:
            photo_file = request.files['photo']
            if photo_file.filename != '':
                saved_photo_path = save_photo(photo_file)
                if saved_photo_path:
                    current_photo_paths = entry_doc.get('photo_file_paths', [])
                    if current_photo_paths and current_photo_paths[0]:
                        old_photo_disk_path = os.path.join(current_app.static_folder, current_photo_paths[0])
                        if os.path.exists(old_photo_disk_path):
                            try:
                                os.remove(old_photo_disk_path)
                            except Exception as e:
                                flash(f'Не удалось удалить старое фото: {e}', 'warning')
                    update_data['photo_file_paths'] = [saved_photo_path]

        mongo.db.diary.update_one(
            {'_id': ObjectId(entry_id)},
            {'$set': update_data}
        )
        flash('Запись успешно обновлена!', 'success')
        return redirect(url_for('diary_bp.entry_detail', entry_id=entry_id))

    return render_template('entry_form.html', form_data=entry_doc, entry_id=entry_id, is_edit=True)


@diary_bp.route('/entries/<entry_id>/delete', methods=['POST'])
@login_required
def delete_entry(entry_id):
    entry = mongo.db.diary.find_one({'_id': ObjectId(entry_id), 'user_id': current_user.get_id()})
    if entry:
        if entry.get('photo_file_paths'):
            for photo_path in entry['photo_file_paths']:
                if photo_path:
                    photo_disk_path = os.path.join(current_app.static_folder, photo_path)
                    if os.path.exists(photo_disk_path):
                        try:
                            os.remove(photo_disk_path)
                        except Exception as e:
                            flash(f'Не удалось удалить фото записи: {e}', 'warning')

        mongo.db.diary.delete_one({'_id': ObjectId(entry_id), 'user_id': current_user.get_id()})
        flash('Запись успешно удалена', 'success')
    else:
        flash('Запись не найдена или доступ запрещен', 'error')

    return redirect(url_for('diary_bp.entries'))