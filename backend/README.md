# SmartDocZ — Backend (FastAPI)

Milestone 1: project setup, PostgreSQL connection, the 7-table schema, and Clerk
auth (session-token validation via `GET /me`).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

- `DATABASE_URL` — your Postgres connection string
- `CLERK_ISSUER` — your Clerk Frontend API URL, e.g. `https://your-app.clerk.accounts.dev`
  (this is the JWT `iss`; the backend derives the JWKS URL from it)
- `CLERK_SECRET_KEY` — optional but recommended; lets the backend backfill
  email + name from the Clerk Backend API
- `CLERK_AUTHORIZED_PARTIES` / `FRONTEND_ORIGINS` — your frontend origin(s)

## Migrate + run

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

- Health: http://localhost:8000/health
- Interactive docs: http://localhost:8000/docs

## Auth model

```
User Login → Clerk Session Token → FastAPI Validation → Authorized Request
```

The frontend sends `Authorization: Bearer <clerk session jwt>`. The backend
verifies the RS256 signature against Clerk's JWKS, checks the issuer/expiry and
`azp`, then upserts the user (keyed by the `sub` claim) and returns it from `/me`.

## Endpoint status (Milestone 1)

| Route                       | Status                         |
| --------------------------- | ------------------------------ |
| `GET  /health`              | ✅ implemented                  |
| `GET  /me`                  | ✅ implemented (auth)           |
| `*    /sessions...`         | 🚧 501 — Milestone 3           |
| `POST /upload`, `/files/*`  | 🚧 501 — Milestone 2           |
| `POST /chat`, `/messages/*` | 🚧 501 — Milestone 2           |
| `*    /analytics...`        | 🚧 501 — Milestone 6           |

All scaffolded routes already enforce auth, so the ownership boundary is in
place before the features land.
