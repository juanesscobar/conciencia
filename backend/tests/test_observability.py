"""Tests Fase H — Observability: timeline estructurado, costos, tokens, runtime,
acciones, tool calls y failure state.

DoD Phase H: "An operator can understand exactly what a Mission is doing."
"""

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
        model="deepseek-chat",
        status="idle",
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@pytest.fixture
def fake_dispatch(monkeypatch):
    """Dispatch con usage/tokens/meta completos (como un adapter real)."""
    calls = []

    def dispatch(self, identity, task, context=None):
        calls.append({"agent_id": identity.agent_id, "task": task})
        if task and "FAIL" in task:
            return DispatchResult(ok=False, status="failed", error="boom", runtime="generic",
                                  provider="deepseek", model="deepseek-chat", duration_ms=3)
        return DispatchResult(
            ok=True, status="completed", output="resultado",
            runtime="generic", provider="deepseek", model="deepseek-chat",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150,
                   "cost_estimate_usd": 0.002},
            duration_ms=7,
            meta={"actions": ["search", "read"], "tool_calls": ["web_search:1", "read:2"]},
        )

    monkeypatch.setattr(GenericAgentAdapter, "dispatch_task", dispatch)
    return calls


def _create_wf(client, auth_headers, steps, name="wf-obs"):
    res = client.post("/api/v1/workflows/", headers=auth_headers, json={"name": name, "steps": steps})
    assert res.status_code == 201, res.text
    return res.json()


def test_step_results_enriquecidos(client, auth_headers, dev_agent, fake_dispatch):
    """Cada step registra tokens, runtime, provider, model, duración, acciones y tool calls."""
    wf = _create_wf(client, auth_headers, [
        {"name": "research", "task": "investigar", "agent_id": str(dev_agent.id)},
    ])
    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    assert run["status"] == "completed"

    step = run["step_results"][0]
    assert step["status"] == "completed"
    assert step["tokens"] == {"prompt": 100, "completion": 50, "total": 150}
    assert step["cost"] == 0.002
    assert step["runtime"] == "generic"
    assert step["provider"] == "deepseek"
    assert step["model"] == "deepseek-chat"
    assert step["duration_ms"] == 7
    assert step["agent_name"] == "DEV Agent"
    assert step["actions"] == ["search", "read"]
    assert step["tool_calls"] == ["web_search:1", "read:2"]


def test_timeline_eventos_estructurados(client, auth_headers, dev_agent, fake_dispatch):
    wf = _create_wf(client, auth_headers, [
        {"name": "research", "task": "investigar", "agent_id": str(dev_agent.id)},
    ])
    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()

    types = [e["type"] for e in run["events"]]
    assert types == ["workflow_started", "step_started", "step_completed", "workflow_completed"]

    done = run["events"][2]
    assert done["step"] == "research"
    assert done["agent_name"] == "DEV Agent"
    assert done["runtime"] == "generic"
    assert done["tokens"]["total"] == 150
    assert done["cost"] == 0.002
    assert done["tool_calls"] == ["web_search:1", "read:2"]


def test_failure_state_con_eventos(client, auth_headers, dev_agent, fake_dispatch):
    wf = _create_wf(client, auth_headers, [
        {"name": "research", "task": "tarea FAIL", "agent_id": str(dev_agent.id)},
    ])
    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    assert run["status"] == "failed"
    assert run["error"] == "research: boom"

    types = [e["type"] for e in run["events"]]
    assert "step_failed" in types and "workflow_failed" in types
    failed = next(e for e in run["events"] if e["type"] == "step_failed")
    assert "boom" in failed["error"]
    # el step fallido conserva metadata de runtime
    step = run["step_results"][0]
    assert step["status"] == "failed"
    assert step["runtime"] == "generic"
    assert step["error"] == "boom"


def test_approval_gate_registra_eventos(client, auth_headers, dev_agent, fake_dispatch):
    wf = _create_wf(client, auth_headers, [
        {"name": "research", "task": "investigar", "agent_id": str(dev_agent.id)},
        {"name": "gate", "approval": True},
    ])
    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    assert run["status"] == "paused"
    assert [e["type"] for e in run["events"]][-1] == "approval_required"

    run = client.post(f"/api/v1/workflows/runs/{run['id']}/approve", headers=auth_headers,
                      json={"approved": True}).json()
    assert run["status"] == "completed"
    types = [e["type"] for e in run["events"]]
    assert "approval_approved" in types
    assert types[-1] == "workflow_completed"


def test_parallel_children_con_tokens(client, auth_headers, dev_agent, fake_dispatch):
    wf = _create_wf(client, auth_headers, [
        {
            "name": "fanout",
            "parallel": True,
            "steps": [
                {"name": "a", "task": "A", "agent_id": str(dev_agent.id)},
                {"name": "b", "task": "B", "agent_id": str(dev_agent.id)},
            ],
        },
    ])
    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    assert run["status"] == "completed"
    step = run["step_results"][0]
    assert step["parallel"] is True
    assert step["cost"] == 0.004  # 2 × 0.002
    assert step["children"][0]["tokens"]["total"] == 150
    assert step["children"][0]["agent_name"] == "DEV Agent"
    assert [e["type"] for e in run["events"]].count("step_started") == 1
    assert any(e["type"] == "parallel_completed" for e in run["events"])


def test_mission_run_refleja_logs_tokens_y_costo(client, auth_headers, db, fake_dispatch):
    """El MissionRun expone el timeline (logs), tokens agregados y costo (Fase H)."""
    a = Agent(name="ResearchBot", role=AgentRole.RD, capabilities=["research"],
              runtime=AgentRuntime.GENERIC, provider=AgentProvider.DEEPSEEK, status="idle")
    db.add(a)
    db.commit()
    db.refresh(a)

    res = client.post("/api/v1/missions/", headers=auth_headers, json={
        "name": "Misión observable", "objective": "investigar X", "type": "research",
        "agent_ids": [str(a.id)],
    })
    m = res.json()
    client.post(f"/api/v1/missions/{m['id']}/plan", headers=auth_headers)
    run = client.post(f"/api/v1/missions/{m['id']}/run", headers=auth_headers).json()

    assert run["status"] == "waiting_approval"
    # logs = timeline espejado del workflow
    assert run["logs"], "el run debe exponer el timeline estructurado"
    messages = " ".join(lg["message"] for lg in run["logs"])
    assert "step_completed" in messages
    assert "research" in messages
    # tokens agregados (2 steps × 150)
    assert run["tokens"] == {"prompt": 200, "completion": 100, "total": 300}
    # costo agregado
    assert run["cost_usd"]["total"] == 0.004

    # API con detalle: step_results en el workflow run
    res = client.get(f"/api/v1/missions/{m['id']}/runs", headers=auth_headers)
    assert res.status_code == 200
