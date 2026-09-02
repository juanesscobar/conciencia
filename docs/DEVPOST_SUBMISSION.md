# 🏆 DEVPOST — WebMCP Challenge · Submission Kit (Conciencia)

> Hackathon: [webmcp.devpost.com](https://webmcp.devpost.com/) · Premio: top 10 → $3,000 + premios.
> Jurado: WebMCP Leverage · Execution · Potential Impact · Creativity & Ambition.
> Fecha del kit: 2026-09-02.

---

## 1. CHECKLIST DE SUBMISIÓN (estado real)

### ✅ Listo
| Requisito Devpost | Estado | Dónde |
|---|---|---|
| Repo público en GitHub | ✅ | github.com/juanesscobar/mission-control |
| Licencia open source detectable | ✅ MIT | LICENSE (badge en README + About del repo) |
| Código fuente + assets + instrucciones | ✅ | README.md + docs/USAGE.md + docker-compose |
| Implementación WebMCP no-trivial | ✅ | Fase K: step `webmcp` en workflows + adapter bridge + app demo con tools estándar |
| App demo agent-native (tools estándar `document.modelContext.registerTool`) | ✅ | `backend/app/services/webmcp/demo_app.py` |
| Evidencia preservada por interacción | ✅ | action log + snapshot → Signal/Evidence (Fase I) |
| Observabilidad / economics | ✅ | `workflow_runs.events`, `run inspect --steps`, `economics` |
| Tests | ✅ | 309 passed / 8 deselected (LLM providers) |

### ⏳ Pendiente (acción tuya)
| Requisito Devpost | Qué falta | Cómo |
|---|---|---|
| **Live URL** accesible por jueces | Deployar la demo app WebMCP en un host público | Render / Vercel / Railway / Fly / Hetzner. App = FastAPI (`demo_app.py`). Ver §4 |
| **Video demo < 3 min** en YouTube público | Grabar | Guión en §5 |
| Descripción en el formulario | Redactar/pegar | Borradores en §2 |
| Credenciales (opcional) | Solo si la app pide login | — (no hace falta: demo app sin auth) |
| URL del repo en el formulario | — | https://github.com/juanesscobar/mission-control |

### 🛡️ Checklist de seguridad antes de publicar (repo ya público, verificado)
- [x] Sin API keys / tokens en el repo (settings viven en DB local ignorada; `.env.example` sin valores)
- [x] `missioncontrol.db` NO trackeado (gitignored) — borrado localmente
- [x] Sin secrets en logs/events (audit §20/§11)
- [ ] Rotar claves SI alguna vez se expuso (GCM, ver TOOLS.md)
- [x] Routers sensibles con auth JWT (audit final)
- [ ] Confirmar que el badge "tests 140 green" del README se actualizó a 309

---

## 2. DESCRIPCIÓN — borradores para el formulario

### 2.1 Why your use case is a strong fit for WebMCP
> Conciencia is an **open control plane for agent work** (missions → workflows → agents →
> evidence). WebMCP is what makes a web app *usable by agents* instead of scrapable.
> We use WebMCP twice: (1) an agent-native demo app exposes structured tools
> (`submit_contact`, `get_status`, `increment_counter`) via the standard
> `document.modelContext.registerTool`; (2) a **mission** in Conciencia drives that same
> app through a WebMCP adapter with a full governance loop — capability discovery, action
> log, snapshot evidence, human approval gates and cost tracking. WebMCP is the bridge
> that lets the control plane treat any website as a governed tool.

### 2.2 How it creates a better user experience
> Humans and agents operate the **same** app with the same structured tools — no brittle
> UI scraping, no fake "automation" that breaks when markup changes. A person fills the
> form by hand; an agent fills it through `submit_contact` with typed inputs and gets
> typed results. Everything an agent does is recorded as evidence (action log +
> snapshot), so the human can audit *exactly what happened* before approving the outcome.

### 2.3 What people and agents can do together that was difficult/impossible before
> **Governed delegation to the open web.** Before: an autonomous mission either lived
> inside a walled runtime or "clicked around" a website blindly. With WebMCP, a mission
> can delegate to a website's *declared* capabilities, capture traceable evidence of each
> action, pause for human approval before write side-effects, and account for cost —
> then emit a Signal with Evidence linking run → step → tool call → snapshot. Human
> oversight plus agent execution on the agent-native web.

### 2.4 Briefly explain how you implemented WebMCP
> Conciencia (FastAPI + React, MIT) implements a **WebMCP adapter**: mission workflows can
> include a `webmcp` step `{url, actions[]}`; the adapter speaks the app's WebMCP bridge
> (`/api/webmcp/context|act|snapshot`), executes typed actions (input/click/submit/
> navigate), and preserves an action log + state snapshot as Evidence. The companion demo
> app is agent-native: it registers tools through the standard
> `document.modelContext.registerTool` API (feature-detected) with JSON input schemas,
> and keeps a `window.webmcp` bridge so the Conciencia control plane can drive it
> server-side. Evidence is promoted to Signal/Evidence rows tied to the mission; a 3-min
> CLI/API demo shows the loop: mission → tool call → evidence → approval → economics.

---

## 3. EL "PITCH" (1 línea / elevator)
> **Conciencia: el control plane open source que convierte apps web WebMCP-enabled en
> herramientas gobernadas — misiones que actúan, dejan evidencia y piden aprobación
> humana, sobre el web agent-native.**

---

## 4. LIVE URL — plan de deploy de la demo app

La app a deployar es la **demo WebMCP app** (NO el control plane completo): una sola
página + bridge, sin auth, perfecta para que los jueces la abran en el browser de ChatGPT
(WebMCP out-of-the-box) o Chrome con `chrome://flags/#enable-webmcp-testing`.

```bash
cd backend
pip install -r requirements.txt   # o usar el Dockerfile del repo
python -m app.services.webmcp.demo_runner --port 8765   # sirve http://localhost:8765
```

Opciones de hosting (elige una):
- **Render** (más fácil para FastAPI): nuevo Web Service → repo `mission-control` →
  root dir `backend` → start command `python -m app.services.webmcp.demo_runner
  --port $PORT` (Render inyecta PORT; ajustar el runner para leerlo).
- **Vercel**: `vercel.json` con handler ASGI (FastAPI) para `demo_app.py`.
- **Railway/Fly.io**: mismo comando uvicorn.
- **Hetzner** (ya tenés server + sslip.io): servir `demo_app.py` en un puerto + reverse
  proxy nginx (patrón ya usado con `mc.46.62.196.151.sslip.io`).

⚠️ La demo usa estado EN MEMORIA por proceso — suficiente para el demo; si se deploya con
>1 réplica, cada una tiene su estado. Para el video y los jueces está bien.

---

## 5. VIDEO DEMO — guión (< 3 min, con audio, YouTube público)

**Escena 1 — El problema (0:00–0:30)**
Mostrar (captura de la app demo en el browser de ChatGPT): un agente de ChatGPT abre la
app y usa las tools WebMCP (`submit_contact`) — typed, sin adivinar el UI.

**Escena 2 — El control plane (0:30–1:30)**
Terminal: `conciencia ask "contactar al lead de la demo"` → propuesta → misión con step
`webmcp` contra la app → `conciencia run inspect <id> --steps`: tabla con la acción
ejecutada, tool_call, snapshot, costo.

**Escena 3 — Evidencia + aprobación (1:30–2:30)**
`conciencia signal list --mission <id>` → Signal "WebMCP: llenar-form" con Evidence por
acción; mostrar el approval gate (la misión espera decisión humana antes de un WRITE) y
aprobar.

**Escena 4 — Cierre (2:30–3:00)**
`conciencia economics summary --mission <id>` (costo total) + 1 frase: "el web
agent-native necesita un control plane que gobierne, evidencie y rinda cuentas — eso es
Conciencia."

---

## 6. SUBIR A DEVPOST — paso a paso

1. Entrá a https://webmcp.devpost.com/ → **"Submit your project"** (requiere cuenta Devpost
   + confirmar elegibilidad en las reglas oficiales).
