"""Outbound voice provider interface.

NEXORA places calls through the voice provider configured in the environment.
Without a configured provider the platform does NOT claim to have dialed anyone:
attempts return {"dialed": False, "reason": "voice_provider_not_configured"} and
the caller records that outcome. No API keys are hardcoded.
"""
import base64, logging, urllib.parse, urllib.request
from .config import settings

log = logging.getLogger("nexora.voice")

def _configured() -> bool:
    return bool(settings.voice_provider and settings.voice_account_sid
                and settings.voice_auth_token and settings.voice_from_number)

def place_call(to_phone: str, script_text: str) -> dict:
    """Place one outbound call reading script_text to the callee (Twilio-compatible REST)."""
    if not _configured():
        log.info("Voice provider not configured; call to %s not dialed", to_phone)
        return {"dialed": False, "reason": "voice_provider_not_configured"}
    if settings.voice_provider != "twilio":
        return {"dialed": False, "reason": "voice_provider_unsupported"}
    twiml = f"<Response><Say>{script_text[:4000]}</Say></Response>"
    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.voice_account_sid}/Calls.json"
    auth = base64.b64encode(
        f"{settings.voice_account_sid}:{settings.voice_auth_token}".encode()).decode()
    data = urllib.parse.urlencode(
        {"To": to_phone, "From": settings.voice_from_number, "Twiml": twiml}).encode()
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Authorization": f"Basic {auth}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
            sid = ""
            if '"sid"' in body:
                sid = body.split('"sid": "')[1].split('"')[0] if '"sid": "' in body else ""
        return {"dialed": True, "provider_ref": sid}
    except Exception as exc:  # provider failure is data, never a crash
        log.warning("Voice provider request failed: %s", exc)
        return {"dialed": False, "reason": "voice_provider_error"}
