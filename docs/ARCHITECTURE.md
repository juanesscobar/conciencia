# 🏗️ Arquitectura Técnica

## Flujo canónico A–L (actualizado 2026-09-01, audit final)

```
User / CLI / API (JWT)
        ↓
MISSION (por qué existe el trabajo) — missions, estado, budget, approval_policy
        ↓
WORKFLOW (cómo se secuencia) — steps declarativos: agent_id | capabilities | approval | parallel | webmcp
        ↓
TEAM / AGENT (quién trabaja) — resolución: agent_id → team → mission.agent_ids pool → registry global
        ↓        (capabilities = soft · required_capabilities = hard)
HARNESS (cómo se ejecuta) — instructions/context/tools/guardrails/runtime.allowed/output_contract, versionado
        ↓
CONTEXT PACK (qué información ahora) — retrieval keywords (título 3x/claves 2x/valores 1x), top-K, max_chars
        ↓
TOOLS (qué capacidad externa) — WebMCP (step webmcp) · MCP · runtimes externos
        ↓
EXECUTION — adapters generic/openclaw; bloques paralelos con sesión propia por child
        ↓
OBSERVABILITY (qué pasó) — workflow_runs.events + step_results enriquecidos → MissionRun logs/tokens/cost
        ↓
SIGNALS + EVIDENCE (qué se encontró / qué lo respalda) — marcadores SIGNAL:/EVIDENCE:, provenance mission/run/step/agent
        ↓
APPROVAL (gobernanza humana) — gate de ejecución (paused → approve/reject; sin re-ejecución)
        ↓
ECONOMICS (cuánto costó) — costos LLM/tools/total, tokens, providers/models, external costs
```

Separaciones de concepto (no colapsar): Agent ≠ Harness ≠ Context Pack ≠ Tool ≠ Workflow ≠ Team ≠
Mission ≠ Observability ≠ Signal ≠ Evidence ≠ Approval ≠ Economics.

Persistencia (tablas): missions, mission_runs, workflows, workflow_runs (+events), teams, agents,
harnesses (+versions), context_packs, signals, evidence, agent_executions, cost_records,
settings, projects, tasks, users, audit_events.

---

## Stack Tecnológico

### Backend
- **FastAPI** — API REST async, moderna, typed
- **PostgreSQL** — datos estructurados (proyectos, tareas, métricas)
- **Redis** — cache, sesiones, colas de trabajo
- **Celery** — background tasks, scheduled jobs
- **SQLAlchemy 2.0** — ORM con type hints
- **Pydantic** — validación y serialización

### Frontend
- **React 18** + TypeScript
- **TanStack Query** — server state management
- **Tailwind CSS** — styling
- **Recharts** — visualizaciones de métricas
- **Vite** — build tool rápido

### Integraciones
- **GitHub API** — repos, commits, PRs, issues
- **Telegram Bot API** — notificaciones y comandos
- **Docker + Docker Compose** — local dev y deployment

### Infra
- **Railway / Render / Fly.io** — hosting (start simple)
- **GitHub Actions** — CI/CD

---

## Modelo de Datos

### Core Entities

```
Project
├── id: UUID
├── name: string
├── description: text
├── status: active|paused|archived|completed
├── priority: p0|p1|p2|p3
├── category: core|legacy|portfolio
├── github_repo: string
├── tech_stack: json
├── created_at: datetime
├── updated_at: datetime
└── metrics: ProjectMetrics

Task
├── id: UUID
├── project_id: FK → Project
├── title: string
├── description: text
├── status: backlog|todo|in_progress|review|done|cancelled
├── priority: critical|high|medium|low
├── assignee: string (agent name)
├── due_date: date
├── github_issue: string
├── github_pr: string
├── created_at: datetime
├── updated_at: datetime
└── subtasks: Task[]

Agent
├── id: UUID
├── name: string
├── emoji: string
├── role: dev|ops|qa|pm|rd|comms|fin|admin
├── status: active|paused
├── personality: text
├── capabilities: string[]
├── autonomy_level: full|preview|approval
└── created_at: datetime

Metric
├── id: UUID
├── project_id: FK → Project (nullable)
├── agent_id: FK → Agent (nullable)
├── category: industry|personal|custom
├── name: string
├── value: float
├── target: float
├── unit: string
├── period: daily|weekly|monthly
├── recorded_at: datetime
└── source: string

Activity
├── id: UUID
├── project_id: FK → Project
├── agent_id: FK → Agent
├── type: commit|pr|deploy|release|comment|task_change
├── description: text
├── metadata: json
├── created_at: datetime
└── external_url: string

Sprint
├── id: UUID
├── name: string
├── start_date: date
├── end_date: date
├── status: planning|active|completed
├── goals: string[]
└── tasks: Task[]
```

