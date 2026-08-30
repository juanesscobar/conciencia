# PLAN DE EJECUCIÓN — LeadHunter Intelligence Engine + Modular Agentic Business OS

> Fuente: `CONCIENCIA—LEADHUNTER-INTELLIGENCE+ENGINE+MODULAR AGENTIC-BUSINESS-OS` (spec 53 secciones)
> Rama: `v2-refactor` · Fecha: 2026-08-23
> Principio rector de la spec: **LeadHunter first, no romper nada, refactor incremental, dominio reutilizable (UI/API/CLI/Agents).**

---

## 1. AUDITORÍA (spec §48, P0 — HECHA)

### 1.1 Stack actual

| Capa | Estado |
|---|---|
| Backend | FastAPI + SQLAlchemy (SQLite dev / Postgres prod) + alembic + `sync_schema` |
| Frontend | React + Vite + Tailwind (dark theme) |
| Módulo LeadHunter | `backend/app/modules/leadhunter/` — ya modular: `router.py` (797 ln), `discovery.py`, `service.py` (scoring), `sources/` (base + overpass), `enrich.py`, `jobs.py` (async), `scheduler.py`, `delivery.py`, `proposal.py`, `pdfgen.py`, `catalog.py`, `schemas.py`, `exceptions.py` |
| Settings | Tabla `Setting` + overlay `os.environ` en upsert; `VISIBLE_KEYS` ya incluye `LEADHUNTER_CRON/BBOX/SCOPE` |
| Tests | `test_leadhunter_e2e.py` (jobs lifecycle, exceptions), `test_discovery.py` |
| CLI | ❌ NO existe (sin typer/click en requirements) |
| Agentes | Ya existe `AgentRuntime` + tabla agents + SOUL.md (`routers/agents.py`) → reutilizable |
| Vector DB | ❌ No hay embeddings ni pgvector |

### 1.2 Flujo actual de LeadHunter

```
UI (Leads.tsx, 1335 ln)
  ├─ list_leads  → GET /api/v1/leads/  → filtros SQL ILIKE + paginación page/page_size
  ├─ hunt/run    → run_discovery()     → fuentes (overpass) → dedupe O(n²) → compute_score → INSERT
  └─ pipeline    → status/contact/qualify/proposal/enrich/events/lists/searches
```

### 1.3 Problemas encontrados (mapeados a la spec)

| # | Problema | Severidad | Spec |
|---|---|---|---|
| P1 | **"Cazar TODO (sin filtros)"** en la UI ignora filtros y scope: `huntRun.mutate(undefined)`. Una caza accidental toca todo el bbox/country | 🔴 Alta | §9, §5 |
| P2 | **Geografía no es first-class**: bbox hardcodeado en env (`LEADHUNTER_BBOX` Gran Asunción); no hay jerarquía país→región→ciudad; no hay "Global" explícito; país default no configurable en Settings (solo env) | 🔴 Alta | §7, §8, §9 |
| P3 | **Sin pipeline NL→filtros**: el search box es un ILIKE ambiguo sobre 6 columnas; no existe `SearchQuery` canónico ni intent parser | 🔴 Alta | §5, §6, §32 |
| P4 | **Dedupe O(n²)**: `_is_duplicate` carga TODOS los leads por candidato (`db.query(Lead).all()`); a 10k+ leads se vuelve inusable; sin índice de nombre normalizado | 🔴 Alta | §12 |
| P5 | **Filtro región con full-scan**: carga pares (id, region) y normaliza en Python por request | 🟠 Media | §5 |
| P6 | **Scoring único y hardcodeado**: `compute_score` mezcla relevancia de búsqueda + lead score; keywords fijas de vertical software-factory; sin `RankingWeights` ni `LeadScore` separado ni data quality | 🟠 Media | §15, §16, §35 |
| P7 | **Sin "why this result?"**: no hay breakdown de por qué matchea un lead | 🟠 Media | §34 |
| P8 | **Sin capa de search engine**: `list_leads` es un WHERE gigante; no hay full-text, ni ranking, ni híbrido | 🟠 Media | §13 |
| P9 | **Provenance débil**: osm_id/lat/lon van en `meta` JSON; no hay `source_records`, ni confidence estructurada | 🟡 Baja | §11, §35 |
| P10 | **Sin CLI** | 🟠 Media | §19, §41 |
| P11 | **Sin cache** (geocoding, provider, búsquedas) | 🟡 Baja | §36 |
| P12 | **Sin export** (CSV/JSON) | 🟡 Baja | §38 |
| P13 | **Router 797 ln / Leads.tsx 1335 ln** — god-objects; lógica mezclada (pipeline + propuestas + import + CRUD) | 🟡 Baja | §42 |
| P14 | **Tests insuficientes**: no cubren NL, geo, dedupe v2, ranking, filtros, CLI, API search, exports | 🟠 Media | §39 |
| P15 | Región del filtro usa `Lead.region` libre (calle, ciudad, suburbio) — `regions` endpoint limpia a mano | 🟡 Baja | §5 |

