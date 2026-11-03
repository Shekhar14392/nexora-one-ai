"""Email delivery provider interface.

NEXORA sends mail through the SMTP provider configured in the environment.
Without SMTP settings the platform does NOT claim to have sent anything:
calls return {"sent": False, "reason": "smtp_not_configured"} and the caller
logs the outcome. No third-party API keys are hardcoded.
"""
import logging, smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from .config import settings

log = logging.getLogger("nexora.emailer")

def _configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_user and settings.smtp_password)

def send_email(to_email: str, subject: str, body_text: str, body_html: str | None = None) -> dict:
    if not _configured():
        log.info("SMTP not configured; email to %s not sent (subject=%r)", to_email, subject)
        return {"sent": False, "reason": "smtp_not_configured"}
    msg = MIMEMultipart("alternative")
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body_text, "plain"))
    if body_html:
        msg.attach(MIMEText(body_html, "html"))
    try:
        if settings.smtp_port == 465:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20)
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)
            server.starttls(context=ssl.create_default_context())
        with server:
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(msg["From"], [to_email], msg.as_string())
        return {"sent": True}
    except Exception as exc:  # provider failure is data, never a crash
        log.warning("SMTP send failed: %s", exc)
        return {"sent": False, "reason": "smtp_send_failed"}

def verification_email(to_email: str, token: str) -> dict:
    base = settings.frontend_origin.rstrip("/")
    link = f"{base}/verify?token={token}"
    return send_email(
        to_email,
        "Verify your NEXORA AI account",
        f"Welcome to NEXORA AI.\n\nConfirm your email address: {link}\n\n"
        "If you did not create this account, ignore this message.",
        f'<p>Welcome to NEXORA AI.</p><p><a href="{link}">Confirm your email address</a></p>',
    )

def recovery_email(to_email: str, token: str) -> dict:
    base = settings.frontend_origin.rstrip("/")
    link = f"{base}/reset-password?token={token}"
    return send_email(
        to_email,
        "Reset your NEXORA AI password",
        f"A password reset was requested for your NEXORA AI account.\n\n{link}\n\n"
        "If this was not you, ignore this message and your password stays unchanged.",
    )
