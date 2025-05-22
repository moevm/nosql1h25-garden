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

