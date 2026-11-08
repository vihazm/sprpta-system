# SPRPTA System

Complaint & Recommendation Management System for the Southern Provincial Road Passenger Transport Authority.

Stack: Next.js 16 (React 19, TypeScript, Tailwind CSS 4) + FastAPI (Python) + PostgreSQL.

## Prerequisites

- Node.js 22+ and npm
- Python 3.13+
- PostgreSQL (create an empty database named `sprpta_db`)
- Git

## Setup

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env
```

Edit `backend/.env`: set `DATABASE_URL` (your PostgreSQL password) and `JWT_SECRET` (generate one with `.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(48))"`). Then create the tables and the starting data:

```bash
.venv\Scripts\alembic upgrade head
.venv\Scripts\python -m app.scripts.seed
```

Frontend:

```bash
cd frontend
npm install
copy .env.example .env.local
```

`.env` and `.env.local` are ignored by git. Never commit real secrets; only `.env.example` files (with dummy values) belong in the repo.

## Run

Backend (http://localhost:8000, docs at /docs):

```bash
cd backend
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Frontend (http://localhost:3000, forwards `/api/*` to the backend):

```bash
cd frontend
npm run dev
```

Open http://localhost:3000 and sign in.

## Development accounts

`python -m app.scripts.seed` creates these only while `APP_ENV=development`. They exist so every role's landing page can be tried; they are never created in production.

| Role | Login | Password | Lands on |
| --- | --- | --- | --- |
| Level 3 chairman | `test_chairman@sprpta.test` | `chairman123` | `/l3/dashboard` |
| Level 2 area officer (Galle) | `test_ad_galle@sprpta.test` | `ad_galle123` | `/l2/dashboard` |
| Level 1 office staff | `test_office@sprpta.test` | `office123` | `/l1/dashboard` |
| System administrator | `system_admin@sprpta.test` | `admin123` | `/admin/dashboard` |
| Implementing staff | `test_groundstaff@sprpta.test` | `groundstaff123` | `/is/cases` |
| Complainant | `test_client1@sprpta.test` | `client1abc` | `/cp/complaints` |

## How sign-in works

- `POST /api/auth/login` checks the password (argon2) and starts a session: a 15-minute access JWT and a rotating refresh token, both in httpOnly cookies. The session is also stored in the `auth_sessions` table, so logout and deactivating a user take effect immediately.
- A session ends after 30 minutes without activity or 12 hours in total. 5 wrong passwords lock the account for 15 minutes.
- The backend returns where the user should land; the frontend redirects there. Role pages live under `frontend/src/app/(portal)/<role>/`.
- To protect a backend route, add `Depends(require_roles("l2"))` (from `app/api/deps.py`). `principal.area_id` is set for L2 officers.
- To add a role page, put it under that role's folder; its `layout.tsx` already requires the role.

## Notifications

Sitewide alerts use one reusable "island pill": green for good news, red for bad news. Use it instead of `alert()`, `confirm()` or the browser's own form bubbles.

```ts
import { notify } from "@/lib/notify";

notify.success("Saved", "The complaint was forwarded.");
notify.error("Could not save", "Please check the highlighted fields.");
```

- Call it from any client component or event handler; nothing else to set up. One message shows at a time and a new one replaces it. It disappears after 4 seconds (7 for errors), pauses while hovered, and closes with the X or the Escape key.
- To show a message after a full page load (for example after logout), add `?reason=signed-out`, `?reason=expired` or `?denied=1` to the address; `UrlNotices` turns it into a pill and removes it from the address bar. Add new reasons there.
- Files: `src/lib/notify.ts` (the `notify` calls), `src/components/notify/` (`Toaster` is mounted once in `src/app/layout.tsx`, `IslandPill` is the look).

## Tests

```bash
cd backend
.venv\Scripts\python -m pytest
```

The tests use a separate `sprpta_test` database (created automatically) and never touch `sprpta_db`.

## Contributing

- Nobody pushes to `main` or `dev`.
- Work only on your own branch (`feature/<name>-<module>`), commit there, and push it.
- Keep it up to date with `git pull origin dev`.
- Open a pull request from your branch into `dev`. The repo admin tests and merges it.
- The admin merges `dev` into `main` after testing.
