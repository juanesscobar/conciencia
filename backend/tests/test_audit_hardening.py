"""Tests audit final — hardening: auth en routers, guard de aprobación,
harness inactivo bloqueado, cascade de signals, provenance de harness.

Baseline del audit: 291 passed / 8 deselected — estos tests no bajan el número.
"""

import pytest

from app.adapters.base import DispatchResult
from app.adapters.generic import GenericAgentAdapter
from app.models.agent import Agent, AgentProvider, AgentRole, AgentRuntime
from app.models.signal import Signal, Evidence
from app.services import harness_service, signal_service


@pytest.fixture
def dev_agent(db):
    agent = Agent(
        name="DEV Agent",
        role=AgentRole.DEV,
        capabilities=["python", "code_review"],
        runtime=AgentRuntime.GENERIC,
        provider=AgentProvider.DEEPSEEK,
        status="idle",
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def _seed_agent(db, name="ResearchBot", caps=None):
    a = Agent(name=name, role=AgentRole.RD, capabilities=caps or ["research"],
              runtime=AgentRuntime.GENERIC, provider=AgentProvider.DEEPSEEK, status="idle")
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _create_wf(client, auth_headers, steps, name="wf-audit"):
    res = client.post("/api/v1/workflows/", headers=auth_headers, json={"name": name, "steps": steps})
    assert res.status_code == 201, res.text
    return res.json()


@pytest.fixture
def fake_dispatch(monkeypatch):
    def dispatch(self, identity, task, context=None):
        return DispatchResult(ok=True, status="completed", output="ok",
                              runtime="generic", provider="deepseek", model="deepseek-chat",
                              usage={"prompt_tokens": 5, "completion_tokens": 3,
                                     "total_tokens": 8, "cost_estimate_usd": 0.001},
                              duration_ms=2)

    monkeypatch.setattr(GenericAgentAdapter, "dispatch_task", dispatch)


# ---------------------------------------------------------------------------
# §12 — Approval guard: no re-ejecución de runs ya terminados
# ---------------------------------------------------------------------------

def test_aprobar_run_completado_rechazado(client, auth_headers, dev_agent, fake_dispatch):
    wf = _create_wf(client, auth_headers, [
        {"name": "gate", "approval": True},
        {"name": "fin", "task": "final", "agent_id": str(dev_agent.id)},
    ])
    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    assert run["status"] == "paused"

    run = client.post(f"/api/v1/workflows/runs/{run['id']}/approve", headers=auth_headers,
                      json={"approved": True}).json()
    assert run["status"] == "completed"

    # aprobar de nuevo sobre un run COMPLETADO → error (no re-ejecuta)
    res = client.post(f"/api/v1/workflows/runs/{run['id']}/approve", headers=auth_headers,
                      json={"approved": True})
    assert res.status_code == 400
    assert "no está esperando aprobación" in res.json()["detail"]


def test_aprobar_step_inexistente_rechazado(client, auth_headers, db):
    """La API de misión acepta step_index: un índice que no espera aprobación → 400."""
    from app.models.agent import Agent
    a = Agent(name="Bot", role=AgentRole.RD, capabilities=["research"],
              runtime=AgentRuntime.GENERIC, provider=AgentProvider.DEEPSEEK, status="idle")
    db.add(a)
    db.commit()
    db.refresh(a)
    res = client.post("/api/v1/missions/", headers=auth_headers, json={
        "name": "M", "objective": "O", "type": "research", "agent_ids": [str(a.id)],
    })
    m = res.json()
    client.post(f"/api/v1/missions/{m['id']}/plan", headers=auth_headers)
    run = client.post(f"/api/v1/missions/{m['id']}/run", headers=auth_headers).json()
    assert run["status"] == "waiting_approval"

    res = client.post(f"/api/v1/missions/{m['id']}/approve", headers=auth_headers,
                      json={"step_index": 5, "approved": True})
    assert res.status_code == 400
    assert "no está esperando aprobación" in res.json()["detail"]


def test_aprobar_mission_completada_rechazado(client, auth_headers, db, fake_dispatch):
    """Re-aprobar una misión ya completada no debe re-ejecutar steps."""
    a = _seed_agent(db)
    res = client.post("/api/v1/missions/", headers=auth_headers, json={
        "name": "M", "objective": "O", "type": "research", "agent_ids": [str(a.id)],
    })
    m = res.json()
    client.post(f"/api/v1/missions/{m['id']}/plan", headers=auth_headers)
    run = client.post(f"/api/v1/missions/{m['id']}/run", headers=auth_headers).json()
    assert run["status"] == "waiting_approval"

    # aprobar el gate (step 2 en research) → completed
    res = client.post(f"/api/v1/missions/{m['id']}/approve", headers=auth_headers,
                      json={"step_index": 2, "approved": True})
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "completed"

    # re-aprobar → 400, sin re-ejecución
    res = client.post(f"/api/v1/missions/{m['id']}/approve", headers=auth_headers,
                      json={"step_index": 2, "approved": True})
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# §6 — Harness inactivo no puede ejecutar (ni por step override)
# ---------------------------------------------------------------------------

def test_harness_draft_en_step_bloqueado(client, auth_headers, db):
    from app.models.workflow import WorkflowRun
    h = harness_service.create_harness(db, name="Draft H", spec={"instructions": "x"})  # draft
    a = _seed_agent(db)

    wf = _create_wf(client, auth_headers, [
        {"name": "research", "task": "tarea", "agent_id": str(a.id), "harness_id": str(h.id)},
    ])
    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    assert run["status"] == "failed"
    assert "no está activo" in run["error"]


# ---------------------------------------------------------------------------
# §17 — Mission delete: cascade de signals + evidence (sin huérfanos)
# ---------------------------------------------------------------------------

def test_delete_mission_cascades_signals_y_evidence(client, auth_headers, db):
    from app.models.mission import Mission
    res = client.post("/api/v1/missions/", headers=auth_headers, json={
        "name": "M", "objective": "O",
    })
    m = res.json()
    sig = signal_service.create_signal(
        db, mission_id=m["id"], title="Hallazgo", evidences=[{"kind": "quote", "content": "ev"}],
    )
    assert db.query(Signal).count() == 1
    assert db.query(Evidence).count() == 1

    res = client.delete(f"/api/v1/missions/{m['id']}", headers=auth_headers)
    assert res.status_code == 204
    # cascade: no quedan signals ni evidence huérfanos
    assert db.query(Signal).count() == 0
    assert db.query(Evidence).count() == 0


# ---------------------------------------------------------------------------
# §22 — Provenance del harness en step_results (id + versión)
# ---------------------------------------------------------------------------

def test_step_results_incluyen_harness_provenance(client, auth_headers, db, fake_dispatch):
    h = harness_service.create_harness(db, name="H", spec={"instructions": "Eres X"})
    harness_service.set_status(db, h, "active")
    a = _seed_agent(db)

    wf = _create_wf(client, auth_headers, [
        {"name": "research", "task": "tarea", "agent_id": str(a.id), "harness_id": str(h.id)},
    ])
    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    step = run["step_results"][0]
    assert step["harness_id"] == str(h.id)
    assert step["harness_version"] == "1.0.0"


# ---------------------------------------------------------------------------
# §20 — Routers sensibles exigen auth
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", [
    "/api/v1/context-packs/",
    "/api/v1/traces/",
    "/api/v1/costs/summary",
    "/api/v1/metrics",
    "/api/v1/decisions/",
    "/api/v1/policies/",
    "/api/v1/sprints/",
    "/api/v1/mcp/servers",
    "/api/v1/deliverables",
    "/api/v1/integrations/github/repos",
    "/api/v1/assistant/ask",
])
def test_routers_sensibles_exigen_auth(client, path):
    """HTTPBearer sin header → 403 (FastAPI); sin auth nunca 200."""
    if path == "/api/v1/assistant/ask":
        res = client.post(path, json={})  # POST-only
    else:
        res = client.get(path)
    assert res.status_code in (401, 403), f"{path} debería exigir auth, dio {res.status_code}"


def test_routers_sensibles_ok_con_auth(client, auth_headers):
    res = client.get("/api/v1/context-packs/", headers=auth_headers)
    assert res.status_code == 200
    res = client.get("/api/v1/traces/", headers=auth_headers)
    assert res.status_code == 200
    res = client.get("/api/v1/costs/summary", headers=auth_headers)
    assert res.status_code == 200
