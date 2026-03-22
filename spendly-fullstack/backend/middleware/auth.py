import jwt
from functools import wraps
from datetime import datetime, timezone
from flask import request, jsonify, current_app
from models import User


def generate_tokens(user_id):
    now = datetime.now(timezone.utc)
    cfg = current_app.config
    access  = jwt.encode({"sub": str(user_id), "iat": now,
                           "exp": now + cfg["JWT_ACCESS_TOKEN_EXPIRES"], "type": "access"},
                          cfg["JWT_SECRET_KEY"], algorithm="HS256")
    refresh = jwt.encode({"sub": str(user_id), "iat": now,
                           "exp": now + cfg["JWT_REFRESH_TOKEN_EXPIRES"], "type": "refresh"},
                          cfg["JWT_SECRET_KEY"], algorithm="HS256")
    return {"access_token": access, "refresh_token": refresh,
            "expires_in": int(cfg["JWT_ACCESS_TOKEN_EXPIRES"].total_seconds())}


def decode_token(token, token_type="access"):
    payload = jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
    if payload.get("type") != token_type:
        raise jwt.InvalidTokenError("Wrong token type")
    return payload


def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"success": False, "error": "Missing token"}), 401
        try:
            payload = decode_token(auth.split(" ", 1)[1])
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "error": "Token expired"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"success": False, "error": f"Invalid token: {e}"}), 401
        user = User.query.get(int(payload["sub"]))
        if not user or not user.is_active:
            return jsonify({"success": False, "error": "User not found"}), 401
        request.current_user = user
        return f(*args, **kwargs)
    return decorated
