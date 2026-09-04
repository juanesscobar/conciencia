"""Tests Fase 9 — Multi-Runtime Agent Integration (requisito CEO, spec §28/§29/§47).

Registry de runtimes (Settings JSON), salud de binarios, PUT admin-only, y
ejecución de agentes en runtimes CLI externos con subprocess mockeado.
"""

import subprocess

import pytest

from app.models.agent import Agent, AgentRole, AgentType, AgentStatus, AutonomyLevel, AgentRuntime, AgentProvider


def _seed_agent(db, role=AgentRole.DEV):
    agent = Agent(
        name="DevTest", emoji="👨‍💻", role=role, type=AgentType.SYSTEM,
        status=AgentStatus.IDLE, personality="Dev de test.",
        capabilities=["code_review"], autonomy_level=AutonomyLevel.PREVIEW,
        runtime=AgentRuntime.GENERIC, provider=AgentProvider.DEEPSEEK, model="deepseek-chat",
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def _make_admin(client, db):
    """Registra un usuario y lo promueve a admin (token ya emitido)."""
    client.post("/api/v1/auth/register", json={
        "email": "admin@test.com", "username": "adminuser",
        "password": "***", "display_name": "Admin",
    })
    from app.models.user import User
    user = db.query(User).filter(User.username == "adminuser").first()
    user.role = "admin"
    db.commit()
    res = client.post("/api/v1/auth/login", json={"username": "adminuser", "password": "***"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _mock_subprocess(monkeypatch, stdout="OK desde CLI externo", returncode=0):
    from app.services import capability_readiness

    class FakeProc:
        def __init__(self):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = "" if returncode == 0 else "boom"

    def fake_run(*args, **kwargs):
        return FakeProc()

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(capability_readiness.shutil, "which", lambda command: f"/bin/{command}")


def _enable_runtime(client, db, name="codex"):
    """Habilita un runtime CLI vía PUT admin."""
    headers = _make_admin(client, db)
    res = client.put("/api/v1/agents/runtimes/config",
                     json={"configs": [{"name": name, "enabled": True}]}, headers=headers)
    assert res.status_code == 200
    return headers


def _mock_generic_adapter(monkeypatch):
    """Fake del adapter generic (evita llamadas LLM reales en tests)."""
    from app.adapters import registry as registry_mod
    from app.adapters.base import DispatchResult

    class FakeAdapter:
        def dispatch_task(self, identity, task, context=None):
            return DispatchResult(ok=False, status="failed", error="LLM no configurado (simulado)",
                                  simulated=True, runtime="generic")

        def get_capabilities(self):
            return ["llm_chat"]

    monkeypatch.setattr(registry_mod, "get_adapter", lambda name: FakeAdapter())


class TestRuntimesAPI:
    def test_get_configs(self, client, auth_headers):
        res = client.get("/api/v1/agents/runtimes/config", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        names = {r["name"] for r in data}
        assert {"generic", "mcp", "codex", "openclaw", "claude_code"} <= names
        generic = next(r for r in data if r["name"] == "generic")
        assert generic["enabled"] is True
        assert "online" in generic

    def test_put_requiere_admin(self, client, auth_headers):
        res = client.put("/api/v1/agents/runtimes/config", json={"configs": []}, headers=auth_headers)
        assert res.status_code == 403

    def test_put_admin_persiste(self, client, db):
        headers = _make_admin(client, db)
        configs = [
            {"name": "codex", "enabled": True, "command": "codex", "cwd": "C:/tmp", "timeout_s": 99},
            {"name": "desconocido", "enabled": True},  # se ignora
        ]
        res = client.put("/api/v1/agents/runtimes/config", json={"configs": configs}, headers=headers)
        assert res.status_code == 200
        data = res.json()
        codex = next(r for r in data if r["name"] == "codex")
        assert codex["enabled"] is True
        assert codex["timeout_s"] == 99
        assert not any(r["name"] == "desconocido" for r in data)
        # persiste: GET de nuevo
        res2 = client.get("/api/v1/agents/runtimes/config", headers=headers)
        assert next(r for r in res2.json() if r["name"] == "codex")["enabled"] is True

    def test_requiere_auth(self, client):
        res = client.get("/api/v1/agents/runtimes/config")
        assert res.status_code in (401, 403)


class TestRunInRuntime:
    def test_cli_ok(self, client, auth_headers, db, monkeypatch):
        _mock_subprocess(monkeypatch, stdout="Refactor listo\n")
        _enable_runtime(client, db, "codex")
        agent = _seed_agent(db)
        res = client.post(f"/api/v1/agents/{agent.id}/run", json={
            "task_text": "Refactorizá el módulo X",
            "runtime": "codex",
        }, headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "completed"
        assert "Refactor listo" in data["output"]
        assert data["runtime"] == "codex"
        assert data["provider"] == "cli"

    def test_cli_error(self, client, auth_headers, db, monkeypatch):
        _mock_subprocess(monkeypatch, returncode=1, stdout="")
        _enable_runtime(client, db, "codex")
        agent = _seed_agent(db)
        res = client.post(f"/api/v1/agents/{agent.id}/run", json={
            "task_text": "tarea que falla",
            "runtime": "codex",
        }, headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["status"] == "failed"
        assert "boom" in (res.json().get("error") or "")

    def test_runtime_deshabilitado(self, client, auth_headers, db, monkeypatch):
        _mock_subprocess(monkeypatch)
        agent = _seed_agent(db)
        res = client.post(f"/api/v1/agents/{agent.id}/run", json={
            "task_text": "x",
            "runtime": "opencode",  # default enabled=False
        }, headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["status"] == "failed"
        assert "deshabilitado" in res.json()["error"]

    def test_sin_override_usa_adapter(self, client, auth_headers, db, monkeypatch):
        _mock_generic_adapter(monkeypatch)
        agent = _seed_agent(db)
        res = client.post(f"/api/v1/agents/{agent.id}/run", json={
            "task_text": "hola",
        }, headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["runtime"] == "generic"
        assert res.json()["simulated"] is True


class TestUnit:
    def test_get_runtime_configs_defaults(self, db):
        from app.core.agent_runtime import get_runtime_configs
        configs = get_runtime_configs(db)
        by_name = {c.name: c for c in configs}
        assert by_name["generic"].type == "internal"
        assert by_name["codex"].command == "codex"
        assert by_name["mcp"].type == "mcp"

    def test_check_health_internal(self, db):
        from app.core.agent_runtime import get_runtime, check_runtime_health
        cfg = get_runtime(db, "generic")
        h = check_runtime_health(cfg)
        assert h["online"] is h["ready"]
        assert h["state"] in {"ready", "blocked", "misconfigured", "unavailable"}
