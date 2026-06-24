"""
Middleware: auth_middleware.py
JWT Authentication + Role-Based Access Control middleware.
"""

import logging
from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from backend.models.database import execute_query

logger = logging.getLogger(__name__)


def jwt_required_middleware(fn):
    """
    Wraps a route with JWT verification.
    Returns 401 if token is missing or invalid.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return fn(*args, **kwargs)
        except Exception as e:
            logger.warning(f"JWT verification failed: {e}")
            return jsonify({"error": "Authentication required. Invalid or missing token."}), 401
    return wrapper


def admin_required(fn):
    """
    Wraps a route that requires admin role.
    Verifies JWT first, then checks the user's role in the database.
    Returns 403 if the authenticated user is not an admin.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            current_user_id = get_jwt_identity()
            user = execute_query(
                "SELECT role FROM users WHERE id = %s", (current_user_id,)
            )
            if not user or user[0].get("role") != "admin":
                logger.warning(
                    f"Unauthorized admin access attempt by user_id={current_user_id}"
                )
                return jsonify({"error": "Admin privileges required for this action."}), 403
            return fn(*args, **kwargs)
        except Exception as e:
            logger.error(f"Admin check failed: {e}")
            return jsonify({"error": "Authentication error."}), 401
    return wrapper


def validate_json(*required_fields):
    """
    Decorator factory that validates JSON body for required fields.
    Usage: @validate_json("name", "email", "password")
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                return jsonify({"error": "Content-Type must be application/json"}), 415
            data = request.get_json(silent=True) or {}
            missing = [f for f in required_fields if f not in data or data[f] is None or data[f] == ""]
            if missing:
                return jsonify({
                    "error": f"Missing required fields: {', '.join(missing)}"
                }), 400
            return fn(*args, **kwargs)
        return wrapper
    return decorator
