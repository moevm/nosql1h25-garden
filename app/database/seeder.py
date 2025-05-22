import json
import os
from datetime import datetime
from flask import current_app
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from applications import mongo
from applications.schemas import User

def load_json_data(file_path):
    """Load data from a JSON file."""
    with open(file_path, 'r') as file:
        return json.load(file)

def parse_datetime(date_str):
    """Parse datetime string to datetime object."""
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return datetime.utcnow()

def seed_database():
    """Seed the database with initial data if it's empty."""
    db = mongo.db
    
    # Check if database is empty
    if db.users.count_documents({}) > 0:
        print("Database already contains data. Skipping seeding.")
        return

    print("Seeding database with initial data...")

    # Load seed data
    seed_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'seed_data')
    
    # Seed users
    users_data = load_json_data(os.path.join(seed_dir, 'users.json'))
    user_id_map = {}  # To store mapping between user emails and their ObjectIds
    
    for user_data in users_data['users']:
        try:
            # Create user using the User model
            user = User(
                email=user_data['email'],
                password=user_data['password'],
                name=user_data['name'],
                roles=user_data.get('roles', ['user']),
                is_admin=user_data.get('is_admin', False),
                email_verified=user_data.get('email_verified', True),
                created_at=parse_datetime(user_data['created_at']),
                updated_at=parse_datetime(user_data['updated_at'])
            )
            result = db.users.insert_one(user.to_dict())
            # Store the string representation of the ID to match how the application uses it
            user_id_map[user.email] = str(result.inserted_id)
            print(f"Created user: {user.email}")
        except DuplicateKeyError:
            print(f"Skipping duplicate user: {user_data['email']}")

    # Seed gardens
    gardens_data = load_json_data(os.path.join(seed_dir, 'gardens.json'))
    garden_id_map = {}  # To store mapping between garden names and their ObjectIds
    
    for garden in gardens_data['gardens']:
        # Assign garden to the regular user using string ID
        garden['user_id'] = user_id_map['user1@garden.com']  # Now a string ID
        garden['registration_time'] = datetime.utcnow()
        garden['last_modified_time'] = datetime.utcnow()
        garden['stats'] = {
            'total_beds': 0,
            'active_beds': 0,
            'total_crops': 0
        }
        try:
            result = db.gardens.insert_one(garden)
            garden_id_map[garden['name']] = result.inserted_id  # Keep this as ObjectId for internal references
            print(f"Created garden: {garden['name']}")
        except DuplicateKeyError:
            print(f"Skipping duplicate garden: {garden['name']}")

    # Seed beds
    beds_data = load_json_data(os.path.join(seed_dir, 'beds.json'))
    bed_id_map = {}  # To store mapping between bed names and their ObjectIds
    
    # Distribute beds among gardens
    gardens = list(garden_id_map.items())
    for i, bed in enumerate(beds_data['beds']):
        garden_name, garden_id = gardens[i % len(gardens)]
        bed['garden_id'] = garden_id  # Keep as ObjectId for internal reference
        bed['user_id'] = user_id_map['user1@garden.com']  # Use string ID
        bed['creation_time'] = datetime.utcnow()
        bed['last_modified_time'] = datetime.utcnow()
        
        # Convert planting_date to datetime
        if 'planting_date' in bed:
            bed['planting_date'] = parse_datetime(bed['planting_date'])
            
        bed['stats'] = {
            'total_care_actions': 0,
            'last_care_date': None,
            'pending_recommendations': 0,
            'completed_recommendations': 0
        }
        try:
            result = db.beds.insert_one(bed)
            bed_id_map[bed['name']] = result.inserted_id  # Keep as ObjectId for internal reference
            print(f"Created bed: {bed['name']} in garden: {garden_name}")
            
            # Update garden stats
            db.gardens.update_one(
                {'_id': garden_id},
                {
                    '$inc': {
                        'stats.total_beds': 1,
                        'stats.active_beds': 1,
                        'stats.total_crops': 1
                    }
                }
            )
        except DuplicateKeyError:
            print(f"Skipping duplicate bed: {bed['name']}")

    # Seed care logs
    care_logs_data = load_json_data(os.path.join(seed_dir, 'care_logs.json'))
    
    # Distribute care logs among beds
    beds = list(bed_id_map.items())
    for i, care_log in enumerate(care_logs_data['care_logs']):
        bed_name, bed_id = beds[i % len(beds)]
        bed = db.beds.find_one({'_id': bed_id})
        care_log['bed_id'] = bed_id  # Keep as ObjectId for internal reference
        care_log['garden_id'] = bed['garden_id']  # Keep as ObjectId for internal reference
        care_log['user_id'] = user_id_map['user1@garden.com']  # Use string ID
        
        # Convert string dates to datetime objects
        care_log['log_date'] = parse_datetime(care_log['log_date'])
        care_log['created_at'] = parse_datetime(care_log['created_at'])
        care_log['updated_at'] = parse_datetime(care_log['updated_at'])
        
        try:
            result = db.care_logs.insert_one(care_log)
            print(f"Created care log for bed: {bed_name}")
            
            # Update bed stats
            db.beds.update_one(
                {'_id': bed_id},
                {
                    '$inc': {'stats.total_care_actions': 1},
                    '$set': {
                        'stats.last_care_date': care_log['log_date'],
                        'last_modified_time': datetime.utcnow()
                    }
                }
            )
        except DuplicateKeyError:
            print(f"Skipping duplicate care log for bed: {bed_name}")

    # Create indexes
    db.users.create_index('email', unique=True)
    db.users.create_index('name')
    db.gardens.create_index([('user_id', 1), ('name', 1)], unique=True)
    db.beds.create_index([('garden_id', 1), ('name', 1)], unique=True)
    db.beds.create_index('user_id')
    db.care_logs.create_index([('user_id', 1), ('log_date', -1)])
    db.care_logs.create_index('garden_id')
    db.care_logs.create_index('bed_id')

    print("Database seeding completed successfully.") 