# PRODUCTION_READINESS — Conciencia Platform (audit final, actualizado 2026-09-03)

Clasificación por área: **READY** · **READY WITH LIMITATIONS** · **EXPERIMENTAL** · **NOT IMPLEMENTED**.
No se marketing de capacidades incompletas como completas.

## Control Plane (Missions / Workflows / Agentes / Teams)

| Área | Estado | Notas |
|---|---|---|
| Mission lifecycle (draft→planned→running→waiting_approval→completed/failed/cancelled) | READY | E2E verificado con LLM real |
| Workflow engine (secuencial + bloques paralelos) | READY | fan-out/fan-in, sesiones propias por child, outputs parciales |
| Resolución de agentes (agent_id → team → pool → global) | READY | determinista; capabilities = soft, required_capabilities = hard |
| Teams (CRUD, members, match) | READY | tie determinista por orden de inserción |
| Runtimes externos (claude_code/codex/opencode/openclaw) | READY WITH LIMITATIONS | solo `generic` y `openclaw` tienen adapter; los demás config en Settings sin adapter → error claro |

## Harness (contrato de ejecución)

| Área | Estado | Notas |
|---|---|---|
| Harness versionado (instructions/context/tools/guardrails/runtime/output_contract) | READY | historial de versiones preservado |
| Harness inactivo NO ejecuta (misión ni step override) | READY | audit §6 — fijado |
| Validación post-dispatch (output_contract) | READY | falla con error observable |
| Guardrail de runtime (allowed) | READY | bloquea antes del dispatch |

## Context Packs

| Área | Estado | Notas |
|---|---|---|
| Retrieval por keywords (título 3x/claves 2x/valores 1x), top-K, max_chars | READY | determinista, sin LLM, sin vectores |
| pack explícito de misión override retrieval | READY | existencia y pertenencia al proyecto validadas; nunca hace fallback silencioso |
| Aislamiento por proyecto | READY WITH LIMITATIONS | estricto cuando la misión declara proyecto; sin proyecto el retrieval sigue siendo global (single-tenant hoy) |
| Embeddings/semántica | NOT IMPLEMENTED | intencional (§7: no agregar vectores en este audit) |

## Observabilidad

| Área | Estado | Notas |
|---|---|---|
| workflow_runs.events (timeline estructurado) | READY | workflow/step/approval/parallel/failure events |
| step_results (tokens, costo, runtime, provider, model, duration, actions, tool_calls) | READY | |
| MissionRun logs/tokens/cost agregados | READY | incluye children paralelos |
| CLI run inspect --steps / run watch / --json | READY | misma data canónica |

## Signals + Evidence

| Área | Estado | Notas |
|---|---|---|
| Signal/Evidence con provenance (mission/run/step/agent) | READY | |
| Extracción automática de marcadores SIGNAL:/EVIDENCE: | READY | al completar; no fabrica evidencia |
| Evidence vinculada a missions.evidence_ids | READY | cascade al borrar misión (audit §17 — fijado) |

## WebMCP

| Área | Estado | Notas |
|---|---|---|
| WebMCP como tool/adapter gobernado | READY | step `webmcp` en workflow; sin agente LLM |
| Evidencia de interacción (action log + snapshot) → Signal/Evidence | READY | |
| Timeouts/errores estructurados | READY | httpx timeout + WebMCPError |
| App demo (window.webmcp + bridge) | EXPERIMENTAL | solo para pruebas; el demo_runner no es un producto |

## Economics

| Área | Estado | Notas |
|---|---|---|
| Costos LLM/tools/total por run y misión | READY | cost_records del harness + external_costs |
| Tokens agregados (prompt/completion/total) | READY | |
| Costo desconocido | READY WITH LIMITATIONS | sin usage del provider → 0 (no se asume costo falso; documentado) |
| Billing/límites de presupuesto | NOT IMPLEMENTED | intencional (§13) |

## Seguridad

| Área | Estado | Notas |
|---|---|---|
| Auth en routers sensibles | READY | audit §20 — 12 routers protegidos (HTTPBearer) |
| Secrets fuera de logs/events | READY | revisado: no se loguean keys |
| Approval como control de ejecución | READY WITH LIMITATIONS | gates detienen el engine y se bloquean runs activos duplicados; `approval_policy` de Mission aún no genera gates automáticos |
| Rate limiting / tenancy multi-cliente | NOT IMPLEMENTED | single-tenant hoy; fuera de alcance (§29) |

## Deployment

| Área | Estado | Notas |
|---|---|---|
| Docker + docker-compose | READY | WebMCP exige `WEBMCP_ALLOWED_HOSTS` en producción; revisar healthchecks/restart en OPERATIONS.md |
| Migraciones alembic | READY | cadena lineal a1b2c3d4e5f7→…→c3d4e5f6a7b9 |
| CORS / host binding | READY WITH LIMITATIONS | verificar `get_cors_origins` para prod |

## Frontend (Control Plane UI)

**Clasificación: PARTIALLY_CONNECTED**

Conectado con API real (axios + JWT): Dashboard, Projects, Tasks, Agents, Workflows,
Approvals, Context, Traces, Costs, Leads, Email, Settings.
Sin pantalla todavía (backend listo): **Missions, Teams, Harnesses, Signals/Evidence,
Economics, WebMCP**. La UI es React+Vite (sin redesign en este audit — §FRONTEND).

## Verificación del hardening 2026-09-03

- Suite final local: **328 passed, 0 failed, 0 skipped, 0 deselected** en 281.43 s.
- `compileall`, Ruff de errores fatales, build TypeScript/Vite, Compose config, CLI help y
  API `/health` pasaron. El lint amplio conserva deuda preexistente documentada.
- Reanudación tras approval resincroniza eventos, tokens, costo, error y timestamps desde
  `WorkflowRun`; después extrae Signals/Evidence idempotentemente.
- Context Packs explícitos inexistentes o de otro proyecto fallan antes del dispatch.
- WebMCP valida URL/payload/JSON, requiere allowlist de hosts en producción y respeta
  `harness.spec.tools.allow/deny` antes de ejecutar acciones.
- Limitación aceptada: la aprobación previa a un side effect depende hoy del orden de gates
  en el Workflow; no existe aún clasificación universal READ/WRITE/DESTRUCTIVE ejecutable.

---
Generado por: audit final `master-prompt-final1.md` · 2026-09-01 · rama v2-refactor
