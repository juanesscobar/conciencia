# Development Guide (local, no Docker)

Iterate fast with hot reload. Production uses Docker (see root README).

## Requirements

- Python 3.11+
- Node 18+
- (Optional) an LLM API key — DeepSeek: https://platform.deepseek.com

## 1. Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
```

Create `backend/.env`:

```
DATABASE_URL=sqlite:///./missioncontrol.db
SECRET_KEY=dev-secret-change-me
LOCAL_ADMIN_PASSWORD=your-admin-password
```

Seed and run:

```bash
python scripts/seed_local_admin.py   # creates/resets the admin user
python scripts/seed_agents.py        # upserts the 8 agents
python -m uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

## 2. Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

The Vite dev server proxies `/api` to the backend on port 8000.

## 3. Login

- User: `admin`
- Password: `LOCAL_ADMIN_PASSWORD` (env) — if unset and admin exists, the
  password is NOT modified; if admin doesn't exist, a random one is generated
  and printed at startup.

> The seed never hardcodes passwords (the repo is public). Password comes from
> `LOCAL_ADMIN_PASSWORD` / `ADMIN_PASSWORD` env or `.env`.

## Tests

```bash
cd backend
pytest
```

## Code conventions

- Backend: FastAPI routers under `app/routers` and domain modules under
  `app/modules`; docstrings in the style of existing modules.
- Frontend: dark terminal theme (`bg-bg-900`, `primary-400`, JetBrains Mono);
  API clients centralized in `frontend/src/services/api.ts`.
- Never commit secrets. Use `.env` / `.env.local` (gitignored).
