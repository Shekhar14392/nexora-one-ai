from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .. import models
from ..database import get_db
from ..security import audit, get_current_user

router = APIRouter(prefix="/social", tags=["social-media"])

PLATFORMS = ["facebook", "instagram", "youtube", "linkedin", "tiktok", "pinterest", "x"]

class PostIn(BaseModel):
    platform: str
    body: str
    scheduled_at: datetime | None = None

def _org_id(user: models.User) -> str:
    if not user.organization_id:
        raise HTTPException(400, "User has no organization")
    return user.organization_id

@router.get("/accounts")
def accounts(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Connection status comes from real authorized connections only.
    A platform with no granted OAuth connection is reported as not_connected - never as ready."""
    rows = (db.query(models.SocialAccount)
              .filter(models.SocialAccount.organization_id == _org_id(user),
                      models.SocialAccount.oauth_granted == True).all())  # noqa: E712
    granted = {r.platform for r in rows}
    return [{"platform": p, "status": "connected" if p in granted else "not_connected"} for p in PLATFORMS]

@router.post("/posts", status_code=201)
def create_post(data: PostIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.platform not in PLATFORMS:
        raise HTTPException(400, f"Unsupported platform; supported: {', '.join(PLATFORMS)}")
    post = models.SocialPost(organization_id=_org_id(user), created_by=user.id,
                             platform=data.platform, body=data.body,
                             scheduled_at=data.scheduled_at,
                             status="scheduled" if data.scheduled_at else "draft")
    db.add(post); db.commit()
    return {"id": post.id, "status": post.status}

@router.post("/posts/{post_id}/publish")
def publish(post_id: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Publishes through the platform's official API ONLY when an authorized connection exists.
    With no connection the post is marked export_ready: the copy is handed to the user to post
    themselves. The platform never bypasses a platform's permissions and never claims a publish
    that did not happen."""
    post = db.get(models.SocialPost, post_id)
    if not post or post.organization_id != _org_id(user):
        raise HTTPException(404, "Post not found")
    conn = (db.query(models.SocialAccount)
              .filter(models.SocialAccount.organization_id == post.organization_id,
                      models.SocialAccount.platform == post.platform,
                      models.SocialAccount.oauth_granted == True).first())  # noqa: E712
    if not conn:
        post.status = "export_ready"
        db.commit()
        return {"status": "export_ready",
                "note": f"No authorized {post.platform} connection on this deployment. The post is ready to copy and post; connect the official {post.platform} account to publish from here."}
    # Official-API publish path: implemented per provider when credentials are configured.
    raise HTTPException(501, f"Official {post.platform} publishing requires configured provider credentials on this deployment; the post stays export_ready until then.")

@router.get("/posts")
def list_posts(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(models.SocialPost).filter(models.SocialPost.organization_id == _org_id(user))
              .order_by(models.SocialPost.created_at.desc()).all())
    return [{"id": p.id, "platform": p.platform, "status": p.status, "scheduled_at": p.scheduled_at} for p in rows]
