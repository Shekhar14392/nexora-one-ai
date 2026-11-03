from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..security import audit, get_current_user, require_roles

router = APIRouter(prefix="/marketing", tags=["marketing"])
seo_router = APIRouter(prefix="/seo", tags=["seo"])
crm_router = APIRouter(prefix="/crm", tags=["crm"])

def _org_id(user: models.User) -> str:
    if not user.organization_id:
        raise HTTPException(400, "User has no organization")
    return user.organization_id

# ---------------- campaigns ----------------
@router.get("/campaigns")
def list_campaigns(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(models.Campaign).filter(models.Campaign.organization_id == _org_id(user))
              .order_by(models.Campaign.created_at.desc()).all())
    return [{"id": c.id, "name": c.name, "channel": c.channel, "status": c.status,
             "objective": c.objective, "strategy": c.strategy, "schedule_at": c.schedule_at} for c in rows]

@router.post("/campaigns", status_code=201)
def create_campaign(data: schemas.CampaignIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = models.Campaign(organization_id=_org_id(user), created_by=user.id,
                        name=data.name, channel=data.channel, objective=data.objective,
                        strategy={"note": "Run POST /marketing/campaigns/{id}/strategy to generate an AI strategy."})
    db.add(c); db.commit()
    return {"id": c.id, "status": c.status}

@router.post("/campaigns/{campaign_id}/strategy")
def generate_strategy(campaign_id: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.get(models.Campaign, campaign_id)
    if not c or c.organization_id != _org_id(user):
        raise HTTPException(404, "Campaign not found")
    prompt = (f"You are a senior marketing strategist. Business objective: {c.objective or c.name}. "
              f"Channel: {c.channel}. Produce a compact JSON plan with keys: audience, positioning, "
              f"channels_plan (list), weekly_cadence, kpis, first_3_actions.")
    result = _ai_generate(prompt, user, db)
    c.strategy = result if isinstance(result, dict) else {"text": str(result)}
    c.status = "scheduled"
    audit(db, "marketing.strategy_generated", user.id, {"campaign": c.id})
    db.commit()
    return {"strategy": c.strategy}

# ---------------- content studio ----------------
@router.get("/content")
def list_content(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(models.ContentItem).filter(models.ContentItem.organization_id == _org_id(user))
              .order_by(models.ContentItem.created_at.desc()).all())
    return [{"id": x.id, "kind": x.kind, "topic": x.topic, "status": x.status,
             "language": x.language, "created_at": x.created_at} for x in rows]

@router.post("/content/generate", status_code=201)
def generate_content(data: schemas.ContentIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    KINDS = {"blog": "Write a structured blog post", "seo_article": "Write an SEO-optimized article",
             "social_caption": "Write social media captions", "ad_copy": "Write advertising copy",
             "product_desc": "Write a product description", "email": "Write a marketing email",
             "hashtags": "Generate relevant hashtags"}
    instruction = KINDS.get(data.kind)
    if not instruction:
        raise HTTPException(400, f"Unsupported content kind; supported: {', '.join(KINDS)}")
    prompt = (f"{instruction} about: {data.topic}. Language: {data.language}. "
              f"Brand voice: {data.brand_voice or 'professional, clear'}. Keep it original and specific.")
    body = _ai_generate(prompt, user, db)
    item = models.ContentItem(organization_id=_org_id(user), created_by=user.id, kind=data.kind,
                              language=data.language, brand_voice=data.brand_voice,
                              topic=data.topic, body=body if isinstance(body, str) else str(body))
    db.add(item); db.commit()
    return {"id": item.id, "body": item.body}

@router.post("/content/{item_id}/approve")
def approve_content(item_id: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(models.ContentItem, item_id)
    if not item or item.organization_id != _org_id(user):
        raise HTTPException(404, "Content not found")
    item.status = "approved"; db.commit()
    return {"ok": True, "status": item.status}

# ---------------- AI provider interface ----------------
def _ai_generate(prompt: str, user: models.User, db: Session) -> object:
    """Calls the configured OpenAI-compatible AI provider. Without credentials it returns a
    graceful template fallback and records usage either way. Never claims a live provider."""
    db.add(models.UsageRecord(user_id=user.id, kind="ai_generation", amount=1,
                              detail={"with_provider": bool(_ai_key())}))
    if _ai_key():
        import httpx
        resp = httpx.post(f"{_ai_base()}/chat/completions",
                          headers={"Authorization": f"Bearer {_ai_key()}"},
                          json={"model": _ai_model(),
                                "messages": [{"role": "system", "content": "You are NEXORA AI, a marketing assistant."},
                                             {"role": "user", "content": prompt}],
                                "temperature": 0.7}, timeout=60)
        if resp.status_code < 300:
            return resp.json()["choices"][0]["message"]["content"]
    # Template fallback so the platform stays usable without external AI credentials.
    topic = prompt
    return (f"[NEXORA AI template draft - no external AI provider configured]\n\n"
            f"{topic}\n\n1) Hook: state the single biggest outcome for the reader in one line.\n"
            f"2) Problem: name the pain your audience feels today.\n"
            f"3) Solution: what you offer, in plain words.\n"
            f"4) Proof: one concrete result, number or testimonial.\n"
            f"5) Call to action: one clear next step.")

def _ai_key() -> str:
    from ..config import settings
    return settings.ai_api_key

def _ai_base() -> str:
    from ..config import settings
    return settings.ai_api_base.rstrip("/")

def _ai_model() -> str:
    from ..config import settings
    return settings.ai_model

# ---------------- SEO engine ----------------
class SeoAuditIn(BaseModel):
    url: str

@seo_router.post("/audit")
def audit_site(data: SeoAuditIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    import httpx
    from bs4 import BeautifulSoup  # noqa - imported lazily; see requirements-aux
    url = data.url if data.url.startswith("http") else f"https://{data.url}"
    findings, score = [], 100
    try:
        resp = httpx.get(url, timeout=20, follow_redirects=True, headers={"User-Agent": "NEXORA-AI-Auditor/1.0"})
    except Exception:
        raise HTTPException(502, f"Could not fetch {url}; check the URL or network access")
    html = resp.text
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("title")
    if not title or not (title.string or "").strip():
        findings.append({"check": "title", "ok": False, "detail": "Missing <title> tag"}); score -= 15
    else:
        findings.append({"check": "title", "ok": True, "detail": title.string.strip()[:120]})
    desc = soup.find("meta", attrs={"name": "description"})
    if not desc or not (desc.get("content") or "").strip():
        findings.append({"check": "meta_description", "ok": False, "detail": "Missing meta description"}); score -= 15
    h1s = soup.find_all("h1")
    if len(h1s) != 1:
        findings.append({"check": "h1_count", "ok": False, "detail": f"Found {len(h1s)} <h1> tags; expected exactly 1"}); score -= 10
    robots = httpx.get(url.rstrip("/") + "/robots.txt", timeout=10)
    findings.append({"check": "robots_txt", "ok": robots.status_code == 200,
                     "detail": "robots.txt reachable" if robots.status_code == 200 else "robots.txt missing"})
    score -= 5 if robots.status_code != 200 else 0
    https_ok = url.startswith("https://")
    findings.append({"check": "https", "ok": https_ok, "detail": "HTTPS" if https_ok else "Not HTTPS"}); score -= 20 if not https_ok else 0
    report = models.SeoReport(organization_id=_org_id(user), url=url, score=max(score, 0), findings=findings)
    db.add(report)
    db.add(models.UsageRecord(user_id=user.id, kind="seo_audit", amount=1))
    db.commit()
    return {"id": report.id, "url": url, "score": report.score, "findings": findings}

@seo_router.get("/reports")
def list_reports(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(models.SeoReport).filter(models.SeoReport.organization_id == _org_id(user))
              .order_by(models.SeoReport.created_at.desc()).limit(50).all())
    return [{"id": r.id, "url": r.url, "score": r.score, "created_at": r.created_at} for r in rows]

# ---------------- CRM / leads ----------------
@crm_router.get("/leads")
def list_leads(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(models.Lead).filter(models.Lead.organization_id == _org_id(user))
              .order_by(models.Lead.created_at.desc()).all())
    return [{"id": l.id, "name": l.name, "email": l.email, "phone": l.phone,
             "source": l.source, "score": l.score, "stage": l.stage} for l in rows]

@crm_router.post("/leads", status_code=201)
def create_lead(data: schemas.LeadIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    score = 20 + (30 if data.email else 0) + (20 if data.phone else 0) + (10 if data.source == "referral" else 0)
    lead = models.Lead(organization_id=_org_id(user), name=data.name, email=data.email,
                       phone=data.phone, source=data.source, notes=data.notes, score=score,
                       owner_id=user.id)
    db.add(lead)
    db.add(models.Notification(user_id=user.id, kind="lead", title="New lead captured",
                               body=data.name or data.email or "New lead"))
    db.commit()
    return {"id": lead.id, "score": lead.score}

@crm_router.patch("/leads/{lead_id}/stage")
def set_stage(lead_id: str, data: schemas.LeadStageIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.get(models.Lead, lead_id)
    if not lead or lead.organization_id != _org_id(user):
        raise HTTPException(404, "Lead not found")
    if data.stage not in ("new", "qualified", "contacted", "won", "lost"):
        raise HTTPException(400, "Invalid stage")
    lead.stage = data.stage; db.commit()
    return {"ok": True}

# ---------------- analytics ----------------
class AnalyticsIn(BaseModel):
    pass

@router.get("/analytics")
def analytics(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    org = _org_id(user)
    return {
        "campaigns": db.query(func.count(models.Campaign.id)).filter(models.Campaign.organization_id == org).scalar() or 0,
        "content_items": db.query(func.count(models.ContentItem.id)).filter(models.ContentItem.organization_id == org).scalar() or 0,
        "leads": db.query(func.count(models.Lead.id)).filter(models.Lead.organization_id == org).scalar() or 0,
        "won_leads": db.query(func.count(models.Lead.id)).filter(models.Lead.organization_id == org, models.Lead.stage == "won").scalar() or 0,
        "seo_reports": db.query(func.count(models.SeoReport.id)).filter(models.SeoReport.organization_id == org).scalar() or 0,
    }
