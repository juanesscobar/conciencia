def test_create_task(client, auth_headers):
    project = client.post("/api/v1/projects/", headers=auth_headers, json={
        "name": "Task Project",
    }).json()

    res = client.post("/api/v1/tasks/", headers=auth_headers, json={
        "title": "My Task",
        "description": "Do something",
        "project_id": project["id"],
        "priority": "high",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "My Task"
    assert data["status"] == "backlog"
    assert data["priority"] == "high"


def test_list_tasks(client, auth_headers):
    project = client.post("/api/v1/projects/", headers=auth_headers, json={
        "name": "List Project",
    }).json()

    client.post("/api/v1/tasks/", headers=auth_headers, json={
        "title": "Task 1",
        "project_id": project["id"],
    })
    client.post("/api/v1/tasks/", headers=auth_headers, json={
        "title": "Task 2",
        "project_id": project["id"],
    })

    res = client.get("/api/v1/tasks/", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_filter_tasks_by_project(client, auth_headers):
    p1 = client.post("/api/v1/projects/", headers=auth_headers, json={
        "name": "P1",
    }).json()
    p2 = client.post("/api/v1/projects/", headers=auth_headers, json={
        "name": "P2",
    }).json()

    client.post("/api/v1/tasks/", headers=auth_headers, json={
        "title": "Task A", "project_id": p1["id"],
    })
    client.post("/api/v1/tasks/", headers=auth_headers, json={
        "title": "Task B", "project_id": p2["id"],
    })

    res = client.get(f"/api/v1/tasks/?project_id={p1['id']}", headers=auth_headers)
    assert len(res.json()) == 1
    assert res.json()[0]["title"] == "Task A"


def test_update_task_status(client, auth_headers):
    project = client.post("/api/v1/projects/", headers=auth_headers, json={
        "name": "Update Project",
    }).json()

    task = client.post("/api/v1/tasks/", headers=auth_headers, json={
        "title": "Update Me",
        "project_id": project["id"],
    }).json()

    res = client.put(
        f"/api/v1/tasks/{task['id']}",
        headers=auth_headers,
        json={"status": "done"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "done"
