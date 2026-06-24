# SmartDocZ — Deployment Guide (Milestone 8)

Production topology (TRD §13):

| Layer        | Service        | Notes                                  |
| ------------ | -------------- | -------------------------------------- |
| Frontend     | **Vercel**     | Next.js, root directory `frontend/`    |
| Backend API  | **Railway**    | FastAPI via the `backend/Dockerfile`   |
| Relational   | **Railway Postgres** (or any managed PG) | the 7 tables    |
| Vector store | **Qdrant Cloud** | set `QDRANT_URL` to switch off Chroma |
| Auth         | **Clerk** (production instance) | email + Google OAuth     |

The app auto-selects the vector backend: **if `QDRANT_URL` is set it uses
Qdrant; otherwise Chroma** (local dev). No code change needed to switch.

---

## 1. Postgres

Create a managed Postgres (Railway "Add Postgres" plugin is simplest). Copy its
connection string into the backend env as `DATABASE_URL`. Use the SQLAlchemy
psycopg form:

```
postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME
```

Migrations run automatically on backend boot (the Docker `CMD` runs
`alembic upgrade head`).

## 2. Qdrant Cloud

1. Create a free cluster at <https://cloud.qdrant.io>.
2. Copy the **cluster URL** and an **API key**.
3. Set on the backend: `QDRANT_URL=https://xxxx.qdrant.io:6333` and
   `QDRANT_API_KEY=...`.

The collection (`smartdocz_chunks`) is created automatically on first upload,
with the correct vector dimension probed from the embedding model.

## 3. Clerk (production instance)

1. In the Clerk dashboard, create/promote a **production** instance for your
   domain and enable Email + Google.
2. Copy the production keys. Frontend: `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
   (`pk_live_…`) and `CLERK_SECRET_KEY` (`sk_live_…`). Backend: the same
   `CLERK_SECRET_KEY`, plus `CLERK_ISSUER` = your production Frontend API URL
   (`https://clerk.<your-domain>` or the `*.clerk.accounts.dev` issuer).
3. Add your Vercel domain to Clerk's allowed origins.

## 4. Backend → Railway

1. New Railway project → **Deploy from GitHub repo**, root `backend/`
   (Railway auto-detects the `Dockerfile`).
2. Set environment variables (see table below).
3. Deploy. Note the public backend URL, e.g. `https://smartdocz-api.up.railway.app`.

### Backend environment variables

| Variable                   | Required | Example / note                                   |
| -------------------------- | -------- | ------------------------------------------------ |
| `DATABASE_URL`             | ✅       | `postgresql+psycopg://…`                         |
| `CLERK_SECRET_KEY`         | ✅       | `sk_live_…`                                       |
| `CLERK_ISSUER`             | ✅       | production Clerk Frontend API URL                |
| `CLERK_AUTHORIZED_PARTIES` | ✅       | your Vercel URL, e.g. `https://smartdocz.vercel.app` |
| `FRONTEND_ORIGINS`         | ✅       | same Vercel URL (CORS allowlist)                 |
| `GOOGLE_API_KEY`           | ✅       | Gemini embeddings + generation                   |
| `QDRANT_URL`               | ✅       | Qdrant Cloud cluster URL (enables prod backend)  |
| `QDRANT_API_KEY`           | ✅       | Qdrant Cloud API key                             |
| `ANTHROPIC_API_KEY`        | optional | enables Claude fallback (needs account credits)  |
| `LLM_PROVIDER`             | optional | `gemini` (default) or `claude`                   |
| `GEMINI_MODEL`             | optional | default `gemini-2.5-flash`                        |
| `EMBEDDING_MODEL`          | optional | default `models/gemini-embedding-001`            |

## 5. Frontend → Vercel

1. New Vercel project → import the repo → set **Root Directory = `frontend`**.
2. Framework preset: Next.js (auto-detected).
3. Set environment variables:
   - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` = `pk_live_…`
   - `CLERK_SECRET_KEY` = `sk_live_…`
   - `NEXT_PUBLIC_BACKEND_URL` = your Railway backend URL
   - `NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in`, `…SIGN_UP_URL=/sign-up`,
     `…SIGN_IN_FALLBACK_REDIRECT_URL=/chat`, `…SIGN_UP_FALLBACK_REDIRECT_URL=/chat`
4. Deploy. Note the Vercel domain.

## 6. Wire the two together

- On the **backend** (Railway), set `FRONTEND_ORIGINS` and
  `CLERK_AUTHORIZED_PARTIES` to the Vercel domain, then redeploy.
- Confirm the backend health check: `GET https://<backend>/health` → `{"status":"ok"}`.

## 7. Production test checklist

- [ ] Sign up / log in (email + Google) via Clerk production
- [ ] Upload a PDF/DOCX/TXT/CSV/JSON and a YouTube URL
- [ ] Ask questions → grounded answers with citations
- [ ] Conversation memory: a follow-up resolves references
- [ ] Analytics: evaluate an answer (metric cards render)
- [ ] Resume a previous session after reload
- [ ] (If Claude funded) provider fallback works

---

## Notes & known limitations

- **Raw file storage** uses the container's local disk (`UPLOAD_DIR`), which is
  ephemeral on Railway — uploaded *files* are lost on redeploy, but the indexed
  **vectors persist in Qdrant** and messages persist in Postgres, so chats keep
  working. Wiring S3/GCS object storage (Backend Schema §7) is the natural
  next step for durable raw-file storage.
- The backend image runs `alembic upgrade head` on every boot (idempotent).
- Free Gemini tier caps embeddings at ~100/min; the app retries and (if
  configured) falls back to Claude.