**Buenas noticias (no romper):** ya existe registry de fuentes (`sources/base.py`), dedupe básico, jobs async con cancel/retry, enrich web + IA, propuestas + PDF + delivery, webhook intake, búsquedas guardadas y listas, scheduler. Eso se **preserva** y se usa como base.

---

## 2. PLAN POR FASES (cada fase = commit shippable + tests verdes)

> Orden = spec §49 (P0→P10). Cada fase incluye: archivos, migración, tests, DoD propio.
> **Regla de oro:** los endpoints existentes no cambian su contrato; todo lo nuevo es aditivo.

### FASE 1 — Correctness + Geographic Scope (spec P1/P2) ⚡
**Objetivo:** nadie puede consultar el mundo por accidente; el país default es PY y configurable.

1. **`backend/app/modules/leadhunter/geo.py` (NUEVO)**
   - `GeographicScope`: `default_country=PY`, `allowed_countries=[PY,BR,AR,...]`, `default_region`, `default_city`, `scope=city|region|country|multi|global` (global SOLO si se pide explícito).
   - `GeoProvider` abstracto: `search_places()`, `geocode()`, `reverse_geocode()`, `resolve_region()`, `resolve_country()`, `resolve_city()`.
   - `OpenStreetMapProvider` adapter que envuelve a OverpassSource (reusa endpoints/mirrors existentes). Sin evasión de rate limits (spec §10).
   - Cache TTL (dict simple + opcional redis si está configurado).
2. **`backend/app/config.py`**: `SEARCH_DEFAULT_COUNTRY=PY`, `SEARCH_ALLOWED_COUNTRIES`, `SEARCH_DEFAULT_REGION`, `SEARCH_DEFAULT_CITY`, `SEARCH_SCOPE` (compat: leer `LEADHUNTER_SCOPE/BBOX` como fallback).
3. **`sources/overpass.py`**: usa el scope geográfico en vez de `LEADHUNTER_SCOPE` directo; si scope es city/region → bbox derivado del lugar (geocode), si country → `PARAGUAY_AREA`, si multi/global → permitido solo con flag explícito.
4. **`discovery.py` + router `hunt/run`**: aplicar scope por defecto cuando el usuario no pasa `region`; `scope` param explícito (`global` requiere confirmación `allow_global=true`).
5. **Frontend `Leads.tsx`**: el botón "Cazar" pasa filtros activos + muestra chip de scope activo ("PY · Gran Asunción"); eliminar el "Cazar TODO sin filtros" como acción default (queda detrás de confirmación).
6. **Settings UI + router**: sección "Search Geography" (país default, países permitidos, scope). `VISIBLE_KEYS` ampliado.

**Migración:** ninguna (solo env/settings). **Tests:** `test_geo.py` — default PY, global bloqueado sin flag, resolve country/region, cache.

