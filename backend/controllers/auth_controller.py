"""
controllers/auth_controller.py
Business logic for authentication operations.
Separated from routes for clean architecture (Controller layer).
"""

import logging
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from backend.models.database import execute_query

logger = logging.getLogger(__name__)


class AuthController:

    @staticmethod
    def register_user(username: str, email: str, password: str, role: str = "user") -> dict:
        """
        Registers a new user. Returns dict with 'message' or 'error'.
        """
        try:
            existing = execute_query(
                "SELECT id FROM users WHERE username = %s OR email = %s",
                (username, email)
            )
            if existing:
                return {"error": "Username or email already registered", "status": 400}

            password_hash = generate_password_hash(password)
            execute_query(
                "INSERT INTO users (username, password_hash, email, role) VALUES (%s, %s, %s, %s)",
                (username, password_hash, email, role),
                fetch=False
            )
            logger.info(f"New user registered: {username} (role={role})")
            return {"message": "User registered successfully", "status": 201}

        except Exception as e:
            logger.error(f"Registration error for {username}: {e}")
            return {"error": f"Registration failed: {str(e)}", "status": 500}

    @staticmethod
    def login_user(username: str, password: str) -> dict:
        """
        Authenticates a user and issues a JWT access token.
        """
        try:
            user_rows = execute_query(
                "SELECT * FROM users WHERE username = %s OR email = %s", (username, username)
            )
            if not user_rows:
                return {"error": "Invalid credentials", "status": 401}

            user = user_rows[0]
            if not check_password_hash(user["password_hash"], password):
                return {"error": "Invalid credentials", "status": 401}

            access_token = create_access_token(
                identity=str(user["id"]),
                additional_claims={
                    "role": user["role"],
                    "username": user["username"]
                }
            )
            logger.info(f"User logged in: {username}")
            return {
                "token": access_token,
                "user": {
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                    "role": user["role"]
                },
                "status": 200
            }

        except Exception as e:
            logger.error(f"Login error for {username}: {e}")
            return {"error": f"Login failed: {str(e)}", "status": 500}

    @staticmethod
    def get_user_profile(user_id: str) -> dict:
        """
        Returns user profile data for the authenticated user.
        """
        try:
            user = execute_query(
                "SELECT id, username, email, role, created_at FROM users WHERE id = %s",
                (user_id,)
            )
            if not user:
                return {"error": "User not found", "status": 404}

            user_data = user[0]
            if user_data.get("created_at"):
                user_data["created_at"] = str(user_data["created_at"])

            return {"user": user_data, "status": 200}

        except Exception as e:
            logger.error(f"Profile fetch error for user_id={user_id}: {e}")
            return {"error": f"Failed to retrieve profile: {str(e)}", "status": 500}

    @staticmethod
    def change_password(user_id: str, old_password: str, new_password: str) -> dict:
        """
        Allows authenticated user to change their own password.
        """
        try:
            user_rows = execute_query(
                "SELECT password_hash FROM users WHERE id = %s", (user_id,)
            )
            if not user_rows:
                return {"error": "User not found", "status": 404}

            if not check_password_hash(user_rows[0]["password_hash"], old_password):
                return {"error": "Current password is incorrect", "status": 401}

            new_hash = generate_password_hash(new_password)
            execute_query(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (new_hash, user_id),
                fetch=False
            )
            logger.info(f"Password changed for user_id={user_id}")
            return {"message": "Password changed successfully", "status": 200}

        except Exception as e:
            logger.error(f"Password change error for user_id={user_id}: {e}")
            return {"error": f"Password change failed: {str(e)}", "status": 500}
