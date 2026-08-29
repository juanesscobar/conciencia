# PLAN DE EJECUCIÃ“N â€” LeadHunter Intelligence Engine + Modular Agentic Business OS

> Fuente: `CONCIENCIAâ€”LEADHUNTER-INTELLIGENCE+ENGINE+MODULAR AGENTIC-BUSINESS-OS` (spec 53 secciones)
> Rama: `v2-refactor` Â· Fecha: 2026-08-23
> Principio rector de la spec: **LeadHunter first, no romper nada, refactor incremental, dominio reutilizable (UI/API/CLI/Agents).**

---

## 1. AUDITORÃA (spec Â§48, P0 â€” HECHA)

### 1.1 Stack actual

| Capa | Estado |
|---|---|
| Backend | FastAPI + SQLAlchemy (SQLite dev / Postgres prod) + alembic + `sync_schema` |
| Frontend | React + Vite + Tailwind (dark theme) |
| MÃ³dulo LeadHunter | `backend/app/modules/leadhunter/` â€” ya modular: `router.py` (797 ln), `discovery.py`, `service.py` (scoring), `sources/` (base + overpass), `enrich.py`, `jobs.py` (async), `scheduler.py`, `delivery.py`, `proposal.py`, `pdfgen.py`, `catalog.py`, `schemas.py`, `exceptions.py` |
| Settings | Tabla `Setting` + overlay `os.environ` en upsert; `VISIBLE_KEYS` ya incluye `LEADHUNTER_CRON/BBOX/SCOPE` |
| Tests | `test_leadhunter_e2e.py` (jobs lifecycle, exceptions), `test_discovery.py` |
| CLI | âŒ NO existe (sin typer/click en requirements) |
| Agentes | Ya existe `AgentRuntime` + tabla agents + SOUL.md (`routers/agents.py`) â†’ reutilizable |
| Vector DB | âŒ No hay embeddings ni pgvector |

### 1.2 Flujo actual de LeadHunter

```
UI (Leads.tsx, 1335 ln)
  â”œâ”€ list_leads  â†’ GET /api/v1/leads/  â†’ filtros SQL ILIKE + paginaciÃ³n page/page_size
  â”œâ”€ hunt/run    â†’ run_discovery()     â†’ fuentes (overpass) â†’ dedupe O(nÂ²) â†’ compute_score â†’ INSERT
  â””â”€ pipeline    â†’ status/contact/qualify/proposal/enrich/events/lists/searches
```

### 1.3 Problemas encontrados (mapeados a la spec)