---

## Estructura de Carpetas

```
mission-control/
├── README.md                    # Este archivo
├── ARCHITECTURE.md              # Este archivo
├── agents/
│   ├── dev/SOUL.md
│   ├── ops/SOUL.md
│   ├── qa/SOUL.md
│   ├── pm/SOUL.md
│   ├── rd/SOUL.md
│   ├── comms/SOUL.md
│   ├── fin/SOUL.md
│   └── admin/SOUL.md
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings
│   │   ├── database.py          # SQLAlchemy setup
│   │   ├── models/              # DB models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── routers/             # API endpoints
│   │   ├── services/            # Business logic
│   │   ├── agents/              # Agent implementations
│   │   ├── integrations/        # GitHub, Telegram, etc.
│   │   └── tasks.py             # Celery tasks
│   ├── tests/
│   ├── alembic/                 # Migrations
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/          # Reusable UI
│   │   ├── pages/               # Route pages
│   │   ├── hooks/               # Custom hooks
│   │   ├── services/            # API clients
│   │   ├── store/               # State management
│   │   └── types/               # TypeScript types
│   ├── public/
│   ├── index.html
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── .github/
    └── workflows/
        ├── ci.yml
        └── deploy.yml
```

---

## API Endpoints (V1)

### Projects
```
GET    /api/v1/projects           # List projects
POST   /api/v1/projects           # Create project
GET    /api/v1/projects/{id}      # Get project details
PUT    /api/v1/projects/{id}      # Update project
DELETE /api/v1/projects/{id}      # Delete project
GET    /api/v1/projects/{id}/metrics  # Project metrics
GET    /api/v1/projects/{id}/activity # Activity feed
```

### Tasks
```
GET    /api/v1/tasks              # List tasks (with filters)
POST   /api/v1/tasks              # Create task
GET    /api/v1/tasks/{id}         # Get task details
PUT    /api/v1/tasks/{id}         # Update task
DELETE /api/v1/tasks/{id}         # Delete task
POST   /api/v1/tasks/{id}/assign  # Assign to agent
```

### Agents
```
GET    /api/v1/agents             # List agents
GET    /api/v1/agents/{id}        # Get agent details
GET    /api/v1/agents/{id}/tasks  # Agent's tasks
GET    /api/v1/agents/{id}/activity
```

### Metrics
```
GET    /api/v1/metrics            # List metrics
POST   /api/v1/metrics            # Record metric
GET    /api/v1/metrics/dashboard  # Dashboard data
GET    /api/v1/metrics/industry   # Industry benchmarks
```

### GitHub Integration
```
POST   /api/v1/integrations/github/sync  # Sync repos
GET    /api/v1/integrations/github/repos # List connected repos
```

### Telegram Bot
```
POST   /api/v1/telegram/webhook   # Webhook handler
```

---

## Agente Implementación

Los agentes se implementan como servicios con:

```python
class Agent(ABC):
    name: str
    emoji: str
    role: AgentRole
    autonomy_level: AutonomyLevel
    
    @abstractmethod
    async def handle_task(self, task: Task) -> TaskResult:
        """Process a task assigned to this agent"""
        pass
    
    @abstractmethod
    async def generate_update(self) -> StatusUpdate:
        """Generate daily/status update"""
        pass
    
    async def request_approval(self, action: Action) -> Approval:
        """Request CEO approval for action"""
        pass
```

---

## Flujos de Trabajo

### 1. Sync GitHub → Mission Control
```
GitHub webhook → API → Parse payload → Update DB → Notify agents
```

### 2. Daily Status Update
```
Celery scheduled task → Collect data from all agents → Generate summary → Telegram notification
```

### 3. Agent Execution
```
Task assigned → Agent picks up → Execute → Update status → If needs approval → Request → Wait → Continue
```

### 4. Deploy Pipeline
```
PR merged → GitHub Actions → Build → Deploy staging → Notify → QA validation → Preview to CEO → Deploy prod
```

---

## Seguridad

- **API Keys:** En variables de entorno, nunca en código
- **GitHub:** Solo read access inicial, write con permissions específicas
- **Telegram:** Webhook con secret token
- **DB:** PostgreSQL con SSL, backups automáticos

