import hashlib, hmac, json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .. import models, schemas
from ..config import settings
from ..database import get_db
from ..security import audit, get_current_user

router = APIRouter(prefix="/billing", tags=["billing"])

PLAN_SEED = [
    ("free", "Free", 0.0, 0.0, {"ai_generations_per_month": 10, "seo_audits_per_month": 3, "campaigns": 1}),
    ("starter", "Starter", 19.0, 190.0, {"ai_generations_per_month": 200, "seo_audits_per_month": 30, "campaigns": 5}),
    ("pro", "Pro", 49.0, 490.0, {"ai_generations_per_month": 1000, "seo_audits_per_month": 150, "campaigns": 25}),
    ("business", "Business", 149.0, 1490.0, {"ai_generations_per_month": 5000, "seo_audits_per_month": 600, "campaigns": 100}),
    ("enterprise", "Enterprise", 499.0, 4990.0, {"ai_generations_per_month": 20000, "seo_audits_per_month": 3000, "campaigns": 500}),
    ("custom", "Custom", 0.0, 0.0, {"note": "custom pricing set by Super Admin"}),
]

def _invoice_number(db: Session) -> str:
    return f"NEX-{datetime.utcnow().strftime('%Y%m%d')}-{db.query(models.Invoice).count() + 1:06d}"

@router.get("/plans")
def list_plans(db: Session = Depends(get_db)):
    plans = db.query(models.Plan).filter(models.Plan.is_active == True).all()  # noqa: E712
    return [{"code": p.code, "name": p.name, "price_monthly": p.price_monthly,
             "price_yearly": p.price_yearly, "currency": p.currency, "limits": p.limits} for p in plans]

