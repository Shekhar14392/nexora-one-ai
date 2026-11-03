# Security policy - NEXORA AI

- Report vulnerabilities privately to the platform owner's security contact. Do not open public issues for exploitable findings.
- Passwords are stored as PBKDF2-SHA256 hashes (260,000 iterations, per-user salt). Never in plaintext.
- Authentication uses short-lived JWT access tokens plus rotating refresh tokens; both are required and type-checked.
- Super admin is protected by role checks on every /admin endpoint and is seeded only from environment variables - there is no default password.
- Payment webhooks verify HMAC signatures (Razorpay) or PayPal's verification API before any state change. Subscriptions never activate on unverified claims.
- Secrets live only in environment variables and are never sent to the frontend.
- Audit logging records privileged actions (user suspension, plan changes, license events, refunds).
- Known gap to close in a later stage: rate limiting is wired via slowapi but must be tuned per route; add brute-force lockout on login.
