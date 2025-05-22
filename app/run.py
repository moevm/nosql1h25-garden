import os
from applications import app
from database.seeder import seed_database

# Set environment variables for MongoDB
os.environ['MONGO_URI'] = "mongodb://garden_user:garden_password@db:27017/garden_db?authSource=admin"
os.environ['SECRET_KEY'] = "your-secret-key-here"

# Initialize database with seed data
with app.app_context():
    seed_database()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 