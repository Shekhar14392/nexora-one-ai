import secrets
import uuid
from datetime import datetime
from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, JSON, UniqueConstraint,
                        String, Text, Float, Enum)
from sqlalchemy.orm import relationship
from .database import Base

def uid() -> str:
    return uuid.uuid4().hex

class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"
    id = Column(String(32), primary_key=True, default=uid)
    name = Column(String(200), nullable=False)
    owner_id = Column(String(32), ForeignKey("users.id"), nullable=True)
    plan_overrides = Column(JSON, default=dict)

class User(Base, TimestampMixin):
    __tablename__ = "users"
    id = Column(String(32), primary_key=True, default=uid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200), default="")
    # roles: superadmin | user | reseller
    role = Column(String(20), default="user", nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(64), nullable=True)
    recovery_token = Column(String(64), nullable=True)
    two_factor_secret = Column(String(64), nullable=True)
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    language = Column(String(10), default="en", nullable=False)
    organization_id = Column(String(32), ForeignKey("organizations.id"), nullable=True)
    organization = relationship("Organization", foreign_keys=[organization_id])
    reseller_account = relationship("ResellerAccount", back_populates="user", uselist=False)

class Plan(Base):
    __tablename__ = "plans"
    id = Column(String(32), primary_key=True, default=uid)
    code = Column(String(30), unique=True, nullable=False, index=True)  # free starter pro business enterprise custom
    name = Column(String(100), nullable=False)
    price_monthly = Column(Float, default=0.0)
    price_yearly = Column(Float, default=0.0)
    currency = Column(String(8), default="USD")
    limits = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True, nullable=False)

class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"
    id = Column(String(32), primary_key=True, default=uid)
    user_id = Column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(String(32), ForeignKey("plans.id"), nullable=False)
    period = Column(String(10), default="monthly")  # monthly | yearly
    status = Column(String(20), default="pending", nullable=False)  # pending | active | cancelled | expired
    current_period_end = Column(DateTime, nullable=True)
    provider = Column(String(30), default="none")
    canceled_reason = Column(String(255), default="")

class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    id = Column(String(32), primary_key=True, default=uid)
    invoice_id = Column(String(32), ForeignKey("invoices.id"), nullable=True, index=True)
    user_id = Column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String(30), nullable=False)  # razorpay | paypal | manual
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="USD")
    status = Column(String(20), default="created", nullable=False)  # created | captured | failed | refunded
    provider_ref = Column(String(128), nullable=True, index=True)
    verified_server_side = Column(Boolean, default=False, nullable=False)
    refunded_amount = Column(Float, default=0.0)

class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"
    id = Column(String(32), primary_key=True, default=uid)
    number = Column(String(30), unique=True, nullable=False)
    user_id = Column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="USD")
    description = Column(String(255), default="")
    status = Column(String(20), default="due")  # due | paid | refunded

