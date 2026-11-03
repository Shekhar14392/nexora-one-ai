import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..security import audit, require_roles

router = APIRouter(prefix="/licenses", tags=["licenses"])
admin = APIRouter(prefix="/admin/licenses", tags=["licenses"])

def _generate_key(db: Session) -> str:
    while True:
        raw = secrets.token_hex(10).upper()
        key = "NEX-" + "-".join(raw[i:i + 4] for i in range(0, 20, 4))
        if not db.query(models.License).filter(models.License.key == key).first():
            return key

@admin.post("/issue")
def issue_license(data: schemas.LicenseIssueIn, db: Session = Depends(get_db),
                  admin_user: models.User = Depends(require_roles("superadmin"))):
    lic = models.License(key=_generate_key(db), owner_email=(data.owner_email or "").lower(),
                         kind=data.kind, max_activations=data.max_activations,
                         issued_by=admin_user.id,
                         expires_at=datetime.utcnow() + timedelta(days=365))
    db.add(lic); db.commit()
    audit(db, "license.issued", admin_user.id, {"key": lic.key, "kind": data.kind})
    return {"key": lic.key, "kind": lic.kind, "expires_at": lic.expires_at}

@admin.get("")
def list_licenses(db: Session = Depends(get_db)):
    rows = db.query(models.License).order_by(models.License.created_at.desc()).limit(300).all()
    return [{"key": l.key, "kind": l.kind, "status": l.status, "owner_email": l.owner_email,
             "bound_domain": l.bound_domain, "activations": l.activations_used,
             "expires_at": l.expires_at} for l in rows]

@admin.post("/set-status")
def set_status(data: schemas.LicenseSuspendIn, db: Session = Depends(get_db),
               admin_user: models.User = Depends(require_roles("superadmin"))):
    lic = db.query(models.License).filter(models.License.key == data.key).first()
    if not lic:
        raise HTTPException(404, "License not found")
    if data.status not in ("active", "suspended", "expired"):
        raise HTTPException(400, "Invalid status")
    lic.status = data.status
    lic.audit = (lic.audit or []) + [{"at": datetime.utcnow().isoformat(), "action": f"set_status:{data.status}"}]
    audit(db, "license.status_changed", admin_user.id, {"key": data.key, "status": data.status})
    db.commit()
    return {"ok": True}

@admin.post("/transfer")
def transfer(data: schemas.LicenseTransferIn, db: Session = Depends(get_db),
             admin_user: models.User = Depends(require_roles("superadmin"))):
    lic = db.query(models.License).filter(models.License.key == data.key).first()
    if not lic:
        raise HTTPException(404, "License not found")
    lic.transferred_from = lic.owner_email or ""
    lic.owner_email = data.new_owner_email.lower()
    lic.audit = (lic.audit or []) + [{"at": datetime.utcnow().isoformat(), "action": "transfer",
                                      "from": lic.transferred_from, "to": lic.owner_email}]
    audit(db, "license.transferred", admin_user.id, {"key": data.key})
    db.commit()
    return {"ok": True}

@router.post("/activate")
def activate(data: schemas.LicenseActivateIn, db: Session = Depends(get_db)):
    lic = db.query(models.License).filter(models.License.key == data.key).first()
    if not lic:
        raise HTTPException(404, "License key not found")
    if lic.status == "suspended":
        raise HTTPException(403, "License is suspended")
    if lic.expires_at and lic.expires_at < datetime.utcnow():
        raise HTTPException(403, "License expired")
    if lic.bound_domain and lic.bound_domain != data.domain:
        raise HTTPException(409, f"License is already bound to {lic.bound_domain}; request a transfer from the vendor")
    if not lic.bound_domain:
        if lic.activations_used >= lic.max_activations:
            raise HTTPException(409, "Activation limit reached")
        lic.bound_domain = data.domain
    lic.status = "active"
    lic.activations_used += 1
    lic.audit = (lic.audit or []) + [{"at": datetime.utcnow().isoformat(), "action": "activate", "domain": data.domain}]
    db.commit()
    return {"ok": True, "status": lic.status, "bound_domain": lic.bound_domain, "expires_at": lic.expires_at}

@router.get("/verify/{key}")
def verify(key: str, db: Session = Depends(get_db)):
    lic = db.query(models.License).filter(models.License.key == key).first()
    if not lic:
        return {"valid": False, "reason": "not_found"}
    valid = lic.status == "active" and (lic.expires_at is None or lic.expires_at >= datetime.utcnow())
    return {"valid": valid, "status": lic.status, "kind": lic.kind,
            "bound_domain": lic.bound_domain, "expires_at": lic.expires_at}
