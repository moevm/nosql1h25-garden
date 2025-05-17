from flask import Flask
from flask_pymongo import PyMongo
import os
from flask_login import LoginManager
from dotenv import load_dotenv

load_dotenv()
mongo = PyMongo()
login_manager = LoginManager()

app = Flask(__name__, static_folder='../static', template_folder='../templates')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['MONGO_URI'] = os.getenv('MONGO_URI')
mongo.init_app(app)


login_manager.init_app(app)
login_manager.login_view = 'auth_bp.login'
login_manager.login_message = "Пожалуйста, войдите, чтобы получить доступ к этой странице."
login_manager.login_message_category = "info"
    
from .auth import auth_bp
from .index import main_bp

app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(main_bp, url_prefix="") 

