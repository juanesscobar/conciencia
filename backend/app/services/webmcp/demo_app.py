"""Demo WebMCP app — una aplicación web WebMCP-enabled de prueba (Fase K).

La app expone `window.webmcp` en su página (JS que habla con el bridge por
fetch) y un bridge HTTP `/api/webmcp/*` que un agente de Conciencia usa para
interactuar: consultar contexto, ejecutar acciones (input/click/submit/
navigate) y tomar snapshots (evidencia).

Estado en memoria: formulario de contacto + contador + registro de visitas.
"""

import uuid
from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Estado de la app (sesión única en memoria — demo)
# ---------------------------------------------------------------------------

STATE: Dict[str, Any] = {
    "app": "WebMCP Demo App",
    "version": "0.1.0",
    "form": {"name": "", "email": "", "message": ""},
    "submitted": False,
    "counter": 0,
    "visits": [],
}


def _reset_state() -> None:
    STATE["form"] = {"name": "", "email": "", "message": ""}
    STATE["submitted"] = False
    STATE["counter"] = 0
    STATE["visits"] = []


# ---------------------------------------------------------------------------
# Acciones soportadas (contrato WebMCP mínimo)
# ---------------------------------------------------------------------------

def apply_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """Aplica una acción al estado de la app. Devuelve {ok, result, state}."""
    atype = (action or {}).get("type", "")
    if atype == "input":
        selector = action.get("selector", "")
        value = action.get("value", "")
        fields = {"#name": "name", "#email": "email", "#message": "message"}
        if selector not in fields:
            return {"ok": False, "error": f"selector desconocido: {selector}"}
        STATE["form"][fields[selector]] = value
        STATE["submitted"] = False
        return {"ok": True, "result": f"input {selector} = {value!r}"}
    if atype == "click":
        selector = action.get("selector", "")
        if selector == "#increment":
            STATE["counter"] += 1
            return {"ok": True, "result": f"counter → {STATE['counter']}"}
        if selector == "#reset":
            _reset_state()
            return {"ok": True, "result": "estado reseteado"}
        return {"ok": False, "error": f"selector no clicable: {selector}"}
    if atype == "submit":
        form = STATE["form"]
        if not (form["name"] and form["email"]):
            return {"ok": False, "error": "formulario incompleto (name y email requeridos)"}
        STATE["submitted"] = True
        STATE["visits"].append({
            "ts": datetime.utcnow().isoformat(),
            "name": form["name"], "email": form["email"],
        })
        return {"ok": True, "result": f"formulario enviado por {form['name']}"}
    if atype == "navigate":
        # navegación simulada: registra la visita a otra ruta
        STATE["visits"].append({"ts": datetime.utcnow().isoformat(), "route": action.get("url", "/")})
        return {"ok": True, "result": f"navegó a {action.get('url', '/')}"}
    return {"ok": False, "error": f"acción no soportada: {atype}"}


def snapshot() -> Dict[str, Any]:
    """Snapshot del estado (evidencia): estado + resumen renderizado."""
    return {"state": STATE, "taken_at": datetime.utcnow().isoformat()}


def render_snapshot(snap: Dict[str, Any]) -> str:
    """Snapshot → texto plano legible (output del step)."""
    state = snap.get("state", {})
    form = state.get("form", {})
    lines = [
        f"# WebMCP snapshot — {state.get('app')} v{state.get('version')}",
        f"- form: name={form.get('name')!r} email={form.get('email')!r} message={form.get('message')!r}",
        f"- submitted: {state.get('submitted')}",
        f"- counter: {state.get('counter')}",
        f"- visits: {len(state.get('visits') or [])}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# FastAPI app (la aplicación web WebMCP-enabled)
# ---------------------------------------------------------------------------

class ActionRequest(BaseModel):
    action: Dict[str, Any]


def create_demo_app() -> FastAPI:
    app = FastAPI(title="WebMCP Demo App", docs_url=None, redoc_url=None)
    _reset_state()

    @app.get("/", response_class=HTMLResponse)
    def index():
        return """<!doctype html><html><body>
<h1>WebMCP Demo App</h1>
<form id="contact"><input id="name" placeholder="Nombre"/><input id="email" placeholder="Email"/>
<textarea id="message"></textarea><button id="submit">Enviar</button></form>
<button id="increment">+1</button><button id="reset">Reset</button>
<script>
// WebMCP-enabled: expone window.webmcp (puente con el bridge HTTP)
window.webmcp = {
  getContext: () => fetch('/api/webmcp/context').then(r => r.json()),
  act: (action) => fetch('/api/webmcp/act', {method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({action})}).then(r => r.json()),
  snapshot: () => fetch('/api/webmcp/snapshot').then(r => r.json())
};
</script></body></html>"""

    @app.get("/api/webmcp/context")
    def context():
        return {"app": STATE["app"], "version": STATE["version"], "state": STATE}

    @app.post("/api/webmcp/act")
    def act(req: ActionRequest):
        result = apply_action(req.action)
        if not result["ok"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result

    @app.get("/api/webmcp/snapshot")
    def snap():
        return snapshot()

    return app
