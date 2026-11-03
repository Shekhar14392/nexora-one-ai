# NEXORA AI

Autonomous global AI marketing & business automation platform. Independent stack: its own backend, database, user management, CRM, licensing engine and admin system. Optional external services (payment gateways, AI providers, social platforms) are modular providers with graceful fallbacks - the platform never claims an integration is operational without configured credentials.

## Architecture

```
nexora-ai/
├── backend/    FastAPI (Python) REST API, SQLAlchemy models, JWT auth, RBAC,
│               licensing engine, billing with server-side payment verification,
│               marketing engine (campaigns, content studio, SEO audits, CRM, analytics)
├── frontend/   Next.js 14 + TypeScript + Tailwind (landing, login, customer dashboard, admin dashboard)
├── scripts/    operational scripts (database backup)
├── documentation/  legal + commercial templates
├── docker-compose.yml   Postgres + Redis + backend + frontend
└── .env.example         every credential is environment-only, never hardcoded
```

Directory modules at the repo root (ai-engine, marketing-engine, voice-agent, crm, seo-engine, content-studio, social-media, payment-engine, licensing-engine, analytics, admin-dashboard, customer-dashboard) map to the backend routers and frontend sections that implement them; they carry module-level READMEs as the implementation grows stage by stage.

## Stage status (build log)

- STAGE 1 DONE: core architecture, FastAPI backend, SQLAlchemy models (users, organizations, plans, subscriptions, payments, invoices, licenses, campaigns, content, leads, customers, conversations, SEO reports, social accounts, integrations, notifications, audit logs, resellers, usage, websites), registration/login/JWT refresh, RBAC (superadmin protected, no default password), 8 automated tests passing.
- STAGE 2..10: see roadmap below; implemented incrementally with tests after each stage.

## Install (local development)

```bash
cp .env.example .env            # then edit: JWT secret + super admin email/password
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload   # API on http://localhost:8000 (docs at /docs)
cd ../frontend
npm install && npm run dev      # UI on http://localhost:3000
```

On first startup the API seeds the six subscription plans and, if `NEXORA_ADMIN_EMAIL` / `NEXORA_ADMIN_PASSWORD` are set, the single super admin account. If you skip those variables no admin exists and none can be created through the public API.

## Super Admin access

1. Set `NEXORA_ADMIN_EMAIL` and `NEXORA_ADMIN_PASSWORD` in `.env` before first startup (12+ random characters; store them in a password manager).
2. Start the backend; the account is seeded once.
3. Open the frontend `/admin` route and sign in with those credentials. Ordinary users receive 403 on every `/admin` endpoint - enforced server-side, not in the UI.
4. The super admin can: create/suspend users, edit plans and pricing, issue/suspend/transfer licenses, view payments and refunds, monitor AI usage, read audit logs, and manage resellers.

## Payment configuration

- Razorpay: set `NEXORA_RAZORPAY_KEY_ID`, `NEXORA_RAZORPAY_KEY_SECRET`, and `NEXORA_RAZORPAY_WEBHOOK_SECRET`; point the dashboard webhook at `POST /billing/webhooks/razorpay`. Signature is verified with HMAC before any subscription activates.
- PayPal: set `NEXORA_PAYPAL_CLIENT_ID/SECRET/WEBHOOK_ID`; point the webhook at `POST /billing/webhooks/paypal`. Every webhook is verified through PayPal's verify-webhook-signature API before activation.
- Without credentials, checkout records a manual invoice and the subscription stays `pending`. Subscriptions NEVER activate on screenshots or unverified claims - only on a verified gateway webhook.
- Test mode: run PayPal against `NEXORA_PAYPAL_API_BASE=https://api-m.sandbox.paypal.com` and Razorpay test keys.

## License management

- Issue: `POST /admin/licenses/issue` (super admin) returns keys shaped `NEX-XXXX-XXXX-XXXX-XXXX-XXXX`.
- Activate on a customer deployment: `POST /licenses/activate {key, domain}` binds the domain (1 default activation; more via `max_activations`).
- Verify any installation: `GET /licenses/verify/{key}` returns validity, bound domain and expiry.
- Suspend/re-activate/transfer: `POST /admin/licenses/set-status`, `POST /admin/licenses/transfer`. Every action is appended to the license audit history and the platform audit log.

## Deployment

```bash
docker compose up -d --build     # Postgres + Redis + backend + frontend
```

- Set real secrets in `.env` (64-char JWT secret, gateway keys, super admin password).
- Put the stack behind a reverse proxy (Caddy/Nginx) for HTTPS and point your domain at it; backend on :8000, frontend on :3000.
- Migrations: `Base.metadata.create_all` runs on startup for development; for production add Alembic (`alembic init migrations` is the next infrastructure stage).
- Backups: `scripts/backup_db.sh /var/backups/nexora` from cron daily (30-day retention).
- Health check: `GET /health`.

## Automated tests

```bash
cd backend && python -m pytest tests -q
```

Last run: 8 passed (registration, login, refresh, wrong-password rejection, RBAC denial for ordinary users, license endpoint protection, checkout without gateway stays pending, content fallback generation, lead scoring).

## Remaining external integrations (require credentials / official authorization)

- Email sending (SMTP provider) for verification, recovery and campaigns.
- Razorpay / PayPal live credentials for real payments.
- Social platforms (Facebook, Instagram, YouTube, LinkedIn, TikTok, Pinterest, X) publish only through their official OAuth APIs when the customer authorizes; without a granted connection the platform offers manual publishing/export instead. No tool bypasses platform permissions.
- WhatsApp messaging only through officially supported channels (e.g. WhatsApp Business API) once credentials are configured.
- Live voice calls for the AI voice agent (Stage 6) need a telephony/SIP provider.

## Ownership

Original implementation and branding. Third-party dependencies keep their own licenses (see `documentation/`). Commercial license, privacy policy, terms of service, acceptable use and reseller agreement templates are in `documentation/`.