| # | Problema | Severidad | Spec |
|---|---|---|---|
| P1 | **"Cazar TODO (sin filtros)"** en la UI ignora filtros y scope: `huntRun.mutate(undefined)`. Una caza accidental toca todo el bbox/country | ðŸ”´ Alta | Â§9, Â§5 |
| P2 | **GeografÃ­a no es first-class**: bbox hardcodeado en env (`LEADHUNTER_BBOX` Gran AsunciÃ³n); no hay jerarquÃ­a paÃ­sâ†’regiÃ³nâ†’ciudad; no hay "Global" explÃ­cito; paÃ­s default no configurable en Settings (solo env) | ðŸ”´ Alta | Â§7, Â§8, Â§9 |
| P3 | **Sin pipeline NLâ†’filtros**: el search box es un ILIKE ambiguo sobre 6 columnas; no existe `SearchQuery` canÃ³nico ni intent parser | ðŸ”´ Alta | Â§5, Â§6, Â§32 |
| P4 | **Dedupe O(nÂ²)**: `_is_duplicate` carga TODOS los leads por candidato (`db.query(Lead).all()`); a 10k+ leads se vuelve inusable; sin Ã­ndice de nombre normalizado | ðŸ”´ Alta | Â§12 |
| P5 | **Filtro regiÃ³n con full-scan**: carga pares (id, region) y normaliza en Python por request | ðŸŸ  Media | Â§5 |
| P6 | **Scoring Ãºnico y hardcodeado**: `compute_score` mezcla relevancia de bÃºsqueda + lead score; keywords fijas de vertical software-factory; sin `RankingWeights` ni `LeadScore` separado ni data quality | ðŸŸ  Media | Â§15, Â§16, Â§35 |
| P7 | **Sin "why this result?"**: no hay breakdown de por quÃ© matchea un lead | ðŸŸ  Media | Â§34 |
| P8 | **Sin capa de search engine**: `list_leads` es un WHERE gigante; no hay full-text, ni ranking, ni hÃ­brido | ðŸŸ  Media | Â§13 |
| P9 | **Provenance dÃ©bil**: osm_id/lat/lon van en `meta` JSON; no hay `source_records`, ni confidence estructurada | ðŸŸ¡ Baja | Â§11, Â§35 |
| P10 | **Sin CLI** | ðŸŸ  Media | Â§19, Â§41 |
| P11 | **Sin cache** (geocoding, provider, bÃºsquedas) | ðŸŸ¡ Baja | Â§36 |
| P12 | **Sin export** (CSV/JSON) | ðŸŸ¡ Baja | Â§38 |
| P13 | **Router 797 ln / Leads.tsx 1335 ln** â€” god-objects; lÃ³gica mezclada (pipeline + propuestas + import + CRUD) | ðŸŸ¡ Baja | Â§42 |
| P14 | **Tests insuficientes**: no cubren NL, geo, dedupe v2, ranking, filtros, CLI, API search, exports | ðŸŸ  Media | Â§39 |
| P15 | RegiÃ³n del filtro usa `Lead.region` libre (calle, ciudad, suburbio) â€” `regions` endpoint limpia a mano | ðŸŸ¡ Baja | Â§5 |

**Buenas noticias (no romper):** ya existe registry de fuentes (`sources/base.py`), dedupe bÃ¡sico, jobs async con cancel/retry, enrich web + IA, propuestas + PDF + delivery, webhook intake, bÃºsquedas guardadas y listas, scheduler. Eso se **preserva** y se usa como base.

---

## 2. PLAN POR FASES (cada fase = commit shippable + tests verdes)

> Orden = spec Â§49 (P0â†’P10). Cada fase incluye: archivos, migraciÃ³n, tests, DoD propio.
> **Regla de oro:** los endpoints existentes no cambian su contrato; todo lo nuevo es aditivo.

### FASE 1 â€” Correctness + Geographic Scope (spec P1/P2) âš¡
**Objetivo:** nadie puede consultar el mundo por accidente; el paÃ­s default es PY y configurable.

1. **`backend/app/modules/leadhunter/geo.py` (NUEVO)**
   - `GeographicScope`: `default_country=PY`, `allowed_countries=[PY,BR,AR,...]`, `default_region`, `default_city`, `scope=city|region|country|multi|global` (global SOLO si se pide explÃ­cito).
   - `GeoProvider` abstracto: `search_places()`, `geocode()`, `reverse_geocode()`, `resolve_region()`, `resolve_country()`, `resolve_city()`.
   - `OpenStreetMapProvider` adapter que envuelve a OverpassSource (reusa endpoints/mirrors existentes). Sin evasiÃ³n de rate limits (spec Â§10).
   - Cache TTL (dict simple + opcional redis si estÃ¡ configurado).
2. **`backend/app/config.py`**: `SEARCH_DEFAULT_COUNTRY=PY`, `SEARCH_ALLOWED_COUNTRIES`, `SEARCH_DEFAULT_REGION`, `SEARCH_DEFAULT_CITY`, `SEARCH_SCOPE` (compat: leer `LEADHUNTER_SCOPE/BBOX` como fallback).
3. **`sources/overpass.py`**: usa el scope geogrÃ¡fico en vez de `LEADHUNTER_SCOPE` directo; si scope es city/region â†’ bbox derivado del lugar (geocode), si country â†’ `PARAGUAY_AREA`, si multi/global â†’ permitido solo con flag explÃ­cito.
4. **`discovery.py` + router `hunt/run`**: aplicar scope por defecto cuando el usuario no pasa `region`; `scope` param explÃ­cito (`global` requiere confirmaciÃ³n `allow_global=true`).
5. **Frontend `Leads.tsx`**: el botÃ³n "Cazar" pasa filtros activos + muestra chip de scope activo ("PY Â· Gran AsunciÃ³n"); eliminar el "Cazar TODO sin filtros" como acciÃ³n default (queda detrÃ¡s de confirmaciÃ³n).
6. **Settings UI + router**: secciÃ³n "Search Geography" (paÃ­s default, paÃ­ses permitidos, scope). `VISIBLE_KEYS` ampliado.

