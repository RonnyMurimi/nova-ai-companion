import json
import os
import hashlib
import uuid
import re
from datetime import datetime, timedelta
from config import config
import jwt


class AuthManager:
    def __init__(self):
        self.users_path = config.USERS_PATH
        os.makedirs(self.users_path, exist_ok=True)

    def _get_user_path(self, username):
        safe_username = re.sub(r'[^a-zA-Z0-9_-]', '', username)
        return os.path.join(self.users_path, f"{safe_username}.json")

    def hash_password(self, password):
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def validate_username(self, username):
        if not username or len(username) < 3:
            return False, "Username must be at least 3 characters long"
        if len(username) > 20:
            return False, "Username must be less than 20 characters"
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return False, "Username can only contain letters, numbers, hyphens, and underscores"
        return True, ""

    def validate_password(self, password):
        if not password or len(password) < 6:
            return False, "Password must be at least 6 characters long"
        if len(password) > 100:
            return False, "Password is too long"
        return True, ""

    def register(self, username, password, email=None):
        try:
            valid, error = self.validate_username(username)
            if not valid:
                return False, error

            valid, error = self.validate_password(password)
            if not valid:
                return False, error

            path = self._get_user_path(username)
            if os.path.exists(path):
                return False, "Username already exists"

            user_id = str(uuid.uuid4())
            user = {
                "user_id": user_id,
                "username": username,
                "password_hash": self.hash_password(password),
                "email": email,
                "created_at": datetime.now().isoformat(),
                "last_login": None
            }

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(user, f, indent=2, ensure_ascii=False)

            print(f"✅ User registered: {username} (ID: {user_id})")
            return True, user_id

        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False, f"Registration failed: {str(e)}"

    def authenticate(self, username, password):
        try:
            if not username or not password:
                return False, None

            path = self._get_user_path(username)
            if not os.path.exists(path):
                return False, None

            with open(path, 'r', encoding='utf-8') as f:
                user = json.load(f)

            if user["password_hash"] != self.hash_password(password):
                return False, None

            user["last_login"] = datetime.now().isoformat()
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(user, f, indent=2, ensure_ascii=False)

            print(f"✅ User authenticated: {username}")
            return True, user

        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False, None

    def create_token(self, username, user_id):
        try:
            payload = {
                "sub": username,
                "user_id": user_id,
                "exp": datetime.utcnow() + timedelta(days=7),
                "iat": datetime.utcnow()
            }
            token = jwt.encode(payload, config.SECRET_KEY, algorithm="HS256")
            return token
        except Exception as e:
            print(f"❌ Token creation error: {e}")
            return None

    def verify_token(self, token):
        try:
            payload = jwt.decode(token, config.SECRET_KEY, algorithms=["HS256"])
            return payload.get("sub"), payload.get("user_id")
        except jwt.ExpiredSignatureError:
            print("⚠️  Token expired")
            return None, None
        except jwt.InvalidTokenError as e:
            print(f"⚠️  Invalid token: {e}")
            return None, None
        except Exception as e:
            print(f"❌ Token verification error: {e}")
            return None, None