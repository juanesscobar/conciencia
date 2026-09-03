# CHANGELOG — Conciencia Platform

## 2026-09-03 — Hardening de contratos de ejecución
- Context Packs explícitos: validación de existencia/proyecto y límites estrictos.
- WebMCP: URL/payload/JSON validados, allowlist obligatoria en producción y enforcement
  de `Harness.tools` antes del dispatch.
- Approval resume: MissionRun vuelve a derivar logs, tokens, costos, errores y timestamps
  del WorkflowRun; Signals/Evidence finales se promueven de forma idempotente.
- Evidencia: extraction repetida no duplica Signals y delete limpia `mission.evidence_ids`.
- Baseline reparada: metadata defensiva del LLM Harness y expectativa HTTPBearer 401.
- JobScout: la tarea de expiración vuelve a importar `Opportunity` y deja de fallar con
  `NameError` al ejecutarse.

## 2026-09-03 — RC deploy en producción (Hetzner)
- Backend + frontend F–L + audit desplegados en el server (46.62.196.151) — código
  `ae72bc1`; tablas/columnas nuevas creadas en Postgres prod (teams, harnesses, signals,
  evidence, events, external_costs). Verificado /health 200, 0 errores, frontend y demo
  /webmcp-demo/ 200. Backup pre-deploy en /opt/backups/.

## 2026-09-02 — WebMCP Challenge (Devpost)
- Demo app agent-native (tools WebMCP estándar) + kit DEVPOST_SUBMISSION.md.
- Deploy live: https://mc.46.62.196.151.sslip.io/webmcp-demo/ (servicio webmcp-demo
  interno + location nginx con sub_filter).

## 2026-09-01 — Fases F–L + Audit final de hardening (rama v2-refactor)

### Fase F — Agent/Team Orchestration (`3347495`)
- Teams (modelo, API `/api/v1/teams`, CLI `conciencia team`).
- Bloques paralelos en workflow engine (fan-out/fan-in, sesiones propias por child).
- Resolución team-primero con fallback global; capabilities soft vs required hard.
- Workflow default lead-research con bloque paralelo.

### Fase G — Harness Layer (`416d004`)
- Harness versionado (instructions/context/tools/validation/guardrails/runtime/
  output_contract) con historial; API + CLI.
- Aplicación del harness a la identidad del agente + validación post-dispatch.
- Fix: mission.agent_ids ahora es pool preferido en matching.

### Fase H — Observability (`7f39026`)
- `workflow_runs.events`: timeline estructurado (workflow/step/approval/parallel/failure).
- step_results enriquecidos (tokens, costo, runtime, provider, model, duration,
  actions, tool_calls).
- MissionRun espeja logs + tokens agregados; CLI `run inspect --steps` / `run watch`.

### Fase I — Signals + Evidence (`209e8f5`)
- Modelos Signal/Evidence con provenance mission/run/step/agent.
- Extracción automática de marcadores `SIGNAL:`/`EVIDENCE:`; evidencia vinculada a
  `missions.evidence_ids`; API + CLI `conciencia signal`.

### Fase J — Context Packs (`c32e0d1`)
- Retrieval eficiente por keywords (título 3x/claves 2x/valores 1x), top-K acotado a
  max_chars; pack explícito override; harness `{context_pack}`; API retrieve/assemble;
  CLI `conciencia context`.

### Fase K — WebMCP (`4162824`)
- WebMCP como tool/adapter: demo app WebMCP-enabled + cliente bridge (action log +
  snapshot); step `webmcp` en engine; evidencia promovida a Signal/Evidence;
  `mission.workflow_id` en create; API `/api/v1/webmcp`; CLI `conciencia webmcp`.

### Fase L — Economics (`59b4754`)
- `mission_runs.external_costs`; economics_service (mission/platform, record_external_cost);
  API `/api/v1/economics`; CLI `conciencia economics summary/record-external`.

### Audit final — hardening & production readiness
- **Seguridad**: 12 routers sensibles ahora exigen auth (context-packs, traces, costs,
  metrics, decisions, policies, sprints, reports, activities, assistant, github, mcp).
- **Aprobaciones**: re-aprobar un run terminado bloqueado (400) — no re-ejecución;
  approve de workflows valida estado paused y devuelve 400 en vez de 500.
- **Harness**: steps con harness inactivo (draft/archived) no ejecutan.
- **Persistencia**: borrar misión hace cascade de signals + evidence (sin huérfanos).
- **Provenance**: step_results incluyen `harness_id`/`harness_version`.
- Docs: ARCHITECTURE.md (actualizado), PRODUCTION_READINESS.md, SECURITY.md,
  OPERATIONS.md, CHANGELOG.md, FUTURE_NOTES.md.
- Suite: 291 passed + 8 deselected (LLM providers) → tras audit: 291 + 18 nuevos
  (test_audit_hardening) — ver resultado final del audit.

---
Historial anterior: ver git log (fases A–E en commits previos).
