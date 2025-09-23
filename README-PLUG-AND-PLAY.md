# Lease SaaS – Full Plug‑and‑Play Bundle

This bundle includes:
- **FastAPI backend** with JWT auth, file uploads, monthly quota (free/pro), and Stripe billing hooks.
- **Nginx frontend** serving your existing site (mounted from: `/mnt/data/lease-saas-all-in-one-final/lease-saas-all-in-one-final/web-frontend/site/lease`) and proxying `/api/*` to the backend.
- **Docker Compose** to run everything with one command.

## Quick Start

1. Copy `.env.example` to `backend/.env` and fill in values:
   ```bash
   cp backend/.env.example backend/.env
   ```

   Minimum to change:
   - `JWT_SECRET` – long random string
   - `FRONTEND_ORIGIN` – e.g., `http://localhost:8080`
   - Stripe: `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID_PRO`, `STRIPE_SUCCESS_URL`, `STRIPE_CANCEL_URL`

2. Launch:
   ```bash
   docker compose up --build
   ```
   - Frontend: http://localhost:8080
   - Backend health: http://localhost:8080/api/health

3. API usage (prefix `/api` from the browser because nginx proxies to backend):
   - `POST /api/auth/register` – `{ "email": "...", "password": "..." }`
   - `POST /api/auth/login` – `{ "email": "...", "password": "..." }` → returns `access_token`
   - `GET /api/quota` – auth required (Bearer)
   - `POST /api/upload` – auth required (multipart file)
   - `POST /api/billing/create-checkout-session` – auth required → returns `checkout_url`
   - `POST /api/billing/webhook` – set Stripe webhook to `http://localhost:8080/api/billing/webhook` (or backend URL)

## Notes

- Database: SQLite at `backend/app.db` (mounted). Swap `DATABASE_URL` in `backend/.env` for Postgres if desired.
- Quotas:
  - free: `MAX_UPLOAD_MB_FREE`
  - pro: `MAX_UPLOAD_MB_PRO`
- Single-File cap: `MAX_FILE_SIZE_MB`

## Frontend Integration

Your existing site is served as-is. For JS calls, use `/api/*` endpoints (relative path) so it works behind nginx.
Add an Authorization header after login:
```
Authorization: Bearer <access_token>
```

Enjoy!