**MigraciÃ³n:** ninguna (solo env/settings). **Tests:** `test_geo.py` â€” default PY, global bloqueado sin flag, resolve country/region, cache.

**DoD Fase 1:** `"restaurantes"` con settings PY â†’ bÃºsqueda PY, nunca mundo; cazar sin filtros queda acotado al scope; settings persistente.

---

### FASE 2 â€” SearchQuery canÃ³nico + NL â†’ filtros (spec P3, Â§5/Â§6/Â§32) ðŸ§ 
**Objetivo:** un objeto `SearchQuery` reutilizable por UI/API/CLI/Agents; la UI muestra chips editables (interpreted filters).

1. **`leadhunter/search.py` (NUEVO)**:
   - `SearchQuery` (pydantic): `query`, `entity_type`, `country`, `region`, `city`, `category`, `industry`, `required_fields[]`, `sort`, `scope`.
   - `SearchEngine`: `execute(SQLAlchemySession, SearchQuery) -> SearchResult` â€” unifica `list_leads` actual (filtros estructurados + full-text con `ilike` normalizado, preparado para FTS).
   - Cursor pagination como opciÃ³n (`cursor` param), manteniendo `page/page_size` para compat.
2. **`leadhunter/nlu.py` (NUEVO)**: intent parser por reglas (esâ†’categorÃ­as/sinÃ³nimos + geografÃ­a + required_fields). Ej: "playas de autos usados en Ciudad del Este" â†’ `{category: used_car_dealer, city: Ciudad del Este, country: PY}`. Backend opcional LLM (DeepSeek) para fallback, sin romper si no hay key.
3. **Router**: `POST /api/v1/leads/search/interpret` (NL â†’ SearchQuery) y `POST /api/v1/leads/search` (ejecuta SearchQuery) â€” aditivos, no tocan `GET /`.
4. **Frontend**: caja de bÃºsqueda con lenguaje natural + chips editables (paÃ­s/regiÃ³n/ciudad/categorÃ­a/filtros) que se mapean 1:1 al `SearchQuery`.
5. **`catalog.py`**: ampliar con sinÃ³nimos (playa de autos â†’ used_car_dealer/car_dealer/automotive) y categorÃ­as usadas por el NL parser.

**MigraciÃ³n:** ninguna. **Tests:** `test_nlu.py` (5 queries benchmark de spec Â§40), `test_search_api.py`.

**DoD Fase 2:** una query humana produce filtros visibles/editables; misma query corre por UI y por API con los mismos resultados.

---

### FASE 3 â€” NormalizaciÃ³n + Dedupe v2 (spec P4, Â§12) ðŸ”—
**Objetivo:** dedupe indexado y entity resolution sin duplicados.

1. **`leadhunter/normalization.py` (NUEVO)**: extraer/mejorar `normalize_company`, `domain_of`, `norm_phone` (E.164-ish), `norm_address`; normalizar tambiÃ©n emails.
2. **Modelo `Lead`**: columna `normalized_name` (String, index) + `normalized_phone` (String, index) â€” poblada en create/update/import/hunt (hook en `Lead.__init__` o en servicios).
3. **`leadhunter/entity.py` (NUEVO)**: `find_duplicates(db, company, website, phone, email)` con lookups indexados (equality por `normalized_name` + `normalized_phone` + dominio), en vez de `db.query(Lead).all()`.
4. **`discovery.py` + `import_csv` + `create_lead`**: usar dedupe v2. `_is_duplicate` viejo queda como compat interno (o se elimina tras tests).
5. **Backfill**: script/migraciÃ³n para poblar `normalized_name/phone` de leads existentes (idempotente).

