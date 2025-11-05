# routes/auth_routes.py
from flask import Blueprint, request, jsonify
import jwt
import datetime
from functools import wraps
from config import Config
from models.user_model import UserModel

auth_bp = Blueprint("auth", __name__)
user_model = None

def init_auth_routes(db):
    global user_model
    user_model = UserModel(db)

# ------------------------------------------------------------
# JWT Decorator
# ------------------------------------------------------------
def token_required(f):
    """JWT auth decorator"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Token missing"}), 401

        try:
            if token.startswith("Bearer "):
                token = token[7:]
            data = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
            user, err = user_model.get_user_by_id(data["user_id"])
            if err or not user:
                return jsonify({"error": "Invalid user"}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        return f(user, *args, **kwargs)
    return decorated

# ------------------------------------------------------------
# SIGNUP Route
# ------------------------------------------------------------
@auth_bp.route("/signup", methods=["POST"])
def signup():
    """Register a new user"""
    data = request.get_json() or {}

    # Validate input
    if not data.get("email") or not data.get("password") or not data.get("name"):
        return jsonify({
            "success": False,
            "message": "Missing required fields"
        }), 400

    # Create user (model checks for duplicates)
    user, err = user_model.create_user(data)

    if err:
        # Explicit duplicate email error from UserModel
        if "already exists" in err.lower():
            return jsonify({
                "success": False,
                "message": "Email already exists. Please log in."
            }), 409
        # Other error
        return jsonify({
            "success": False,
            "message": err
        }), 400

    # JWT token
    token = jwt.encode({
        "user_id": user["id"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=Config.JWT_EXPIRES_HOURS)
    }, Config.JWT_SECRET_KEY, algorithm="HS256")

    if isinstance(token, bytes):
        token = token.decode("utf-8")

    return jsonify({
        "success": True,
        "message": "User created successfully",
        "token": token,
        "user": user
    }), 201

# ------------------------------------------------------------
# LOGIN Route
# ------------------------------------------------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate user"""
    data = request.get_json() or {}

    if not data.get("email") or not data.get("password"):
        return jsonify({
            "success": False,
            "message": "Email and password required"
        }), 400

    user, err = user_model.verify_password(data.get("email"), data.get("password"))
    if err:
        if "invalid email" in err.lower() or "password" in err.lower():
            return jsonify({
                "success": False,
                "message": "Invalid email or password"
            }), 401
        return jsonify({
            "success": False,
            "message": err
        }), 400

    token = jwt.encode({
        "user_id": user["id"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=Config.JWT_EXPIRES_HOURS)
    }, Config.JWT_SECRET_KEY, algorithm="HS256")

    if isinstance(token, bytes):
        token = token.decode("utf-8")

    return jsonify({
        "success": True,
        "message": "Login successful",
        "token": token,
        "user": user
    }), 200

# ------------------------------------------------------------
# USER INFO
# ------------------------------------------------------------
@auth_bp.route("/me", methods=["GET"])
@token_required
def me(user):
    """Get authenticated user's info"""
    return jsonify({
        "success": True,
        "user": user
    }), 200

# ------------------------------------------------------------
# USER STATS
# ------------------------------------------------------------
@auth_bp.route("/stats", methods=["GET"])
@token_required
def stats(user):
    """Fetch user stats"""
    stats, err = user_model.get_user_stats(user["id"])
    if err:
        return jsonify({
            "success": False,
            "message": err
        }), 400
    return jsonify({
        "success": True,
        "stats": stats
    }), 200

# ------------------------------------------------------------
# Setup Function
# ------------------------------------------------------------
def setup_auth_routes(app):
    app.register_blueprint(auth_bp, url_prefix="/auth")
