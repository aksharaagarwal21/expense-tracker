import bcrypt
import jwt
from datetime import datetime, timezone
from flask import Blueprint, request
from config.database import db
from models import User, RefreshToken
from middleware.auth import generate_tokens, decode_token, jwt_required
from utils.helpers import success, error

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    d = request.get_json(silent=True) or {}
    name  = (d.get("name") or "").strip()
    email = (d.get("email") or "").strip().lower()
    pw    = d.get("password") or ""
    if not name or not email or not pw:
        return error("name, email and password are required")
    if len(pw) < 6:
        return error("Password must be at least 6 characters")
    if User.query.filter_by(email=email).first():
        return error("Email already registered", 409)
    hashed = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
    user   = User(name=name, email=email, password=hashed)
    db.session.add(user)
    db.session.commit()
    tokens = generate_tokens(user.id)
    _save_refresh(user.id, tokens["refresh_token"])
    return success({"user": user.to_dict(), "tokens": tokens}, "Account created", 201)


@auth_bp.route("/login", methods=["POST"])
def login():
    d = request.get_json(silent=True) or {}
    email = (d.get("email") or "").strip().lower()
    pw    = d.get("password") or ""
    if not email or not pw:
        return error("email and password are required")
    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.checkpw(pw.encode(), user.password.encode()):
        return error("Invalid email or password", 401)
    if not user.is_active:
        return error("Account disabled", 403)
    tokens = generate_tokens(user.id)
    _save_refresh(user.id, tokens["refresh_token"])
    return success({"user": user.to_dict(), "tokens": tokens}, "Login successful")


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    d  = request.get_json(silent=True) or {}
    rt = d.get("refresh_token") or ""
    if not rt:
        return error("refresh_token required")
    try:
        payload = decode_token(rt, "refresh")
    except jwt.ExpiredSignatureError:
        return error("Refresh token expired", 401)
    except jwt.InvalidTokenError as e:
        return error(str(e), 401)
    rec = RefreshToken.query.filter_by(token=rt, revoked=False).first()
    if not rec:
        return error("Token revoked", 401)
    user = User.query.get(int(payload["sub"]))
    if not user:
        return error("User not found", 401)
    rec.revoked = True
    tokens = generate_tokens(user.id)
    _save_refresh(user.id, tokens["refresh_token"])
    db.session.commit()
    return success({"tokens": tokens}, "Token refreshed")


@auth_bp.route("/logout", methods=["POST"])
@jwt_required
def logout():
    d  = request.get_json(silent=True) or {}
    rt = d.get("refresh_token")
    if rt:
        rec = RefreshToken.query.filter_by(token=rt).first()
        if rec:
            rec.revoked = True
            db.session.commit()
    return success(message="Logged out")


@auth_bp.route("/me", methods=["GET"])
@jwt_required
def get_me():
    return success({"user": request.current_user.to_dict()})


@auth_bp.route("/me", methods=["PUT"])
@jwt_required
def update_me():
    user = request.current_user
    d    = request.get_json(silent=True) or {}
    if d.get("name"):     user.name     = d["name"].strip()
    if d.get("currency"): user.currency = d["currency"]
    db.session.commit()
    return success({"user": user.to_dict()}, "Profile updated")


@auth_bp.route("/change-password", methods=["PUT"])
@jwt_required
def change_password():
    user = request.current_user
    d    = request.get_json(silent=True) or {}
    curr = d.get("current_password") or ""
    new  = d.get("new_password") or ""
    if not curr or not new:
        return error("current_password and new_password required")
    if len(new) < 6:
        return error("New password must be at least 6 characters")
    if not bcrypt.checkpw(curr.encode(), user.password.encode()):
        return error("Current password incorrect", 401)
    user.password = bcrypt.hashpw(new.encode(), bcrypt.gensalt()).decode()
    db.session.commit()
    return success(message="Password changed")


def _save_refresh(user_id, token):
    from flask import current_app
    exp = datetime.now(timezone.utc) + current_app.config["JWT_REFRESH_TOKEN_EXPIRES"]
    db.session.add(RefreshToken(user_id=user_id, token=token, expires_at=exp))
    db.session.commit()
