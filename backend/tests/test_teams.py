"""Tests Fase F — Teams: CRUD, miembros, matching, misión con team, ask con team.

DoD Phase F: "A Mission can coordinate multiple specialized agents."
"""

import pytest

from app.models.agent import Agent, AgentProvider, AgentRole, AgentRuntime
from app.services import team_service


def _seed_agent(db, name="ResearchBot", role="rd", caps=None, model="deepseek-chat"):
    a = Agent(
        name=name,
        role=role,
        status="idle",
        runtime=AgentRuntime.GENERIC,
        provider=AgentProvider.DEEPSEEK,
        model=model,
        capabilities=caps or ["research"],
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

def test_create_team_valida_agentes(db):
    with pytest.raises(ValueError):
        team_service.create_team(db, name="Equipo fantasma", member_ids=["00000000-0000-0000-0000-000000000000"])
    assert team_service.list_teams(db) == []


def test_team_crud_y_miembros(db):
    a1 = _seed_agent(db, name="Dev A", role="dev", caps=["code", "testing"])
    a2 = _seed_agent(db, name="Dev B", role="dev", caps=["code_review"])

    t = team_service.create_team(db, name="Delivery Squad", purpose="Entregar features", member_ids=[str(a1.id)])
    assert t.member_ids == [str(a1.id)]
    assert t.status == "active"

    # add idempotente + remove
    team_service.add_member(db, t, str(a1.id))
    assert t.member_ids == [str(a1.id)]
    team_service.add_member(db, t, str(a2.id))
    assert len(t.member_ids) == 2

    # resolve preserva orden
    agents = team_service.resolve_team_agents(db, t)
    assert [a.name for a in agents] == ["Dev A", "Dev B"]

    caps = team_service.team_capabilities(db, t)
    assert "code" in caps["union"] and "code_review" in caps["union"]

    team_service.remove_member(db, t, str(a1.id))
    assert t.member_ids == [str(a2.id)]

    team_service.update_team(db, t, patch={"status": "paused", "name": "Delivery 2"})
    assert t.status == "paused" and t.name == "Delivery 2"

    team_service.delete_team(db, t)
    assert team_service.list_teams(db) == []


def test_match_teams_por_capabilities(db):
    a = _seed_agent(db, name="ResearchBot", caps=["research", "reporting"])
    _seed_agent(db, name="Otro", role="fin", caps=["budget"])
    t = team_service.create_team(db, name="Research Squad", member_ids=[str(a.id)])

    matches = team_service.match_teams(db, required_capabilities=["research"])
    assert len(matches) == 1
    assert matches[0]["team_id"] == str(t.id)
    assert matches[0]["coverage"] == 100
    assert matches[0]["members_count"] == 1

    # capabilities que el team no cubre → sin match
    assert team_service.match_teams(db, required_capabilities=["kubernetes"]) == []
    # team pausado no matchea
    team_service.update_team(db, t, patch={"status": "paused"})
    assert team_service.match_teams(db, required_capabilities=["research"]) == []


def test_best_agent_in_team(db):
    a1 = _seed_agent(db, name="Member", caps=["research"])
    a2 = _seed_agent(db, name="Global", caps=["research", "reporting"])
    t = team_service.create_team(db, name="Squad", member_ids=[str(a1.id)])

    best = team_service.best_agent_in_team(db, team_id=str(t.id), required_capabilities=["research"])
    assert best["agent_id"] == str(a1.id)  # solo miembros del team
    assert team_service.best_agent_in_team(db, team_id=str(t.id), required_capabilities=["kubernetes"]) is None

    # a2 global queda fuera aunque cubra más
    _ = a2
    best = team_service.best_agent_in_team(db, team_id=str(t.id), required_capabilities=["research"])
    assert best["agent_id"] == str(a1.id)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

def test_teams_api_crud(client, auth_headers, db):
    a = _seed_agent(db)
    res = client.post("/api/v1/teams/", headers=auth_headers, json={
        "name": "Research Squad",
        "purpose": "Investigación",
        "member_ids": [str(a.id)],
        "default_runtime": "generic",
    })
    assert res.status_code == 201, res.text
    t = res.json()
    assert t["member_ids"] == [str(a.id)]
    assert t["status"] == "active"

    # list
    res = client.get("/api/v1/teams/", headers=auth_headers)
    assert len(res.json()) == 1

    # get + members detail
    res = client.get(f"/api/v1/teams/{t['id']}", headers=auth_headers)
    assert res.json()["name"] == "Research Squad"
    res = client.get(f"/api/v1/teams/{t['id']}/members", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()[0]["name"] == "ResearchBot"

    # patch
    res = client.patch(f"/api/v1/teams/{t['id']}", headers=auth_headers, json={"status": "paused"})
    assert res.json()["status"] == "paused"

    # delete
    res = client.delete(f"/api/v1/teams/{t['id']}", headers=auth_headers)
    assert res.status_code == 204
    res = client.get(f"/api/v1/teams/{t['id']}", headers=auth_headers)
    assert res.status_code == 404


def test_teams_api_member_validation(client, auth_headers, db):
    a = _seed_agent(db)
    res = client.post("/api/v1/teams/", headers=auth_headers, json={"name": "S", "member_ids": ["no-existe"]})
    assert res.status_code == 400

    t = client.post("/api/v1/teams/", headers=auth_headers, json={"name": "S"}).json()
    res = client.post(f"/api/v1/teams/{t['id']}/members", headers=auth_headers, json={"agent_id": "no-existe"})
    assert res.status_code == 400

    res = client.post(f"/api/v1/teams/{t['id']}/members", headers=auth_headers, json={"agent_id": str(a.id)})
    assert res.status_code == 200
    res = client.delete(f"/api/v1/teams/{t['id']}/members/{a.id}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["member_ids"] == []


def test_teams_api_match(client, auth_headers, db):
    a = _seed_agent(db, caps=["research"])
    client.post("/api/v1/teams/", headers=auth_headers, json={"name": "Squad", "member_ids": [str(a.id)]})
    res = client.get("/api/v1/teams/match?capabilities=research", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["coverage"] == 100
    res = client.get("/api/v1/teams/match?capabilities=kubernetes", headers=auth_headers)
    assert res.json() == []


# ---------------------------------------------------------------------------
# Misión con team
# ---------------------------------------------------------------------------

def test_mission_con_team_toma_runtime_y_miembros(client, auth_headers, db):
    a = _seed_agent(db, caps=["research"])
    t = client.post("/api/v1/teams/", headers=auth_headers, json={
        "name": "Squad", "default_runtime": "openclaw", "member_ids": [str(a.id)],
    }).json()

    res = client.post("/api/v1/missions/", headers=auth_headers, json={
        "name": "Research con team",
        "objective": "Investigar X",
        "type": "research",
        "team_id": t["id"],
    })
    assert res.status_code == 201, res.text
    m = res.json()
    assert m["team_id"] == t["id"]
    assert m["runtime"] == "openclaw"          # runtime default del team
    assert m["agent_ids"] == [str(a.id)]        # miembros del team

    # team inexistente → 400
    res = client.post("/api/v1/missions/", headers=auth_headers, json={
        "name": "X", "objective": "Y", "team_id": "00000000-0000-0000-0000-000000000000",
    })
    assert res.status_code == 400


def test_ask_sugiere_team(client, auth_headers, db):
    from app.services import ask_service
    a = _seed_agent(db, caps=["research"])
    team_service.create_team(db, name="Research Squad", purpose="Investigación", member_ids=[str(a.id)])
    p = ask_service.build_proposal(db, "investigar el mercado de logística en Paraguay")
    assert p["team"] is not None
    assert p["team"]["name"] == "Research Squad"
    assert p["team"]["coverage"] == 100
    assert "team" in client.post("/api/v1/ask", headers=auth_headers,
                                 json={"text": "investigar X"}).json()
