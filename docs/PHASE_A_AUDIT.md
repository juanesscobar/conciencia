# PHASE A — Architecture Audit & Capability Matrix

> Fuente: `master-implementation-prompt.md` — Conciencia como **Mission Orchestration Control Plane**.
> Fecha: 2026-08-30 · Rama: v2-refactor · Commit: 1545f78

---

## 1. Estado actual del repositorio

| Área | Detalle |
|---|---|
| Backend | FastAPI 0.115 + SQLAlchemy 2.0.25 + Pydantic 2 · ~103 endpoints en 20 routers |
| Frontend | React + Vite + Tailwind · 17 páginas (Dashboard, Projects, Tasks, Agents, Workflows, Approvals, Context, Governance, Traces, Costs, Audit, Leads, Email, Settings, …) |
| CLI | typer + rich · 13 comandos (`health`, `search`, `leads list/export`, `lead inspect/score/enrich`, `hunt`, `config get/set`, `agents`, `modules`, `map`) |
| Tests | 21 archivos · ~211 tests · 209 verdes (2 fallos pre-existentes en `test_llm_harness`, requieren providers LLM reales) |
| Modelos | 17 tablas: user, project, sprint, task, task_dependency, deliverable, workflow, workflow_run, agent, agent_execution, context_pack, cost_record, policy, decision, audit, activity, metric, user_memory, setting |
| Módulos | leadhunter (prospección completa), jobscout, whatsapp (bridge), email (multi-proveedor MCP) |
| Agentes | 11 en DB (8 core + 3 LeadHunter: lead_research, business_classification, contact_discovery) · SOUL.md en disco para los 8 core |
| Runtimes | AGENT_RUNTIMES: generic, claude_code, codex, opencode, openclaw, mcp · runner seguro subprocess |
| Infra | Docker compose (nginx + backend + frontend + postgres + redis) · prod en Hetzner 46.62.196.151 |

---

## 2. Capability Matrix (KEEP / IMPROVE / REFACTOR / DEPRECATE / BUILD)

### 2.1 Ya existe y funciona → KEEP / IMPROVE

| Capacidad (master prompt) | Estado real | Calidad | Acción |
|---|---|---|---|
| Auth + roles | `/api/v1/auth` + JWT + roles (ceo/admin/…) | Buena | KEEP |
| Agent Registry | 10 endpoints, 11 agentes, SOUL.md, capabilities, permisos ALLOW/DENY | Buena | KEEP — cubre §10 casi completo |
| Multi-Runtime | AGENT_RUNTIMES + runner seguro + override por agente | Buena | KEEP — cubre §13 |
| Workflow/DAG | `workflow_engine.py` (steps, approval, retry, timeout, max_cost) + `task_dag.py` (dependencias, ciclos) | Buena | KEEP + IMPROVE — cubre §12, falta parallel/conditional |
| Approvals | Workflow steps `approval: true` + frontend `/approvals` | Buena | KEEP + IMPROVE — falta CLI (cubre §16 a medias) |
| Audit trail | `/api/v1/audit` + system logs | Buena | KEEP — cubre §18/evidence parcial |
| Cost tracking | `cost_records` (provider/model/tokens/cost_usd) + `/api/v1/costs` | Buena | KEEP — base de §24/27, falta agregación por misión |
| Traces | `/api/v1/traces` (1 endpoint) | Básica | IMPROVE — base de §15 observabilidad |
| Context Packs | 7 endpoints + modelo canónico + adapters | Buena | KEEP + IMPROVE — cubre §19, falta integrar a Mission |
| User Memory | `user_memories` CRUD + panel | Buena | KEEP — parte de §20 |
| AgentExecution | modelo + estado PENDING→…→CANCELLED | Buena | IMPROVE → **Run** de misión |
| LLM Harness | multi-proveedor, fallback, costos, token budgets | Buena | KEEP — cubre §14 parcial |
| MCP | client + email_server + tool registry | Buena | KEEP — base de §21 WebMCP |
| CLI base | typer + rich + `_make_session` respeta DATABASE_URL | Buena | KEEP — base de §6 |
| LeadHunter | pipeline completo hunt→enrich→score→propose | Excelente | KEEP — módulo según §22 |

