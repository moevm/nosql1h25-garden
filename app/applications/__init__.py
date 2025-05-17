from flask import Flask
from flask_pymongo import PyMongo
from .auth import auth_bp
from .index import main_bp
import os
from flask_pymongo import PyMongo

mongo = PyMongo()
app = Flask(__name__, static_folder='../static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['MONGO_URI'] = os.getenv('MONGO_URI')
mongo.init_app(app)
    
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(main_bp) 

