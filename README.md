# 🎯 Mission Control

> **Agent orchestration engine** — Software Factory + Project Governance System
> Orquesta proyectos, sub-agentes IA y métricas de negocio en un solo dashboard.

![Version](https://img.shields.io/badge/version-2.0.0--alpha-00ff41?style=flat-square&labelColor=0a0f1a)
![Stack](https://img.shields.io/badge/stack-FastAPI%20%2B%20React-00d9ff?style=flat-square&labelColor=0a0f1a)
![License](https://img.shields.io/badge/license-MIT-00ff41?style=flat-square&labelColor=0a0f1a)

---

## ⚡ Qué es

**Mission Control** es el cerebro operativo de una software factory personal: un motor de agentes IA que ejecuta tareas usando sus propios archivos de identidad (`SOUL.md`, `AGENTS.md`) como system prompts, conectado a APIs de LLM (DeepSeek, OpenAI, Anthropic, Google, OpenRouter, Ollama).

- 🎯 **Dashboard** con métricas, activity feed y oficina virtual de agentes
- 🤖 **8 agentes** (Dev, Ops, QA, PM, R&D, Comms, Fin, Admin) — cada uno con su `SOUL.md`
- 🧠 **LLM Harness multimodal** — fallback automático entre providers, cost tracking y routing inteligente
- ⚙️ **Control plane** — workflows con approval gates (human-in-the-loop), DAG de tareas, audit log y capability matching
- 💰 **Pipeline de ventas E2E** — Lead Hunter (Overpass/OSM) → enrich → kanban → propuestas IA en PDF → envío por email
- 👤 **Memoria de usuario** — cada operador tiene su propio "memorial" persistente
- 📊 **Governance** — proyectos, tareas, sprints, métricas y actividad en tiempo real
- 🔀 **GitHub integrado** — commits, PRs, issues por proyecto

---

## 🔗 Acceso

### Local (esta máquina, dev)

| Servicio | URL |
|----------|-----|
| Frontend (Vite HMR) | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

### Celular (misma red Wi-Fi)

El frontend escucha en `0.0.0.0` y proxya `/api` al backend local:

```
http://<IP-LAN-DE-ESTA-PC>:5173
```

> Ej: `http://192.168.100.2:5173`. El celular debe estar en la misma red.
> IP LAN actual: `ipconfig` → adaptador Wi-Fi.

### Remoto (Tailscale)

```
http://100.109.233.101:5173
```

> Con Tailscale instalado en el celular/PC tenés acceso desde cualquier red.
> Alternativa: `docker compose -f docker-compose.tailscale.yml up`.

### Producción (servidor Hetzner)

| Servicio | URL |
|----------|-----|
| App (HTTP por IP) | http://46.62.196.151 |
| App (HTTPS con Let's Encrypt) | https://mc.46.62.196.151.sslip.io |
| API Docs | https://mc.46.62.196.151.sslip.io/docs |

> ⚠️ El dominio sslip.io requiere que tu DNS local resuelva (hosts file o router con 8.8.8.8).
> Por IP directa funciona siempre (HTTP).

---

## 🚀 Quickstart (local, sin Docker — recomendado para iterar rápido)

### Requisitos
- Python 3.11+ y Node 18+
- (Opcional) API key de DeepSeek: https://platform.deepseek.com

### 1. Backend

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows / source .venv/bin/activate (Linux)
pip install -r requirements.txt                  # o requirements-dev.txt para tests

# SQLite (dev local, sin Postgres/Redis):
#   en backend/.env → DATABASE_URL=sqlite:///./missioncontrol.db

python scripts/seed_local_admin.py               # crea/resetea el admin local
python scripts/seed_agents.py                    # crea/actualiza los 8 agentes
python -m uvicorn app.main:app --reload --port 8000
```

### 2. Frontend (otra terminal)

```bash
cd frontend
npm install
npm run dev                                      # http://localhost:5173
```

### 3. Login

- Usuario: `admin`
- Password: la de `LOCAL_ADMIN_PASSWORD` (env). Si no la definís y el admin ya existe, **no se modifica**; si no existe, se genera una aleatoria y se loguea en el arranque.
- Dev local típica: `LOCAL_ADMIN_PASSWORD=*** python scripts/seed_local_admin.py` o definirla en `backend/.env`.

> ⚠️ El seed **nunca** hardcodea passwords en el repo (es público). La password se lee de `LOCAL_ADMIN_PASSWORD` / `ADMIN_PASSWORD` (env o `.env`).

### Producción (Docker)

```bash
cp .env.example .env    # completar POSTGRES_PASSWORD, REDIS_PASSWORD, SECRET_KEY, LOCAL_ADMIN_PASSWORD...
docker compose up -d --build
```

> 🔒 Producción: solo nginx expone puertos (80/443). Postgres y Redis quedan en la red
> interna de Docker. Backend corre con gunicorn (`ENVIRONMENT=production`, sin `--reload`).
> Al arrancar, el entrypoint ejecuta el seed de admin + agentes automáticamente.

---

## 🤖 Motor de Agentes

### Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                     FRONTEND (React)                    │
│  Dashboard · Projects · Tasks · Agents · Memories ·     │
│  Leads · Workflows · Reports · Settings                 │
└──────────────────────┬──────────────────────────────────┘
                       │ REST /api/v1
┌──────────────────────▼──────────────────────────────────┐
│                     BACKEND (FastAPI)                   │
│  routers/agents.py → /run                               │
│       │                                                 │
│       ├── lee agents/<role>/SOUL.md + AGENTS.md         │
│       │        (system prompt)                          │
│       ├── arma mensaje con la tarea                     │
│       └── llama a services/llm.py  (wrapper)            │
│              └── LLM Harness (services/llm_harness/)    │
│                   ├── provider adapters                 │
│                   │   (deepseek · openai · anthropic ·  │
│                   │    google · openrouter · ollama)    │
│                   ├── fallback chain + retries          │
│                   ├── cost tracking (USD por llamada)   │
│                   └── routing (estrategias)             │
└─────────────────────────────────────────────────────────┘
```

### Cómo funciona

1. Cada agente tiene un directorio `agents/<role>/` con su identidad:
   - `SOUL.md` — personalidad, responsabilidades, boundaries
   - `AGENTS.md` — workflow, herramientas, convenciones (opcional)
2. Al ejecutar una tarea, el backend **arma el system prompt con esos archivos**
3. El **LLM Harness** ejecuta la llamada: intenta el provider activo, y si falla (timeout, rate limit, auth) hace **fallback automático** a los providers configurados (`LLM_FALLBACK_PROVIDERS`), con reintentos y tracking de costo por llamada.
4. El resultado vuelve al dashboard y se guarda en `agent_executions` + **audit log**.

### Configuración de providers

- **UI:** Configuración → Integraciones (provider, key, modelo, base URL + test de conexión)
- **Env:** `LLM_PROVIDER`, `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `OPENROUTER_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_FALLBACK_PROVIDERS` (JSON list, ej: `["openai","openrouter"]`)
- Sin ninguna key → **modo simulado** (responde con la tarea recibida, para probar el flujo)

### API de ejecución

```bash
curl -X POST http://localhost:8000/api/v1/agents/{agent_id}/run \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"task_text": "Analiza el backlog y sugiere prioridades"}'
```

---

## ⚙️ Control Plane (gobernanza)

- **Workflows declarativos** — motor con pasos, dependencias y **approval gates human-in-the-loop** (`workflow_engine.py`). Un workflow puede pausarse esperando aprobación de un rol (ej: CEO) antes de continuar.
- **DAG de tareas** — dependencias entre tareas con estados `READY` / `ASSIGNED` / `BLOCKED` y detección de ciclos (`task_dag.py`).
- **Capability matching** — empareja requirements → candidates → best según capabilities declaradas de cada agente (`capability_matching.py`).
- **Audit log append-only** — toda mutación de tasks y ejecuciones de agentes queda registrada (`audit.py` + endpoints `/api/v1/audit/`).
- **UI:** página `/workflows` con cola de aprobaciones; tasks con DAG visible.

---

## 💰 Pipeline de Ventas (Lead Hunter v2)

Módulo que **caza leads B2B reales** del Gran Asunción (o todo Paraguay) y los lleva por el pipeline hasta propuesta enviada.

### Qué hace

- 🗺️ **Fuente Overpass (OpenStreetMap)** — sin API key. Busca por categoría dentro de un bounding box (`LEADHUNTER_BBOX`, default Gran Asunción; `LEADHUNTER_SCOPE=country` = todo Paraguay).
- 🔁 **Dedupe automático** — por nombre normalizado (sin acentos/sufijos legales), dominio web y últimos 8 dígitos del teléfono.
- 🧮 **Scoring heurístico 0-100** — sector objetivo, completitud de datos, fuente.
- 🌐 **Enrich web** — raspa el website del lead y extrae email + teléfono reales (anti-junk).
- ✦ **Enrich IA** — análisis del lead, score sugerido, preguntas para la primera llamada.
- ⏰ **Scheduler** — `LEADHUNTER_CRON` (default lunes 09:00 Asunción; vacío = off).
- 📋 **Historial de corridas** — encontrados/nuevos/duplicados por fuente.

### Pipeline

| Etapa | Endpoint | Qué hace |
|-------|----------|----------|
| Cazar | `POST /leads/hunt/run` · `POST /leads/import` | Descubrir (Overpass) o importar CSV con dedupe |
| Enriquecer | `POST /leads/{id}/enrich-website` · `POST /leads/{id}/enrich` | Email/tel del sitio · análisis IA |
| Contactar | `POST /leads/{id}/contact` | Marca contacted + evento en timeline |
| Calificar | `POST /leads/{id}/qualify` | Valida el prospecto |
| Propuesta | `POST /leads/{id}/proposal/generate` · `POST /leads/proposals/{id}/send` | **Squad multi-agente** genera la propuesta (PDF descargable) y se envía por email |
| Cierre | `POST /leads/{id}/won` · `POST /leads/{id}/lost` | Gana/pierde con motivo |

Filtros del listado: `?region=asuncion&segment=pyme&online=website&age_days=30&min_score=40&industry=salud&sort=score`

Webhook público para landings: `POST /api/v1/leads/intake` (ej: conciencia-software en Vercel).

---

## 👤 Memoria de Usuario

```bash
curl -X POST http://localhost:8000/api/v1/memories/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title": "Stack preferido", "content": "FastAPI + React", "category": "preference"}'
```

Categorías: `general` · `project` · `decision` · `preference`

---

## 📁 Estructura

```
mission-control/
├── agents/                  # Identidad de cada agente (SOUL.md, AGENTS.md)
│   ├── dev/ ├── ops/ ├── qa/ ├── pm/
│   └── rd/ ├── comms/ ├── fin/ └── admin/
├── backend/
│   ├── app/
│   │   ├── routers/         # projects, tasks, agents, leads, workflows, audit...
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── modules/
│   │   │   └── leadhunter/  # motor de prospección + pipeline + propuestas
│   │   └── services/
│   │       ├── llm.py           # wrapper compat (run_agent, test_connection)
│   │       ├── llm_harness/     # harness multimodal (base, harness, routing,
│   │       │                    #  cost_tracker, providers/*)
│   │       ├── workflow_engine.py / task_dag.py / capability_matching.py
│   │       └── audit.py / auth.py / agent_soul.py
│   ├── scripts/             # seeds (admin vía env, agentes) — en git, sin secrets
│   └── .env.example
├── frontend/
│   └── src/                 # pages: Dashboard, Projects, Tasks, Agents,
│                            #  Memories, Leads, Workflows, Reports, Settings
├── nginx/nginx.conf         # HTTP por IP + HTTPS (LE) por dominio
├── docker-compose.yml       # prod (postgres + redis + backend + frontend + nginx)
└── docker-compose.dev.yml   # dev con HMR
```

---

## 🔐 Seguridad

- **Nunca** commitees `.env` (está en `.gitignore`; usá `.env.example`)
- `SECRET_KEY` fuerte y única por instalación (el backend **no arranca** en producción sin ella)
- Passwords hasheadas con bcrypt · JWT expira a los 60 minutos
- El seed de admin lee la password de `LOCAL_ADMIN_PASSWORD` — **el repo público no contiene credenciales**
- Los seed scripts que antes tenían passwords hardcodeadas se refactorizaron para leer de env (2026-08-15)

### Checklist antes de pushear a un repo público

```bash
git status                              # revisar qué se va
git check-ignore backend/.env           # debe imprimir la ruta
grep -rIn "ghp_\|sk-\|BEGIN.*PRIVATE" . --exclude-dir=node_modules --exclude-dir=.git
```

---

## 🗺️ Roadmap

- [x] **MVP** — dashboard, proyectos, tareas, métricas, activity
- [x] **Agent Office** — panel visual con 8 agentes
- [x] **Dark hacker theme** — UI estilo terminal
- [x] **Motor DeepSeek** — ejecución de agentes con LLM
- [x] **Memoria de usuario** — memorial por operador
- [x] **Lead Hunter** — prospección automática (Overpass/OSM) + enrich web/IA
- [x] **Pipeline E2E** — lead → contactar → calificar → propuesta IA (PDF/email) → ganar/perder
- [x] **Integraciones centralizadas** — GitHub + proveedores IA multi + Lead Hunter
- [x] **LLM Harness multimodal** — fallback, cost tracking, routing (ago 2026)
- [x] **Control plane** — workflows + approval gates, DAG de tareas, audit log, capability matching (ago 2026)
- [x] **Seed automático de admin/agentes** en deploy (ago 2026)
- [ ] **Auth avanzada** — roles, rate limiting, 2FA
- [ ] **Sprints y governance** — planificación, retrospectivas
- [ ] **Deploys automatizados** — aprobación previa al push
- [ ] **Métricas predictivas** — tendencias y alertas

---

## 🚀 Deploy (servidor 46.62.196.151)

```bash
ssh root@46.62.196.151
cd /opt/mission-control
git pull origin v2-refactor

# Editar .env raíz si cambió algo (POSTGRES_PASSWORD, REDIS_PASSWORD, SECRET_KEY,
# GITHUB_TOKEN, DEEPSEEK_API_KEY, LOCAL_ADMIN_PASSWORD...)

docker compose up -d --build
docker compose ps                      # verificar que backend esté healthy
curl localhost/health                  # → {"status":"healthy"}
```

> El entrypoint del backend hace el seed de admin + agentes automáticamente en cada arranque
> (idempotente). `LOCAL_ADMIN_PASSWORD` opcional: si se omite y el admin ya existe, no se toca.

---

## 🧑‍💻 Contribuir

1. Fork + branch (`feature/xyz`)
2. PR con descripción clara
3. Los agentes revisan tu código 🤖

---

## 📄 Licencia

MIT — uso libre con atribución.

---

*Built by [@juanesscobar](https://github.com/juanesscobar) — Iron Toto*
