def test_list_projects_empty(client, auth_headers):
    res = client.get("/api/v1/projects/", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() == []


def test_create_project(client, auth_headers):
    res = client.post("/api/v1/projects/", headers=auth_headers, json={
        "name": "Test Project",
        "description": "A test project",
        "status": "active",
        "priority": "p1",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Test Project"
    assert data["status"] == "active"
    assert "id" in data


def test_get_project(client, auth_headers):
    create = client.post("/api/v1/projects/", headers=auth_headers, json={
        "name": "Get Test",
    }).json()

    res = client.get(f"/api/v1/projects/{create['id']}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["name"] == "Get Test"


def test_get_project_not_found(client, auth_headers):
    res = client.get(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert res.status_code == 404


def test_update_project(client, auth_headers):
    create = client.post("/api/v1/projects/", headers=auth_headers, json={
        "name": "Before Update",
    }).json()

    res = client.put(
        f"/api/v1/projects/{create['id']}",
        headers=auth_headers,
        json={"name": "After Update", "priority": "p0"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "After Update"
    assert res.json()["priority"] == "p0"


def test_delete_project(client, auth_headers):
    create = client.post("/api/v1/projects/", headers=auth_headers, json={
        "name": "To Delete",
    }).json()

    res = client.delete(
        f"/api/v1/projects/{create['id']}",
        headers=auth_headers,
    )
    assert res.status_code == 200

    get = client.get(
        f"/api/v1/projects/{create['id']}",
        headers=auth_headers,
    )
    assert get.status_code == 404
