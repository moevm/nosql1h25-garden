from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import current_user, login_required
from datetime import datetime
from bson import ObjectId
import os

from applications import mongo
from .utils import save_photo  # предполагается, что такая функция есть

user_bp = Blueprint(
    "user_bp", __name__,
    template_folder="../../templates",
    static_folder="../../static"
)


@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_id = current_user.get_id()

    print("User ID:", user_id)
    print("Is Authenticated:", current_user.is_authenticated)

    user = mongo.db.users.find_one({'_id': ObjectId(user_id)})

    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        new_name = request.form.get('name', '').strip()
        if not new_name:
            flash('Name cannot be empty.', 'error')
        else:
            update_data = {
                'name': new_name,
                'updated_at': datetime.utcnow()
            }

            if 'photo' in request.files:
                photo_file = request.files['photo']
                if photo_file.filename != '':
                    saved_photo_path = save_photo(photo_file)
                    if saved_photo_path:
                        current_photo_path = user.get('photo_path', '')
                        if current_photo_path:
                            old_photo_disk_path = os.path.join(current_app.static_folder, current_photo_path)
                            if os.path.exists(old_photo_disk_path):
                                try:
                                    os.remove(old_photo_disk_path)
                                except Exception as e:
                                    flash(f'Could not delete old photo: {e}', 'warning')
                        update_data['photo_path'] = saved_photo_path

            mongo.db.users.update_one({'_id': ObjectId(user_id)}, {'$set': update_data})
            flash('Profile updated successfully!', 'success')

        # Обновляем данные пользователя после изменения
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})

    return render_template('profile.html', user=user)