### 2.2 Existe a medias → IMPROVE / REFACTOR

| Capacidad | Estado | Gap | Acción |
|---|---|---|---|
| Deliverables | modelo + CRUD (report/commit/pr/…) | No ligado a missions, sin provenance formal | IMPROVE → evidence (§18) |
| Decisions | `/api/v1/decisions` (5 endpoints) | Sin relación con missions/signals | IMPROVE (§17/20) |
| Reports | 7 endpoints | Generales, no por misión | REFACTOR ligero |
| GitHub integration | 5 endpoints con cache | Útil para project context (§8) | KEEP + usar en `project inspect` |
| WorkflowRun | modelo + estados por step | Sin `run watch` CLI, sin logs estructurados | IMPROVE → base de §15 |
| Settings | 12 endpoints | Ya cubre ranking/bbox/cron/runtimes | KEEP — extender a missions |

### 2.3 No existe → BUILD (en orden de fases)

| Capacidad | Fase del master | Nota |
|---|---|---|
| **Mission como objeto de dominio** | B | La pieza central que falta. Hoy el trabajo se orquesta en Task/Workflow/AgentExecution sin una unidad de gobierno superior |
| MissionRun / Run CLI (`run list/inspect/watch`) | C | AgentExecution es la base, falta la vista misión |
| `conciencia init` / `status` / `doctor` | C | Proyecto: git, stack, contexto |
| `project inspect` | D | Detección de repo/stack/branch |
| `conciencia ask` (NL → misión propuesta) | E | Harness + intents |
| Teams | F | Registro de equipos reutilizables |
| Harness como asset versionable | G | Instrucciones + contexto + validaciones + output contract |
| `run watch` con observabilidad | H | Logs estructurados, costos, tokens, acciones |
| Signals + Evidence | I | Observaciones trazables con confianza |
| Context Pack integrado a Mission | J | Ya existe el modelo, falta el pipeline |
| WebMCP | K | Conector como tool MCP |
| Economics por misión | L | Agregar cost_records por mission_id/run_id/action |

---

## 3. Mission Orchestration Gap Analysis

**Hallazgo principal: no existe `Mission`.** El dominio actual es:

```
Project → Sprint → Task → (TaskDependency DAG)
Workflow → WorkflowRun (steps con approval/retry/timeout)
Agent → AgentExecution (runs por tarea)
```

El master prompt pide:

```
Intent → Mission → Context → Plan → Team → Runtime → Workflow/DAG → Tools → Execución
        → Approvals → Evidence → Outcome → Observabilidad → Learning
```

**Brecha conceptual**: el repo orquesta *tareas y workflows sueltos*; no hay una unidad de trabajo que agrupe objetivo + contexto + agentes + workflow + runtime + presupuesto + criterios de éxito + evidencia + outcome + costo.

**Estrategia recomendada (sin romper nada):**
1. Crear `Mission` como **capa superior** que referencia (no reemplaza) lo existente: `mission.project_id`, `mission.workflow_id`, `mission.agent_ids`, `mission.run_ids`.
2. `MissionRun` puede reusar `AgentExecution` (agregar `mission_id` nullable) o ser un wrapper con su propia tabla.
3. NO tocar LeadHunter, email, whatsapp, auth, audit — quedan como módulos.
4. Migración aditiva: nuevas tablas + columnas nullable → sin breaking changes en prod.

**Mapeo del yaml objetivo (§4) a lo existente:**

| Campo objetivo | Fuente existente | Acción |
|---|---|---|
| id, name, description | — | BUILD (tabla missions) |
| objective | — | BUILD |
| project | project.id | FK nullable |
| type | — | BUILD (enum: research, software-development, code-review, …) |
| status | workflow.status / execution.status | BUILD (draft→planned→running→…→done/failed/cancelled) |
| requester | user.id | FK |
| context | context_pack.id | FK nullable |
| agents / team | agent.id[] | BUILD (JSON o join table) |
| workflow | workflow.id | FK nullable |
| runtime | AGENT_RUNTIMES | Config del mission |
| permissions / approval_policy | policies | FK nullable |
| budget / cost_limit / token_limit | settings | BUILD (JSON en mission) |
| success_criteria | — | BUILD (JSON) |
| evidence | deliverables | FK/conexión |
| outcome | — | BUILD (JSON resumen) |
| created/started/completed_at | patrón existente | BUILD |

