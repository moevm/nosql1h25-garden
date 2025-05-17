from flask import (
    Blueprint, render_template
)
from flask import Flask, jsonify, request, render_template, flash, redirect, url_for, session, send_from_directory
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from .schemas import User
from applications import mongo, login_manager
from bson import ObjectId


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


