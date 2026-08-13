"""Tests PR-1.3 — DAG de dependencias: READY/BLOCKED, ciclos, propagación."""


def _setup_tasks(client, auth_headers):
    project = client.post("/api/v1/projects/", headers=auth_headers, json={
        "name": "DAG Project",
    }).json()
    a = client.post("/api/v1/tasks/", headers=auth_headers, json={
        "title": "Task A", "project_id": project["id"],
    }).json()
    b = client.post("/api/v1/tasks/", headers=auth_headers, json={
        "title": "Task B", "project_id": project["id"],
    }).json()
    return a, b


def _set_status(client, auth_headers, task_id, status):
    res = client.put(f"/api/v1/tasks/{task_id}", headers=auth_headers, json={"status": status})
    assert res.status_code == 200
    return res.json()


def test_dependencia_bloquea_tarea_ready(client, auth_headers):
    a, b = _setup_tasks(client, auth_headers)
    _set_status(client, auth_headers, b["id"], "ready")

    res = client.post(
        f"/api/v1/tasks/{b['id']}/dependencies",
        headers=auth_headers,
        json={"depends_on_id": a["id"]},
    )
    assert res.status_code == 201
    assert res.json()["depends_on_id"] == a["id"]

    task_b = client.get(f"/api/v1/tasks/{b['id']}", headers=auth_headers).json()
    assert task_b["status"] == "blocked"


def test_dag_view_muestra_bloqueadores(client, auth_headers):
    a, b = _setup_tasks(client, auth_headers)
    client.post(
        f"/api/v1/tasks/{b['id']}/dependencies",
        headers=auth_headers,
        json={"depends_on_id": a["id"]},
    )

    res = client.get(f"/api/v1/tasks/{b['id']}/dag", headers=auth_headers)
    assert res.status_code == 200
    dag = res.json()
    assert dag["task_id"] == b["id"]
    assert len(dag["dependencies"]) == 1
    assert dag["dependencies"][0]["satisfied"] is False
    assert len(dag["blocked_by"]) == 1


def test_completar_dependencia_desbloquea(client, auth_headers):
    a, b = _setup_tasks(client, auth_headers)
    _set_status(client, auth_headers, b["id"], "ready")
    client.post(
        f"/api/v1/tasks/{b['id']}/dependencies",
        headers=auth_headers,
        json={"depends_on_id": a["id"]},
    )

    _set_status(client, auth_headers, a["id"], "done")

    task_b = client.get(f"/api/v1/tasks/{b['id']}", headers=auth_headers).json()
    assert task_b["status"] == "ready"

    dag = client.get(f"/api/v1/tasks/{b['id']}/dag", headers=auth_headers).json()
    assert dag["dependencies"][0]["satisfied"] is True
    assert dag["blocked_by"] == []


def test_ciclo_es_rechazado(client, auth_headers):
    a, b = _setup_tasks(client, auth_headers)
    res = client.post(
        f"/api/v1/tasks/{b['id']}/dependencies",
        headers=auth_headers,
        json={"depends_on_id": a["id"]},
    )
    assert res.status_code == 201

    res = client.post(
        f"/api/v1/tasks/{a['id']}/dependencies",
        headers=auth_headers,
        json={"depends_on_id": b["id"]},
    )
    assert res.status_code == 400
    assert "ciclo" in res.json()["detail"].lower()


def test_auto_dependencia_es_rechazada(client, auth_headers):
    a, _ = _setup_tasks(client, auth_headers)
    res = client.post(
        f"/api/v1/tasks/{a['id']}/dependencies",
        headers=auth_headers,
        json={"depends_on_id": a["id"]},
    )
    assert res.status_code == 400


def test_dependencia_duplicada_es_idempotente(client, auth_headers):
    a, b = _setup_tasks(client, auth_headers)
    r1 = client.post(
        f"/api/v1/tasks/{b['id']}/dependencies",
        headers=auth_headers,
        json={"depends_on_id": a["id"]},
    )
    r2 = client.post(
        f"/api/v1/tasks/{b['id']}/dependencies",
        headers=auth_headers,
        json={"depends_on_id": a["id"]},
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


def test_eliminar_dependencia_desbloquea(client, auth_headers):
    a, b = _setup_tasks(client, auth_headers)
    _set_status(client, auth_headers, b["id"], "ready")
    client.post(
        f"/api/v1/tasks/{b['id']}/dependencies",
        headers=auth_headers,
        json={"depends_on_id": a["id"]},
    )

    res = client.delete(
        f"/api/v1/tasks/{b['id']}/dependencies/{a['id']}",
        headers=auth_headers,
    )
    assert res.status_code == 204

    task_b = client.get(f"/api/v1/tasks/{b['id']}", headers=auth_headers).json()
    assert task_b["status"] == "ready"
