# RUNTIME_ECOSYSTEM — matriz de capacidades (master-prompt-cli §34)

> Nota de arquitectura: qué sistemas externos se pueden orquestar y CÓMO.
> Clasificación verificada contra el código actual (2026-09-03) — no inventar soporte.
> Política: integrar por **interfaces/capabilities**, nunca `if runtime == "codex"` suelto.

## Matriz

| Sistema | Tipo | Estado en Conciencia | Ruta de integración |
|---|---|---|---|
| Conciencia generic (LLM Harness) | runtime interno | ✅ adapter `GenericAgentAdapter` | motor embebido multi-proveedor |
| OpenClaw | runtime | ✅ adapter `OpenClawAdapter` | CLI/gateway (`openclaw run`) — subprocess con allowlist |
| Claude Code | runtime | 🟡 config listo, SIN adapter | CLI (`claude -p`) — falta `ClaudeCodeAdapter` |
| OpenAI Codex | runtime | 🟡 config listo, SIN adapter | CLI (`codex exec`) — falta `CodexAdapter` |
| OpenCode | runtime | 🟡 config listo, SIN adapter | CLI (`opencode run`) — falta adapter |
| MCP | tool/protocol | ✅ `routers/mcp.py` + client stdio | Tool Registry (`/api/v1/mcp`) |
| WebMCP | tool/protocol | ✅ Fase K: step `webmcp` + demo agent-native | bridge HTTP `/api/webmcp/*` + tools estándar `document.modelContext.registerTool` |
| Git / filesystem / browser / HTTP / search | tool/protocol | parcial (integraciones por servicio) | adapters de tool dedicados (futuro) |
| Hermes / Orca / Utopia | (no verificados) | ❌ no soportados | solo cuando expongan CLI/API/protocolo estable |

## Arquitectura objetivo (concepto)

```
Mission Core (interfaces/capabilities)
   ├── RuntimeRegistry → RuntimeAdapter (id, capabilities, availability, execute, cancel, health)
   ├── Tool Registry   → MCP servers / WebMCP apps
   └── Capability Readiness (execution_overview)
```

Reglas:
- Un runtime externo SOLO ejecuta si: `enabled=true` (Settings), comando allowlist, cwd válido, timeout.
- Si un runtime no tiene adapter → error claro "runtime X sin adapter" (nunca falla silencioso).
- Los nombres de producto NO se hardcodean en la lógica de Mission: van en el registro/config.

## Discovery (Windows + Git Bash + WSL first-class)
- `conciencia onboard` / `conciencia runtime-doctor`: detectan binarios en PATH (PowerShell,
  Git Bash, WSL) y reportan health sin habilitar nada por defecto.
- `conciencia runtime list` / `runtime inspect NAME` para visibilidad.

---
Generado: 2026-09-03 · verificado contra `app/adapters/registry.py`, `app/core/agent_runtime.py`,
`app/services/capability_readiness.py`, Fase K (webmcp).