**MigraciÃ³n:** alembic `leadhunter_normalization` (2 columnas + 2 Ã­ndices). **Tests:** `test_dedupe_v2.py` â€” nombre+acentos+sufijos legales, dominio, tel 8 dÃ­gitos, email, y benchmark sin full-scan.

**DoD Fase 3:** 10k leads â†’ dedupe <100ms; 2Âª corrida de caza = 0 nuevos (como el E2E 17/08 pero sin degradaciÃ³n).

---

### FASE 4 â€” Ranking + Scoring separados + Data Quality (spec P5, Â§15/Â§16/Â§34/Â§35) ðŸ“Š âœ… HECHA (29/08)
**Objetivo:** relevancia â‰  lead score â‰  opportunity; weights configurables; "why this match".

1. **`leadhunter/ranking.py` (NUEVO)**:
   - `SearchRelevance` (por query): category_match, geographic_match, keyword_match â†’ 0-1.
   - `LeadScore` (independiente de la query): reusa `compute_score` refactorizado como componente (completitud + industria + fuente) â€” **sin romper** el contrato actual.
   - `OpportunityScore` (opcional, stub con seÃ±ales: website+tel+actividad).
   - `DataQualityScore`: completeness + freshness + source reliability + consistency (0-100).
   - `RankingWeights` configurable (settings DB, default en cÃ³digo).
   - `explain()` â†’ lista de razones ("Automotive", "En Ciudad del Este", "Website detectado"...) para el "Why this lead matches".
2. **Schemas**: `LeadResponse` gana `search_relevance`, `data_quality`, `reasons[]` (aditivo, sin romper frontend).
3. **Settings**: "Ranking & Scoring" (weights editables) + `VISIBLE_KEYS`.
4. **Frontend**: en lead detail y filas, mostrar score breakdown + razones.

**MigraciÃ³n:** ninguna (campos calculados). **Tests:** `test_ranking.py` â€” weights default, separaciÃ³n scores, reasons.

**Resultado (commit `8aa7989`):**
- `ranking.py` nuevo: `SearchRelevance` (category/geo/keyword), `LeadScore` ponderado por bloques (reusa `_blocks` de service sin romper `compute_score`), `OpportunityScore`, `DataQualityScore` (completitud+frescura+fuente), `RankingWeights` configurables, `explain()` â†’ razones.
- `RANKING_WEIGHTS` (JSON) en Settings (VISIBLE_KEYS) + `GET/PUT /api/v1/leads/ranking/weights` (PUT solo admin/owner/ceo).
- `LeadResponse` gana `search_relevance`, `opportunity_score`, `data_quality`, `reasons[]` (aditivo, sin romper frontend).
- UI: tabla muestra `O:n Â· Q:n` con tooltip de razones; LeadDetail gana card "Score Intelligence" con 4 barras + "Â¿Por quÃ© este lead?"; Settings â†’ Ranking & Scoring con editor JSON de pesos.
- 21 tests nuevos (`test_ranking.py`); suite F1-F4: 81 tests verdes. Typecheck + build OK.

**DoD Fase 4:** un lead con relevance 92% puede tener lead score 81 y opportunity 74 (ejemplo spec Â§16); el admin cambia pesos sin tocar cÃ³digo.

---

### FASE 5 â€” BÃºsqueda semÃ¡ntica foundation (spec P6, Â§14) ðŸ§¬ âœ… HECHA (29/08)
**Objetivo:** arquitectura lista para embeddings, sin vector DB externa.

1. **`leadhunter/embeddings.py` (NUEVO)**: `VectorBackend` abstracto (`upsert`, `search`) + `PgVectorBackend` (pgvector, solo si postgres + extensiÃ³n) + `InMemoryBackend` (cosine en numpy, SQLite dev).
2. **`BusinessDocument`** modelo (o JSONB dentro de `leads.meta`): text = company+industry+category+description+address, embedding vector.
3. **Router**: `POST /api/v1/leads/search/semantic` (aditivo; devuelve 501 "embedding model not configured" si no hay key).
4. **Settings**: `EMBEDDING_MODEL`, `EMBEDDING_ENABLED`.

