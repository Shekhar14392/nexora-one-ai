import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "NEXORA AI"
    environment: str = os.getenv("NEXORA_ENV", "development")
    database_url: str = os.getenv("NEXORA_DATABASE_URL", "sqlite:///./nexora.db")
    redis_url: str = os.getenv("NEXORA_REDIS_URL", "redis://localhost:6379/0")
    jwt_secret: str = os.getenv("NEXORA_JWT_SECRET", "")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = int(os.getenv("NEXORA_ACCESS_TOKEN_MINUTES", "30"))
    refresh_token_days: int = int(os.getenv("NEXORA_REFRESH_TOKEN_DAYS", "14"))
    # Super admin is seeded ONLY from environment. There is no public default password.
    admin_email: str = os.getenv("NEXORA_ADMIN_EMAIL", "")
    admin_password: str = os.getenv("NEXORA_ADMIN_PASSWORD", "")
    # Payment providers (verified server-side only; keys never reach the frontend)
    razorpay_key_id: str = os.getenv("NEXORA_RAZORPAY_KEY_ID", "")
    razorpay_key_secret: str = os.getenv("NEXORA_RAZORPAY_KEY_SECRET", "")
    razorpay_webhook_secret: str = os.getenv("NEXORA_RAZORPAY_WEBHOOK_SECRET", "")
    paypal_client_id: str = os.getenv("NEXORA_PAYPAL_CLIENT_ID", "")
    paypal_client_secret: str = os.getenv("NEXORA_PAYPAL_CLIENT_SECRET", "")
    paypal_webhook_id: str = os.getenv("NEXORA_PAYPAL_WEBHOOK_ID", "")
    paypal_api_base: str = os.getenv("NEXORA_PAYPAL_API_BASE", "https://api-m.sandbox.paypal.com")
    # AI provider: any OpenAI-compatible endpoint (open-source or hosted)
    ai_api_key: str = os.getenv("NEXORA_AI_API_KEY", "")
    ai_api_base: str = os.getenv("NEXORA_AI_API_BASE", "https://api.openai.com/v1")
    ai_model: str = os.getenv("NEXORA_AI_MODEL", "gpt-4o-mini")
    frontend_origin: str = os.getenv("NEXORA_FRONTEND_ORIGIN", "http://localhost:3000")
    # Email delivery provider (SMTP). Unconfigured = mail is skipped and logged, never claimed sent.
    smtp_host: str = os.getenv("NEXORA_SMTP_HOST", "")
    smtp_port: int = int(os.getenv("NEXORA_SMTP_PORT", "587"))
    smtp_user: str = os.getenv("NEXORA_SMTP_USER", "")
    smtp_password: str = os.getenv("NEXORA_SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("NEXORA_SMTP_FROM", "")

settings = Settings()

if not settings.jwt_secret:
    raise RuntimeError("NEXORA_JWT_SECRET must be set in the environment (see .env.example)")
