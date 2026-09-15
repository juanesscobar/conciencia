# 📖 Guía de Uso — Conciencia Platform

> Control Plane para trabajo autónomo con IA: agentes, leads, email, gobernanza y auditoría.
> Esta guía cubre las **3 interfaces**: 🌐 Web, 💻 CLI (`conciencia`) y 🔌 API REST.

---

## Tabla de contenidos

1. [Instalación](#1-instalación)
2. [Primeros pasos](#2-primeros-pasos)
3. [🌐 Uso Web](#3-uso-web)
4. [💻 Uso CLI](#4-uso-cli)
5. [🔌 Referencia API](#5-referencia-api)
6. [⚙️ Configuración](#6-configuración)
7. [❓ FAQ y solución de problemas](#7-faq-y-solución-de-problemas)

---

## 1. Instalación

### Opción A — Docker (producción, recomendada)

```bash
git clone https://github.com/juanesscobar/mission-control.git
cd mission-control
cp .env.example .env        # completá POSTGRES_PASSWORD, REDIS_PASSWORD, SECRET_KEY, LOCAL_ADMIN_PASSWORD
docker compose up -d --build
```

Abrí `http://localhost` (o la IP del server). Solo nginx expone puertos; Postgres y Redis quedan en red interna.

### Opción B — Desarrollo local sin Docker

```bash
# Backend (puerto 8000)
cd backend
python -m venv .venv && .venv\Scripts\activate    # Windows
pip install -r requirements.txt
pip install -e .                                   # instala el CLI `conciencia`
uvicorn app.main:app --reload --port 8000

# Frontend (puerto 5173)
cd frontend
npm install
npm run dev
```

- API: `http://localhost:8000/docs` (Swagger interactivo)
- Web: `http://localhost:5173`

> 🧪 **Sin API keys?** El LLM Harness corre en *modo simulado* y la búsqueda semántica usa embeddings simulados determinísticos. Toda la plataforma se puede explorar sin gastar un centavo.

### Opción C — Terminal local (Windows/Git Bash, uso diario ⭐)

Instalá el wrapper global `conciencia` (apunta al venv del backend, fuerza UTF-8 y usa la DB local con ruta absoluta):

```bash
# El venv del backend ya tiene el entry point instalado (pip install -e .)
# Los scripts viven en ~/bin (ya está en PATH en Git Bash):
#   ~/bin/conciencia            → wrapper (fuerza UTF-8, DB local absoluta)
#   ~/bin/conciencia-prod-setup → abre túnel SSH + guarda credenciales
```

Uso desde cualquier directorio:

```bash
conciencia health          # DB local (SQLite, 835 leads)
conciencia search "farmacias" --country PY
conciencia leads list --status qualified
conciencia map
```

**Modo PROD (datos reales de Hetzner vía túnel SSH):**

```bash
conciencia-prod-setup       # descubre IP del contenedor db + abre túnel + guarda credenciales
CONCIENCIA_ENV=prod conciencia health    # 799 leads reales de prod
```

Notas:
- El wrapper fuerza `PYTHONIOENCODING=utf-8` (rich/typer necesitan UTF-8 en Windows).
- El modo prod descubre la IP interna del contenedor `db` (el compose NO publica 5432) y tunela por SSH.
- Los scripts viven en `~/bin/conciencia` y `~/bin/conciencia-prod-setup` (fuera del repo).

---

## 2. Primeros pasos

1. **Login** con el admin seedeado desde `LOCAL_ADMIN_PASSWORD` (usuario `admin`).
2. **Dashboard** → mirá métricas, activity feed y la Agent Office.
3. **Leads** → tocá **"Cazar leads ahora"** para poblar la base desde Overpass/OSM (Gran Asunción por defecto).
4. **Agentes** → ejecutá un agente (dev, ops, qa, research…) y mirá el audit trail.
5. **Settings** → configurá DeepSeek, WhatsApp, weights de ranking y runtimes.

---

## 3. Uso Web

Todas las pantallas están bajo `/` con login. Hay dos modos (spec §36): **Operator** (control total) y **Client** (solo resultados), seleccionables en la sidebar (por rol: ceo/admin → operator; member/viewer → client).

| Ruta | Pantalla | Qué hace |
|---|---|---|
| `/` | **Dashboard** | Métricas, actividad reciente, Agent Office (8 agentes trabajando) |
| `/projects` · `/projects/:id` | **Projects** | Proyectos + GitHub: commits, PRs, issues en vivo |
| `/tasks` | **Tasks** | Tareas con DAG de dependencias (READY/ASSIGNED/BLOCKED) |
| `/agents` | **Agents** | 11 agentes (8 roles + 3 LeadHunter) con SOUL.md, permisos ALLOW/DENY, runtime selector y ejecución |
| `/workflows` | **Workflows** | Flujos multi-paso con approval gates |
| `/approvals` | **Approvals** | Aprobaciones human-in-the-loop pendientes |
| `/context` | **Context** | Context packs para sesiones de agentes |
| `/governance` | **Governance** | Proyectos, sprints, métricas, reportes, decisiones |
| `/traces` | **Traces** | Trazas de ejecución de agentes/misiones |
| `/costs` | **Costs** | Costos por agente/modelo/proveedor |
| `/audit` | **Audit** | Log de auditoría completo (quién hizo qué) |
| `/leads` | **Leads** | 🎯 Lead Hunter: caza, búsqueda, pipeline, enrich, propuestas, listas |
| `/email` | **Email** | Módulo de email multi-proveedor (SMTP/IMAP), credenciales cifradas |
| `/settings` | **Settings** | Config: ranking weights, runtimes, DeepSeek, WhatsApp, embeddings, scheduler |

### 🎯 Leads (Lead Hunter Intelligence)

El módulo estrella. Pipeline completo: **cazar → enriquecer → rankear → calificar → proponer → enviar**.

- **Cazar leads**: botón *Cazar leads ahora* (fuente Overpass/OSM, sin API key). Dedupe automático por nombre normalizado, dominio y teléfono.
- **Buscar**: free-text con NLU (interpreta "empresas logísticas en Asunción que vendan online") + filtros estructurados (país, región, ciudad, categoría, industria, segmento, online, score mínimo) + orden (score/company/newest).
- **Semántica**: botón 🧬 — búsqueda por embeddings (cosine). Sin API key usa embeddings simulados determinísticos; con provider configurado, embeddings reales.
- **Score Intelligence**: 4 puntajes separados — **Search Relevance** (match de búsqueda), **Lead Score** (calidad del lead), **Opportunity Score** (oportunidad comercial) y **Data Quality** (completitud de datos). Con "why this match": razones explicables de cada puntaje. Badges O:n/Q:n por fila.
- **Enriquecer**: botón por fila (raspa el website → email/tel reales, anti-junk) y/o agente IA `enrich` (research/classify/contacts).
- **Pipeline kanban**: new → contacted → qualified → proposal → won/lost. Acciones rápidas por lead: contactar, calificar, ganar/perder, nota.
- **Propuestas**: generación de PDF + envío por email/WhatsApp.
- **Listas y búsquedas guardadas**: organizá leads en listas, persistí búsquedas.
- **Export**: CSV/JSON (botón o endpoint).
- **Scheduler**: caza automática configurable (default lunes 09:00 Asunción) vía APScheduler.

---

## 4. Uso CLI

El CLI `conciencia` usa **la misma lógica de dominio** que la web/API (cero backend duplicado). Se instala con `pip install -e .` desde `backend/`.

```bash
conciencia --help          # lista todos los comandos
conciencia mission --help   # ayuda de un grupo (cualquier grupo/comando sirve)
```

### health

```bash
conciencia health
# Estado: DB, nº de leads, nº de agentes, embeddings (enabled/disabled + modelo)
```

### search — búsqueda de leads (misma lógica que POST /leads/search)

```bash
conciencia search "empresas logísticas" --country PY --region "Asunción" --online website
conciencia search "farmacias" --min-score 60 --sort score -n 30
conciencia search --category "salud" --segment pyme --json
```

Filtros: `--country/-c`, `--region/-r`, `--city`, `--category`, `--industry`, `--segment` (pyme|mediana|corporativo), `--online` (website|email|phone|any), `--min-score`, `--sort` (newest|oldest|score|company), `--limit/-n` (1-200), `--json`.

### leads — listar y exportar

```bash
conciencia leads list --status qualified --region Asunción -n 100
conciencia leads list --json
conciencia leads export --format csv --out leads.csv
conciencia leads export --format json --status new --out leads.json
```

### lead — inspeccionar, scorear, enriquecer

```bash
conciencia lead inspect <lead_id>            # detalle completo + razones
conciencia lead inspect <lead_id> --json
conciencia lead score <lead_id>              # 4 scores separados + explicación
conciencia lead enrich <lead_id>             # enrich desde el website (email/tel)
```

### hunt — cazar leads (misma lógica que POST /leads/hunt/run)

```bash
conciencia hunt                              # caza overpass con config por defecto
conciencia hunt --industry "distribuidoras" --region "Central" --limit 100
conciencia hunt --source overpass --segment pyme
```

### config — settings persistentes (tabla settings + env)

```bash
conciencia config get                        # lista todas las settings
conciencia config get search.country         # lee una (mapea a SEARCH_DEFAULT_COUNTRY)
conciencia config set search.country BR      # persiste y aplica
```

Claves mapeadas: `search.country`, `search.region`, `search.city`, `search.scope`, `leadhunter.cron`, `leadhunter.bbox`, `embeddings.enabled/model/provider/backend`, `ranking.weights`.

### agents y modules

```bash
conciencia agents                            # lista agentes registrados (tabla agents)
conciencia agents --json
conciencia modules                           # lista módulos del sistema y su estado
conciencia modules --json
```

### mission — misiones (Fase B: Mission = unidad central de trabajo)

> IDs: aceptan el UUID completo **o el corto con prefijo** `M-6998bc52`
> (`R-` runs, `T-` teams, `H-` harnesses, `S-` signals, `W-` workflows).

```bash
conciencia mission create "Auditar arquitectura" "Identificar deuda técnica" --type technical-audit
conciencia mission list
conciencia mission inspect MISSION_ID    # sin ID: usa la única misión activa (o lista candidatas)
conciencia mission plan MISSION_ID       # genera workflow por defecto del tipo
conciencia mission run MISSION_ID        # crea MissionRun + ejecuta workflow
conciencia mission watch MISSION_ID      # observa en vivo el último run de la misión
conciencia approvals                     # misiones esperando aprobación
conciencia approve MISSION_ID STEP_INDEX # aprueba el step (MISSION_ID/STEP_INDEX son placeholders)
conciencia reject MISSION_ID STEP_INDEX  # rechaza el step
conciencia run list --mission MISSION_ID
conciencia run inspect RUN_ID
conciencia run watch RUN_ID              # en vivo: status, costo, tokens y timeline
conciencia status                        # overview: misiones por estado + approvals + runtimes
```

Tipos de misión: research, software-development, code-review, debugging, architecture, testing, devops, deployment, technical-audit, agent-design, workflow-design, automation, integration, data-analysis, product-research, competitive-research, technical-discovery, lead-research, technical-proposal.

Ciclo completo: `create → plan → run → (waiting_approval) → approve → completed`. Los workflows con step `approval: true` quedan pausados esperando decisión humana (human-in-the-loop).

Con team (Fase F): `conciencia mission create "..." "..." --team <team_id>` → la misión toma el runtime default del team y sus miembros como agentes; los steps se resuelven DENTRO del team primero (fallback al registry global).

### team — equipos de agentes (Fase F: Agent/Team Orchestration)

Un Team agrupa agentes especializados (ej: squad de investigación). Una misión puede apuntar a un team y los steps del workflow resuelven agentes por capabilities dentro del team primero.

```bash
conciencia team create "Research Squad" --purpose "Investigación" --members <agent_id>[,<agent_id>] [--runtime generic]
conciencia team list [--status active]
conciencia team inspect <team_id>        # detalle + miembros
conciencia team members-add <team_id> <agent_id>
conciencia team members-remove <team_id> <agent_id>
conciencia team match research,reporting # teams que cubren capabilities (score)
```

API: `POST/GET/PATCH/DELETE /api/v1/teams/`, `POST/DELETE /api/v1/teams/{id}/members`, `GET /api/v1/teams/{id}/members`, `GET /api/v1/teams/match?capabilities=a,b`.

### Workflows con pasos paralelos (Fase F)

Un step puede ser un BLOQUE PARALELO (fan-out → fan-in): los children corren concurrentemente y el bloque espera a todos; si uno falla, el bloque falla conservando outputs parciales. Se define en el API de workflows con `parallel: true` + `steps`:

```json
{"name": "discovery", "parallel": true, "max_parallel": 2, "steps": [
  {"name": "discover-leads", "task": "...", "required_capabilities": ["leads.read"]},
  {"name": "enrich-websites", "task": "...", "required_capabilities": ["website_fetch"]}
]}
```

El workflow default de `lead-research` ya usa un bloque paralelo (discovery ⚡ + enrich en paralelo, luego classify, luego approval). `conciencia ask` marca los steps paralelos con ⚡ y sugiere el mejor team si existe.

### harness — contratos versionados de ejecución (Fase G: Harness Layer)

Un Harness formaliza CÓMO ejecuta un agente, independiente de quién es: **instructions** (system prompt con placeholders `{objective}` `{project_name}` `{context_pack}`), **context** (template + max_chars), **tools** (allow/deny), **validation** (reglas de input/output), **guardrails** (constraints), **runtime** (allowed runtimes) y **output_contract** (formato + campos requeridos, validado post-dispatch). Se versiona con `new_version` (historial en `versions`) y se reutiliza entre misiones.

```bash
conciencia harness create "Research Harness" --spec harness_spec.json   # spec JSON → draft
conciencia harness activate <harness_id>                                # solo activos se usan
conciencia harness list [--status active]
conciencia harness inspect <harness_id>                                 # spec + historial
conciencia harness validate <harness_id> "output real"                  # prueba contra el contrato
conciencia mission create "..." "..." --harness <harness_id>            # misión con harness
```

Ejemplo de spec:
```json
{
  "instructions": "Eres un investigador senior. Objetivo: {objective}.",
  "context": {"template": "Misión: {objective}", "max_chars": 4000},
  "tools": {"allow": ["web_search", "read"], "deny": ["write"]},
  "guardrails": ["no_network"],
  "runtime": {"default": "generic", "allowed": ["generic", "claude_code"]},
  "output_contract": {"format": "json", "required_fields": ["summary", "findings"]}
}
```

Comportamiento: instructions reemplazan el system prompt (template renderizado con el contexto de la misión), el runtime del agente debe estar en `allowed` (si no, el step falla con error claro), y el output se valida contra `output_contract`/`validation` después del dispatch (si no cumple, el step falla). API: `/api/v1/harnesses` (CRUD + `/activate` + `/archive` + `/validate`). Los steps de workflow aceptan `harness_id` propio (override del de la misión).

### signal — hallazgos trazables con evidencia (Fase I)

Una **Signal** es un hallazgo de una misión (insight/risk/opportunity/decision/lead/finding) con trazabilidad completa: de qué misión/run/step/agente salió y qué **Evidence** lo respalda (quote, URL, dato, tool_result). Las evidencias se agregan a `missions.evidence_ids` (vista global de la misión).

```bash
conciencia signal list [--mission <id>] [--type risk] [--status new]
conciencia signal inspect <signal_id>      # detalle + evidencia
conciencia signal add <mission_id> "Título" --type risk --summary "..." --evidence "..."
conciencia signal extract <mission_id>     # extracción automática desde outputs
```

**Extracción automática**: cuando una misión se completa (o con `signal extract`), los outputs de los steps se escanean por marcadores — cada uno genera una Signal con su Evidence:

```text
SIGNAL: risk| Mercado saturado | Alta competencia en refrigerado
EVIDENCE: competidores con flota propia en Asunción
EVIDENCE: https://ejemplo.com/mercado
SIGNAL: oportunidad
```

API: `/api/v1/signals` (CRUD + `/extract` + `/{id}/evidence`).

### context — retrieval eficiente de contexto (Fase J)

Los agentes reciben **solo el contexto relevante**: los ContextPacks se rankean por relevancia al objetivo de la misión (score por keywords, sin LLM) y se ensambla un contexto **acotado** a `max_chars` — nunca el proyecto entero.

```bash
conciencia context retrieve "investigar el mercado de logística refrigerada" [--project <id>] [--limit 3]
conciencia context assemble "investigar logística refrigerada" --max-chars 4000
```

- `retrieve`: packs rankeados con score y términos matcheados (título 3x, claves 2x, valores 1x).
- `assemble`: contexto final desde los top-K packs, truncado por pack para respetar el presupuesto (`truncated: true` si no entró todo).
- **En misiones**: si la misión tiene `context_pack_id` explícito se usa ese pack; si no, se recuperan los top-2 por el objetivo. El harness lo inyecta con el placeholder `{context_pack}` en su template de contexto.

API: `GET /api/v1/context-packs/retrieve?query=&project_id=&limit=`, `POST /api/v1/context-packs/assemble` (además del CRUD/generate/export existente).

### webmcp — interactuar con apps web WebMCP-enabled (Fase K)

Una MISIÓN puede interactuar con una aplicación web WebMCP-enabled (que expone `window.webmcp`) y **preservar la evidencia** de cada interacción.

```bash
# correr la demo app (formulario + contador) en otro terminal
conciencia webmcp demo --port 8765

# ejecutar un script de acciones contra la app
conciencia webmcp run http://127.0.0.1:8765 "input:#name:Juan,input:#email:j@x.com,submit,click:#increment"
```

**En workflows/misiones** — un step con `webmcp` ejecuta acciones contra la app sin agente LLM:

```json
{"name": "llenar-form", "webmcp": {"url": "http://127.0.0.1:8765", "actions": [
  {"type": "input", "selector": "#name", "value": "Juan"},
  {"type": "submit", "selector": "form"}
]}}
```

Acciones: `input` (selector:valor), `click`, `submit`, `navigate`. El step registra en observabilidad sus `actions`/`tool_calls` y guarda `webmcp_evidence` (action log + snapshot). Al completarse (o quedar en waiting_approval), la evidencia se promueve automáticamente a **Signal + Evidence** (Fase I) vinculada a la misión — DoD: interactúa y preserva evidencia.

API: `POST /api/v1/webmcp/run {url, actions}` · `GET /api/v1/webmcp/demo`. Demo: `python -m app.services.webmcp.demo_runner --port 8765`.

### economics — economía inspeccionable (Fase L)

Sin billing: solo inspección de la economía de misiones — costos LLM/tools, tokens, modelos/providers usados, runtimes, acciones/tool calls y outcomes.

```bash
conciencia economics summary                    # plataforma (últimos 30 días)
conciencia economics summary --mission <id>     # detalle de una misión
conciencia economics record-external <run_id> <tool> <cost_usd>   # costo de tool/servicio externo
```

- `record-external` guarda el costo en `mission_runs.external_costs` y actualiza `cost_usd.tools/total` del run.
- Los costos LLM provienen de los `cost_records` del LLM Harness (por llamada real) + los `step_results` agregados.

API: `GET /api/v1/economics/` (platform, `?days=`), `GET /api/v1/economics/missions/{id}`, `POST /api/v1/economics/external-cost`.

### Observabilidad (Fase H)

Cada ejecución produce un **timeline estructurado** (`workflow_runs.events`): `workflow_started`, `step_started`, `step_completed`, `step_failed`, `workflow_failed`, `approval_required/approved/rejected`, `parallel_completed` — cada evento con step, agente, runtime, provider, model, tokens, costo, duración y error. Los `step_results` registran por step: **tokens** (prompt/completion/total), **costo**, **runtime**, **provider**, **model**, **duration_ms**, **actions**, **tool_calls** y **failure state** (error exacto).

```bash
conciencia run inspect <run_id> --steps   # desglose por step + timeline
conciencia run inspect <run_id> --json    # todo estructurado (incluye step_results + events)
conciencia run watch <run_id>             # en vivo: status, costo, tokens y timeline
```

El MissionRun expone: `logs` (timeline espejado como líneas legibles), `tokens` (agregados de todos los steps, incluye children paralelos) y `cost_usd` (desglose llm/tools/total). Con `--json` en run inspect obtenés el detalle completo para pipelines.

### Fase C — Foundation: init, doctor, agent, workflow, runtimes

```bash
conciencia init [dir]                  # detecta git/stack/CI y crea .conciencia/
conciencia doctor                      # diagnóstico: DB, tablas, runtimes, embeddings
conciencia agent inspect <id|rol>      # detalle: SOUL, capabilities, permisos, runtime
conciencia agent run <id|rol> "tarea" [--runtime generic]   # ejecuta el agente
conciencia workflow                    # lista workflows
conciencia workflow-inspect <id>       # steps de un workflow
conciencia workflow-run <id>           # ejecuta un workflow directo
conciencia runtime                     # runtimes + salud de binarios
conciencia tool                        # tools / servidores MCP
conciencia model                       # providers/modelos en uso
conciencia run-watch <run_id>          # observa un run en vivo (estado/costo/logs)
```

> `agent run` sin `DEEPSEEK_API_KEY` responde "LLM no configurado" (modo real requiere key en Settings; el adapter generic es el motor embebido).

### ask - misión desde lenguaje natural (Fase E: Mission Planning)

Convierte texto natural en una propuesta estructurada de misión (tipo, agentes sugeridos por capabilities, TEAM sugerido si existe (Fase F), runtime, workflow, costo estimado y criterios de éxito). Funciona 100% por reglas, sin API keys. La creación requiere confirmación humana (o `--yes`).

```bash
conciencia ask "investigar el mercado de logística en Paraguay"   # propuesta → confirmar → crear
conciencia ask "implementar un módulo de reportes" --yes          # crea directo
conciencia ask "auditar el backend" --json                        # propuesta como JSON (no crea nada)
```

```text
📋 Propuesta de misión — tipo: research
   Nombre: investigar el mercado de logística en Paraguay
   Runtime: generic
   Costo est.: $0.0013 · 2100 tokens (deepseek/deepseek-chat)
   Agentes sugeridos:
     • ResearchBot (rd) — 100% match · score 100 · generic/deepseek/deepseek-chat
   Workflow:
     0: research
     1: synthesis
     2: approval 🔒 aprobación
   Criterios de éxito:
     • resultado documentado
     • evidencia adjunta
✅ Misión creada: ... · Siguiente: conciencia mission plan <id>
```

Clasificación de intentos: technical-audit, code-review, debugging, testing, deployment, devops, architecture, data-analysis, competitive-research, product-research, technical-discovery, lead-research, technical-proposal, integration, automation, agent-design, workflow-design, research, software-development (fallback). API: `POST /api/v1/ask` (propuesta) y `POST /api/v1/ask/create` (confirmación → misión).

### map - mapa conceptual

```bash
conciencia map                              # grafo ASCII del flujo completo de la plataforma
```

Imprime un mapa conceptual del pipeline en la terminal: cazar leads → buscar/rankear →
enriquecer → pipeline CRM → proponer/exportar, más los comandos de operación. Ideal para
orientarse rápido o pegar en documentación.

---

## 5. Referencia API

Base: `http://<host>:8000` · Auth: `POST /api/v1/auth/login` → token JWT → header `Authorization: Bearer <token>`. Swagger en `/docs`.

### Auth
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/auth/register` | Registro |
| POST | `/api/v1/auth/login` | Login → JWT |
| GET | `/api/v1/auth/me` | Usuario actual |

### Leads (`/api/v1/leads`, requiere auth)
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/` | Listar leads (filtros por query params) |
| POST | `/` | Crear lead |
| GET | `/{id}` · DELETE `/{id}` | Detalle / eliminar |
| POST | `/search` | Búsqueda NL + filtros estructurados |
| POST | `/search/interpret` | Interpreta texto → SearchQuery |
| POST | `/search/semantic` · GET `/search/semantic/status` | Búsqueda semántica (embeddings) |
| GET | `/ranking/weights` · PUT `/ranking/weights` | Ponderación del ranking (admin) |
| GET | `/export` | Export CSV/JSON |
| GET | `/regions` · GET `/stats` | Catálogo y estadísticas |
| POST | `/hunt/run` | Ejecutar caza de leads |
| GET | `/hunt/sources` · GET `/hunt/runs` | Fuentes e historial de cazas |
| POST | `/jobs` · GET `/jobs` · GET `/jobs/{id}` · POST `/jobs/{id}/cancel` · POST `/jobs/{id}/retry` | Jobs async de caza |
| POST | `/{id}/enrich-website` | Enrich web (email/tel) |
| POST | `/{id}/enrich/agent` | Enrich con agente IA |
| POST | `/{id}/contact` · `/qualify` · `/won` · `/lost` · `/note` | Transiciones de pipeline |
| GET | `/{id}/events` | Timeline de eventos del lead |
| POST | `/import` | Import masivo |
| GET/POST | `/searches` | Búsquedas guardadas |
| GET/POST/DELETE | `/lists` · `/lists/{id}/leads` | Listas de leads |
| GET/POST | `/{id}/proposals` · `/{id}/proposal/generate` · `/proposals/{id}/send` · `/proposals/{id}/pdf` | Propuestas |

### Otros routers principales
`/api/v1/agents` (registro + run con override de runtime), `/api/v1/workflows`, `/api/v1/approvals` (via workflows), `/api/v1/audit`, `/api/v1/costs`, `/api/v1/traces`, `/api/v1/policies`, `/api/v1/decisions`, `/api/v1/context-packs`, `/api/v1/memories` (memoria de usuario), `/api/v1/settings`, `/api/v1/projects`, `/api/v1/tasks`, `/api/v1/reports`, `/api/v1/email` (multi-proveedor SMTP/IMAP), `/api/v1/mcp` (tool registry MCP), `/api/v1/whatsapp` (bridge), `/api/v1/system/health`.

---

## 6. Configuración

Variables de entorno clave (ver `.env.example`):

| Variable | Uso |
|---|---|
| `DATABASE_URL` | SQLite local (`sqlite:///./missioncontrol.db`) o Postgres |
| `SECRET_KEY` | Firma de JWT (producción: valor fuerte) |
| `LOCAL_ADMIN_PASSWORD` | Password del admin seedeado |
| `DEEPSEEK_API_KEY` / `OPENAI_API_KEY` | LLM Harness (sin key → modo simulado) |
| `LEADHUNTER_BBOX` | Bounding box de la caza Overpass (default Gran Asunción) |
| `LEADHUNTER_CRON` | Cron del scheduler (default `0 9 * * 1`) |
| `RANKING_WEIGHTS` | Pesos de lead/opportunity score (JSON) |
| `EMBEDDING_ENABLED` / `EMBEDDING_MODEL` / `EMBEDDING_PROVIDER` / `EMBEDDING_BACKEND` | Búsqueda semántica |
| `AGENT_RUNTIMES` | Registro de runtimes (generic, claude_code, codex, opencode, openclaw, mcp) |
| `CORS_ORIGINS` | Orígenes permitidos |

Settings en DB (tabla `settings`) se pueden leer/escribir desde la UI (Settings) o CLI (`conciencia config set <clave> <valor>`).

---

## 7. FAQ y solución de problemas

**"El login no funciona en prod"** → el admin se seedea con `LOCAL_ADMIN_PASSWORD` al primer arranque; si cambiás la variable después, reseteá con `scripts/seed_local_admin.py`.

**"La búsqueda semántica da 501"** → está deshabilitada (`EMBEDDING_ENABLED=false`). Activá en Settings o `conciencia config set embeddings.enabled true`.

**"¿Por qué este lead tiene score X?"** → usá `conciencia lead score <id>` o el panel Score Intelligence: los 4 scores son independientes y explicables (`reasons`).

**"La caza no encuentra nada nuevo"** → es normal: el dedupe evita duplicados. Revisá `GET /leads/hunt/runs` para ver encontrados/nuevos/duplicados.

**"¿Cómo exporto mis leads?"** → UI: botón Export · CLI: `conciencia leads export` · API: `GET /leads/export`.

**"¿Necesito API keys para probar?"** → No. LLM y embeddings corren en modo simulado sin keys.

**Encoding raro en archivos** → nunca usar `Set-Content` de PowerShell para UTF-8 (mangla acentos); usar el edit tool, Python o `write` con UTF-8.

---

*Documentación viva — actualizada con el plan LeadHunter Intelligence (F1-F11, 30/08/2026).*
