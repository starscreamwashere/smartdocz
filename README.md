# SmartDocZ

> Chat with any document — PDFs, CSVs, JSON, text, DOCX, or YouTube transcripts.

SmartDocZ is an AI-powered document assistant: upload documents, ask questions in
natural language, get RAG-grounded answers with source citations, keep conversational
memory within a session, and evaluate answer quality with RAGAS metrics.

This repository is a **monorepo**:

| Folder      | Stack                                   | Hosting       |
| ----------- | --------------------------------------- | ------------- |
| `frontend/` | Next.js · TypeScript · Tailwind · Clerk | Vercel        |
| `backend/`  | FastAPI · SQLAlchemy · LangGraph (later)| Railway       |
| Postgres    | Application data (7 tables)             | Railway / RDS |
| Qdrant      | Vector store (prod) / Chroma (dev)      | Qdrant Cloud  |

## Roadmap (Vertical Slice First)

The product is built in 8 milestones, each one deployable and demoable:

1. ✅ Project Setup + Auth
2. ✅ PDF-only RAG (upload → chunk → embed → retrieve → answer)
3. ✅ Session persistence
4. ✅ Multi-file support (PDF/DOCX/TXT/CSV/JSON/YouTube)
5. ✅ Conversation memory
6. ✅ Analytics (RAGAS-style evaluation)
7. ✅ Claude fallback routing
8. ✅ Deployment (Vercel + Railway + Qdrant Cloud) — see [DEPLOYMENT.md](DEPLOYMENT.md)

## Milestone 1 — what's implemented

- Next.js (App Router) + TypeScript + Tailwind + dark design system
- Clerk auth: sign-up (email + Google OAuth), email verification, sign-in, sign-out
- Public pages: `/home`, `/sign-in`, `/sign-up`
- Protected pages: `/chat`, `/analytics` (Clerk middleware-gated)
- FastAPI backend with Clerk JWT validation, PostgreSQL connection, SQLAlchemy
  models for all 7 tables, and an Alembic initial migration
- `GET /me` — validates the Clerk session token, upserts the user, returns the profile
- Scaffolded (auth-protected) routers for sessions, files, chat, analytics

## Quick start

See [`frontend/README.md`](frontend/README.md) and [`backend/README.md`](backend/README.md).

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in values
alembic upgrade head
uvicorn app.main:app --reload # http://localhost:8000

# 2. Frontend (new terminal)
cd frontend
npm install
cp .env.local.example .env.local   # fill in Clerk keys + backend URL
npm run dev                        # http://localhost:3000
```
