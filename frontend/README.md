# SmartDocZ — Frontend (Next.js)

Milestone 1: marketing home, Clerk auth (sign-up/in/out, email verification,
Google OAuth), and the authenticated workspace shell (280px sidebar) with
protected `/chat` and `/analytics` routes.

## Setup

```bash
npm install
cp .env.local.example .env.local
```

Fill in `.env.local`:

- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` / `CLERK_SECRET_KEY` — from the Clerk dashboard
- `NEXT_PUBLIC_BACKEND_URL` — the FastAPI base URL (default `http://localhost:8000`)

In the Clerk dashboard, enable **Email + Password** and **Google** as sign-in
options to match the PRD.

## Run

```bash
npm run dev   # http://localhost:3000
```

## Routes

| Route                  | Access    | Purpose                                  |
| ---------------------- | --------- | ---------------------------------------- |
| `/` → `/home`          | public    | Landing page                             |
| `/home`                | public    | Product intro, supported formats, CTAs   |
| `/sign-in` (`/login`)  | public    | Clerk sign-in                            |
| `/sign-up` (`/signup`) | public    | Clerk sign-up + email verification       |
| `/chat`                | protected | Workspace shell (upload/chat land in M2) |
| `/analytics`           | protected | RAGAS dashboard (lands in M6)            |

Protection is enforced by Clerk middleware (`middleware.ts`). The `/chat` page
calls the backend's `GET /me` with the Clerk session token, so a green
"Authenticated as…" status confirms the full auth handshake works.

## Design system

Dark-first, from the UI/UX Design Brief. Tokens live in
[`src/app/globals.css`](src/app/globals.css): brand `#6C47FF`, bg `#0D0D0D`,
surface `#151515`, text `#F5F5F7`, muted `#A1A1AA`; Inter + Geist Mono; 8px radius.
