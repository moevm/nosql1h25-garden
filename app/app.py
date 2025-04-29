from flask import Flask
from flask_pymongo import PyMongo
from routes.auth import auth_bp
from routes.index import main_bp
import os
from flask_pymongo import PyMongo

mongo = PyMongo()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['MONGO_URI'] = os.getenv('MONGO_URI')
    mongo.init_app(app)
    
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(main_bp) 
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host="0.0.0.0")