---

## 4. CLI Gap Analysis (actual 13 → target ~40)

| Comando target (§6) | Estado | Acción |
|---|---|---|
| `conciencia` (sin args) | muestra help | KEEP |
| `status` / `doctor` | ✗ | BUILD (C) |
| `init` | ✗ | BUILD (C) — crear `.conciencia/` |
| `project inspect` | ✗ | BUILD (D) — git/stack/branch |
| `mission list/create/inspect/plan/run/pause/resume/cancel` | ✗ | BUILD (C) — **core** |
| `run list/inspect/logs/watch` | ✗ | BUILD (H) — sobre AgentExecution/WorkflowRun |
| `agent list/inspect/run` | `agents` parcial | IMPROVE |
| `team list/run` | ✗ | BUILD (F) |
| `workflow list/inspect/run` | ✗ (solo API) | BUILD (C) |
| `tool list` / `runtime list` / `model list` | ✗ | BUILD (C) — leer registries existentes |
| `context inspect` | ✗ | BUILD (J) |
| `knowledge search` / `memory search` | ✗ | BUILD (I/J) |
| `approvals` / `approve` / `reject` | ✗ | BUILD (C) — sobre workflow approval gates |
| `cost` | ✗ | BUILD (L) — agregación cost_records |
| `signals list/inspect/search` | ✗ | BUILD (I) |
| `modules` | ✅ | KEEP |
| `mcp` | ✗ | BUILD (K) |
| `ask` | ✗ | BUILD (E) |

**Principio**: el CLI debe hablar con los MISMOS services que la API (ya lo hace hoy — patrón a mantener, §6).

---

## 5. Architecture Risks

1. **Misión ausente vs. dominio maduro**: agregar Mission sobre un dominio ya rico sin duplicar Workflow/AgentExecution es el riesgo #1 → Mission debe ser capa de orquestación (referencias), no un segundo motor.
2. **Enum migrations en Postgres prod**: ya mordió (agentrole LEAD_RESEARCH). Cualquier enum nuevo de Mission type requiere `ALTER TYPE ... ADD VALUE` en prod → planificar en deploy.
3. **workflow_engine sincrónico**: `execute_workflow` corre inline; para `run watch` y parallel se necesita background execution (celery/APScheduler ya están como deps).
4. **UUID vs String ids inconsistente**: algunas tablas usan `Uuid`, otras `String(hex)` (workflow, context_pack). Mantener coherencia en lo nuevo.
5. **SQLite vs Postgres divergencias**: ya mordió con Uuid/str en task_dag (fixed). Los tests corren en SQLite; prod es Postgres → agregar CI con Postgres cuando GitHub billing se resuelva.
6. **Repo name `mission-control` vs producto `Conciencia`**: renombrar repo rompe links/CI/docs → mantener repo, renombrar branding interno gradualmente (FastAPI title ya es "Mission Control" → cambiar a "Conciencia" es seguro y barato).
7. **2 tests LLM pre-existentes rojos**: requieren providers reales; documentar o mockear con fixtures (no bloquear).
8. **Duplicación potencial**: no construir otro workflow engine, otro agent registry ni otro cost tracker — extender los existentes.

---

## 6. Reuse Opportunities (no duplicar)

| Necesidad nueva | Reusar |
|---|---|
| Run de misión | `AgentExecution` + `WorkflowRun` (+ `mission_id` nullable) |
| Approval gates | `workflow_engine` step `approval: true` + frontend `/approvals` |
| Context de misión | `ContextPack` (ya canónico, con adapters) |
| Economics | `CostRecord` + `/api/v1/costs` (+ `mission_id` nullable) |
| Agent selección | `capability_matching.py` + `Agent` registry |
| Observabilidad | `system_logger` + `audit` + `traces` |
| Seguridad | `policies` + `auth` + `crypto` |
| CLI | typer + rich + `_make_session` (respeta DATABASE_URL) |

