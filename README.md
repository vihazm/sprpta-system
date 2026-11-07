# SPRPTA System

Complaint & Recommendation Management System for the Southern Provincial Road Passenger Transport Authority.

Stack: Next.js 16 (React 19, TypeScript, Tailwind CSS 4) + FastAPI (Python).

## Prerequisites

- Node.js 22+ and npm
- Python 3.13+
- Git

## Setup

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Frontend:

```bash
cd frontend
npm install
copy .env.example .env.local
```

`.env.local` is ignored by git. Never commit real secrets; only `.env.example` files (with dummy values) belong in the repo.

## Run

Backend (http://localhost:8000, docs at /docs):

```bash
cd backend
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Frontend (http://localhost:3000):

```bash
cd frontend
npm run dev
```

The home page shows the API status. Database, AI and messaging are not set up yet.

## Contributing

- Nobody pushes to `main` or `dev`.
- Work only on your own branch (`feature/<name>-<module>`), commit there, and push it.
- Keep it up to date with `git pull origin dev`.
- Open a pull request from your branch into `dev`. The repo admin tests and merges it.
- The admin merges `dev` into `main` after testing.