**MigraciÃ³n:** opcional `pgvector` en prod (flag), cero en dev. **Tests:** `test_semantic.py` con InMemoryBackend + modelo fake.

**Resultado (commit `8a1ce4b`):**
- `embeddings.py` nuevo: `VectorBackend` abstracto (upsert/search/delete/count) + `InMemoryBackend` (cosine numpy, dev) + `PgVectorBackend` (pgvector autocontenido, fallback a memory si no hay extensiÃ³n).
- `embed_text()`: OpenAI-compatible si hay API key; modo SIMULADO determinÃ­stico (n-grams hasheados dim 384) sin key â†’ demo/tests nunca rompen.
- `BusinessDocument` como JSONB en `leads.meta["semantic"]` (provenance: text/model/dim/indexed_at) â€” sin migraciÃ³n en dev.
- `POST /api/v1/leads/search/semantic` (501 si EMBEDDING_ENABLED no estÃ¡) + `GET /search/semantic/status` (backend/modelo/indexados/simulado). IndexaciÃ³n lazy incremental (`reindex_if_needed`).
- Settings: EMBEDDING_ENABLED/MODEL/PROVIDER/BACKEND/BASE_URL (VISIBLE_KEYS + UI en Lead Hunter); `numpy` agregado a requirements.
- UI: botÃ³n ðŸ§¬ SemÃ¡ntica en Leads (usa la consulta NL o el buscador), banner de resultados semÃ¡nticos + R: en badges; Settings muestra estado con contador.
- 13 tests nuevos; suite F1-F5: 94 verdes. tsc + build OK.

**DoD Fase 5:** el endpoint existe, es abstracto, y funciona end-to-end con un embedding model barato (p.ej. `text-embedding-3-small` o local) o en modo simulado; no introduce Qdrant/Weaviate.

---

### FASE 6 â€” CLI `conciencia` (spec P7, Â§19/Â§41) ðŸ’» âœ… HECHA (29/08)
**Objetivo:** misma lÃ³gica de dominio que UI/API, cero backend duplicado.

1. **`backend/cli.py` + pyproject entry point `conciencia`** (typer + rich; agregar a requirements).
   - `conciencia health`
   - `conciencia search "playas de autos usados" --country PY --region "Alto ParanÃ¡" --json`
   - `conciencia leads list|export --format csv|json`
   - `conciencia lead inspect <id> | enrich <id> | score <id>`
   - `conciencia hunt run --source overpass --region ...`
   - `conciencia config get|set search.country PY`
   - `conciencia agent list | module list` (stubs que leen el core)
2. Usa **los mismos services** (`search.py`, `discovery.py`, `geo.py`) con su propia sesiÃ³n DB (`SessionLocal`).

**MigraciÃ³n:** ninguna. **Tests:** `test_cli.py` (runner con `CliRunner` de typer sobre DB de test).

**Resultado (commit `4ae1122`):**
- `backend/cli.py` (typer + rich) + `pyproject.toml` con entry point `conciencia` (pip install -e .).
- Comandos: `health`, `search` (misma lÃ³gica que POST /search, con `--country/--region/--category/--online/--min-score/--sort/--json`), `leads list`, `leads export --format csv|json [--out]`, `lead inspect|score|enrich <id>` (inspect/score integran Fase 4: lead_score/opportunity/data_quality/reasons), `hunt run --source --region --industry`, `config get|set search.country PY` (mapea claves cortas â†’ settings), `agents` (tabla real), `modules` (registry spec Â§21).
- `_make_session()` respeta `DATABASE_URL` (tests/deploy) y agrega backend/ al sys.path para correr desde cualquier CWD.
- typer+rich en requirements; numpy ya estaba. 14 tests nuevos; suite F1-F6: 108 verdes.
- Fix test: `config set` escribe os.environ directo â†’ limpiar con `os.environ.pop` (monkeypatch.delenv restaura el valor en su undo y contaminaba test_geo).

