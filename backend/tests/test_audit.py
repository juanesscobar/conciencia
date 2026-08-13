"""Tests PR-1.4 — Audit log append-only + hooks en tasks."""


def test_crear_tarea_registra_audit(client, auth_headers):
    project = client.post("/api/v1/projects/", headers=auth_headers, json={
        "name": "Audit Project",
    }).json()
    task = client.post("/api/v1/tasks/", headers=auth_headers, json={
        "title": "Audited Task", "project_id": project["id"],
    }).json()

    res = client.get(
        "/api/v1/audit/?event_type=task_created",
        headers=auth_headers,
    )
    assert res.status_code == 200
    events = res.json()
    assert len(events) == 1
    assert events[0]["task_id"] == task["id"]
    assert events[0]["payload"]["title"] == "Audited Task"


def test_actualizar_tarea_registra_audit(client, auth_headers):
    project = client.post("/api/v1/projects/", headers=auth_headers, json={
        "name": "Audit Project 2",
    }).json()
    task = client.post("/api/v1/tasks/", headers=auth_headers, json={
        "title": "Task", "project_id": project["id"],
    }).json()

    client.put(f"/api/v1/tasks/{task['id']}", headers=auth_headers, json={"status": "done"})

    events = client.get("/api/v1/audit/?event_type=task_updated", headers=auth_headers).json()
    assert len(events) == 1
    assert events[0]["task_id"] == task["id"]
    assert events[0]["payload"]["status"] == "done"


def test_evento_manual_y_filtro_por_correlation(client, auth_headers):
    res = client.post("/api/v1/audit/", headers=auth_headers, json={
        "event_type": "approval_granted",
        "actor": "test-actor",
        "actor_type": "user",
        "payload": {"decision": "approve"},
        "correlation_id": "corr-123",
    })
    assert res.status_code == 201
    event = res.json()
    assert event["event_type"] == "approval_granted"
    assert event["correlation_id"] == "corr-123"

    res = client.get("/api/v1/audit/?correlation_id=corr-123", headers=auth_headers)
    assert len(res.json()) == 1

    res = client.get("/api/v1/audit/?actor=test-actor", headers=auth_headers)
    assert len(res.json()) == 1


def test_audit_requiere_auth(client):
    res = client.get("/api/v1/audit/")
    assert res.status_code in (401, 403)
