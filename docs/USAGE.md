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
conciencia <cmd> --help    # ayuda de un comando
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

### map — mapa conceptual

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