class License(Base, TimestampMixin):
    __tablename__ = "licenses"
    id = Column(String(32), primary_key=True, default=uid)
    key = Column(String(64), unique=True, nullable=False, index=True)
    owner_email = Column(String(255), nullable=True, index=True)
    kind = Column(String(20), default="subscription")  # commercial | enterprise | reseller | subscription
    status = Column(String(20), default="inactive", nullable=False)  # inactive | active | suspended | expired
    bound_domain = Column(String(255), nullable=True)
    activations_used = Column(Integer, default=0)
    max_activations = Column(Integer, default=1)
    issued_by = Column(String(32), ForeignKey("users.id"), nullable=True)
    transferred_from = Column(String(255), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    notes = Column(Text, default="")
    audit = Column(JSON, default=list)

class Campaign(Base, TimestampMixin):
    __tablename__ = "campaigns"
    id = Column(String(32), primary_key=True, default=uid)
    organization_id = Column(String(32), ForeignKey("organizations.id"), nullable=False, index=True)
    created_by = Column(String(32), ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    channel = Column(String(50), default="multi")  # email | social | seo | multi
    objective = Column(Text, default="")
    status = Column(String(20), default="draft")  # draft | scheduled | running | completed
    strategy = Column(JSON, default=dict)
    schedule_at = Column(DateTime, nullable=True)
    metrics = Column(JSON, default=dict)

class ContentItem(Base, TimestampMixin):
    __tablename__ = "content_items"
    id = Column(String(32), primary_key=True, default=uid)
    organization_id = Column(String(32), ForeignKey("organizations.id"), nullable=False, index=True)
    created_by = Column(String(32), ForeignKey("users.id"), nullable=False)
    kind = Column(String(30), default="blog")  # blog | seo_article | social_caption | ad_copy | product_desc | email | hashtags
    language = Column(String(10), default="en")
    brand_voice = Column(String(255), default="")
    topic = Column(Text, nullable=False)
    body = Column(Text, default="")
    status = Column(String(20), default="draft")  # draft | approved | scheduled | published
    scheduled_at = Column(DateTime, nullable=True)

class Lead(Base, TimestampMixin):
    __tablename__ = "leads"
    id = Column(String(32), primary_key=True, default=uid)
    organization_id = Column(String(32), ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String(200), default="")
    email = Column(String(255), index=True)
    phone = Column(String(40), default="")
    source = Column(String(100), default="website")
    score = Column(Integer, default=0)
    stage = Column(String(30), default="new")  # new | qualified | contacted | won | lost
    notes = Column(Text, default="")
    owner_id = Column(String(32), ForeignKey("users.id"), nullable=False)

class Customer(Base, TimestampMixin):
    __tablename__ = "customers"
    id = Column(String(32), primary_key=True, default=uid)
    organization_id = Column(String(32), ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String(200), default="")
    email = Column(String(255), index=True)
    phone = Column(String(40), default="")
    lifetime_value = Column(Float, default=0.0)
    notes = Column(Text, default="")

class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"
    id = Column(String(32), primary_key=True, default=uid)
    organization_id = Column(String(32), ForeignKey("organizations.id"), nullable=False, index=True)
    channel = Column(String(30), default="web")  # web | voice | whatsapp | email
    ai_generated = Column(Boolean, default=True, nullable=False)  # AI conversations are always labeled
    summary = Column(Text, default="")
    messages = Column(JSON, default=list)

class SeoReport(Base, TimestampMixin):
    __tablename__ = "seo_reports"
    id = Column(String(32), primary_key=True, default=uid)
    organization_id = Column(String(32), ForeignKey("organizations.id"), nullable=False, index=True)
    url = Column(String(500), nullable=False)
    score = Column(Integer, default=0)
    findings = Column(JSON, default=list)

class SocialAccount(Base):
    __tablename__ = "social_accounts"
    id = Column(String(32), primary_key=True, default=uid)
    organization_id = Column(String(32), ForeignKey("organizations.id"), nullable=False, index=True)
    platform = Column(String(30), nullable=False)  # facebook instagram youtube linkedin tiktok pinterest x
    account_label = Column(String(200), default="")
    oauth_granted = Column(Boolean, default=False, nullable=False)
    access_data = Column(JSON, default=dict)  # tokens stored server-side only, never sent to the frontend

class Integration(Base):
    __tablename__ = "integrations"
    id = Column(String(32), primary_key=True, default=uid)
    organization_id = Column(String(32), ForeignKey("organizations.id"), nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    enabled = Column(Boolean, default=False, nullable=False)
    config = Column(JSON, default=dict)

class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"
    id = Column(String(32), primary_key=True, default=uid)
    user_id = Column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    kind = Column(String(40), default="info")  # info | payment | subscription | campaign | lead | security | admin
    title = Column(String(200), nullable=False)
    body = Column(Text, default="")
    read = Column(Boolean, default=False, nullable=False)

class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"
    id = Column(String(32), primary_key=True, default=uid)
    user_id = Column(String(32), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    detail = Column(JSON, default=dict)
    ip = Column(String(64), default="")

class ResellerAccount(Base):
    __tablename__ = "reseller_accounts"
    id = Column(String(32), primary_key=True, default=uid)
    user_id = Column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    user = relationship("User", back_populates="reseller_account")
    brand_name = Column(String(200), default="")
    custom_domain = Column(String(255), default="")
    discount_percent = Column(Float, default=0.0)
    licenses_issued = Column(Integer, default=0)
    revenue_tracked = Column(Float, default=0.0)

class UsageRecord(Base, TimestampMixin):
    __tablename__ = "usage_records"
    id = Column(String(32), primary_key=True, default=uid)
    user_id = Column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    kind = Column(String(50), nullable=False)  # ai_generation | seo_audit | voice_minutes | emails_sent
    amount = Column(Float, default=1.0)
    detail = Column(JSON, default=dict)

class Website(Base, TimestampMixin):
    __tablename__ = "websites"
    id = Column(String(32), primary_key=True, default=uid)
    organization_id = Column(String(32), ForeignKey("organizations.id"), nullable=False, index=True)
    url = Column(String(500), nullable=False)
    integration_authorized = Column(Boolean, default=False, nullable=False)
    analytics = Column(JSON, default=dict)


class EmailSubscriber(Base):
    __tablename__ = "email_subscribers"
    id = Column(String(32), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(32), ForeignKey("organizations.id"), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    list_name = Column(String(100), default="default")
    unsubscribed = Column(Boolean, default=False)
    unsub_token = Column(String(64), default=lambda: secrets.token_hex(16))
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("organization_id", "email", "list_name", name="uq_subscriber"),)

class EmailCampaign(Base):
    __tablename__ = "email_campaigns"
    id = Column(String(32), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(32), ForeignKey("organizations.id"), nullable=False, index=True)
    created_by = Column(String(32), ForeignKey("users.id"))
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    list_name = Column(String(100), default="default")
    status = Column(String(20), default="draft")  # draft | sent | sent_with_failures
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class SocialPost(Base):
    __tablename__ = "social_posts"
    id = Column(String(32), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(32), ForeignKey("organizations.id"), nullable=False, index=True)
    created_by = Column(String(32), ForeignKey("users.id"))
    platform = Column(String(40), nullable=False)  # facebook|instagram|youtube|linkedin|tiktok|pinterest|x|other
    body = Column(Text, nullable=False)
    scheduled_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="draft")  # draft|scheduled|published|export_ready
    external_ref = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class VoiceAgent(Base, TimestampMixin):
    __tablename__ = "voice_agents"
    id = Column(String(32), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(32), ForeignKey("organizations.id"), nullable=False, index=True)
    created_by = Column(String(32), ForeignKey("users.id"))
    name = Column(String(200), nullable=False)
    language = Column(String(10), default="en")
    script = Column(Text, default="")
    is_active = Column(Boolean, default=True)


class VoiceCall(Base, TimestampMixin):
    __tablename__ = "voice_calls"
    id = Column(String(32), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(32), ForeignKey("voice_agents.id"), nullable=False)
    organization_id = Column(String(32), ForeignKey("organizations.id"), nullable=False, index=True)
    to_phone = Column(String(32), nullable=False)
    # queued | dialing | not_configured | failed
    status = Column(String(20), default="queued")
    provider = Column(String(30), default="")
    provider_ref = Column(String(255), nullable=True)
    outcome_note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