2. **Project title**: `Conciencia — Open Control Plane for the Agent-Native Web`
   (o similar; claro y descriptivo).
3. **Tagline / elevator pitch**: pegá el de §3.
4. **Description**: pegá §2.1–§2.4 (podés estructurarlo con headers/markdown).
5. **Build with**: listá las tecnologías — FastAPI, React, SQLAlchemy, Docker, Python,
   WebMCP.
6. **Live URL**: la URL deployada de §4.
7. **Demo video**: pegá el link de YouTube público (§5).
8. **Code repository**: https://github.com/juanesscobar/mission-control
9. **Credential / login (opcional)**: vacío (la demo no pide login).
10. Revisá el checklist de §1 y **Submit**.

---

## 7. MAPEO CON CRITERIOS DEL JURADO

| Criterio | Cómo lo cubre Conciencia |
|---|---|
| **WebMCP Leverage** | Tools estándar registradas con schema + un control plane completo CONSUMIENDO WebMCP como herramienta gobernada (no trivial: adapter, evidencia, approvals) |
| **Execution** | 309 tests verdes, E2E reales (misión que llenó el formulario de la app en vivo), CLI+API+UI, docker |
| **Potential Impact** | Problema real: agentes del web abierto sin gobernanza/evidencia — audiencia: equipos que operan agentes (hoy: control plane con missions/approvals/economics) |
| **Creativity & Ambition** | Poco común: no "otra app con tools" sino un control plane que orquesta apps WebMCP y preserva evidencia auditable — humano-en-el-loop |

---
Generado: 2026-09-02 · repo `mission-control` · rama `v2-refactor` · commit `e836b7d`
