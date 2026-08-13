"""Tests PR-2.1 — Capability matching (requirements → candidates → best)."""

from app.models.agent import Agent, AgentProvider, AgentRole, AgentRuntime, AgentStatus
from app.services.capability_matching import best_agent, match_agents, normalize_cap


def _create_agent(db, name, role, caps, status=AgentStatus.IDLE, runtime=AgentRuntime.GENERIC):
    agent = Agent(
        name=name,
        role=role,
        capabilities=caps,
        status=status,
        runtime=runtime,
        provider=AgentProvider.DEEPSEEK,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def test_normalize_cap():
    assert normalize_cap("Code-Review") == "code_review"
    assert normalize_cap(" data analysis ") == "data_analysis"
    assert normalize_cap(None) == ""


def test_match_orders_by_coverage(db):
    _create_agent(db, "Dev Full", AgentRole.DEV, ["python", "code_review", "testing"])
    _create_agent(db, "Dev Partial", AgentRole.DEV, ["python"])
    _create_agent(db, "Ops", AgentRole.OPS, ["deploy"])

    results = match_agents(db, required_capabilities=["python", "code_review"])
    assert [r["name"] for r in results] == ["Dev Full", "Dev Partial"]
    assert results[0]["coverage"] == 100
    assert results[0]["matched_caps"] == ["python", "code_review"]
    assert results[0]["missing_caps"] == []
    assert results[1]["coverage"] == 50
    assert results[1]["missing_caps"] == ["code_review"]


def test_match_excludes_agents_in_error(db):
    _create_agent(db, "Roto", AgentRole.DEV, ["python"], status=AgentStatus.ERROR)

    results = match_agents(db, required_capabilities=["python"])
    assert results == []


def test_match_filters_by_role_and_runtime(db):
    _create_agent(db, "Dev", AgentRole.DEV, ["python"])
    _create_agent(db, "Ops", AgentRole.OPS, ["python"], runtime=AgentRuntime.OPENCLAW)

    results = match_agents(db, required_capabilities=["python"], role="ops")
    assert [r["name"] for r in results] == ["Ops"]

    results = match_agents(db, required_capabilities=["python"], runtime="openclaw")
    assert [r["name"] for r in results] == ["Ops"]


def test_match_normalizes_required_caps(db):
    _create_agent(db, "Dev", AgentRole.DEV, ["code_review"])

    results = match_agents(db, required_capabilities=["Code-Review"])
    assert results[0]["coverage"] == 100


def test_match_empty_requirements(db):
    _create_agent(db, "Dev", AgentRole.DEV, ["python"])
    assert match_agents(db, required_capabilities=[]) == []


def test_best_agent_requires_50_percent(db):
    _create_agent(db, "Dev", AgentRole.DEV, ["python"])

    assert best_agent(db, required_capabilities=["python"]) is not None
    assert best_agent(db, required_capabilities=["python", "testing", "deploy"]) is None


def test_match_endpoint(client, auth_headers, db):
    _create_agent(db, "Dev", AgentRole.DEV, ["python", "code_review"])

    res = client.post(
        "/api/v1/agents/match",
        headers=auth_headers,
        json={"required_capabilities": ["python"]},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["name"] == "Dev"
    assert data[0]["coverage"] == 100


def test_match_endpoint_requires_auth(client):
    res = client.post(
        "/api/v1/agents/match",
        json={"required_capabilities": ["python"]},
    )
    assert res.status_code in (401, 403)
