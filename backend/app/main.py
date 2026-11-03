from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from . import models
from .config import settings
from .database import Base, SessionLocal, engine
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .ratelimit import limiter
from .routers import admin, auth, billing, licenses, marketing, misc
from .security import hash_password

app = FastAPI(title=settings.app_name, version="1.0.0",
              description="NEXORA AI - autonomous AI marketing & business automation platform (API)")

app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(billing.router)
app.include_router(licenses.router)
app.include_router(licenses.admin)
app.include_router(marketing.router)
app.include_router(marketing.seo_router)
app.include_router(marketing.crm_router)
app.include_router(misc.router)

@app.on_event("startup")
def seed():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        # Plans
        for code, name, m, y, limits in billing.PLAN_SEED:
            if not db.query(models.Plan).filter(models.Plan.code == code).first():
                db.add(models.Plan(code=code, name=name, price_monthly=m, price_yearly=y, limits=limits))
        # Super admin is created ONLY from environment credentials. There is no default password.
        if settings.admin_email and settings.admin_password:
            existing = db.query(models.User).filter(models.User.email == settings.admin_email.lower()).first()
            if not existing:
                db.add(models.User(email=settings.admin_email.lower(),
                                   hashed_password=hash_password(settings.admin_password),
                                   full_name="Platform Owner", role="superadmin", email_verified=True))
        db.commit()
    finally:
        db.close()

@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name, "time": datetime.utcnow().isoformat()}
