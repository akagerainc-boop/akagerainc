"""
Authentication utilities — password hashing, signed tokens, FastAPI dependencies.

Self-contained: uses only the standard library (hashlib/hmac/base64/json) so it works
without extra packages. PyJWT / passlib are listed in requirements.txt for teams that
prefer them, but are NOT required at runtime.
"""
import os
import hmac
import json
import base64
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from models import User

JWT_SECRET = os.getenv("JWT_SECRET", "dev-insecure-secret-change-me")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "168"))

ADMIN_ROLES = {"admin", "super_admin"}
STAFF_ROLES = {"staff", "developer", "support", "content_manager", "admin", "super_admin"}

_bearer = HTTPBearer(auto_error=False)


# ----------------------------- password hashing -----------------------------
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 240_000)
    return "pbkdf2_sha256$240000$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def verify_password(password: str, stored: Optional[str]) -> bool:
    if not stored:
        return False
    try:
        algo, iters, salt_b64, hash_b64 = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iters))
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


# ----------------------------- signed tokens -----------------------------
def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def create_token(payload: dict, expires_hours: int = JWT_EXPIRE_HOURS) -> str:
    body = dict(payload)
    body["exp"] = int((datetime.utcnow() + timedelta(hours=expires_hours)).timestamp())
    body["iat"] = int(datetime.utcnow().timestamp())
    raw = _b64url(json.dumps(body, separators=(",", ":")).encode())
    sig = _b64url(hmac.new(JWT_SECRET.encode(), raw.encode(), hashlib.sha256).digest())
    return f"{raw}.{sig}"


def decode_token(token: str) -> Optional[dict]:
    try:
        raw, sig = token.split(".")
        expected = _b64url(hmac.new(JWT_SECRET.encode(), raw.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        body = json.loads(_b64url_decode(raw))
        if int(body.get("exp", 0)) < int(datetime.utcnow().timestamp()):
            return None
        return body
    except Exception:
        return None


# ----------------------------- FastAPI dependencies -----------------------------
def _extract_token(creds: Optional[HTTPAuthorizationCredentials]) -> Optional[str]:
    if creds and creds.scheme.lower() == "bearer":
        return creds.credentials
    return None


def get_optional_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    token = _extract_token(creds)
    if not token:
        return None
    data = decode_token(token)
    if not data or "sub" not in data:
        return None
    user = db.query(User).filter(User.id == int(data["sub"])).first()
    if user and not user.is_active:
        return None
    return user


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    user = get_optional_user(creds, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def require_role(*roles: str):
    allowed = set(roles) if roles else ADMIN_ROLES

    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _dep


def get_admin_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    user = get_optional_user(creds, db)
    if not user or user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