**DoD Fase 6:** `conciencia search "empresas logÃ­sticas" --country PY` devuelve los mismos leads (orden/score) que `GET /api/v1/leads/search`.

---

### FASE 7 â€” Boundaries de core + slimming (spec P8, Â§42/Â§48) ðŸ§±
**Objetivo:** dominio reutilizable y routers/pÃ¡ginas mÃ¡s delgados, sin rewrites.

1. **Extraer servicios**: `search.py` (search engine), `geo.py`, `normalization.py`, `entity.py`, `ranking.py` ya creados en fases previas â†’ router.py queda como capa fina HTTP.
2. **`leadhunter/service.py`** refactor: `compute_score` se convierte en wrapper de `ranking.lead_score()` (compat garantizado por tests existentes).
3. **`core/` conceptual** (spec Â§20/Â§21): crear `backend/app/core/` solo con `config.py` (settings unificados) + `interfaces.py` (protocolos: GeoProvider, VectorBackend, LeadSource) â€” **sin** implementar CRM/ERP/modules aÃºn (scope control Â§47).
4. **Frontend**: dividir `Leads.tsx` en componentes (`LeadSearchBar`, `LeadFiltersPanel`, `LeadTable`, `LeadDetail`, `HuntPanel`) â€” refactor puro, cero cambio de comportamiento.

**MigraciÃ³n:** ninguna. **Tests:** correr toda la suite existente (regresiÃ³n = seÃ±al de Ã©xito).

**DoD Fase 7:** `router.py` < 400 ln, `Leads.tsx` < 600 ln, suite completa verde, funcionalidad idÃ©ntica.

---

### FASE 8 â€” Agentes LeadHunter mÃ­nimos (spec P9, Â§17/Â§18/Â§27/Â§28) ðŸ¤–
**Objetivo:** enrichment agents usando el AgentRuntime existente; NO construir agentes autÃ³nomos todavÃ­a.

1. Registrar agents LeadHunter en la tabla `agents` (SOUL.md): `LeadResearchAgent`, `BusinessClassificationAgent`, `ContactDiscoveryAgent`.
2. **Router**: `POST /api/v1/leads/{id}/enrich/agent` â€” corre agent con herramientas `leads.read`, `search.execute`, `website_fetch` (mapea a `enrich.py`). Permisos: ALLOW leads.read/search.execute; DENY finance.write (spec Â§28).
3. **Audit** (spec Â§29): los runs de agentes ya caen en `audit_events`/traces â€” verificar y documentar.

**MigraciÃ³n:** seed de agents. **Tests:** `test_leadhunter_agents.py` con LLM mockeado.

**DoD Fase 8:** "Enrich these 20 leads" corre como job de agente; cada acciÃ³n auditable; sin permisos globales.

---

### FASE 9 â€” Multi-Runtime Agent Integration: Conciencia como Control Plane del dueÃ±o (requisito CEO, 23/08) ðŸ”Œ
**Objetivo:** Conciencia = dashboard centralizado adaptado al dueÃ±o. Poder operar agentes externos reales (Claude Code, Codex, OpenCode, OpenClaw, etc.) desde la plataforma, ademÃ¡s del runtime interno DeepSeek/LLM. Alineado con spec Â§17/Â§18/Â§27/Â§28 y con la Integration Layer de la landing (adapters runtime-agnostic).

1. **`backend/app/core/agent_runtime.py` (NUEVO)**: abstracciÃ³n `AgentRuntime` con `run(task, context, tools) -> RunResult` + registry de runtimes:
   - `InternalLLMRuntime` â€” el AgentRuntime actual (DeepSeek/LLM + SOUL.md)
   - `ClaudeCodeRuntime` â€” CLI `claude -p` en un repo/cwd
   - `CodexRuntime` â€” CLI `codex exec`
   - `OpenCodeRuntime` â€” CLI `opencode run`
   - `OpenClawRuntime` â€” CLI `openclaw` / gateway API
   - `McpRuntime` â€” herramientas MCP ya existentes (`routers/mcp.py`)
