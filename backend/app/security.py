import hashlib, hmac, os, secrets
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from . import models

PBKDF2_ITERATIONS = 260_000

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS).hex()
    return f"pbkdf2${PBKDF2_ITERATIONS}${salt}${digest}"

def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, digest = stored.split("$")
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations)).hex()
        return hmac.compare_digest(candidate, digest)
    except Exception:
        return False

def _token(sub: str, kind: str, minutes: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": sub, "typ": kind, "iat": int(now.timestamp()),
               "exp": int((now + timedelta(minutes=minutes)).timestamp()),
               "jti": secrets.token_hex(8)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def create_access_token(user_id: str) -> str:
    return _token(user_id, "access", settings.access_token_minutes)

def create_refresh_token(user_id: str) -> str:
    return _token(user_id, "refresh", settings.refresh_token_days * 24 * 60)

def decode_token(token: str, expected: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    if payload.get("typ") != expected:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Wrong token type, expected {expected}")
    return payload

bearer = HTTPBearer(auto_error=False)

def get_current_user(request: Request, creds: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> models.User:
    header = request.headers.get("X-Nexora-Access-Token")
    token = creds.credentials if creds else header
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    payload = decode_token(token, "access")
    user = db.get(models.User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account inactive or missing")
    return user

def require_roles(*roles):
    def dep(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed: insufficient role")
        return user
    return dep

def audit(db: Session, action: str, user_id: str | None = None, detail: dict | None = None, ip: str = ""):
    db.add(models.AuditLog(user_id=user_id, action=action, detail=detail or {}, ip=ip or ""))
