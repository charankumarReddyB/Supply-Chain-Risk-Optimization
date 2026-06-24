"""
routes/auth.py
Authentication endpoints: register, login, profile, password change, logout.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.controllers.auth_controller import AuthController

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    POST /api/auth/register
    Body: { "username": str, "email": str, "password": str, "role": str (optional) }
    Registers a new user. Returns 201 on success.
    """
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    role = data.get("role", "user")

    if not username or not email or not password:
        return jsonify({"error": "username, email, and password are required"}), 400

    result = AuthController.register_user(username, email, password, role)
    return jsonify({k: v for k, v in result.items() if k != "status"}), result["status"]


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    POST /api/auth/login
    Body: { "username": str, "password": str }
    Returns JWT access token on success.
    """
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    result = AuthController.login_user(username, password)
    return jsonify({k: v for k, v in result.items() if k != "status"}), result["status"]


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """
    GET /api/auth/me
    Returns the profile of the currently authenticated user.
    Requires: Authorization: Bearer <token>
    """
    user_id = get_jwt_identity()
    result = AuthController.get_user_profile(user_id)
    if result.get("status") == 200 and "user" in result:
        res = {k: v for k, v in result.items() if k != "status"}
        res["username"] = result["user"]["username"]
        res["role"] = result["user"]["role"]
        return jsonify(res), 200
    return jsonify({k: v for k, v in result.items() if k != "status"}), result["status"]


@auth_bp.route("/change-password", methods=["PUT"])
@jwt_required()
def change_password():
    """
    PUT /api/auth/change-password
    Body: { "old_password": str, "new_password": str }
    Allows authenticated user to update their password.
    """
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    old_password = data.get("old_password") or ""
    new_password = data.get("new_password") or ""

    if not old_password or not new_password:
        return jsonify({"error": "old_password and new_password are required"}), 400

    result = AuthController.change_password(user_id, old_password, new_password)
    return jsonify({k: v for k, v in result.items() if k != "status"}), result["status"]


@auth_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    """
    PUT /api/auth/profile
    Body: { "email": str, "full_name": str, "phone": str, "location": str, "department": str, "employee_id": str }
    Allows authenticated user to update their own profile details.
    """
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    full_name = data.get("full_name")
    phone = data.get("phone")
    location = data.get("location")
    department = data.get("department")
    employee_id = data.get("employee_id")

    if not email:
        return jsonify({"error": "email is required"}), 400

    result = AuthController.update_user_profile(
        user_id=user_id,
        email=email,
        full_name=full_name,
        phone=phone,
        location=location,
        department=department,
        employee_id=employee_id
    )
    return jsonify({k: v for k, v in result.items() if k != "status"}), result["status"]


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """
    POST /api/auth/logout
    Client-side logout. JWT is stateless; client should discard the token.
    Returns success acknowledgement.
    """
    return jsonify({"message": "Logged out successfully. Please discard your token."}), 200
