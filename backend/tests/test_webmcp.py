"""Tests Fase K — WebMCP: misión interactúa con una app web WebMCP-enabled
y preserva evidencia.

DoD Phase K: "A Mission can interact with a WebMCP-enabled web application
and preserve evidence."
"""

import threading
import time
import uuid

import pytest
import uvicorn

from app.adapters.base import DispatchResult
from app.adapters.generic import GenericAgentAdapter
from app.models.agent import Agent, AgentProvider, AgentRole, AgentRuntime
from app.models.mission import Mission
from app.models.signal import Signal
from app.services.webmcp import client as wm
from app.services.webmcp.demo_app import create_demo_app


def test_demo_app_registra_tools_webmcp_estandar():
    """La demo app registra tools con la API WebMCP estándar (agent-native),
    con fallback al bridge de Conciencia (window.webmcp)."""
    from app.services.webmcp.demo_app import create_demo_app
    from fastapi.testclient import TestClient

    html = TestClient(create_demo_app()).get("/").text
    assert "modelContext?.registerTool" in html
    assert "get_status" in html
    assert "submit_contact" in html
    assert "increment_counter" in html
    assert "inputSchema" in html
    assert "window.webmcp" in html  # fallback bridge para el control plane


# ---------------------------------------------------------------------------
# Demo app WebMCP-enabled en vivo (uvicorn en thread)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def demo_url():
    app = create_demo_app()
    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    port = next(sock.getsockname()[1] for sock in server.servers[0].sockets)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


# ---------------------------------------------------------------------------
# Cliente WebMCP
# ---------------------------------------------------------------------------

def test_cliente_context_act_snapshot(demo_url):
    ctx = wm.get_context(demo_url)
    assert ctx["app"] == "WebMCP Demo App"
    assert ctx["state"]["counter"] == 0

    r = wm.act(demo_url, {"type": "input", "selector": "#name", "value": "Juan"})
    assert r["ok"] is True
    r = wm.act(demo_url, {"type": "click", "selector": "#increment"})
    assert r["result"] == "counter → 1"

    snap = wm.snapshot(demo_url)
    assert snap["state"]["counter"] == 1
    assert snap["state"]["form"]["name"] == "Juan"


def test_cliente_run_script_preserva_evidencia(demo_url):
    result = wm.run_script(demo_url, [
        {"type": "input", "selector": "#name", "value": "Juan"},
        {"type": "input", "selector": "#email", "value": "juan@correo.com"},
        {"type": "submit", "selector": "form"},
    ])
    assert result["actions_count"] == 3
    assert all(a["ok"] for a in result["action_log"])
    assert result["action_log"][2]["result"] == "formulario enviado por Juan"
    assert result["snapshot"]["state"]["submitted"] is True
    assert len(result["snapshot"]["state"]["visits"]) == 1
    # evidencia: contexto inicial + action log + snapshot final
    assert "initial_context" in result and "action_log" in result and "snapshot" in result


def test_cliente_accion_fallida_reporta_error(demo_url):
    result = wm.run_script(demo_url, [{"type": "click", "selector": "#no-existe"}])
    assert result["action_log"][0]["ok"] is False
    assert "selector no clicable" in result["action_log"][0]["error"]


def test_cliente_rechaza_url_y_accion_malformadas():
    with pytest.raises(wm.WebMCPError, match="http/https"):
        wm.run_script("file:///etc/passwd", [{"type": "click"}])
    with pytest.raises(wm.WebMCPError, match="type requerido"):
        wm.run_script("http://127.0.0.1:8765", [{"selector": "#x"}])


