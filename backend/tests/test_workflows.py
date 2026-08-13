"""Tests PR-1.5 + PR-2.1 — Workflow engine declarativo, approval gates y
resolución de agentes por capabilities."""

import pytest

from app.adapters.base import DispatchResult
from app.adapters.generic import GenericAgentAdapter
from app.models.agent import Agent, AgentProvider, AgentRole, AgentRuntime


@pytest.fixture
def dev_agent(db):
    agent = Agent(
        name="DEV Agent",
        role=AgentRole.DEV,
        capabilities=["python", "code_review"],
        runtime=AgentRuntime.GENERIC,
        provider=AgentProvider.DEEPSEEK,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@pytest.fixture
def fake_dispatch(monkeypatch):
    """Evita depender del LLM: el adapter generic devuelve un resultado fijo."""
    calls = []

    def dispatch(self, identity, task, context=None):
        calls.append({"agent_id": identity.agent_id, "task": task})
        return DispatchResult(
            ok=True,
            status="completed",
            output=f"ok: {task}",
            runtime="generic",
            provider=identity.provider,
            usage={"cost_estimate_usd": 0.01},
            duration_ms=5,
        )

    monkeypatch.setattr(GenericAgentAdapter, "dispatch_task", dispatch)
    return calls


def _create_wf(client, auth_headers, steps, name="wf-test"):
    res = client.post(
        "/api/v1/workflows/",
        headers=auth_headers,
        json={"name": name, "steps": steps},
    )
    assert res.status_code == 201
    return res.json()


def test_workflow_declarativo_completa(client, auth_headers):
    wf = _create_wf(client, auth_headers, [{"name": "paso1"}])
    assert wf["status"] == "draft"

    res = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers)
    assert res.status_code == 200
    run = res.json()
    assert run["status"] == "completed"
    assert run["step_results"][0]["status"] == "completed"
    assert "declarativo" in run["step_results"][0]["output"]


def test_workflow_approval_gate_approve(client, auth_headers):
    wf = _create_wf(client, auth_headers, [
        {"name": "gate", "approval": True},
        {"name": "paso2"},
    ])

    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    assert run["status"] == "paused"
    assert run["step_results"][0]["status"] == "waiting_approval"

    res = client.post(
        f"/api/v1/workflows/runs/{run['id']}/approve",
        headers=auth_headers,
        json={"approved": True},
    )
    assert res.status_code == 200
    run = res.json()
    assert run["status"] == "completed"
    assert run["step_results"][0]["status"] == "approved"
    assert run["step_results"][1]["status"] == "completed"


def test_workflow_approval_gate_reject(client, auth_headers):
    wf = _create_wf(client, auth_headers, [
        {"name": "gate", "approval": True},
        {"name": "paso2"},
    ])

    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    run = client.post(
        f"/api/v1/workflows/runs/{run['id']}/approve",
        headers=auth_headers,
        json={"approved": False},
    ).json()
    assert run["status"] == "cancelled"
    assert run["step_results"][0]["status"] == "rejected"
    assert len([r for r in run["step_results"] if r["status"] == "completed"]) == 0


def test_workflow_step_sin_agente_disponible_falla(client, auth_headers):
    wf = _create_wf(client, auth_headers, [
        {"name": "imposible", "task": "hacer algo", "required_capabilities": ["kubernetes"]},
    ])

    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    assert run["status"] == "failed"
    assert ">=50%" in run["error"]


def test_workflow_step_resuelve_agente_por_capabilities(client, auth_headers, dev_agent, fake_dispatch):
    wf = _create_wf(client, auth_headers, [
        {"name": "review", "task": "revisar PR", "required_capabilities": ["code_review"]},
    ])

    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    assert run["status"] == "completed"
    assert run["step_results"][0]["status"] == "completed"
    assert run["step_results"][0]["output"] == "ok: revisar PR"
    assert run["step_results"][0]["cost"] == 0.01
    assert fake_dispatch[0]["agent_id"] == str(dev_agent.id)


def test_workflow_step_con_agent_id_explicito(client, auth_headers, dev_agent, fake_dispatch):
    wf = _create_wf(client, auth_headers, [
        {"name": "directo", "task": "tarea directa", "agent_id": str(dev_agent.id)},
    ])

    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    assert run["status"] == "completed"
    assert fake_dispatch[0]["agent_id"] == str(dev_agent.id)


def test_workflow_run_duplicado_devuelve_409(client, auth_headers):
    wf = _create_wf(client, auth_headers, [{"name": "gate", "approval": True}])
    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    assert run["status"] == "paused"

    res = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers)
    assert res.status_code == 409


def test_workflow_cancel(client, auth_headers):
    wf = _create_wf(client, auth_headers, [{"name": "gate", "approval": True}])
    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()

    res = client.post(f"/api/v1/workflows/runs/{run['id']}/cancel", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"


def test_workflow_no_encontrado(client, auth_headers):
    res = client.post("/api/v1/workflows/inexistente/run", headers=auth_headers)
    assert res.status_code == 404


def test_listar_runs_de_workflow(client, auth_headers):
    wf = _create_wf(client, auth_headers, [{"name": "paso1"}])
    client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers)

    res = client.get(f"/api/v1/workflows/{wf['id']}/runs", headers=auth_headers)
    assert res.status_code == 200
    runs = res.json()
    assert len(runs) == 1
    assert runs[0]["workflow_id"] == wf["id"]
    assert runs[0]["status"] == "completed"


def test_aprobaciones_pendientes(client, auth_headers):
    wf = _create_wf(client, auth_headers, [{"name": "gate", "approval": True}])
    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()

    res = client.get("/api/v1/workflows/runs/pending", headers=auth_headers)
    assert res.status_code == 200
    pending = res.json()
    assert len(pending) == 1
    assert pending[0]["id"] == run["id"]
    assert pending[0]["workflow_name"] == wf["name"]
    assert pending[0]["step_results"][0]["status"] == "waiting_approval"

    client.post(
        f"/api/v1/workflows/runs/{run['id']}/approve",
        headers=auth_headers,
        json={"approved": True},
    )
    pending = client.get("/api/v1/workflows/runs/pending", headers=auth_headers).json()
    assert pending == []
