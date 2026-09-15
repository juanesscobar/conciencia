import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pathlib import Path

_test_tmp = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Temp" / "mission-control-tests"
_test_tmp.mkdir(exist_ok=True)
os.environ["TEMP"] = str(_test_tmp)
os.environ["TMP"] = str(_test_tmp)
os.environ["TMPDIR"] = str(_test_tmp)
tempfile.tempdir = str(_test_tmp)

_default_test_db = _test_tmp / "test.db"
SQLALCHEMY_DATABASE_URL = os.getenv("TEST_DATABASE_URL", f"sqlite:///{_default_test_db.as_posix()}")
os.environ["DATABASE_URL"] = SQLALCHEMY_DATABASE_URL

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.services.auth import hash_password
from app.models import activity, agent, audit, connection, context_pack, cost_record, decision, deliverable, execution, harness, metric, mission, policy, project, setting, sprint, signal, task, task_dependency, team, user, user_memory, workflow
import cli as cli_module

# A single in-memory connection is stable on Windows and is shared by the API,
# CLI and direct ORM fixtures for the duration of each test.
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
cli_module._make_session = lambda: TestingSessionLocal()


@pytest.fixture(autouse=True)
def setup_db():
    from app.services.workspace_semantic import reset_workspace_backend

    reset_workspace_backend()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    reset_workspace_backend()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def auth_token(client):
    """Register a test user and return JWT token"""
    client.post("/api/v1/auth/register", json={
        "email": "test@test.com",
        "username": "testuser",
        "password": "test123",
        "display_name": "Test User",
    })
    res = client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "test123",
    })
    return res.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}