**DoD Fase 1:** `"restaurantes"` con settings PY → búsqueda PY, nunca mundo; cazar sin filtros queda acotado al scope; settings persistente.

---

### FASE 2 — SearchQuery canónico + NL → filtros (spec P3, §5/§6/§32) 🧠
**Objetivo:** un objeto `SearchQuery` reutilizable por UI/API/CLI/Agents; la UI muestra chips editables (interpreted filters).

1. **`leadhunter/search.py` (NUEVO)**:
   - `SearchQuery` (pydantic): `query`, `entity_type`, `country`, `region`, `city`, `category`, `industry`, `required_fields[]`, `sort`, `scope`.
   - `SearchEngine`: `execute(SQLAlchemySession, SearchQuery) -> SearchResult` — unifica `list_leads` actual (filtros estructurados + full-text con `ilike` normalizado, preparado para FTS).
   - Cursor pagination como opción (`cursor` param), manteniendo `page/page_size` para compat.
2. **`leadhunter/nlu.py` (NUEVO)**: intent parser por reglas (es→categorías/sinónimos + geografía + required_fields). Ej: "playas de autos usados en Ciudad del Este" → `{category: used_car_dealer, city: Ciudad del Este, country: PY}`. Backend opcional LLM (DeepSeek) para fallback, sin romper si no hay key.
3. **Router**: `POST /api/v1/leads/search/interpret` (NL → SearchQuery) y `POST /api/v1/leads/search` (ejecuta SearchQuery) — aditivos, no tocan `GET /`.
4. **Frontend**: caja de búsqueda con lenguaje natural + chips editables (país/región/ciudad/categoría/filtros) que se mapean 1:1 al `SearchQuery`.
5. **`catalog.py`**: ampliar con sinónimos (playa de autos → used_car_dealer/car_dealer/automotive) y categorías usadas por el NL parser.

**Migración:** ninguna. **Tests:** `test_nlu.py` (5 queries benchmark de spec §40), `test_search_api.py`.

**DoD Fase 2:** una query humana produce filtros visibles/editables; misma query corre por UI y por API con los mismos resultados.

---

### FASE 3 — Normalización + Dedupe v2 (spec P4, §12) 🔗
**Objetivo:** dedupe indexado y entity resolution sin duplicados.

1. **`leadhunter/normalization.py` (NUEVO)**: extraer/mejorar `normalize_company`, `domain_of`, `norm_phone` (E.164-ish), `norm_address`; normalizar también emails.
2. **Modelo `Lead`**: columna `normalized_name` (String, index) + `normalized_phone` (String, index) — poblada en create/update/import/hunt (hook en `Lead.__init__` o en servicios).
3. **`leadhunter/entity.py` (NUEVO)**: `find_duplicates(db, company, website, phone, email)` con lookups indexados (equality por `normalized_name` + `normalized_phone` + dominio), en vez de `db.query(Lead).all()`.
4. **`discovery.py` + `import_csv` + `create_lead`**: usar dedupe v2. `_is_duplicate` viejo queda como compat interno (o se elimina tras tests).
5. **Backfill**: script/migración para poblar `normalized_name/phone` de leads existentes (idempotente).

**Migración:** alembic `leadhunter_normalization` (2 columnas + 2 índices). **Tests:** `test_dedupe_v2.py` — nombre+acentos+sufijos legales, dominio, tel 8 dígitos, email, y benchmark sin full-scan.

**DoD Fase 3:** 10k leads → dedupe <100ms; 2ª corrida de caza = 0 nuevos (como el E2E 17/08 pero sin degradación).

---

### FASE 4 — Ranking + Scoring separados + Data Quality (spec P5, §15/§16/§34/§35) 📊 ✅ HECHA (29/08)
**Objetivo:** relevancia ≠ lead score ≠ opportunity; weights configurables; "why this match".