---

## Escalabilidad (Futuro)

- **v1:** Monolito simple, un container
- **v2:** Separar agentes a workers independientes
- **v3:** Queue system (RabbitMQ/SQS) para agentes
- **v4:** Microservicios si justifica complejidad

---

*"Empieza simple, escala cuando duele."*


---

## LeadHunter Intelligence Engine — E2E final (spec §52, Fases 1-11)

Flujo completo verificado (test `tests/test_e2e_final.py` + suite de 140 tests):

> "playas de autos usados en Ciudad del Este"

| # | Paso | Dónde |
|---|------|-------|
| 1 | Entiende la request (NL) | `POST /leads/search/interpret` → SearchQuery (categoría automotriz, región CDE, país PY) |
| 2 | Infiere PY del workspace | `GeographicScope.from_env()` (SEARCH_DEFAULT_COUNTRY=PY, allowlist, scope) |
| 3 | Convierte a filtros estructurados | `SearchQuery` canónico (category/region/city/required_fields) |
| 4 | Busca en fuentes | SearchEngine (filtros + full-text por tokens OR + cache TTL) |
| 5 | Normaliza resultados | `normalization.py` + `entity.py` (dedupe v2 indexado) |
| 6 | Deduplica empresas | `normalized_name/domain/phone` (lookups indexados) |
| 7 | Rankea | `ranking.py`: SearchRelevance (query) ≠ LeadScore ≠ OpportunityScore; RankingWeights configurables |
| 8 | Explica cada match | `explain()` → reasons ("why this lead matches", spec §34) |
| 9 | Muestra data quality | `data_quality_score` 0-100 (completitud + frescura + fuente) |
| 10 | Permite enrichment | `POST /leads/{id}/enrich/agent` (LeadResearch/Classification/ContactDiscovery con permisos ALLOW/DENY) |
| 11 | Guarda en LeadHunter | CRUD + listas + búsquedas guardadas |
| 12 | Envía a CRM (futuro) | Listas + export CSV/JSON + pipeline (propuestas, PDF, WhatsApp/email) |
| 13 | Misma operación por CLI | `conciencia search "..." --country PY` (mismos services) |
| 14 | Agente puede operar | AgentRuntime + multi-runtime (generic/claude_code/codex/opencode/openclaw) |

### Definition of Done (spec §50 — 21/21)

- [x] Search E2E · [x] Country default PY · [x] Scope configurable · [x] No mundo accidental
- [x] NL query · [x] Filtros editables · [x] Search y filtros coherentes
- [x] OSM/provider abstraído · [x] Rate limits respetados · [x] Normalización · [x] Dedupe
- [x] Relevance rankeada · [x] Lead Score independiente · [x] Data quality visible
  · [x] Provenance preservada (meta: osm_id/lat/lon/source_detail; source_records table = mejora futura)
- [x] Fundación semántica · [x] Search reutilizable por agentes · [x] CLI mismos services · [x] API/UI misma lógica
- [x] Tests críticos (140) · [x] Funcionalidad existente intacta

### Módulos nuevos (Fases 1-11)

```
backend/app/
├── core/                  # Conciencia Core (spec §20/§21)
│   ├── config.py          # settings unificados (env+DB)
│   ├── interfaces.py      # Protocols: GeoProvider, VectorBackend, LeadSource
│   ├── cache.py           # TTLCache thread-safe (spec §36)
│   └── agent_runtime.py   # multi-runtime CLI seguro (Fase 9)
└── modules/leadhunter/
    ├── geo.py             # GeographicScope + GeoProvider (OSM) (F1)
    ├── nlu.py             # NL → SearchQuery (F2)
    ├── search.py          # SearchEngine + cache (F2/F10)
    ├── normalization.py   # normalize_company/domain/phone (F3)
    ├── entity.py          # dedupe v2 indexado (F3)
    ├── ranking.py         # scores separados + weights + explain (F4)
    ├── embeddings.py      # búsqueda semántica (F5)
    ├── agents.py          # agentes LeadHunter (F8)
    ├── helpers.py         # helpers compartidos (F7)
    └── endpoints/         # search/hunt/lists/proposals/leads (F7)
```

### CLI (Fase 6)

`conciencia health|search|leads list|export|lead inspect|score|enrich|hunt|config get|set|agents|modules`
(entry point `conciencia` en backend/pyproject.toml; `pip install -e .`)
