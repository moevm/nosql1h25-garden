from datetime import datetime
from bson import ObjectId
from werkzeug.security import generate_password_hash

class User:
    def __init__(self, email, password, name, photo_path=None):
        self._id = ObjectId()
        self.email = email
        self.password_hash = generate_password_hash(password)
        self.name = name
        self.registration_time = datetime.now()
        self.last_modified_time = datetime.now()
        self.photo_file_path = photo_path or ""
        self.email_verified = False
        