1. **`leadhunter/ranking.py` (NUEVO)**:
   - `SearchRelevance` (por query): category_match, geographic_match, keyword_match → 0-1.
   - `LeadScore` (independiente de la query): reusa `compute_score` refactorizado como componente (completitud + industria + fuente) — **sin romper** el contrato actual.
   - `OpportunityScore` (opcional, stub con señales: website+tel+actividad).
   - `DataQualityScore`: completeness + freshness + source reliability + consistency (0-100).
   - `RankingWeights` configurable (settings DB, default en código).
   - `explain()` → lista de razones ("Automotive", "En Ciudad del Este", "Website detectado"...) para el "Why this lead matches".
2. **Schemas**: `LeadResponse` gana `search_relevance`, `data_quality`, `reasons[]` (aditivo, sin romper frontend).
3. **Settings**: "Ranking & Scoring" (weights editables) + `VISIBLE_KEYS`.
4. **Frontend**: en lead detail y filas, mostrar score breakdown + razones.

**Migración:** ninguna (campos calculados). **Tests:** `test_ranking.py` — weights default, separación scores, reasons.

**Resultado (commit `8aa7989`):**
- `ranking.py` nuevo: `SearchRelevance` (category/geo/keyword), `LeadScore` ponderado por bloques (reusa `_blocks` de service sin romper `compute_score`), `OpportunityScore`, `DataQualityScore` (completitud+frescura+fuente), `RankingWeights` configurables, `explain()` → razones.
- `RANKING_WEIGHTS` (JSON) en Settings (VISIBLE_KEYS) + `GET/PUT /api/v1/leads/ranking/weights` (PUT solo admin/owner/ceo).
- `LeadResponse` gana `search_relevance`, `opportunity_score`, `data_quality`, `reasons[]` (aditivo, sin romper frontend).
- UI: tabla muestra `O:n · Q:n` con tooltip de razones; LeadDetail gana card "Score Intelligence" con 4 barras + "¿Por qué este lead?"; Settings → Ranking & Scoring con editor JSON de pesos.
- 21 tests nuevos (`test_ranking.py`); suite F1-F4: 81 tests verdes. Typecheck + build OK.

**DoD Fase 4:** un lead con relevance 92% puede tener lead score 81 y opportunity 74 (ejemplo spec §16); el admin cambia pesos sin tocar código.

---

### FASE 5 — Búsqueda semántica foundation (spec P6, §14) 🧬 ✅ HECHA (29/08)
**Objetivo:** arquitectura lista para embeddings, sin vector DB externa.

1. **`leadhunter/embeddings.py` (NUEVO)**: `VectorBackend` abstracto (`upsert`, `search`) + `PgVectorBackend` (pgvector, solo si postgres + extensión) + `InMemoryBackend` (cosine en numpy, SQLite dev).
2. **`BusinessDocument`** modelo (o JSONB dentro de `leads.meta`): text = company+industry+category+description+address, embedding vector.
3. **Router**: `POST /api/v1/leads/search/semantic` (aditivo; devuelve 501 "embedding model not configured" si no hay key).
4. **Settings**: `EMBEDDING_MODEL`, `EMBEDDING_ENABLED`.

**Migración:** opcional `pgvector` en prod (flag), cero en dev. **Tests:** `test_semantic.py` con InMemoryBackend + modelo fake.

**Resultado (commit `8a1ce4b`):**
- `embeddings.py` nuevo: `VectorBackend` abstracto (upsert/search/delete/count) + `InMemoryBackend` (cosine numpy, dev) + `PgVectorBackend` (pgvector autocontenido, fallback a memory si no hay extensión).
- `embed_text()`: OpenAI-compatible si hay API key; modo SIMULADO determinístico (n-grams hasheados dim 384) sin key → demo/tests nunca rompen.
- `BusinessDocument` como JSONB en `leads.meta["semantic"]` (provenance: text/model/dim/indexed_at) — sin migración en dev.
- `POST /api/v1/leads/search/semantic` (501 si EMBEDDING_ENABLED no está) + `GET /search/semantic/status` (backend/modelo/indexados/simulado). Indexación lazy incremental (`reindex_if_needed`).
- Settings: EMBEDDING_ENABLED/MODEL/PROVIDER/BACKEND/BASE_URL (VISIBLE_KEYS + UI en Lead Hunter); `numpy` agregado a requirements.
- UI: botón 🧬 Semántica en Leads (usa la consulta NL o el buscador), banner de resultados semánticos + R: en badges; Settings muestra estado con contador.
- 13 tests nuevos; suite F1-F5: 94 verdes. tsc + build OK.

