# SECURITY — Conciencia Platform (audit final, 2026-09-01)

## Resumen
Revisión práctica por inspección de código + tests locales (sin testing destructivo
contra sistemas externos). Hallazgo principal corregido: routers sensibles sin auth.

## Autenticación / Autorización
- JWT Bearer (HTTPBearer) en los routers del control plane: missions, workflows, agents,
  teams, harnesses, signals, economics, webmcp, projects, tasks, audit, memories,
  settings, system + (fijado en audit) context-packs, traces, costs, metrics, decisions,
  policies, sprints, reports, activities, assistant, github, mcp.
- `/api/v1/auth/register|login` públicos por diseño; `/auth/me` protegido.
- LeadHunter: `/api/v1/leads` protegido; `intake_router` (ingesta externa) es el único
  endpoint público intencional (webhook de entrada) — validar payloads antes de aceptar.

## Secrets
- API keys de providers viven en Settings (DB) o env; NUNCA se loguean.
- Eventos de observabilidad (workflow_runs.events) NO incluyen keys/tokens de auth;
  solo provider/model/tokens/cost/duration/error de ejecución.
- Errores de adapters se truncan (300 chars) antes de persistir/loguear.
- `.env` gitignored; claves rotadas por GCM (ver TOOLS.md del workspace).

## Ejecución de código / comandos
- Runtimes CLI externos (agent_runtime.py): subprocess SIN shell=True, comando desde
  config allowlist, tarea como argumento único, timeout, cwd validado.
- Sin `eval`/`exec` de input de usuario; YAML no se carga con `yaml.load` inseguro
  (revisar si algún path usa `safe_load`).

## WebMCP
- El step `webmcp` ejecuta SOLO contra la URL declarada en el workflow (config del
  dueño). La app demo es local. No hay trust implícito de orígenes remotos: el cliente
  valida respuestas JSON y timeouts; errores estructurados.

## SSRF / URLs
- WebMCP client: URL provista por config del workflow (no input directo de usuario final
  sin revisión). Recomendado para prod: allowlist de hosts en Settings.
- Sin path traversal: el CLI y la API no abren archivos por rutas de usuario.

## Aprobaciones (governance)
- Los approval gates son control de ejecución: el engine se pausa y NO continúa sin
  decisión humana. Re-aprobar un run terminado está bloqueado (400) — no re-ejecuta.

## Riesgos residuales (aceptados / pendientes)
1. Single-tenant: el acceso a datos (context packs, traces) es por auth de usuario, no
   por aislamiento por tenant — revisar antes de multi-cliente.
2. Rate limiting global no implementado (fuera de alcance §29).
3. CORS: verificar `get_cors_origins` en prod (no `*` con credenciales).
4. Ingesta LeadHunter (intake_router): considerar token de webhook dedicado.
5. Logs de la app (uvicorn/estructurados) — verificar que el level de prod no loguee
   bodies de requests (pueden contener datos de leads).
