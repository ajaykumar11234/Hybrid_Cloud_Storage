# models/user_model.py
from datetime import datetime
import uuid
from werkzeug.security import generate_password_hash, check_password_hash

class UserModel:
    """Handles user CRUD, authentication, and stats in MongoDB"""

    def __init__(self, db):
        self.db = db
        self.users = db.users

    def create_user(self, user_data):
        """Create a new user"""
        try:
            if self.users.find_one({"email": user_data["email"].lower()}):
                return None, "User already exists with this email"

            user_id = str(uuid.uuid4())
            now = datetime.utcnow()

            user_doc = {
                "_id": user_id,
                "name": user_data["name"],
                "email": user_data["email"].lower(),
                "password_hash": generate_password_hash(user_data["password"]),
                "created_at": now,
                "updated_at": now,
                "is_active": True,
                "storage_used": 0,
                "file_count": 0,
                "last_login": None,
                "preferences": {
                    "theme": "light",
                    "notifications": True,
                    "auto_analyze": True,
                },
            }

            self.users.insert_one(user_doc)
            return self._serialize_user(user_doc), None
        except Exception as e:
            return None, f"Error creating user: {e}"

    def get_user_by_id(self, user_id):
        """Fetch user by ID"""
        try:
            user = self.users.find_one({"_id": user_id})
            return (self._serialize_user(user), None) if user else (None, "User not found")
        except Exception as e:
            return None, f"Error getting user: {e}"

    def get_user_by_email(self, email):
        """Fetch user by email"""
        try:
            user = self.users.find_one({"email": email.lower()})
            return (self._serialize_user(user), None) if user else (None, "User not found")
        except Exception as e:
            return None, f"Error getting user: {e}"

    def verify_password(self, email, password):
        """Verify user credentials"""
        try:
            user = self.users.find_one({"email": email.lower()})
            if user and check_password_hash(user["password_hash"], password):
                self.users.update_one({"_id": user["_id"]}, {"$set": {"last_login": datetime.utcnow()}})
                return self._serialize_user(user), None
            return None, "Invalid email or password"
        except Exception as e:
            return None, f"Error verifying password: {e}"

    def update_user(self, user_id, update_data):
        """Update user profile fields"""
        try:
            disallowed = {"_id", "email", "password_hash"}
            for field in disallowed:
                update_data.pop(field, None)
            update_data["updated_at"] = datetime.utcnow()

            result = self.users.update_one({"_id": user_id}, {"$set": update_data})
            if result.modified_count:
                return self._serialize_user(self.users.find_one({"_id": user_id})), None
            return None, "No changes made"
        except Exception as e:
            return None, f"Error updating user: {e}"

    def update_password(self, user_id, current_password, new_password):
        """Update user's password"""
        try:
            user = self.users.find_one({"_id": user_id})
            if not user:
                return None, "User not found"
            if not check_password_hash(user["password_hash"], current_password):
                return None, "Incorrect current password"

            new_hash = generate_password_hash(new_password)
            self.users.update_one(
                {"_id": user_id},
                {"$set": {"password_hash": new_hash, "updated_at": datetime.utcnow()}},
            )
            return True, None
        except Exception as e:
            return None, f"Error updating password: {e}"

    def _serialize_user(self, user_doc):
        """Serialize MongoDB user document for responses"""
        if not user_doc:
            return None
        return {
            "id": user_doc["_id"],
            "name": user_doc.get("name"),
            "email": user_doc.get("email"),
            "is_active": user_doc.get("is_active", True),
            "storage_used": user_doc.get("storage_used", 0),
            "file_count": user_doc.get("file_count", 0),
            "preferences": user_doc.get("preferences", {}),
            "created_at": user_doc.get("created_at"),
            "updated_at": user_doc.get("updated_at"),
            "last_login": user_doc.get("last_login"),
        }
