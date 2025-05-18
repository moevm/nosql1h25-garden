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

UPLOAD_FOLDER = os.path.join(app.root_path, '..', 'static', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

mongo.init_app(app)


login_manager.init_app(app)
login_manager.login_view = 'auth_bp.login'
login_manager.login_message = "Пожалуйста, войдите, чтобы получить доступ к этой странице."
login_manager.login_message_category = "info"
    
from .auth import auth_bp
from .index import main_bp
from .land import land_bp
from .land_beds import bed_bp
from .care import care_bp
from .recommendations import recommendation_bp


app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(main_bp, url_prefix="") 
app.register_blueprint(land_bp, url_prefix="")
app.register_blueprint(bed_bp)
app.register_blueprint(care_bp)
app.register_blueprint(recommendation_bp) 
