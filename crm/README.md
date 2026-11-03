# crm

Implemented in this repository as follows:
- ai-engine, marketing-engine, seo-engine, crm, analytics, content-studio, payment-engine, licensing-engine: see `backend/app/routers/` (marketing.py, billing.py, licenses.py) and `backend/app/models.py`.
- admin-dashboard, customer-dashboard: see `frontend/src/app/admin` and `frontend/src/app/dashboard`.
- voice-agent and social-media are the next build stages; they integrate only through official provider APIs once credentials are configured (graceful fallback until then).