def test_cliente_produccion_exige_host_allowlist(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("WEBMCP_ALLOWED_HOSTS", raising=False)

    with pytest.raises(wm.WebMCPError, match="no permitido en producción"):
        wm.run_script("https://example.com", [{"type": "click", "selector": "#x"}])


# ---------------------------------------------------------------------------
# Workflow con step webmcp
# ---------------------------------------------------------------------------

def _create_wf(client, auth_headers, steps, name="wf-webmcp"):
    res = client.post("/api/v1/workflows/", headers=auth_headers, json={"name": name, "steps": steps})
    assert res.status_code == 201, res.text
    return res.json()


def test_workflow_step_webmcp_interactua_y_evidencia(client, auth_headers, demo_url):
    wf = _create_wf(client, auth_headers, [
        {
            "name": "llenar-form",
            "webmcp": {
                "url": demo_url,
                "actions": [
                    {"type": "input", "selector": "#name", "value": "Iron Toto"},
                    {"type": "input", "selector": "#email", "value": "toto@correo.com"},
                    {"type": "submit", "selector": "form"},
                    {"type": "click", "selector": "#increment"},
                ],
            },
        },
    ])
    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    assert run["status"] == "completed"

    step = run["step_results"][0]
    assert step["status"] == "completed"
    assert "submitted: True" in (step["output"] or "")
    assert "Iron Toto" in (step["output"] or "")
    assert step["runtime"] == "webmcp"
    # observabilidad: actions + tool_calls
    assert "input" in step["tool_calls"][0]
    # evidencia preservada en el step result
    ev = step["webmcp_evidence"]
    assert ev["actions_count"] == 4
    assert all(a["ok"] for a in ev["action_log"])
    assert ev["snapshot"]["state"]["submitted"] is True
    assert ev["snapshot"]["state"]["counter"] >= 1  # contador compartido entre tests


def test_workflow_step_webmcp_falla_sin_url(client, auth_headers):
    wf = _create_wf(client, auth_headers, [
        {"name": "mal", "webmcp": {"actions": [{"type": "click", "selector": "#x"}]}},
    ])
    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    assert run["status"] == "failed"
    assert "sin 'url'" in run["error"]


def test_workflow_step_webmcp_accion_fallida_falla_el_step(client, auth_headers, demo_url):
    wf = _create_wf(client, auth_headers, [
        {"name": "intento", "webmcp": {"url": demo_url, "actions": [
            {"type": "click", "selector": "#no-existe"},
        ]}},
    ])
    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    assert run["status"] == "failed"
    assert "webmcp" in run["error"]
    # la evidencia parcial se conserva
    assert run["step_results"][0]["webmcp_evidence"]["actions_count"] == 1


def test_workflow_webmcp_respeta_tools_del_harness(client, auth_headers, db, demo_url):
    from app.services import harness_service

    harness = harness_service.create_harness(
        db, name="Sin WebMCP", spec={"tools": {"allow": ["email"], "deny": ["webmcp"]}}
    )
    harness_service.set_status(db, harness, "active")
    wf = _create_wf(client, auth_headers, [{
        "name": "bloqueado",
        "harness_id": str(harness.id),
        "webmcp": {"url": demo_url, "actions": [{"type": "click", "selector": "#increment"}]},
    }])

    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    assert run["status"] == "failed"
    assert "denegado por harness" in run["error"]


# ---------------------------------------------------------------------------
# Misión: interactúa y preserva evidencia (DoD)
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_dispatch(monkeypatch):
    def dispatch(self, identity, task, context=None):
        return DispatchResult(ok=True, status="completed", output="sin señales",
                              runtime="generic", provider="deepseek", model="deepseek-chat",
                              usage={"prompt_tokens": 1, "completion_tokens": 1,
                                     "total_tokens": 2, "cost_estimate_usd": 0.0},
                              duration_ms=1)

    monkeypatch.setattr(GenericAgentAdapter, "dispatch_task", dispatch)


def test_mision_webmcp_preserva_evidencia_en_signals(client, auth_headers, db, demo_url, fake_dispatch):
    """Una misión con workflow webmcp interactúa con la app y la evidencia
    se promueve a Signal + Evidence (Fase I) vinculada a la misión."""
    a = Agent(name="ResearchBot", role=AgentRole.RD, capabilities=["research"],
              runtime=AgentRuntime.GENERIC, provider=AgentProvider.DEEPSEEK, status="idle")
    db.add(a)
    db.commit()
    db.refresh(a)

    # workflow custom: paso webmcp + paso research + approval
    wf = _create_wf(client, auth_headers, [
        {
            "name": "llenar-form",
            "webmcp": {"url": demo_url, "actions": [
                {"type": "input", "selector": "#name", "value": "Iron Toto"},
                {"type": "input", "selector": "#email", "value": "toto@correo.com"},
                {"type": "submit", "selector": "form"},
            ]},
        },
        {"name": "gate", "approval": True},
    ], name="wf-mision-webmcp")

    res = client.post("/api/v1/missions/", headers=auth_headers, json={
        "name": "Misión WebMCP",
        "objective": "llenar el formulario de la app demo",
        "type": "research",
        "workflow_id": wf["id"],
        "agent_ids": [str(a.id)],
    })
    m = res.json()
    client.post(f"/api/v1/missions/{m['id']}/run", headers=auth_headers)
    run = client.get(f"/api/v1/missions/{m['id']}/runs", headers=auth_headers).json()
    assert run[-1]["status"] == "waiting_approval"

    # DoD: la evidencia se preserva como Signal con Evidence
    res = client.get(f"/api/v1/signals/?mission_id={m['id']}", headers=auth_headers)
    signals = res.json()
    webmcp_signals = [s for s in signals if s["title"].startswith("WebMCP:")]
    assert webmcp_signals, "debe existir una signal WebMCP con la evidencia"
    sig = webmcp_signals[0]
    assert len(sig["evidence"]) >= 4  # 3 acciones + snapshot
    assert any("formulario enviado" in e["content"] for e in sig["evidence"])

    # la misión vincula las evidencias
    res = client.get(f"/api/v1/missions/{m['id']}", headers=auth_headers)
    assert len(res.json()["evidence_ids"]) >= 4


def test_webmcp_api_run(client, auth_headers, demo_url):
    res = client.post("/api/v1/webmcp/run", headers=auth_headers, json={
        "url": demo_url,
        "actions": [{"type": "click", "selector": "#increment"}],
    })
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["actions_count"] == 1
    assert body["action_log"][0]["ok"] is True

    res = client.get("/api/v1/webmcp/demo", headers=auth_headers)
    assert res.status_code == 200
    assert "WebMCP Demo App" in res.json()["description"]
