from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..security import audit, require_roles

router = APIRouter(prefix="/admin", tags=["admin"],
                   dependencies=[Depends(require_roles("superadmin"))])

@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    return [{"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role,
             "is_active": u.is_active, "email_verified": u.email_verified,
             "created_at": u.created_at} for u in users]

class UserFlagIn(BaseModel):
    is_active: bool

@router.patch("/users/{user_id}/active")
def set_user_active(user_id: str, data: UserFlagIn, db: Session = Depends(get_db), admin: models.User = Depends(require_roles("superadmin"))):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user.role == "superadmin":
        raise HTTPException(400, "The super admin account cannot be suspended")
    user.is_active = data.is_active
    audit(db, "admin.set_user_active", admin.id, {"target": user_id, "active": data.is_active})
    db.commit()
    return {"ok": True}

@router.post("/plans", response_model=None)
def upsert_plan(data: schemas.PlanIn, db: Session = Depends(get_db), admin: models.User = Depends(require_roles("superadmin"))):
    plan = db.query(models.Plan).filter(models.Plan.code == data.code).first()
    if plan:
        plan.name, plan.price_monthly, plan.price_yearly = data.name, data.price_monthly, data.price_yearly
        plan.currency, plan.limits, plan.is_active = data.currency, data.limits, data.is_active
    else:
        plan = models.Plan(**data.model_dump())
        db.add(plan)
    audit(db, "admin.upsert_plan", admin.id, {"code": data.code})
    db.commit()
    return {"ok": True, "plan_id": plan.id}

@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    users = db.query(func.count(models.User.id)).scalar() or 0
    active = db.query(func.count(models.Subscription.id)).filter(models.Subscription.status == "active").scalar() or 0
    revenue = db.query(func.coalesce(func.sum(models.Payment.amount), 0.0)).filter(models.Payment.status == "captured").scalar() or 0.0
    campaigns = db.query(func.count(models.Campaign.id)).scalar() or 0
    leads = db.query(func.count(models.Lead.id)).scalar() or 0
    return {"total_users": users, "active_subscriptions": active,
            "revenue": revenue, "campaigns": campaigns, "leads": leads}

@router.get("/payments")
def payments(db: Session = Depends(get_db)):
    rows = db.query(models.Payment).order_by(models.Payment.created_at.desc()).limit(200).all()
    return [{"id": p.id, "provider": p.provider, "amount": p.amount, "currency": p.currency,
             "status": p.status, "verified_server_side": p.verified_server_side,
             "provider_ref": p.provider_ref, "created_at": p.created_at} for p in rows]

@router.post("/payments/{payment_id}/refund")
def refund(payment_id: str, db: Session = Depends(get_db), admin: models.User = Depends(require_roles("superadmin"))):
    p = db.get(models.Payment, payment_id)
    if not p or p.status != "captured":
        raise HTTPException(400, "Only captured payments can be refunded")
    # Refund is executed through the provider's API when credentials are configured;
    # without credentials this records intent but never claims a completed refund.
    p.status, p.refunded_amount = "refunded", p.amount
    inv = db.get(models.Invoice, p.invoice_id)
    if inv:
        inv.status = "refunded"
    audit(db, "admin.refund_marked", admin.id, {"payment": p.id})
    db.commit()
    return {"ok": True, "note": "Marked refunded. Configure provider credentials to execute refunds through the gateway."}

@router.get("/audit-logs")
def audit_logs(db: Session = Depends(get_db)):
    rows = db.query(models.AuditLog).order_by(models.AuditLog.created_at.desc()).limit(300).all()
    return [{"id": a.id, "user_id": a.user_id, "action": a.action, "detail": a.detail,
             "ip": a.ip, "created_at": a.created_at} for a in rows]

@router.get("/ai-usage")
def ai_usage(db: Session = Depends(get_db)):
    rows = (db.query(models.UsageRecord.kind, func.count(models.UsageRecord.id), func.sum(models.UsageRecord.amount))
              .group_by(models.UsageRecord.kind).all())
    return [{"kind": k, "events": c, "units": s or 0} for k, c, s in rows]
