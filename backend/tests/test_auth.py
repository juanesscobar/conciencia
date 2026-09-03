def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_register(client):
    res = client.post("/api/v1/auth/register", json={
        "email": "new@user.com",
        "username": "newuser",
        "password": "secure123",
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_register_duplicate(client):
    client.post("/api/v1/auth/register", json={
        "email": "dup@test.com",
        "username": "dupuser",
        "password": "pass123",
    })
    res = client.post("/api/v1/auth/register", json={
        "email": "dup@test.com",
        "username": "dupuser",
        "password": "pass123",
    })
    assert res.status_code == 400


def test_login(client):
    client.post("/api/v1/auth/register", json={
        "email": "login@test.com",
        "username": "loginuser",
        "password": "mypassword",
    })
    res = client.post("/api/v1/auth/login", json={
        "username": "loginuser",
        "password": "mypassword",
    })
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_wrong_password(client):
    res = client.post("/api/v1/auth/login", json={
        "username": "loginuser",
        "password": "wrongpass",
    })
    assert res.status_code == 401


def test_me_endpoint(client, auth_headers):
    res = client.get("/api/v1/auth/me", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["username"] == "testuser"


def test_me_without_token(client):
    res = client.get("/api/v1/auth/me")
    # HTTPBearer uses the standards-compliant 401 for missing credentials.
    assert res.status_code == 401
