import secrets
import sys
import time
from pathlib import Path

import jwt
import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"

# A fresh random secret per run, so no secret is written into the test file
TEST_SECRET = secrets.token_urlsafe(32)


def make_token(exp_offset_seconds, secret=TEST_SECRET):
    return jwt.encode(
        {"sub": "test-user", "exp": time.time() + exp_offset_seconds},
        secret,
        algorithm="HS256",
    )


# ---- PyJWT behaviour (no app code, no running services) ----

def test_valid_token_decodes():
    token = make_token(60)
    decoded = jwt.decode(token, TEST_SECRET, algorithms=["HS256"])
    assert decoded["sub"] == "test-user"


def test_expired_token_rejected():
    token = make_token(-60)
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(token, TEST_SECRET, algorithms=["HS256"])


def test_invalid_signature_rejected():
    token = make_token(60)
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, secrets.token_urlsafe(32), algorithms=["HS256"])


# ---- the real /auth endpoints in backend/routes/auth_mode.py ----
# These need Flask in the test environment and skip (not fail) without it.

def _auth_client():
    flask = pytest.importorskip("flask")
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    from routes import auth_mode

    app = flask.Flask(__name__)
    app.register_blueprint(auth_mode.auth_bp)
    return app.test_client(), auth_mode


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_issued_token_verifies():
    client, _ = _auth_client()
    issued = client.post("/auth/token")
    assert issued.status_code == 200
    verified = client.get("/auth/verify", headers=_bearer(issued.get_json()["token"]))
    assert verified.status_code == 200
    assert verified.get_json()["sub"] == "test-user"


def test_verify_rejects_missing_token():
    client, _ = _auth_client()
    response = client.get("/auth/verify")
    assert response.status_code == 401


def test_verify_rejects_token_signed_with_other_secret():
    client, _ = _auth_client()
    forged = make_token(60, secret=secrets.token_urlsafe(32))
    response = client.get("/auth/verify", headers=_bearer(forged))
    assert response.status_code == 401
    assert response.get_json()["error"] == "invalid token"


def test_verify_rejects_expired_token():
    client, auth_mode = _auth_client()
    expired = make_token(-60, secret=auth_mode.JWT_SECRET)
    response = client.get("/auth/verify", headers=_bearer(expired))
    assert response.status_code == 401
    assert response.get_json()["error"] == "token expired"