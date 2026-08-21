# Contributing to Conciencia

First off, thanks for being here. Conciencia is an open control plane for
autonomous work — and it only gets better with contributors like you.

## Code of Conduct

Be respectful. Be constructive. Assume good faith. This project welcomes
everyone regardless of experience level, background, or preferred editor.

## How to contribute

### 1. Find something to work on

Look for issues labeled:

- [`good first issue`](https://github.com/juanesscobar/mission-control/labels/good%20first%20issue) — 30 min to 2 h, great for newcomers
- [`help wanted`](https://github.com/juanesscobar/mission-control/labels/help%20wanted)
- [`documentation`](https://github.com/juanesscobar/mission-control/labels/documentation)
- [`integrations`](https://github.com/juanesscobar/mission-control/labels/integrations) — MCP servers, tool adapters, agent adapters

No issue assigned to you? Pick any open one. No open one that fits? Open a
discussion first, or propose a new issue.

### 2. Set up your environment

```bash
git clone https://github.com/juanesscobar/mission-control.git
cd mission-control

# Backend (FastAPI)
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
# DB local (SQLite): crear backend/.env con DATABASE_URL=sqlite:///./missioncontrol.db

# Frontend (React + Vite)
cd ../frontend
npm install
```

Run it:

```bash
# Terminal 1 — backend
cd backend && python -m uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev      # http://localhost:5173
```

### 3. Create a branch and make your change

```bash
git checkout -b feat/your-change
```

Follow existing conventions: same code style, same naming, docstrings in the
backend, terminal/dark theme components in the frontend.

### 4. Test your change

- Backend: `pytest` (see `backend/tests/`)
- Frontend: `npx tsc --noEmit` and `npm run build`
- Manual: run the app, exercise the flow you touched

### 5. Open a pull request

- Target branch: `main`
- Fill out the PR template
- Keep PRs small and focused — one concern per PR
- Reference the issue you're closing (`Closes #123`)

## Good first contributions

| Area | Examples |
|------|----------|
| Integrations | New MCP server, tool adapter, provider preset |
| Docs | README improvements, architecture diagrams, tutorials |
| Examples | Sample missions, seed data, walkthroughs |
| UI | Small dashboard components, dark-theme polish |
| Tests | Unit tests, E2E tests, fixtures |
| Deployment | Docker templates, compose examples, Helm/K8s |

## Architecture at a glance

- `backend/app` — FastAPI application (routers, models, services, modules)
- `backend/app/modules` — domain modules: `email`, `leadhunter`, `whatsapp`, `jobscout`
- `backend/app/services` — LLM harness, MCP client, crypto, auth
- `frontend/src` — React + Vite + Tailwind, dark terminal theme
- `agents/` — agent identities (`SOUL.md` per agent: dev, ops, qa, pm, rd, comms, fin, admin)

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full picture.

## Questions?

Open a discussion or an issue — we reply fast.

Thank you for helping build the open control plane for autonomous work. 🙌
