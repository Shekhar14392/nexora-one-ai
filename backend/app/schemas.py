from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, EmailStr, Field

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = ""
    organization_name: str = "My Business"

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    verification_token: Optional[str] = None
    email_sent: Optional[bool] = None
    role: str
    email_verified: bool

class RefreshIn(BaseModel):
    refresh_token: str

class EmailIn(BaseModel):
    email: EmailStr

class ResetIn(BaseModel):
    token: str
    new_password: str = Field(min_length=10, max_length=128)

class VerifyIn(BaseModel):
    token: str

class MeOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    email_verified: bool
    organization_id: Optional[str]
    language: str

class PlanIn(BaseModel):
    code: str
    name: str
    price_monthly: float = 0.0
    price_yearly: float = 0.0
    currency: str = "USD"
    limits: dict[str, Any] = {}
    is_active: bool = True

class CheckoutIn(BaseModel):
    plan_code: str
    period: str = "monthly"
    provider: str = "razorpay"  # razorpay | paypal

class WebhookIn(BaseModel):
    model_config = {"extra": "allow"}

class LicenseIssueIn(BaseModel):
    kind: str = "commercial"
    owner_email: Optional[EmailStr] = None
    max_activations: int = 1
    notes: str = ""

class LicenseActivateIn(BaseModel):
    key: str
    domain: str

class LicenseSuspendIn(BaseModel):
    key: str
    status: str  # active | suspended | expired

class LicenseTransferIn(BaseModel):
    key: str
    new_owner_email: EmailStr

class CampaignIn(BaseModel):
    name: str
    channel: str = "multi"
    objective: str = ""

class ContentIn(BaseModel):
    kind: str = "blog"
    topic: str
    language: str = "en"
    brand_voice: str = ""

class LeadIn(BaseModel):
    name: str = ""
    email: Optional[EmailStr] = None
    phone: str = ""
    source: str = "website"
    notes: str = ""

class LeadStageIn(BaseModel):
    stage: str
