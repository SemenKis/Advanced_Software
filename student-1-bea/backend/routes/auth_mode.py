import os
import secrets
import time

import jwt
from flask import Blueprint, jsonify, request

auth_bp = Blueprint("auth_mode", __name__)

TOKEN_LIFETIME_SECONDS = 300
BEARER_PREFIX = "Bearer "

JWT_SECRET = os.getenv("JWT_SECRET") or secrets.token_urlsafe(32)


@auth_bp.post("/auth/token")
def issue_token():

    now = int(time.time())
    token = jwt.encode(
        {"sub": "test-user", "iat": now, "exp": now + TOKEN_LIFETIME_SECONDS},
        JWT_SECRET,
        algorithm="HS256",
    )
    return jsonify({"token": token, "expires_in": TOKEN_LIFETIME_SECONDS}), 200


@auth_bp.get("/auth/verify")
def verify_token():
    header = request.headers.get("Authorization", "")
    if not header.startswith(BEARER_PREFIX):
        return jsonify({"error": "missing bearer token"}), 401

    token = header[len(BEARER_PREFIX):].strip()
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "token expired"}), 401
    except jwt.PyJWTError:
        return jsonify({"error": "invalid token"}), 401

    return jsonify({"sub": decoded["sub"]}), 200