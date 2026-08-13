# E2E Health Check — Mission Control

> Fecha: 2026-08-12 · Rama: v2-refactor · Estado: v0.3 funcional

## Arquitectura actual

```
Frontend React+Vite+Tailwind (dark theme) :5173
   └─ /api → proxy Vite (dev) / nginx (prod)
Backend FastAPI :8000
   ├─ Auth JWT (admin / MC-Admin#2026!)
   ├─ SQLite (dev local) / PostgreSQL (prod)
   ├─ Modules: leadhunter · whatsapp · jobscout
   ├─ Routers: projects, tasks, agents, sprints, metrics, activities, reports, memories, settings, github, system
   └─ APScheduler (leadhunter cron) + BackgroundScheduler
Agentes: 8 roles (dev, ops, qa, pm, rd, comms, fin, admin) con SOUL.md
   └─ Motor LLM multi-proveedor (deepseek/openai/openrouter/ollama) — MODO SIMULADO sin API key
```

## Cómo levantar

```bash
# Backend (puerto 8000)
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1

# Frontend (puerto 5173)
cd frontend
npm run dev   # Vite proxy: /api → localhost:8000 (accesible desde celular en LAN)
```

Login local: `admin` / `MC-Admin#2026!` (seed: `scripts/seed_local_admin.py`, gitignored)

## Dependencias

| Componente | Status | Nota |
|------------|--------|------|
| Python 3.12 + venv | ✅ | backend/.venv |
| Node 24 + npm | ✅ | frontend/node_modules |
| SQLite (dev) | ✅ | missioncontrol.db |
| fpdf2 | ✅ | PDF propuestas (2.8.8) |
| openai SDK 1.59.6 | ✅ | fix httpx 0.28 |

## Variables de entorno

| Variable | Estado | Dónde |
|----------|--------|-------|
| `DEEPSEEK_API_KEY` | ❌ falta | backend/.env o Settings DB (Configuración → DeepSeek) |
| `SMTP_HOST/PORT/USER/PASS/FROM` | ❌ falta | Settings DB (Configuración → Email) |
| `LEADHUNTER_BBOX` | ✅ default | env |
| `LEADHUNTER_CRON` | ✅ `0 9 * * 1` | env |
| `SECRET_KEY` | ✅ | backend/.env |
| `VITE_API_URL` | ✅ vacío → proxy | frontend/.env.local (gitignored) |

## Configuración para salir del modo simulado

### DeepSeek (agentes + propuestas reales)

**Opción A — UI (recomendado):**
1. Login como admin → Configuración → DeepSeek
2. Pegar API key (`sk-...`) → Guardar
3. Probar conexión → debe mostrar `✓ DeepSeek · modelo deepseek-chat · Xms`

**Opción B — .env:**
```bash
# backend/.env
DEEPSEEK_API_KEY=sk-tu-key-aqui
```

### SMTP (envío de propuestas por email real)

1. Login como admin → Configuración → Email (SMTP)
2. Completar:
   - Host: `smtp.gmail.com` (o tu proveedor)
   - Puerto: `587`
   - Usuario: tu email
   - Contraseña: App password (Gmail requiere 2FA activado)
   - From: tu email
3. Guardar → Enviar email de prueba

**Opción B — .env:**
```bash
# backend/.env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu@email.com
SMTP_PASS=tu-app-password
SMTP_FROM=tu@email.com
```

## Servicios externos

| Servicio | Estado | Uso |
|----------|--------|-----|
| GitHub API | ✅ verificado | sync repos (Multilimp, Conciencia) |
| Overpass (OSM) | ✅ verificado | caza de leads real (826+ leads) |
| DeepSeek API | ❌ sin key | agentes + propuestas → MODO SIMULADO (único proveedor) |
| SMTP | ❌ sin config | envío propuestas → mailto fallback |
| Gmail MCP (OpenClaw) | ✅ autorizado | agente externo (no backend) |

## Estado por funcionalidad

| Feature | Estado | Detalle |
|---------|--------|---------|
| Auth (login/JWT) | ✅ WORKING | verificado vía API |
| Proyectos CRUD + GitHub sync | ✅ WORKING | from-github, from-lead |
| Tasks CRUD | ✅ WORKING | sin dependencias DAG |
| Sprints | ✅ WORKING | básico |
| Agentes + SOUL + run | 🔶 PARTIALLY | run real con key; hoy simulado |
| Memoria de usuario | ✅ WORKING | CRUD + panel |
| Dashboard + metrics | ✅ WORKING | |
| Agent Office visual | ✅ WORKING | 8 agentes animados |
| Lead Hunter caza | ✅ WORKING | Overpass, dedupe, enrich, scoring, scheduler |
| Lead pipeline UI | ✅ WORKING | tabla + kanban mini-CRM |
| Propuestas IA | 🔶 MOCKED | genera con LLM; sin key → simulado |
| Propuesta PDF | ✅ WORKING | endpoint + botón ⬇ PDF |
| Propuesta email/WhatsApp | 🔶 PARTIALLY | mailto/wa.me sin SMTP/bridge |
| WhatsApp bridge | 🔶 MOCKED | endpoints existen; sin QR escaneado en MC (bot Atiendo AI aparte en :8010) |
| JobScout | 🔶 PARTIALLY | módulo existe, sin cron activo |
| E2E tests | ❌ NOT_IMPLEMENTED | solo unit tests básicos |

## Blockers actuales

1. **DEEPSEEK_API_KEY** — sin key, propuestas y agentes corren en modo simulado (bloquea demo real). Configurar desde UI o .env (ver arriba).
2. **SMTP** — envío de propuestas por email real requiere credenciales (hoy mailto). Configurar desde UI o .env (ver arriba).
3. **WhatsApp bridge en MC** — el bot con QR vive en `C:\Users\juane\Atiendo AI` (:8010), no integrado al dashboard MC

## Cambios recientes

- **LLM simplificado a DeepSeek-only** — eliminados OpenAI/OpenRouter/Ollama/Anthropic/Google del backend y frontend. Solo `DEEPSEEK_API_KEY` requerido.
- **PR-2.1 Capability matching** — agents se resuelven por capabilities requeridas en workflows.
- **PR-2.2 Approval gates UI** — página /workflows con cola de aprobaciones pendientes.

## Próximos pasos (Plan)

1. LeadHunterJob async con cancel/retry (PR-0.2)
2. Observabilidad de pasos del job (PR-0.3)
3. Error handling explícito (PR-0.4)
4. Test E2E (PR-0.5)
5. Agent Adapter + Registry (Etapa 1)
