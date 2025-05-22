from datetime import datetime
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


class User(UserMixin):
    def __init__(
        self,
        email: str,
        password: str,
        name: str,
        photo_path: str = None,
        _id: ObjectId = None,
        email_verified: bool = False,
        created_at: datetime = None,
        updated_at: datetime = None,
        roles: list = None,
        is_admin: bool = False
    ):
        self._id = _id or ObjectId()
        self.email = email
        self.password_hash = generate_password_hash(password)
        self.name = name
        self.photo_path = photo_path or ""
        self.email_verified = email_verified
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.roles = roles or ["user"]  # Default role
        self.is_admin = is_admin

    def get_id(self):
        return str(self._id)

    @property
    def is_active(self):
        # return self.email_verified
        return True

    def verify_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "_id": self._id,
            "email": self.email,
            "password_hash": self.password_hash,
            "name": self.name,
            "photo_path": self.photo_path,
            "email_verified": self.email_verified,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "roles": self.roles,
            "is_admin": self.is_admin
        }

    @classmethod
    def from_dict(cls, data: dict):
        
        user = cls(
            email=data.get("email"),
            password="",  # Password shouldn't be loaded back directly
            name=data.get("name"),
            photo_path=data.get("photo_path", ""),
            _id=data.get("_id"),
            email_verified=data.get("email_verified", False),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            roles=data.get("roles", ["user"]),
            is_admin=data.get("is_admin", False)
        )
        # Restore the hashed password
        if "password_hash" in data:
            user.password_hash = data["password_hash"]
        return user

    def update_password(self, new_password: str):
        self.password_hash = generate_password_hash(new_password)
        self.updated_at = datetime.now()

    def verify_email(self):
        self.email_verified = True
        self.updated_at = datetime.now()