**DoD Fase 5:** el endpoint existe, es abstracto, y funciona end-to-end con un embedding model barato (p.ej. `text-embedding-3-small` o local) o en modo simulado; no introduce Qdrant/Weaviate.

---

### FASE 6 — CLI `conciencia` (spec P7, §19/§41) 💻 ✅ HECHA (29/08)
**Objetivo:** misma lógica de dominio que UI/API, cero backend duplicado.

1. **`backend/cli.py` + pyproject entry point `conciencia`** (typer + rich; agregar a requirements).
   - `conciencia health`
   - `conciencia search "playas de autos usados" --country PY --region "Alto Paraná" --json`
   - `conciencia leads list|export --format csv|json`
   - `conciencia lead inspect <id> | enrich <id> | score <id>`
   - `conciencia hunt run --source overpass --region ...`
   - `conciencia config get|set search.country PY`
   - `conciencia agent list | module list` (stubs que leen el core)
2. Usa **los mismos services** (`search.py`, `discovery.py`, `geo.py`) con su propia sesión DB (`SessionLocal`).

**Migración:** ninguna. **Tests:** `test_cli.py` (runner con `CliRunner` de typer sobre DB de test).

**Resultado (commit `6d119fd`):**
- `backend/cli.py` (typer + rich) + `pyproject.toml` con entry point `conciencia` (pip install -e .).
- Comandos: `health`, `search` (misma lógica que POST /search, con `--country/--region/--category/--online/--min-score/--sort/--json`), `leads list`, `leads export --format csv|json [--out]`, `lead inspect|score|enrich <id>` (inspect/score integran Fase 4: lead_score/opportunity/data_quality/reasons), `hunt run --source --region --industry`, `config get|set search.country PY` (mapea claves cortas → settings), `agents` (tabla real), `modules` (registry spec §21).
- `_make_session()` respeta `DATABASE_URL` (tests/deploy) y agrega backend/ al sys.path para correr desde cualquier CWD.
- typer+rich en requirements; numpy ya estaba. 14 tests nuevos; suite F1-F6: 108 verdes.
- Fix test: `config set` escribe os.environ directo → limpiar con `os.environ.pop` (monkeypatch.delenv restaura el valor en su undo y contaminaba test_geo).

**DoD Fase 6:** `conciencia search "empresas logísticas" --country PY` devuelve los mismos leads (orden/score) que `GET /api/v1/leads/search`.

---

### FASE 7 — Boundaries de core + slimming (spec P8, §42/§48) 🧱 ✅ HECHA (29/08)
**Objetivo:** dominio reutilizable y routers/páginas más delgados, sin rewrites.

1. **Extraer servicios**: `search.py` (search engine), `geo.py`, `normalization.py`, `entity.py`, `ranking.py` ya creados en fases previas → router.py queda como capa fina HTTP.
2. **`leadhunter/service.py`** refactor: `compute_score` se convierte en wrapper de `ranking.lead_score()` (compat garantizado por tests existentes).
3. **`core/` conceptual** (spec §20/§21): crear `backend/app/core/` solo con `config.py` (settings unificados) + `interfaces.py` (protocolos: GeoProvider, VectorBackend, LeadSource) — **sin** implementar CRM/ERP/modules aún (scope control §47).
4. **Frontend**: dividir `Leads.tsx` en componentes (`LeadSearchBar`, `LeadFiltersPanel`, `LeadTable`, `LeadDetail`, `HuntPanel`) — refactor puro, cero cambio de comportamiento.