---

## 7. Propuesta Fase B (Identity & Domain Alignment)

**Objetivo**: confirmar Mission como abstracción central SIN refactor grande.

1. **Modelo `Mission`** (tabla `missions`, aditiva):
   - id, name, description, objective, type (enum), status, project_id (FK), requester_id (FK user), context_pack_id (FK nullable), workflow_id (FK nullable), agent_ids (JSON), runtime (str), approval_policy (JSON), budget (JSON: cost_limit/token_limit/runtime_limit), success_criteria (JSON), evidence_ids (JSON), outcome (JSON), timestamps.
2. **Modelo `MissionRun`** (tabla `mission_runs`): mission_id FK, status, logs (JSON), tokens/cost (snapshot), started/completed_at. (Reusa la lógica de AgentExecution pero como vista de misión.)
3. **Router `/api/v1/missions`**: CRUD + `POST /{id}/plan` (genera workflow propuesto) + `POST /{id}/run` (arranca workflow) + `GET /{id}/runs`. Todo reusando `workflow_engine`.
4. **CLI mínimo Fase C (entregable de la fase)**: `conciencia mission create/list/inspect/run` + `conciencia run list/watch` + `conciencia status` + `conciencia approvals/approve/reject`.
5. **Branding**: FastAPI title "Mission Control" → "Conciencia" (title/description), sin tocar repo name.

**Archivos esperados a cambiar:**
- `backend/app/models/mission.py` (nuevo) + `mission_run.py` (nuevo)
- `backend/app/models/__init__.py` (registrar)
- `backend/app/routers/missions.py` (nuevo) + registrar en `main.py`
- `backend/app/services/mission_service.py` (nuevo): plan/run reusando workflow_engine
- `backend/cli.py`: subcommand `mission` + `run` + `status` + `approvals`
- `backend/app/models/execution.py` (opcional): `mission_id` nullable en AgentExecution
- `backend/tests/test_missions.py` + `test_cli_missions.py` (nuevos)
- `backend/app/main.py` (title, include_router)
- `docs/` (USAGE.md, ARCHITECTURE.md)

**Migration risks:**
- Tablas nuevas = sin riesgo en prod (create_all idempotente + sync_schema).
- Enums: `mission_type` y `mission_status` nuevos — aplicar `ALTER TYPE` en prod al deploy (o usar String para evitar el dolor; decisión: **String** con validación Pydantic, igual que workflow.status — evita migrations de enum en Postgres).
- `AgentExecution.mission_id` nullable = seguro.

**Test plan (Fase B):**
- CRUD mission (crear/listar/inspeccionar/borrar)
- mission plan → genera workflow definition válida
- mission run → crea MissionRun + ejecuta workflow con approval gate
- CLI: mission create/list/inspect/run + run list + approvals (happy path + aprobar)
- Regression: suite completa sigue verde (209+)

---

## 8. Orden de implementación (próximas fases)

```
FASE B (siguiente)  → Mission + MissionRun + /missions API + CLI mission/run/status/approvals
FASE C              → init/doctor/project inspect + workflow/tool/runtime/model list CLI
FASE D              → project detection (.conciencia/) + stack detection
FASE E              → conciencia ask (NL → mission proposal con costo estimado)
FASE F              → teams + parallel execution
FASE G              → harnesses versionables
FASE H              → run watch (logs estructurados, tokens, costos en vivo)
FASE I              → signals + evidence
FASE J              → context packs integrados a missions
FASE K              → WebMCP
FASE L              → economics por misión (cost/outcome)
```

**Regla de oro (§42)**: cada feature debe responder "¿mejora crear/orquestar/ejecutar/gobernar/observar/aprender de Missions?".

---

*Documento de auditoría — Fase A completa. Validación: suite 209 verdes (2 pre-existentes), typecheck frontend OK, CLI smoke OK. Commit base: 1545f78.*
