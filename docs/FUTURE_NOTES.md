# FUTURE_NOTES — oportunidades arquitectónicas (audit final, §21)

> Ideas comparativas (Gentle-AI / OpenClaw) para el FUTURO. NO implementar durante
> el audit ni en el próximo roadmap sin decisión explícita. No copiar productos.

## Persistent memory / Engram (Gentle-AI)
- Hoy: `user_memories` (texto por usuario) + `missions.evidence_ids` + Context Packs.
- Oportunidad: memoria operacional por AGENTE (qué aprendió un agente/team en misiones
  anteriores) reutilizable como fuente de Context Packs — sin transformar Conciencia en
  un chatbot con memoria conversacional.

## Skill Registry (Gentle-AI)
- Hoy: capabilities de agentes (strings libres) + capability_matching por keywords.
- Oportunidad: un registry formal de skills (id, descripción, input/output contract,
  ejemplos) al que referencien agentes y harnesses; habilita routing por skill más
  preciso y tool discovery para WebMCP/MCP.

## Organic routing
- Hoy: resolución determinista agent_id → team → pool → global con score de coverage.
- Oportunidad: feedback de outcomes (señales/costo/éxito por step) para ajustar el
  scoring sin perder la determinismo base (solo como capa opcional).

## Receipt-Driven Development (Gentle-AI)
- Hoy: §22 del audit — el MissionRun + step_results + events reconstruyen un receipt.
- Oportunidad: exponer el "Mission Receipt" como artefacto versionado (markdown/JSON)
  al completar una misión; los BUILD missions podrían consumirlo como spec de entrada
  (Spec-Driven Development).

## OpenClaw / agent runtimes
- Hoy: adapters generic/openclaw (+ claude_code/codex registrados pero sin adapter).
- Oportunidad: adapters reales para Claude Code / Codex / OpenCode (el contrato ya
  existe); sesiones por agente; project isolation por misión.

## Compatibilidad con el control plane
- Conciencia sigue siendo un control plane: cualquier runtime externo (Codex, Claude
  Code, OpenClaw, WebMCP apps) entra como TOOL/ADAPTER gobernado, no como subsistema
  paralelo.

---
Fecha: 2026-09-01 · audit final (master-prompt-final1.md §21)
