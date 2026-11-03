from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from .. import models
from ..database import get_db
from ..emailer import send_email
from ..security import audit, get_current_user

router = APIRouter(prefix="/email", tags=["email-marketing"])

def _org_id(user: models.User) -> str:
    if not user.organization_id:
        raise HTTPException(400, "User has no organization")
    return user.organization_id

class SubscribeIn(BaseModel):
    email: EmailStr
    list_name: str = "default"

class CampaignIn(BaseModel):
    subject: str
    body: str
    list_name: str = "default"

@router.post("/subscribers", status_code=201)
def subscribe(data: SubscribeIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = (db.query(models.EmailSubscriber)
                  .filter(models.EmailSubscriber.organization_id == _org_id(user),
                          models.EmailSubscriber.email == data.email.lower(),
                          models.EmailSubscriber.list_name == data.list_name).first())
    if existing:
        raise HTTPException(409, "Already subscribed")
    sub = models.EmailSubscriber(organization_id=_org_id(user), email=data.email.lower(), list_name=data.list_name)
    db.add(sub); db.commit()
    return {"id": sub.id, "email": sub.email}

@router.get("/subscribers")
def list_subscribers(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(models.EmailSubscriber).filter(models.EmailSubscriber.organization_id == _org_id(user),
                                                    models.EmailSubscriber.unsubscribed == False)  # noqa: E712
              .all())
    return [{"id": s.id, "email": s.email, "list": s.list_name} for s in rows]

@router.post("/campaigns", status_code=201)
def create_campaign(data: CampaignIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = models.EmailCampaign(organization_id=_org_id(user), created_by=user.id,
                             subject=data.subject, body=data.body, list_name=data.list_name)
    db.add(c); db.commit()
    return {"id": c.id, "status": c.status}

@router.post("/campaigns/{campaign_id}/send")
def send_campaign(campaign_id: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Sends through the configured SMTP provider with an unsubscribe footer on every mail.
    Without SMTP configured this reports honestly that nothing was sent."""
    c = db.get(models.EmailCampaign, campaign_id)
    if not c or c.organization_id != _org_id(user):
        raise HTTPException(404, "Campaign not found")
    subs = (db.query(models.EmailSubscriber)
              .filter(models.EmailSubscriber.organization_id == c.organization_id,
                      models.EmailSubscriber.list_name == c.list_name,
                      models.EmailSubscriber.unsubscribed == False).all())  # noqa: E712
    if not subs:
        raise HTTPException(400, "No active subscribers in this list")
    sent = failed = 0
    for s in subs:
        body = (f"{c.body}\n\n---\nYou are receiving this because you subscribed to our list. "
                f"Unsubscribe: {s.unsub_token}")
        result = send_email(s.email, c.subject, body)
        if result.get("sent"):
            sent += 1
        else:
            failed += 1
    c.status = "sent" if failed == 0 else ("sent_with_failures" if sent else "draft")
    c.sent_count, c.failed_count = sent, failed
    audit(db, "email.campaign_sent", user.id, {"campaign": c.id, "sent": sent, "failed": failed,
                                               "smtp_configured": failed != len(subs) or sent > 0})
    db.commit()
    if sent == 0:
        return {"status": c.status, "sent": 0, "failed": failed,
                "note": "No SMTP provider is configured on this deployment, so no mail left the platform."}
    return {"status": c.status, "sent": sent, "failed": failed}

@router.get("/unsubscribe/{token}")
def unsubscribe(token: str, db: Session = Depends(get_db)):
    sub = db.query(models.EmailSubscriber).filter(models.EmailSubscriber.unsub_token == token).first()
    if not sub:
        return {"ok": False}
    sub.unsubscribed = True
    db.commit()
    return {"ok": True}