@router.get("/subscription")
def my_subscription(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = (db.query(models.Subscription).filter(models.Subscription.user_id == user.id)
             .order_by(models.Subscription.created_at.desc()).first())
    if not sub:
        return {"status": "none", "plan": "free"}
    plan = db.get(models.Plan, sub.plan_id)
    return {"status": sub.status, "plan": plan.code if plan else "unknown",
            "period": sub.period, "current_period_end": sub.current_period_end}

@router.post("/checkout")
def checkout(data: schemas.CheckoutIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = db.query(models.Plan).filter(models.Plan.code == data.plan_code,
                                        models.Plan.is_active == True).first()  # noqa: E712
    if not plan:
        raise HTTPException(404, "Plan not found")
    amount = plan.price_monthly if data.period == "monthly" else plan.price_yearly
    invoice = models.Invoice(number=_invoice_number(db), user_id=user.id,
                             amount=amount, currency=plan.currency,
                             description=f"{plan.name} subscription ({data.period})")
    db.add(invoice); db.flush()
    sub = models.Subscription(user_id=user.id, plan_id=plan.id, period=data.period, status="pending")
    db.add(sub); db.flush()
    if data.provider == "razorpay" and settings.razorpay_key_id and settings.razorpay_key_secret:
        import httpx
        resp = httpx.post("https://api.razorpay.com/v1/orders",
                          auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
                          json={"amount": int(amount * 100), "currency": "INR", "receipt": invoice.number})
        if resp.status_code >= 300:
            raise HTTPException(502, "Payment gateway rejected the order; check Razorpay credentials")
        order = resp.json()
        db.add(models.Payment(user_id=user.id, provider="razorpay", amount=amount,
                              currency="INR", provider_ref=order["id"], invoice_id=invoice.id))
        db.commit()
        return {"invoice": invoice.number, "provider": "razorpay", "order_id": order["id"],
                "amount": amount, "key_id": settings.razorpay_key_id}
    if data.provider == "paypal" and settings.paypal_client_id and settings.paypal_client_secret:
        import httpx
        token_resp = httpx.post(f"{settings.paypal_api_base}/v1/oauth2/token",
                                auth=(settings.paypal_client_id, settings.paypal_client_secret),
                                data={"grant_type": "client_credentials"})
        if token_resp.status_code >= 300:
            raise HTTPException(502, "Could not authenticate with PayPal; check PayPal credentials")
        bearer = token_resp.json().get("access_token")
        resp = httpx.post(f"{settings.paypal_api_base}/v2/checkout/orders",
                          headers={"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"},
                          json={"intent": "CAPTURE",
                                "purchase_units": [{"reference_id": invoice.number,
                                                    "amount": {"currency_code": plan.currency,
                                                               "value": f"{amount:.2f}"}}]})
        if resp.status_code >= 300:
            raise HTTPException(502, "Payment gateway rejected the order; check PayPal credentials")
        order = resp.json()
        approve = next((l["href"] for l in order.get("links", []) if l.get("rel") == "approve"), None)
        db.add(models.Payment(user_id=user.id, provider="paypal", amount=amount,
                              currency=plan.currency, provider_ref=order.get("id"), invoice_id=invoice.id))
        db.commit()
        return {"invoice": invoice.number, "provider": "paypal", "order_id": order.get("id"),
                "approval_url": approve, "amount": amount}
    # No gateway configured: record the invoice. Subscriptions NEVER activate on claims.
    db.add(models.Payment(user_id=user.id, provider="manual", amount=amount,
                          currency=plan.currency, invoice_id=invoice.id))
    db.commit()
    return {"invoice": invoice.number, "provider": "manual",
            "note": "No payment gateway is configured on this deployment. The Super Admin must set Razorpay/PayPal credentials in the environment."}

def _activate_subscription(db: Session, payment: models.Payment):
    payment.status = "captured"
    payment.verified_server_side = True
    inv = db.get(models.Invoice, payment.invoice_id)
    if inv:
        inv.status = "paid"
    sub = (db.query(models.Subscription).filter(models.Subscription.user_id == payment.user_id)
             .order_by(models.Subscription.created_at.desc()).first())
    if sub:
        sub.status = "active"
        sub.current_period_end = datetime.utcnow() + timedelta(days=30 if sub.period == "monthly" else 365)
    db.add(models.Notification(user_id=payment.user_id, kind="payment",
                               title="Payment verified",
                               body=f"Invoice {inv.number if inv else ''} verified and subscription activated."))

@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    if not settings.razorpay_webhook_secret:
        raise HTTPException(503, "Razorpay webhook secret is not configured")
    signature = request.headers.get("X-Razorpay-Signature", "")
    expected = hmac.new(settings.razorpay_webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(400, "Invalid webhook signature")
    event = json.loads(body)
    entity = (event.get("payload", {}).get("payment", {}) or {}).get("entity", {}) or {}
    order_id = entity.get("order_id")
    payment = db.query(models.Payment).filter(models.Payment.provider_ref == order_id,
                                              models.Payment.provider == "razorpay").first()
    if not payment:
        raise HTTPException(404, "Unknown order")
    if event.get("event") == "payment.captured":
        _activate_subscription(db, payment)
        audit(db, "billing.razorpay_captured", payment.user_id, {"order": order_id})
        db.commit()
    elif event.get("event") == "payment.failed":
        payment.status = "failed"; db.commit()
    return {"ok": True}

@router.post("/webhooks/paypal")
async def paypal_webhook(request: Request, db: Session = Depends(get_db)):
    if not (settings.paypal_client_id and settings.paypal_client_secret):
        raise HTTPException(503, "PayPal credentials are not configured")
    import httpx
    token_resp = httpx.post(f"{settings.paypal_api_base}/v1/oauth2/token",
                            auth=(settings.paypal_client_id, settings.paypal_client_secret),
                            data={"grant_type": "client_credentials"})
    if token_resp.status_code >= 300:
        raise HTTPException(502, "Could not authenticate with PayPal")
    bearer = token_resp.json().get("access_token")
    body = await request.body()
    verify_headers = {"Content-Type": "application/json", "Authorization": f"Bearer {bearer}",
                      **{k: v for k, v in request.headers.items() if k.lower().startswith("paypal-")}}
    verification = httpx.post(f"{settings.paypal_api_base}/v1/notifications/verify-webhook-signature",
                              headers=verify_headers, content=body)
    if verification.json().get("verification_status") != "SUCCESS":
        raise HTTPException(400, "PayPal webhook verification failed")
    event = json.loads(body)
    resource = event.get("resource", {})
    ref = (resource.get("supplementary_data", {}).get("related_ids", {}) or {}).get("order_id") or resource.get("id")
    payment = db.query(models.Payment).filter(models.Payment.provider_ref == ref).first()
    if not payment:
        raise HTTPException(404, "Unknown payment reference")
    if event.get("event_type") in ("PAYMENT.CAPTURE.COMPLETED", "CHECKOUT.ORDER.APPROVED"):
        _activate_subscription(db, payment)
        audit(db, "billing.paypal_captured", payment.user_id, {"ref": ref})
        db.commit()
    return {"ok": True}

@router.get("/invoices")
def my_invoices(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(models.Invoice).filter(models.Invoice.user_id == user.id).order_by(models.Invoice.created_at.desc()).all()
    return [{"number": i.number, "amount": i.amount, "currency": i.currency,
             "status": i.status, "description": i.description, "created_at": i.created_at} for i in rows]
