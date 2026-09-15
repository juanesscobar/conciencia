"""Tests Fase F — Ejecución paralela en el workflow engine (fan-out/fan-in)
y resolución de agentes dentro de un team.

DoD Phase F: "A Mission can coordinate multiple specialized agents."
"""

import pytest

from app.adapters.base import DispatchResult
from app.adapters.generic import GenericAgentAdapter
from app.models.agent import Agent, AgentProvider, AgentRole, AgentRuntime
from app.services import team_service


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


@pytest.fixture
def fake_dispatch(monkeypatch):
    """Evita depender del LLM: el adapter generic devuelve un resultado fijo."""
    calls = []

    def dispatch(self, identity, task, context=None):
        calls.append({"agent_id": identity.agent_id, "name": identity.name, "task": task})
        if task and "FAIL" in task:
            return DispatchResult(ok=False, status="failed", error="boom child", runtime="generic")
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


def _create_wf(client, auth_headers, steps, name="wf-parallel"):
    res = client.post(
        "/api/v1/workflows/",
        headers=auth_headers,
        json={"name": name, "steps": steps},
    )
    assert res.status_code == 201, res.text
    return res.json()


# ---------------------------------------------------------------------------
# Bloque paralelo
# ---------------------------------------------------------------------------

def test_bloque_paralelo_fanout_fanin(client, auth_headers, dev_agent, fake_dispatch):
    """Todos los children se ejecutan y el bloque agrega resultados."""
    wf = _create_wf(client, auth_headers, [
        {
            "name": "fanout",
            "parallel": True,
            "steps": [
                {"name": "research-a", "task": "tarea A", "agent_id": str(dev_agent.id)},
                {"name": "research-b", "task": "tarea B", "agent_id": str(dev_agent.id)},
                {"name": "research-c", "task": "tarea C", "agent_id": str(dev_agent.id)},
            ],
        },
    ])

    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    assert run["status"] == "completed"
    step = run["step_results"][0]
    assert step["status"] == "completed"
    assert step["parallel"] is True
    assert "3/3" in step["output"]
    assert len(step["children"]) == 3
    assert all(c["status"] == "completed" for c in step["children"])
    # fan-in: costo agregado (3 × 0.01)
    assert step["cost"] == pytest.approx(0.03)
    # los 3 dispatch se ejecutaron
    assert len(fake_dispatch) == 3
    assert {c["task"] for c in fake_dispatch} == {"tarea A", "tarea B", "tarea C"}


def test_bloque_paralelo_falla_con_outputs_parciales(client, auth_headers, dev_agent, fake_dispatch):
    wf = _create_wf(client, auth_headers, [
        {
            "name": "fanout",
            "parallel": True,
            "steps": [
                {"name": "ok-child", "task": "tarea ok", "agent_id": str(dev_agent.id)},
                {"name": "fail-child", "task": "tarea FAIL", "agent_id": str(dev_agent.id)},
            ],
        },
    ])

    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    assert run["status"] == "failed"
    step = run["step_results"][0]
    assert step["status"] == "failed"
    assert "1/2" in step["output"]           # el child ok se conserva
    assert "boom child" in step["error"]     # el error del child se reporta
    statuses = {c["name"]: c["status"] for c in step["children"]}
    assert statuses == {"ok-child": "completed", "fail-child": "failed"}
    # el child ok conserva su output
    ok_child = next(c for c in step["children"] if c["name"] == "ok-child")
    assert ok_child["output"] == "ok: tarea ok"


def test_bloque_paralelo_seguido_de_aprobacion(client, auth_headers, dev_agent, fake_dispatch):
    """Parallel + approval gate: fan-in antes del gate, luego aprobación humana."""
    wf = _create_wf(client, auth_headers, [
        {
            "name": "fanout",
            "parallel": True,
            "steps": [
                {"name": "a", "task": "A", "agent_id": str(dev_agent.id)},
                {"name": "b", "task": "B", "agent_id": str(dev_agent.id)},
            ],
        },
        {"name": "gate", "approval": True},
        {"name": "fin", "task": "final", "agent_id": str(dev_agent.id)},
    ])

    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    assert run["status"] == "paused"
    assert run["step_results"][0]["status"] == "completed"   # bloque paralelo listo
    assert run["step_results"][1]["status"] == "waiting_approval"

    run = client.post(
        f"/api/v1/workflows/runs/{run['id']}/approve",
        headers=auth_headers,
        json={"approved": True},
    ).json()
    assert run["status"] == "completed"
    assert run["step_results"][2]["status"] == "completed"   # sigue después del gate
    assert len(fake_dispatch) == 3


def test_bloque_paralelo_max_parallel(client, auth_headers, dev_agent, fake_dispatch):
    wf = _create_wf(client, auth_headers, [
        {
            "name": "fanout",
            "parallel": True,
            "max_parallel": 1,  # serializa los children a propósito
            "steps": [
                {"name": "a", "task": "A", "agent_id": str(dev_agent.id)},
                {"name": "b", "task": "B", "agent_id": str(dev_agent.id)},
            ],
        },
    ])
    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    assert run["status"] == "completed"
    assert "2/2" in run["step_results"][0]["output"]


# ---------------------------------------------------------------------------
# Resolución dentro del team
# ---------------------------------------------------------------------------

def test_step_resuelve_agente_dentro_del_team_primero(client, auth_headers, db, fake_dispatch):
    """Con team_id, el engine prefiere miembros del team aunque el registry
    global tenga un agente con más coverage."""
    team_member = Agent(
        name="TeamMember", role=AgentRole.RD, capabilities=["research"],
        runtime=AgentRuntime.GENERIC, provider=AgentProvider.DEEPSEEK, status="idle",
    )
    global_better = Agent(
        name="GlobalBetter", role=AgentRole.RD, capabilities=["research", "reporting", "documentation"],
        runtime=AgentRuntime.GENERIC, provider=AgentProvider.DEEPSEEK, status="idle",
    )
    db.add_all([team_member, global_better])
    db.commit()
    db.refresh(team_member)
    db.refresh(global_better)
    team = team_service.create_team(db, name="Squad", member_ids=[str(team_member.id)])

    # workflow directo con required_capabilities (sin agent_id):
    # "reporting" solo lo cubre GlobalBetter → gana el global
    wf = _create_wf(client, auth_headers, [
        {"name": "research", "task": "investigar", "required_capabilities": ["research", "reporting"]},
    ])

    # sin team → gana el global (más coverage)
    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    assert run["status"] == "completed"
    assert fake_dispatch[-1]["name"] == "GlobalBetter"

    # misión con team → gana el miembro del team
    res = client.post("/api/v1/missions/", headers=auth_headers, json={
        "name": "M", "objective": "investigar", "type": "research", "team_id": str(team.id),
    })
    m = res.json()
    client.post(f"/api/v1/missions/{m['id']}/plan", headers=auth_headers)
    run = client.post(f"/api/v1/missions/{m['id']}/run", headers=auth_headers).json()
    assert run["status"] == "waiting_approval"  # research termina en approval gate
    assert fake_dispatch[-1]["name"] == "TeamMember"
