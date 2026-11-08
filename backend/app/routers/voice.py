from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .. import models, voice_provider
from ..database import get_db
from ..security import get_current_user

router = APIRouter(prefix="/voice", tags=["voice-agent"])

class AgentIn(BaseModel):
    name: str
    language: str = "en"
    script: str = ""

class CallIn(BaseModel):
    to_phone: str

def _org_id(user: models.User) -> str:
    if not user.organization_id:
        raise HTTPException(400, "User has no organization")
    return user.organization_id

@router.post("/agents", status_code=201)
def create_agent(data: AgentIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    agent = models.VoiceAgent(organization_id=_org_id(user), created_by=user.id,
                              name=data.name, language=data.language, script=data.script)
    db.add(agent); db.commit()
    return {"id": agent.id, "name": agent.name, "language": agent.language}

@router.get("/agents")
def list_agents(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(models.VoiceAgent).filter(models.VoiceAgent.organization_id == _org_id(user))
              .order_by(models.VoiceAgent.created_at.desc()).all())
    return [{"id": a.id, "name": a.name, "language": a.language, "is_active": a.is_active} for a in rows]

@router.post("/agents/{agent_id}/calls", status_code=201)
def queue_call(agent_id: str, data: CallIn, user: models.User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    agent = db.get(models.VoiceAgent, agent_id)
    if not agent or agent.organization_id != _org_id(user):
        raise HTTPException(404, "Agent not found")
    if not data.to_phone.startswith("+") or not data.to_phone[1:].isdigit():
        raise HTTPException(400, "Phone must be E.164 format, e.g. +919876543210")
    call = models.VoiceCall(agent_id=agent.id, organization_id=agent.organization_id,
                            to_phone=data.to_phone, status="queued")
    db.add(call); db.commit()
    return {"id": call.id, "status": call.status}

@router.post("/calls/{call_id}/dial")
def dial(call_id: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Attempts the call through the configured voice provider ONLY. With no provider
    configured the call is NOT dialed: the status is recorded as not_configured with an
    honest note. The platform never reports a dial that did not happen."""
    call = db.get(models.VoiceCall, call_id)
    if not call or call.organization_id != _org_id(user):
        raise HTTPException(404, "Call not found")
    agent = db.get(models.VoiceAgent, call.agent_id)
    result = voice_provider.place_call(call.to_phone, agent.script if agent else "")
    if result.get("dialed"):
        call.status = "dialing"
        call.provider = settings_provider()
        call.provider_ref = result.get("provider_ref", "")
        call.outcome_note = "Call handed to the voice provider; awaiting provider status."
    else:
        call.status = "not_configured" if result.get("reason") == "voice_provider_not_configured" else "failed"
        call.outcome_note = (f"Call was NOT dialed (reason: {result.get('reason')}). "
                             "Configure a voice provider on this deployment to dial.")
    db.commit()
    return {"id": call.id, "status": call.status, "note": call.outcome_note}

def settings_provider() -> str:
    from ..config import settings
    return settings.voice_provider

@router.get("/calls")
def list_calls(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(models.VoiceCall).filter(models.VoiceCall.organization_id == _org_id(user))
              .order_by(models.VoiceCall.created_at.desc()).all())
    return [{"id": c.id, "to_phone": c.to_phone, "status": c.status,
             "provider_ref": c.provider_ref} for c in rows]
