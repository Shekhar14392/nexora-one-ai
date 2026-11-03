import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from .. import models, schemas
from ..config import settings
from ..database import get_db
from fastapi import Request
from ..ratelimit import limiter
from ..emailer import recovery_email, verification_email
from ..security import (audit, create_access_token, create_refresh_token,
                        decode_token, get_current_user, hash_password,
                        verify_password)

router = APIRouter(prefix="/auth", tags=["auth"])

def _issue_tokens(user: models.User) -> schemas.TokenOut:
    return schemas.TokenOut(access_token=create_access_token(user.id),
                            refresh_token=create_refresh_token(user.id),
                            role=user.role, email_verified=user.email_verified)

@router.post("/register", response_model=schemas.TokenOut, status_code=201)
def register(request: Request, data: schemas.RegisterIn, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == data.email.lower()).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    org = models.Organization(name=data.organization_name)
    db.add(org); db.flush()
    user = models.User(email=data.email.lower(), hashed_password=hash_password(data.password),
                       full_name=data.full_name, organization_id=org.id,
                       verification_token=secrets.token_hex(16))
    db.add(user); db.commit()
    # NOTE: email sending is a provider interface (see /docs); the token is returned in
    # development so verification is testable without an SMTP provider configured.
    audit(db, "auth.register", user.id, {"email": user.email})
    tokens = _issue_tokens(user)
    if settings.environment == "development":
        tokens.verification_token = user.verification_token if settings.environment == "development" else None
        delivery = verification_email(user.email, user.verification_token)
        tokens.email_sent = bool(delivery.get("sent"))
    return tokens

@router.post("/login", response_model=schemas.TokenOut)
def login(request: Request, data: schemas.LoginIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == data.email.lower()).first()
    if not user or not verify_password(data.password, user.hashed_password) or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    audit(db, "auth.login", user.id)
    return _issue_tokens(user)

@router.post("/refresh", response_model=schemas.TokenOut)
def refresh(data: schemas.RefreshIn, db: Session = Depends(get_db)):
    payload = decode_token(data.refresh_token, "refresh")
    user = db.get(models.User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account inactive")
    return _issue_tokens(user)  # rotation: the old refresh token expires with its TTL

@router.get("/me", response_model=schemas.MeOut)
def me(user: models.User = Depends(get_current_user)):
    return schemas.MeOut(id=user.id, email=user.email, full_name=user.full_name,
                         role=user.role, email_verified=user.email_verified,
                         organization_id=user.organization_id, language=user.language)

@router.post("/verify-email")
def verify_email(data: schemas.VerifyIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.verification_token == data.token).first()
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid verification token")
    user.email_verified = True; user.verification_token = None
    db.query(models.Plan).filter(models.Plan.code == "free")
    db.commit()
    return {"ok": True}

@router.post("/recover")
def recover(data: schemas.EmailIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == data.email.lower()).first()
    # Always report ok: never reveal whether an email exists.
    if user:
        user.recovery_token = secrets.token_hex(16)
        recovery_email(user.email, user.recovery_token)
        db.commit()
    return {"ok": True}

@router.post("/reset-password")
def reset_password(data: schemas.ResetIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.recovery_token == data.token).first()
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid recovery token")
    user.hashed_password = hash_password(data.new_password)
    user.recovery_token = None
    audit(db, "auth.reset_password", user.id)
    db.commit()
    return {"ok": True}