**Migración:** ninguna. **Tests:** correr toda la suite existente (regresión = señal de éxito).

**Resultado (commit `6d119fd`):**
- Backend: `router.py` 1126 → 52 ln (agregador); handlers movidos a `endpoints/` (search/hunt/lists/proposals/leads) + `helpers.py` compartido; 48 rutas + intake idénticas (app 177 rutas).
- `service.compute_score` ahora es wrapper de `ranking._blocks()` (única fuente de verdad; HIGH_VALUE_INDUSTRY/SOURCE_BONUS viven en ranking).
- `app/core/` nuevo: `config.py` (settings unificados env+DB: search_defaults/ranking_weights/embedding_config) + `interfaces.py` (Protocols GeoProvider/VectorBackend/LeadSource, spec §10/§14/§11).
- Frontend: `Leads.tsx` 1629 → 476 ln; UI dividida en `components/leads/` (LeadFilters, LeadTable, LeadDetail, PipelineBoard, LeadModal, types) — refactor puro, comportamiento idéntico (tsc + build OK).
- Fix tipos: `LeadList` duplicada (merge de interfaces) separada en `LeadPage` (respuesta paginada) vs `LeadList` (lista guardada).
- Suite completa F1-F7: 108 verdes.

**DoD Fase 7:** `router.py` < 400 ln, `Leads.tsx` < 600 ln, suite completa verde, funcionalidad idéntica.

---

### FASE 8 — Agentes LeadHunter mínimos (spec P9, §17/§18/§27/§28) 🤖 ✅ HECHA (30/08)
**Objetivo:** enrichment agents usando el AgentRuntime existente; NO construir agentes autónomos todavía.

1. Registrar agents LeadHunter en la tabla `agents` (SOUL.md): `LeadResearchAgent`, `BusinessClassificationAgent`, `ContactDiscoveryAgent`.
2. **Router**: `POST /api/v1/leads/{id}/enrich/agent` — corre agent con herramientas `leads.read`, `search.execute`, `website_fetch` (mapea a `enrich.py`). Permisos: ALLOW leads.read/search.execute; DENY finance.write (spec §28).
3. **Audit** (spec §29): los runs de agentes ya caen en `audit_events`/traces — verificar y documentar.

**Migración:** seed de agents. **Tests:** `test_leadhunter_agents.py` con LLM mockeado.

**Resultado (commit `[PENDIENTE]`):**
- 3 roles nuevos en `AgentRole`: lead_research / business_classification / contact_discovery + SOUL.md en `agents/<role>/` (formato de output estricto, permisos declarados).
- `scripts/seed_agents.py` extendido (11 agentes, idempotente) con `config.permissions` (allow/deny spec §28).
- `leadhunter/agents.py` nuevo: `run_lead_agent()` (permisos → contexto del lead → adapter generic → AgentExecution + audit spec §29), `check_permissions`, `build_lead_context`; contact_discovery corre la herramienta real `website_fetch` (enrich_from_website) y la pasa como contexto.
- Endpoint `POST /api/v1/leads/{id}/enrich/agent` (action: research|classify|contacts; 403 si DENY, 404 si no está seedeado, 409 si LLM no configurado). Output guardado en `lead.meta.agents.<action>`.
- 9 tests nuevos (mock de adapter); suite F1-F8: 117 verdes.

**DoD Fase 8:** "Enrich these 20 leads" corre como job de agente; cada acción auditable; sin permisos globales.

---

### FASE 9 — Multi-Runtime Agent Integration: Conciencia como Control Plane del dueño (requisito CEO, 23/08) 🔌
**Objetivo:** Conciencia = dashboard centralizado adaptado al dueño. Poder operar agentes externos reales (Claude Code, Codex, OpenCode, OpenClaw, etc.) desde la plataforma, además del runtime interno DeepSeek/LLM. Alineado con spec §17/§18/§27/§28 y con la Integration Layer de la landing (adapters runtime-agnostic).

