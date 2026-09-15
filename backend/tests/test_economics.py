"""Tests Fase L — Economics: economía de misiones inspeccionable (sin billing).

DoD Phase L: "Mission economics can be inspected without implementing billing."
"""

import uuid

import pytest

from app.adapters.base import DispatchResult
from app.adapters.generic import GenericAgentAdapter
from app.models.agent import Agent, AgentProvider, AgentRole, AgentRuntime
from app.services import economics_service


def _seed_agent(db, name="ResearchBot"):
    a = Agent(name=name, role=AgentRole.RD, capabilities=["research"],
              runtime=AgentRuntime.GENERIC, provider=AgentProvider.DEEPSEEK, status="idle")
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


@pytest.fixture
def fake_dispatch(monkeypatch):
    """Dispatch con usage por step (provider/model/tokens/cost)."""
    calls = {"n": 0}

    def dispatch(self, identity, task, context=None):
        calls["n"] += 1
        if calls["n"] == 1:
            provider, model = "deepseek", "deepseek-chat"
        else:
            provider, model = "openai", "gpt-4o-mini"
        return DispatchResult(
            ok=True, status="completed", output="resultado",
            runtime="generic", provider=provider, model=model,
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150,
                   "cost_estimate_usd": 0.002},
            duration_ms=5,
            meta={"actions": ["search"], "tool_calls": ["web_search:1"]},
        )

    monkeypatch.setattr(GenericAgentAdapter, "dispatch_task", dispatch)


def _create_mission(client, auth_headers, agent_id, objective="investigar X"):
    res = client.post("/api/v1/missions/", headers=auth_headers, json={
        "name": "Misión econ", "objective": objective, "type": "research",
        "agent_ids": [agent_id],
    })
    return res.json()


# ---------------------------------------------------------------------------
# Costo externo
# ---------------------------------------------------------------------------

def test_record_external_cost(db):
    from app.services import mission_service

    a = _seed_agent(db)
    m = mission_service.create_mission(db, name="M", objective="O", agent_ids=[str(a.id)])
    run = mission_service.run_mission(db, m)

    entry = economics_service.record_external_cost(
        db, mission_run_id=str(run.id), tool="webmcp", cost_usd=0.01, detail="demo app"
    )
    assert entry["tool"] == "webmcp"
    assert entry["cost_usd"] == 0.01
    db.refresh(run)
    assert len(run.external_costs or []) == 1
    assert run.cost_usd["tools"] == 0.01
    assert run.cost_usd["total"] >= 0.01

    with pytest.raises(ValueError):
        economics_service.record_external_cost(
            db, mission_run_id="00000000-0000-0000-0000-000000000000", tool="x", cost_usd=1
        )


# ---------------------------------------------------------------------------
# Economía por misión
# ---------------------------------------------------------------------------

def test_mission_economics_agrega(client, auth_headers, db, fake_dispatch):
    a = _seed_agent(db)
    m = _create_mission(client, auth_headers, str(a.id))
    client.post(f"/api/v1/missions/{m['id']}/plan", headers=auth_headers)
    run = client.post(f"/api/v1/missions/{m['id']}/run", headers=auth_headers).json()
    assert run["status"] == "waiting_approval"

    data = economics_service.mission_economics(db, m["id"])
    assert data["mission_id"] == m["id"]
    assert data["runs_count"] == 1
    # 2 steps × 150 tokens = 300
    assert data["tokens"]["total"] == 300
    assert data["tokens"]["prompt"] == 200
    # 2 steps × 0.002
    assert data["cost_usd"]["total"] == pytest.approx(0.004, abs=1e-6)
    # 2 providers distintos (el step de aprobación aporta 'unknown' — sin dispatch)
    providers = {p["key"] for p in data["cost_by_provider"]}
    assert {"deepseek", "openai"} <= providers
    # actions + tool_calls (1 por step)
    assert data["actions_count"] == 2
    assert data["tool_calls_count"] == 2
    # outcomes
    assert data["outcomes"].get("waiting_approval") == 1
    # runtime usage
    assert data["runtime_usage"].get("generic") == 2

    # + costo externo → tools
    economics_service.record_external_cost(db, mission_run_id=run["id"], tool="webmcp", cost_usd=0.005)
    data = economics_service.mission_economics(db, m["id"])
    assert data["cost_usd"]["tools"] == pytest.approx(0.005, abs=1e-6)
    assert data["cost_usd"]["total"] == pytest.approx(0.009, abs=1e-6)


def test_mission_economics_no_encontrada(db):
    with pytest.raises(ValueError):
        economics_service.mission_economics(db, "00000000-0000-0000-0000-000000000000")


# ---------------------------------------------------------------------------
# Economía de plataforma
# ---------------------------------------------------------------------------

def test_platform_economics_agrega(client, auth_headers, db, fake_dispatch):
    a = _seed_agent(db)
    m1 = _create_mission(client, auth_headers, str(a.id), objective="investigar A")
    client.post(f"/api/v1/missions/{m1['id']}/plan", headers=auth_headers)
    client.post(f"/api/v1/missions/{m1['id']}/run", headers=auth_headers)

    # otra misión (mismo agente) para sumar runs
    m2 = _create_mission(client, auth_headers, str(a.id), objective="investigar B")
    client.post(f"/api/v1/missions/{m2['id']}/plan", headers=auth_headers)
    client.post(f"/api/v1/missions/{m2['id']}/run", headers=auth_headers)

    data = economics_service.platform_economics(db, days=30)
    assert data["runs_count"] == 2
    assert data["missions_count"] >= 2
    # 4 steps × 150 tokens
    assert data["tokens"]["total"] == 600
    # 4 steps × 0.002
    assert data["cost_usd"]["total"] == pytest.approx(0.008, abs=1e-6)
    assert data["outcomes"].get("waiting_approval") == 2
    assert data["actions_count"] == 4
    assert data["tool_calls_count"] == 4
    providers = {p["key"] for p in data["cost_by_provider"]}
    assert {"deepseek", "openai"} <= providers
    assert data["note"] == "sin billing — solo inspección"


def test_economics_api(client, auth_headers, db, fake_dispatch):
    a = _seed_agent(db)
    m = _create_mission(client, auth_headers, str(a.id))
    client.post(f"/api/v1/missions/{m['id']}/plan", headers=auth_headers)
    run = client.post(f"/api/v1/missions/{m['id']}/run", headers=auth_headers).json()

    res = client.get("/api/v1/economics/?days=30", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["runs_count"] >= 1

    res = client.get(f"/api/v1/economics/missions/{m['id']}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["tokens"]["total"] == 300

    res = client.post("/api/v1/economics/external-cost", headers=auth_headers, json={
        "mission_run_id": run["id"], "tool": "scraper", "cost_usd": 0.02,
    })
    assert res.status_code == 200, res.text
    assert res.json()["tool"] == "scraper"