2. **Modelo/config `agent_runtimes`**: nombre, tipo, comando, cwd, habilitado, permisos (ALLOW/DENY, spec Â§28). UI en Settings â†’ Agents â†’ Runtimes.
3. **Router**: `GET/POST /api/v1/agents/runtimes` + `POST /api/v1/agents/{id}/run?runtime=<tipo>` (el endpoint actual de run gana el param, aditivo). Output/logs del run en traces + audit (spec Â§29: who/agent/tool/action/result/timestamp/cost).
4. **UI**: selector de runtime por agente + estado (online/offline) + output del run; Dashboard muestra agentes externos como workers (estilo AgentOffice).
5. **Seguridad**: allowlist de cwd/comandos por runtime; los CLIs corren en subproceso con timeout + captura de output; **ningÃºn comando externo se ejecuta sin permiso del dueÃ±o** (spec Â§28/Â§47 â€” nada autÃ³nomo).
6. **Reuso**: los agentes LeadHunter (Fase 8) pueden correr en cualquier runtime configurado.

**MigraciÃ³n:** tabla `agent_runtimes` (o settings JSON). **Tests:** `test_agent_runtimes.py` â€” registry, run con mock CLI, permisos, audit.

**DoD Fase 9:** desde Conciencia se dispara un agente en Claude Code / Codex / OpenCode / OpenClaw y el resultado (output/archivos/status) vuelve al dashboard; cada ejecuciÃ³n auditable y aprobada por el dueÃ±o.

---

### FASE 10 â€” Cache + Exports + Benchmark (spec Â§36/Â§37/Â§38/Â§40) ðŸš€
1. **Cache** en geo/search/enrich (TTL configurable, `SEARCH_CACHE_TTL`), redis si estÃ¡ disponible, dict en local.
2. **Exports**: `GET /api/v1/leads/export?format=csv|json` (usa el SearchQuery actual) + `conciencia leads export`.
3. **Search benchmark** (spec Â§40): script `scripts/benchmark_search.py` con las 5 queries de referencia, mide precision/recall aprox/latency/dupes.
4. **PaginaciÃ³n cursor** en `/search` (Fase 2 ya lo preparÃ³).

**MigraciÃ³n:** ninguna. **Tests:** export CSV/JSON, cache hit/miss.

---

### FASE 11 â€” E2E final + Definition of Done (spec Â§39/Â§50/Â§52) âœ…
1. **Test E2E completo**: "playas de autos usados en Ciudad del Este" â†’ interpret â†’ filtros â†’ search â†’ ranking â†’ detail (sources, quality, reasons) â†’ enrich â†’ save list â†’ export. En `test_leadhunter_e2e.py` ampliado.
2. **Checklist Â§50** completo (21 items) + **test Â§52** (14 pasos) documentado en `docs/ARCHITECTURE.md`.
3. Commits: cada fase con su tag/mensaje; docs de arquitectura BEFORE/AFTER (spec Â§48).

---

## 3. ARCHIVOS A TOCAR (resumen)

**NUEVOS (backend):**
- `app/modules/leadhunter/geo.py` Â· `search.py` Â· `nlu.py` Â· `normalization.py` Â· `entity.py` Â· `ranking.py` Â· `embeddings.py`
- `app/core/agent_runtime.py` (runtimes: internal, claude-code, codex, opencode, openclaw, mcp)
- `backend/cli.py` + entry point `conciencia`
- `scripts/benchmark_search.py`
- tests: `test_geo.py` `test_nlu.py` `test_dedupe_v2.py` `test_ranking.py` `test_search_api.py` `test_cli.py` `test_semantic.py` `test_leadhunter_agents.py` `test_agent_runtimes.py` `test_exports.py`

