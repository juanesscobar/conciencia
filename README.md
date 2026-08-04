# 🎯 Mission Control

> **Agent orchestration engine** — Software Factory + Project Governance System
> Orquesta proyectos, sub-agentes IA y métricas de negocio en un solo dashboard.

![Version](https://img.shields.io/badge/version-2.0.0--alpha-00ff41?style=flat-square&labelColor=0a0f1a)
![Stack](https://img.shields.io/badge/stack-FastAPI%20%2B%20React-00d9ff?style=flat-square&labelColor=0a0f1a)
![License](https://img.shields.io/badge/license-MIT-00ff41?style=flat-square&labelColor=0a0f1a)

---

## ⚡ Qué es

**Mission Control** es el cerebro operativo de una software factory personal: un motor de agentes IA que ejecuta tareas usando sus propios archivos de identidad (`SOUL.md`, `AGENTS.md`) como system prompts, conectado a APIs de LLM como **DeepSeek**.

- 🎯 **Dashboard** con métricas, activity feed y oficina virtual de agentes
- 🤖 **8 agentes** (Dev, Ops, QA, PM, R&D, Comms, Fin, Admin) — cada uno con su `SOUL.md`
- 🧠 **Motor de ejecución** — los agentes corren tareas reales vía API de DeepSeek
- 👤 **Memoria de usuario** — cada operador tiene su propio "memorial" persistente
- 📊 **Governance** — proyectos, tareas, sprints, métricas y actividad en tiempo real
- 🔀 **GitHub integrado** — commits, PRs, issues por proyecto

---

## 🖼️ Screenshots

| Dashboard | Agents |
|-----------|--------|
| Métricas + actividad + memoria + oficina | Grid de 8 agentes + consola de ejecución |

---

## 🚀 Quickstart (local)

### Requisitos
- Docker + Docker Compose
- (Opcional) API key de DeepSeek: https://platform.deepseek.com

### 1. Clonar y configurar

```bash
git clone https://github.com/juanesscobar/mission-control.git
cd mission-control

cp .env.example .env
# Editar .env y completar:
#   POSTGRES_PASSWORD / REDIS_PASSWORD / SECRET_KEY (generar fuertes)
#   GITHUB_TOKEN / DEEPSEEK_API_KEY (https://platform.deepseek.com)
```

### 2. Levantar (producción)

```bash
docker compose up -d --build
```

> 🔒 Producción: solo nginx expone puertos (80). Postgres y Redis quedan en la red
> interna de Docker, sin acceso desde internet. Backend corre con gunicorn
> (ENVIRONMENT=production, sin `--reload`).

### 3. Acceder

| Servicio | URL |
|----------|-----|
| Frontend + API | http://localhost |
| API Docs | http://localhost/docs |

### Desarrollo local con hot-reload

```bash
docker compose -f docker-compose.dev.yml up
```

| Servicio | URL |
|----------|-----|
| Frontend (HMR) | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

> ⚠️ El compose de dev expone puertos y usa credenciales default — nunca usarlo en producción.
> En dev el frontend apunta a `http://localhost:8000`; en producción `VITE_API_URL` se
> configura apuntando al dominio/IP.

---

## 🤖 Motor de Agentes

### Arquitectura

```
┌─────────────────────────────────────────────────────┐
│                     FRONTEND (React)                │
│  Dashboard · Projects · Tasks · Agents · Memories   │
└──────────────────────┬──────────────────────────────┘
                       │ REST /api/v1
┌──────────────────────▼──────────────────────────────┐
│                     BACKEND (FastAPI)               │
│  routers/agents.py → /run                           │
│       │                                             │
│       ├── lee agents/<role>/SOUL.md + AGENTS.md     │
│       │        (system prompt)                      │
│       ├── arma mensaje con la tarea                 │
│       └── llama a services/llm.py                   │
│              └── DeepSeek API (OpenAI-compatible)   │
└─────────────────────────────────────────────────────┘
```

### Cómo funciona

1. Cada agente tiene un directorio `agents/<role>/` con su identidad:
   - `SOUL.md` — personalidad, responsabilidades, boundaries
   - `AGENTS.md` — workflow, herramientas, convenciones (opcional)
2. Al ejecutar una tarea, el backend **arma el system prompt con esos archivos**
3. Llama a DeepSeek con la tarea y devuelve el output al dashboard
4. La ejecución se guarda en `agent_executions` y aparece en el activity feed

### API de ejecución

```bash
# Ejecutar un agente con texto libre
curl -X POST http://localhost:8000/api/v1/agents/{agent_id}/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task_text": "Analiza el backlog y sugiere prioridades"}'

# Ejecutar un agente sobre una tarea existente
curl -X POST http://localhost:8000/api/v1/agents/{agent_id}/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "uuid-de-la-tarea"}'

# Ver los archivos MD de un agente
curl http://localhost:8000/api/v1/agents/{agent_id}/files \
  -H "Authorization: Bearer $TOKEN"
```

> Sin `DEEPSEEK_API_KEY` configurada, el motor corre en **modo simulado**
> (responde con la tarea recibida) para que puedas probar el flujo completo.

---

## 👤 Memoria de Usuario

Cada operador tiene su propio memorial persistente (`user_memories`):

```bash
# Crear
curl -X POST http://localhost:8000/api/v1/memories/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title": "Stack preferido", "content": "FastAPI + React", "category": "preference"}'

# Listar
curl http://localhost:8000/api/v1/memories/ -H "Authorization: Bearer $TOKEN"
```

Categorías: `general` · `project` · `decision` · `preference`

---

## 📁 Estructura

```
mission-control/
├── agents/                  # Identidad de cada agente (SOUL.md, AGENTS.md)
│   ├── dev/
│   ├── ops/
│   ├── qa/
│   ├── pm/
│   ├── rd/
│   ├── comms/
│   ├── fin/
│   └── admin/
├── backend/
│   ├── app/
│   │   ├── routers/         # FastAPI routers (projects, tasks, agents, memories...)
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   └── services/
│   │       └── llm.py       # Motor DeepSeek (OpenAI-compatible)
│   └── .env.example         # Variables de entorno (nunca commitees .env)
├── frontend/
│   └── src/
│       ├── pages/           # Dashboard, Projects, Tasks, Agents, Login
│       └── components/      # Layout, AgentOffice, UserMemory
├── docker-compose.yml
└── nginx/nginx.conf
```

---

## 🔐 Seguridad

- **Nunca** commitees `backend/.env` — está en `.gitignore` (usa `.env.example`)
- `SECRET_KEY` debe ser un valor fuerte y único por instalación
- Las contraseñas se hashean con bcrypt
- JWT con expiración de 60 minutos
- El repo público **no contiene** tokens, claves ni datos reales

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
- [ ] **Auth avanzada** — roles, rate limiting, 2FA
- [ ] **Sprints y governance** — planificación, retrospectivas
- [ ] **Deploys automatizados** — aprobación previa al push
- [ ] **Métricas predictivas** — tendencias y alertas

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

---

## M�dulo de Entregables + Reportes (v2, 2026-08-03)

### Endpoints nuevos

| Endpoint | Descripcion |
|----------|-------------|
| GET/POST /api/v1/deliverables | Listar / crear entregables (report, commit, PR, build, doc, other) |
| GET/PUT/DELETE /api/v1/deliverables/{id} | Detalle / actualizar estado / eliminar |
| GET /api/v1/reports/sprint/{sprint_id} | Informe consolidado: sprint + tareas + entregables + commits/PRs de GitHub |
| GET /api/v1/reports/summary | Resumen global de progreso |
| GET/POST /api/v1/sprints | Listar / crear sprints |

### Vista frontend
- Nueva pagina /reports (Trabajo Entregado): resumen global, informe de sprint con barra de progreso, commits y PRs mergeados, tabla de entregables con filtros y acciones.

### Operacion 24/7 (servidor Hetzner)
- Script autopilot.sh + cron jobs:
  - 0 * * * * -> sync GitHub horario
  - 0 8 * * * -> reporte diario (summary + sprint)
  - 0 9 * * 0 -> reporte semanal completo
- Reportes en /opt/mission-control/reports/daily_*.json
- Log: /var/log/mission-control-autopilot.log

### Deploy (servidor 46.62.196.151)

```bash
ssh -i ~/.ssh/hetzner_mc root@46.62.196.151
cd /opt/mission-control
git pull origin v2-refactor
# Si cambió el .env (raíz): editar /opt/mission-control/.env
docker compose up -d --build
# Verificar:
#   ss -tlnp            → solo 22 y 80 escuchando
#   curl localhost/health
#   docker logs mission-control-backend-1 --tail 50
```
