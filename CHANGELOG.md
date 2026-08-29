# Conciencia Platform — Changelog

> (ex Mission Control) — AI Software Factory Control Plane
> Multi-agente: cada IA/IDE/agent que trabaje en este repo debe actualizar este archivo.

## Formato de entrada

```
## [version] — YYYY-MM-DD
### PR-XXXX — titulo corto
- archivos modificados
- que cambio
- resultado / estado
```

---

## [Unreleased] — LeadHunter Intelligence Engine (Fases 1-4)

### Fase 4 — Ranking + Scoring separados + Data Quality (spec §15/§16/§34/§35)
- **Archivos:** `backend/app/modules/leadhunter/ranking.py` (nuevo), `service.py` (refactor a bloques, contrato intacto), `schemas.py`, `search.py`, `router.py`, `routers/settings.py` (VISIBLE_KEYS), `tests/test_ranking.py` (nuevo); frontend `pages/Leads.tsx`, `pages/Settings.tsx`, `services/api.ts`
- **Cambio:** SearchRelevance (por query) ≠ LeadScore (independiente, ponderado) ≠ OpportunityScore; DataQualityScore 0-100 (completitud+frescura+fuente); RankingWeights configurables via `RANKING_WEIGHTS` (Settings JSON) + `GET/PUT /api/v1/leads/ranking/weights` (PUT solo admin); `explain()` → "Why this lead matches"; LeadResponse gana `search_relevance/opportunity_score/data_quality/reasons`; UI: tabla con `O:n · Q:n` + tooltip razones, LeadDetail "Score Intelligence", Settings "Ranking & Scoring"
- **Resultado:** 21 tests nuevos, suite F1-F4 81 verdes, tsc + build OK — estado done

## Convenciones

- Cada PR = una entrada en este changelog
- Estado: `done` | `partial` | `wip` | `blocked`
- Si usas IA/IDE/agent, firma con tu nombre al final de la entrada
- No borrar entradas anteriores, solo agregar

---

## [Unreleased] — Etapa 0: Estabilización E2E

### PR-0.1 — E2E Health Check
- **Archivos:** `docs/e2e-health-check.md`
- **Cambio:** Inventario WORKING/BROKEN/MOCKED de todas las funcionalidades
- **Estado:** done

### PR-0.2 — LeadHunterJob Async
- **Archivos:** `backend/app/modules/leadhunter/models.py`, `jobs.py`, `router.py`, `schemas.py`, migracion `6234dd9dcf77`
- **Cambio:** Modelo `LeadHunterJob` con estados PENDING/RUNNING/COMPLETED/FAILED/CANCELLED. Endpoints POST/GET /jobs, cancel, retry. Ejecucion async con threading daemon.
- **Estado:** done

### PR-0.3b — Fix observabilidad (step scoring)
- **Archivos:** `backend/app/modules/leadhunter/jobs.py`
- **Cambio:** Agregar step "scoring" en el flujo de progreso del job
- **Estado:** done

### PR-0.4b — Error handling robusto
- **Archivos:** `backend/app/modules/leadhunter/exceptions.py` (nuevo), `jobs.py`, `sources/overpass.py`, `enrich.py`, `models.py`, `models/__init__.py`
- **Cambio:** Custom exceptions (LeadHunterError, RateLimitError, SourceTimeoutError, SourceUnavailableError, InvalidCriteriaError, PartialFailureError), deteccion HTTP 429, backoff exponencial, estado PARTIAL_FAILURE, error categorizado JSON
- **Estado:** done

### PR-0.5b — Tests pytest E2E reales
- **Archivos:** `backend/tests/test_leadhunter_e2e.py` (nuevo), `backend/tests/test_discovery.py` (nuevo)
- **Cambio:** 28 tests pytest con assertions reales: job lifecycle, API, cancel, retry, exceptions, dedupe, scoring, normalize
- **Estado:** done (28 tests pasando)

### PR-0.6b — Scheduler crea LeadHunterJob
- **Archivos:** `backend/app/modules/leadhunter/scheduler.py`
- **Cambio:** El scheduler cron ahora crea un LeadHunterJob trackeable en vez de llamar run_discovery() directo
- **Estado:** done

### Deploy — Hetzner + Tailscale
- **Archivos:** `docker-compose.tailscale.yml` (nuevo), `nginx/nginx-tailscale.conf` (nuevo), `setup-hetzner-tailscale.sh` (nuevo), `docs/deploy-hetzner-tailscale.md` (nuevo)
- **Cambio:** Configuracion para deploy seguro en Hetzner con Tailscale. Sin puertos publicos, acceso solo desde tailnet. Script de setup automatico + documentacion completa.
- **Estado:** done

### Fix — Separacion de requirements
- **Archivos:** `backend/requirements.txt`, `backend/requirements-dev.txt` (nuevo)
- **Cambio:** pytest y pytest-asyncio movidos a requirements-dev.txt. Docker solo instala requirements.txt (produccion). Para tests locales: `pip install -r requirements-dev.txt`
- **Estado:** done

---

## [2.0.0-alpha] — 2026-08

### Control Plane P0 (Etapa 1) — COMPLETADA
- PR-1.1: AgentAdapter interface + Generic/OpenClaw adapter
- PR-1.2: Agent Registry (health/heartbeat, runtime, provider, model)
- PR-1.3: Task DAG (dependencias READY/ASSIGNED/BLOCKED + deteccion ciclos)
- PR-1.4: Audit log append-only + hooks
- PR-1.5: Workflow engine declarativo con approval gates

### Control Plane P1 (Etapa 2) — PARCIAL
- PR-2.1: Capability matching (requirements -> candidates -> best)
- PR-2.2: Approval gates UI (PENDING/APPROVED/REJECTED)
- PR-2.3: Cost tracking in-memory (token counting, pricing, routing) — falta persistencia DB
- PR-2.4: Agent health fields en modelo — falta dashboard real y watchdog
- PR-2.5: GitHub read-only (repos/commits/PRs/issues) — falta write-side

### Lead Hunter
- Motor de prospeccion Overpass/OSM + dedupe + scoring + enrich web
- Pipeline CRM con propuestas PDF + email/WhatsApp
- Sales squad multi-agente
- Integraciones centralizadas (GitHub, LLM multi-provider, Lead Hunter config)

### LLM Harness
- Multi-provider: DeepSeek / OpenAI / OpenRouter / Ollama / Anthropic
- Fallback + cost tracking + routing inteligente (cost/latency/quality/balanced)

### Frontend
- 10 paginas: Dashboard, Projects, ProjectDetail, Tasks, Agents, Leads, Reports, Settings, Workflows, Login
- Agent Office visual (8 agentes)
- Dark hacker theme

---

*Ultima actualizacion: 2026-08-14 — Etapa 0 completada*