1. **`backend/app/core/agent_runtime.py` (NUEVO)**: abstracción `AgentRuntime` con `run(task, context, tools) -> RunResult` + registry de runtimes:
   - `InternalLLMRuntime` — el AgentRuntime actual (DeepSeek/LLM + SOUL.md)
   - `ClaudeCodeRuntime` — CLI `claude -p` en un repo/cwd
   - `CodexRuntime` — CLI `codex exec`
   - `OpenCodeRuntime` — CLI `opencode run`
   - `OpenClawRuntime` — CLI `openclaw` / gateway API
   - `McpRuntime` — herramientas MCP ya existentes (`routers/mcp.py`)
2. **Modelo/config `agent_runtimes`**: nombre, tipo, comando, cwd, habilitado, permisos (ALLOW/DENY, spec §28). UI en Settings → Agents → Runtimes.
3. **Router**: `GET/POST /api/v1/agents/runtimes` + `POST /api/v1/agents/{id}/run?runtime=<tipo>` (el endpoint actual de run gana el param, aditivo). Output/logs del run en traces + audit (spec §29: who/agent/tool/action/result/timestamp/cost).
4. **UI**: selector de runtime por agente + estado (online/offline) + output del run; Dashboard muestra agentes externos como workers (estilo AgentOffice).
5. **Seguridad**: allowlist de cwd/comandos por runtime; los CLIs corren en subproceso con timeout + captura de output; **ningún comando externo se ejecuta sin permiso del dueño** (spec §28/§47 — nada autónomo).
6. **Reuso**: los agentes LeadHunter (Fase 8) pueden correr en cualquier runtime configurado.

**Migración:** tabla `agent_runtimes` (o settings JSON). **Tests:** `test_agent_runtimes.py` — registry, run con mock CLI, permisos, audit.

**DoD Fase 9:** desde Conciencia se dispara un agente en Claude Code / Codex / OpenCode / OpenClaw y el resultado (output/archivos/status) vuelve al dashboard; cada ejecución auditable y aprobada por el dueño.

---

### FASE 10 — Cache + Exports + Benchmark (spec §36/§37/§38/§40) 🚀
1. **Cache** en geo/search/enrich (TTL configurable, `SEARCH_CACHE_TTL`), redis si está disponible, dict en local.
2. **Exports**: `GET /api/v1/leads/export?format=csv|json` (usa el SearchQuery actual) + `conciencia leads export`.
3. **Search benchmark** (spec §40): script `scripts/benchmark_search.py` con las 5 queries de referencia, mide precision/recall aprox/latency/dupes.
4. **Paginación cursor** en `/search` (Fase 2 ya lo preparó).

**Migración:** ninguna. **Tests:** export CSV/JSON, cache hit/miss.

---

### FASE 11 — E2E final + Definition of Done (spec §39/§50/§52) ✅
1. **Test E2E completo**: "playas de autos usados en Ciudad del Este" → interpret → filtros → search → ranking → detail (sources, quality, reasons) → enrich → save list → export. En `test_leadhunter_e2e.py` ampliado.
2. **Checklist §50** completo (21 items) + **test §52** (14 pasos) documentado en `docs/ARCHITECTURE.md`.
3. Commits: cada fase con su tag/mensaje; docs de arquitectura BEFORE/AFTER (spec §48).

---

## 3. ARCHIVOS A TOCAR (resumen)

**NUEVOS (backend):**
- `app/modules/leadhunter/geo.py` · `search.py` · `nlu.py` · `normalization.py` · `entity.py` · `ranking.py` · `embeddings.py`
- `app/core/agent_runtime.py` (runtimes: internal, claude-code, codex, opencode, openclaw, mcp)
- `backend/cli.py` + entry point `conciencia`
- `scripts/benchmark_search.py`
- tests: `test_geo.py` `test_nlu.py` `test_dedupe_v2.py` `test_ranking.py` `test_search_api.py` `test_cli.py` `test_semantic.py` `test_leadhunter_agents.py` `test_agent_runtimes.py` `test_exports.py`

