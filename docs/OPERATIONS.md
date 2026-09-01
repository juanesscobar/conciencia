# OPERATIONS — Conciencia Platform (audit final, 2026-09-01)

## Despliegue
- Docker (producción): ver `docker-compose.yml` (backend + frontend + nginx + wa-bridge).
  Comandos habituales: `docker compose up -d --build`, `docker compose logs -f backend`.
- Local (dev): backend `uvicorn app.main:app --host 0.0.0.0 --port 8000` desde `backend/`;
  frontend `npm run dev` desde `frontend/`.
- CLI: entry point `conciencia` (backend venv) o wrapper `~/bin/conciencia` (fuerza UTF-8,
  DB local absoluta — ver USAGE.md Opción C).

## Migraciones
- Alembic lineal: heads actual `c3d4e5f6a7b9` (external_costs). Cadena:
  initial → leadhunter_jobs_async → agent_runtime_provider → task_dependencies →
  audit_events → workflows → leadhunter_normalization → teams → harnesses →
  workflow_events → signals → external_costs.
- En startup, `Base.metadata.create_all` + `sync_schema` (idempotente, agrega columnas
  faltantes en DBs viejas; NO pisa migraciones).

## Health / diagnóstico
- `conciencia health` — DB, conteos, embeddings.
- `conciencia doctor` — DB, tablas, runtimes, embeddings.
- `conciencia status` — misiones/runs/leads/agentes.
- API: `/api/v1/system/*` (protegido).

## Operación diaria (control plane)
- `conciencia ask "..."` → propuesta → confirmar → misión.
- `conciencia mission plan/run` · `conciencia approvals` / `approve <id> <step>`.
- `conciencia run inspect <id> --steps` · `run watch <id>` (observabilidad §H).
- `conciencia signal list --mission <id>` (hallazgos + evidencia).
- `conciencia economics summary [--mission <id>]` (costos/tokens).
- `conciencia webmcp demo --port 8765` + `webmcp run <url> "actions"`.

## Runtimes externos (Settings → Agents → Runtimes)
- generic (embebido) habilitado por defecto. claude_code/codex/opencode/openclaw
  deshabilitados hasta que el dueño los habilite; solo corren con `enabled=true`,
  comando allowlist y cwd validado. Sin adapter (claude/codex/opencode) → error claro
  "runtime X sin adapter".

## Backups / persistencia
- SQLite local: `backend/missioncontrol.db` (dev). Postgres en prod (commented .env).
- Volúmenes docker para DB y `.wa-session` (wa-bridge).

## Checklist pre-deploy RC
1. `docker compose config` válido.
2. Migraciones: `alembic upgrade head` (o confiar en create_all+sync idempotente).
3. CORS: `get_cors_origins` → orígenes reales del frontend (no `*`).
4. Secrets: DEEPSEEK_API_KEY / LLM_API_KEY en Settings (no .env de prod), rotados.
5. Healthchecks y restart policies en compose (revisar `nginx/` + `docker-compose.yml`).
6. Suite completa: 291+ passed / 8 deselected (baseline audit).
7. Backups de la DB antes del primer deploy real.
