from flask import (
    Blueprint, render_template, current_app, Flask, jsonify, request, flash, redirect, url_for, session, send_from_directory
)
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from .schemas import User
from applications import mongo, login_manager
from bson import ObjectId
from .utils import allowed_file, save_photo
import os
from datetime import datetime
auth_bp = Blueprint("auth_bp", __name__)

@login_manager.user_loader
def load_user(user_id):
    try:
        user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        return User.from_dict(user_data) if user_data else None
    except Exception as e:
        print(f"Error loading user: {e}")
        return None

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main_bp.home'))

    if request.method == 'POST':
        data = request.form
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        
        if not name or not email or not password:
            flash('All fields are required', 'error')
            return render_template('register.html', name=name, email=email)
            
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html', name=name, email=email)

        if mongo.db.users.find_one({'email': email}):
            flash('Email already registered', 'error')
            return render_template('register.html', name=name)
        
        try:
            user = User(
                email=email,
                password=password,
                name=name
            )
            
            mongo.db.users.insert_one(user.to_dict())
            login_user(user)
            flash('Welcome! Registration successful.', 'success')
            return redirect(url_for('main_bp.home'))
            
        except Exception as e:
            flash('Registration failed. Please try again.', 'error')
            print(f"Error during registration: {e}")
    
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main_bp.home'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        if not email or not password:
            flash('Email and password are required', 'error')
            return render_template('login.html', email=email)

        user_data = mongo.db.users.find_one({'email': email})

        if not user_data:
            flash('Email not found. Please check your email or register.', 'error')
            return render_template('login.html', email=email)
        
        user = User.from_dict(user_data)

        if not user.verify_password(password):
            flash('Invalid password. Please try again.', 'error')
            return render_template('login.html', email=email)
        
        login_user(user, remember=remember)
        flash('Logged in successfully!', 'success')
        return redirect(url_for('main_bp.home'))

    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth_bp.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        name = request.form.get('name')
        photo = request.files.get('photo')
        update_fields = {}

        # Обновление имени
        if name and name != current_user.name:
            update_fields['name'] = name

        # Обновление фото
        if photo and photo.filename:
            saved_path = save_photo(photo)
            if saved_path:
                # Удаляем старое фото, если есть
                old_path = getattr(current_user, 'photo_path', None)
                if old_path:
                    try:
                        old_disk_path = os.path.join(current_app.static_folder, old_path)
                        if os.path.exists(old_disk_path):
                            os.remove(old_disk_path)
                    except Exception as e:
                        flash(f'Не удалось удалить старое фото: {e}', 'warning')
                update_fields['photo_path'] = saved_path
            else:
                flash('Ошибка при загрузке фото', 'error')
                return redirect(url_for('auth_bp.profile'))

        # Сохраняем изменения, если есть что сохранять
        if update_fields:
            # обновляем отметку времени изменения
            new_updated = datetime.utcnow()
            update_fields['updated_at'] = new_updated

            # обновляем в базе
            mongo.db.users.update_one(
                {'_id': ObjectId(current_user.get_id())},
                {'$set': update_fields}
            )

            # обновляем текущий объект пользователя для следующего запроса
            if 'name' in update_fields:
                current_user.name = update_fields['name']
            if 'photo_path' in update_fields:
                current_user.photo_path = update_fields['photo_path']
            current_user.updated_at = new_updated

            flash('Профиль обновлён', 'success')
        else:
            flash('Нет изменений для сохранения', 'info')

        # Всегда перенаправляем после POST (PRG), чтобы сбросить форму
        return redirect(url_for('auth_bp.profile'))

    # GET
    return render_template('profile.html')