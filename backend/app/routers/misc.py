from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import models
from ..database import get_db
from ..security import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("")
def my_notifications(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(models.Notification).filter(models.Notification.user_id == user.id)
              .order_by(models.Notification.created_at.desc()).limit(100).all())
    return [{"id": n.id, "kind": n.kind, "title": n.title, "body": n.body, "read": n.read} for n in rows]