**MODIFICAR (backend):**
- `sources/overpass.py` (scope geográfico) · `sources/base.py` (provenance contract)
- `models.py` (normalized_name/phone + índices) · `discovery.py` (dedupe v2 + scope) · `service.py` (wrapper ranking) · `router.py` (endpoints aditivos + slim) · `catalog.py` (sinónimos NL)
- `app/config.py` (SEARCH_*) · `routers/settings.py` (geo + weights en VISIBLE_KEYS)
- `requirements.txt` (+typer, +rich) · alembic migration Fase 3

**FRONTEND:**
- `pages/Leads.tsx` → dividir en `components/leads/*` (search bar NL + chips, filters, table, detail, hunt)
- `pages/Settings.tsx` (Search Geography + Ranking/Scoring) · `services/api.ts` (nuevos endpoints)

---

## 4. MIGRACIONES REQUERIDAS

| Fase | Migración | Contenido |
|---|---|---|
| 3 | `leadhunter_normalization` | `leads.normalized_name` (index), `leads.normalized_phone` (index) + backfill idempotente |
| 5 | opcional | extensión `pgvector` + tabla `business_documents` (solo prod con flag) |
| 8 | seed | agents LeadHunter en tabla `agents` |
| 9 | `agent_runtimes` | tabla de runtimes externos (tipo, comando, cwd, permisos, habilitado) |

> `sync_schema` ya cubre columnas nuevas en SQLite dev; alembic para prod.

---

## 5. RIESGOS Y DECISIONES ABIERTAS

1. **NL parser**: reglas primero (sin API key), LLM como upgrade. Decisión: ¿aceptar DeepSeek para interpretar queries cuando haya key? → sugerido SÍ (fallback silencioso a reglas).
2. **pgvector en prod**: el server usa Postgres; habilitar extensión requiere privilegio. Decisión: dejar Fase 5 con backend in-memory hasta confirmar.
3. **Dedupe v2 y leads existentes**: backfill necesario antes de activar índices. Decisión: correr como script idempotente en deploy.
4. **"Cazar TODO"**: la spec exige scope por defecto; el botón desaparece como acción default → confirmar con Iron Toto que es aceptable.
5. **Archivos accidentales en git status**: `AGENTIC-BUSINESS-OS` (0 bytes, artefacto de `notepad file1 file2`) y `_spec_tmp.md` (ya borrado). Sugerencia: borrar `AGENTIC-BUSINESS-OS` y renombrar la spec a `docs/SPEC_LEADHUNTER_INTELLIGENCE.md` (el nombre actual con em-dash `—` complica los scripts en MINGW).

---

## 6. DEFINITION OF DONE (spec §50 — checklist a completar fase por fase)

- [x] Search funciona E2E · [x] Country default PY · [x] Scope configurable · [x] No se puede consultar el mundo por accidente
- [x] NL query funciona · [x] Filtros estructurados editables · [x] Search y filtros no se contradicen
- [x] OSM/provider abstraído · [x] Rate limits respetados · [x] Resultados normalizados · [x] Duplicados reducidos
- [x] Relevance rankeada · [x] Lead Score independiente de relevance · [x] Data quality visible · [ ] Provenance preservada
- [ ] Fundación semántica · [x] Search reutilizable por agentes · [x] CLI usa mismos services · [x] API y UI misma lógica
- [x] Tests críticos · [x] Funcionalidad existente intacta

**Meta final (spec §52):** el usuario escribe "Find vehicle dealerships in Alto Paraná that have a website, phone number and appear to be active businesses" y Conciencia lo entiende, infiere PY, filtra, busca, normaliza, deduplica, rankea, explica, muestra calidad, permite enrich/save/CRM/CLI/agente.
