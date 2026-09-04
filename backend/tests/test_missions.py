"""Tests Fase B — Mission Orchestration (master prompt §32: test domain behavior)."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def _auth_headers(client):
    res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "test-pass"})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_mission_crud(client, auth_headers):
    res = client.post("/api/v1/missions/", headers=auth_headers, json={
        "name": "Auditar arquitectura",
        "objective": "Identificar deuda técnica del repo",
        "type": "technical-audit",
        "runtime": "openclaw",
        "success_criteria": ["informe entregado"],
    })
    assert res.status_code == 201, res.text
    m = res.json()
    assert m["name"] == "Auditar arquitectura"
    assert m["status"] == "draft"
    assert m["type"] == "technical-audit"
    assert m["runtime"] == "openclaw"

    # list
    res = client.get("/api/v1/missions/", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 1

    # get
    res = client.get(f"/api/v1/missions/{m['id']}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["objective"] == "Identificar deuda técnica del repo"

    # delete
    res = client.delete(f"/api/v1/missions/{m['id']}", headers=auth_headers)
    assert res.status_code == 204
    res = client.get(f"/api/v1/missions/{m['id']}", headers=auth_headers)
    assert res.status_code == 404


def test_mission_validation_tipo_invalido(client, auth_headers):
    res = client.post("/api/v1/missions/", headers=auth_headers, json={
        "name": "X", "objective": "Y", "type": "no-existe",
    })
    assert res.status_code == 400


def test_mission_plan_genera_workflow(client, auth_headers):
    res = client.post("/api/v1/missions/", headers=auth_headers, json={
        "name": "Research WebMCP",
        "objective": "Investigar arquitectura WebMCP",
        "type": "research",
    })
    m = res.json()
    assert m["workflow_id"] is None

    res = client.post(f"/api/v1/missions/{m['id']}/plan", headers=auth_headers)
    assert res.status_code == 200, res.text
    m2 = res.json()
    assert m2["workflow_id"] is not None
    assert m2["status"] == "planned"


def test_mission_run_happy_path(client, auth_headers):
    res = client.post("/api/v1/missions/", headers=auth_headers, json={
        "name": "Code review",
        "objective": "Revisar PR",
        "type": "code-review",
    })
    m = res.json()
    res = client.post(f"/api/v1/missions/{m['id']}/plan", headers=auth_headers)
    m = res.json()

    res = client.post(f"/api/v1/missions/{m['id']}/run", headers=auth_headers)
    assert res.status_code == 200, res.text
    run = res.json()
    assert run["status"] in ("completed", "failed", "waiting_approval")
    assert run["mission_id"] == m["id"]

    # runs list
    res = client.get(f"/api/v1/missions/{m['id']}/runs", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_mission_run_con_aprobacion(client, auth_headers):
    """research tiene step approval → queda waiting_approval y se puede aprobar."""
    res = client.post("/api/v1/missions/", headers=auth_headers, json={
        "name": "Research con gate",
        "objective": "Investigar X",
        "type": "research",
    })
    m = res.json()
    client.post(f"/api/v1/missions/{m['id']}/plan", headers=auth_headers)
    res = client.post(f"/api/v1/missions/{m['id']}/run", headers=auth_headers)
    run = res.json()
    assert run["status"] == "waiting_approval"

    # misión visible en estado waiting_approval
    res = client.get(f"/api/v1/missions/{m['id']}", headers=auth_headers)
    assert res.json()["status"] == "waiting_approval"

    # aprobar step 2 (índice del approval en research: 0,1,2 → step 2)
    res = client.post(f"/api/v1/missions/{m['id']}/approve", headers=auth_headers, json={
        "step_index": 2, "approved": True,
    })
    assert res.status_code == 200, res.text
    run2 = res.json()
    assert run2["status"] == "completed"
    assert run2["completed_at"] is not None
    assert any("workflow_completed" in entry["message"] for entry in run2["logs"])


def test_mission_no_inicia_segundo_run_mientras_espera_aprobacion(client, auth_headers):
    mission = client.post("/api/v1/missions/", headers=auth_headers, json={
        "name": "Research con gate", "objective": "Investigar X", "type": "research",
    }).json()
    client.post(f"/api/v1/missions/{mission['id']}/plan", headers=auth_headers)
    first = client.post(f"/api/v1/missions/{mission['id']}/run", headers=auth_headers)
    assert first.json()["status"] == "waiting_approval"

    second = client.post(f"/api/v1/missions/{mission['id']}/run", headers=auth_headers)
    assert second.status_code == 400
    assert "ejecución activa" in second.json()["detail"]


def test_mission_types_endpoints(client, auth_headers):
    res = client.get("/api/v1/missions/types", headers=auth_headers)
    assert res.status_code == 200
    assert "research" in res.json()
    assert "technical-audit" in res.json()
    res = client.get("/api/v1/missions/statuses", headers=auth_headers)
    assert "completed" in res.json()
