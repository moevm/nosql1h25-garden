import os

class Config:
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://garden_user:garden_password@db:27017/garden_db?authSource=admin')
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    
    # Flask-PyMongo settings
    MONGO_AUTH_SOURCE = 'admin'
    MONGO_AUTH_MECHANISM = 'SCRAM-SHA-256'