**MODIFICAR (backend):**
- `sources/overpass.py` (scope geogrÃ¡fico) Â· `sources/base.py` (provenance contract)
- `models.py` (normalized_name/phone + Ã­ndices) Â· `discovery.py` (dedupe v2 + scope) Â· `service.py` (wrapper ranking) Â· `router.py` (endpoints aditivos + slim) Â· `catalog.py` (sinÃ³nimos NL)
- `app/config.py` (SEARCH_*) Â· `routers/settings.py` (geo + weights en VISIBLE_KEYS)
- `requirements.txt` (+typer, +rich) Â· alembic migration Fase 3

**FRONTEND:**
- `pages/Leads.tsx` â†’ dividir en `components/leads/*` (search bar NL + chips, filters, table, detail, hunt)
- `pages/Settings.tsx` (Search Geography + Ranking/Scoring) Â· `services/api.ts` (nuevos endpoints)

---

## 4. MIGRACIONES REQUERIDAS

| Fase | MigraciÃ³n | Contenido |
|---|---|---|
| 3 | `leadhunter_normalization` | `leads.normalized_name` (index), `leads.normalized_phone` (index) + backfill idempotente |
| 5 | opcional | extensiÃ³n `pgvector` + tabla `business_documents` (solo prod con flag) |
| 8 | seed | agents LeadHunter en tabla `agents` |
| 9 | `agent_runtimes` | tabla de runtimes externos (tipo, comando, cwd, permisos, habilitado) |

> `sync_schema` ya cubre columnas nuevas en SQLite dev; alembic para prod.

---

## 5. RIESGOS Y DECISIONES ABIERTAS

1. **NL parser**: reglas primero (sin API key), LLM como upgrade. DecisiÃ³n: Â¿aceptar DeepSeek para interpretar queries cuando haya key? â†’ sugerido SÃ (fallback silencioso a reglas).
2. **pgvector en prod**: el server usa Postgres; habilitar extensiÃ³n requiere privilegio. DecisiÃ³n: dejar Fase 5 con backend in-memory hasta confirmar.
3. **Dedupe v2 y leads existentes**: backfill necesario antes de activar Ã­ndices. DecisiÃ³n: correr como script idempotente en deploy.
4. **"Cazar TODO"**: la spec exige scope por defecto; el botÃ³n desaparece como acciÃ³n default â†’ confirmar con Iron Toto que es aceptable.
5. **Archivos accidentales en git status**: `AGENTIC-BUSINESS-OS` (0 bytes, artefacto de `notepad file1 file2`) y `_spec_tmp.md` (ya borrado). Sugerencia: borrar `AGENTIC-BUSINESS-OS` y renombrar la spec a `docs/SPEC_LEADHUNTER_INTELLIGENCE.md` (el nombre actual con em-dash `â€”` complica los scripts en MINGW).

---

## 6. DEFINITION OF DONE (spec Â§50 â€” checklist a completar fase por fase)

- [ ] Search funciona E2E Â· [ ] Country default PY Â· [ ] Scope configurable Â· [ ] No se puede consultar el mundo por accidente
- [ ] NL query funciona Â· [ ] Filtros estructurados editables Â· [ ] Search y filtros no se contradicen
- [ ] OSM/provider abstraÃ­do Â· [ ] Rate limits respetados Â· [ ] Resultados normalizados Â· [ ] Duplicados reducidos
- [x] Relevance rankeada Â· [x] Lead Score independiente de relevance Â· [x] Data quality visible Â· [ ] Provenance preservada
- [ ] FundaciÃ³n semÃ¡ntica Â· [x] Search reutilizable por agentes Â· [x] CLI usa mismos services Â· [x] API y UI misma lÃ³gica
- [ ] Tests crÃ­ticos Â· [ ] Funcionalidad existente intacta

**Meta final (spec Â§52):** el usuario escribe "Find vehicle dealerships in Alto ParanÃ¡ that have a website, phone number and appear to be active businesses" y Conciencia lo entiende, infiere PY, filtra, busca, normaliza, deduplica, rankea, explica, muestra calidad, permite enrich/save/CRM/CLI/agente.
