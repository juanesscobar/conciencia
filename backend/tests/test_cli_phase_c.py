"""Tests Fase C — CLI Foundation: init, doctor, agent, workflow, runtimes, models."""

import pytest
from typer.testing import CliRunner

from cli import app

runner = CliRunner()

TEST_DB_URL = "sqlite:///./test.db"


def test_root_help_renders():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0, result.stdout
    assert "Mission Orchestration" in result.stdout


@pytest.fixture(autouse=True)
def _cli_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DB_URL)
    yield


class TestInit:
    def test_init_crea_conciencia_dir(self, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        (tmp_path / "Dockerfile").write_text("FROM python\n", encoding="utf-8")
        res = runner.invoke(app, ["init", str(tmp_path)])
        assert res.exit_code == 0, res.stdout
        assert (tmp_path / ".conciencia" / "project.yaml").exists()
        assert (tmp_path / ".conciencia" / "context.md").exists()
        content = (tmp_path / ".conciencia" / "project.yaml").read_text(encoding="utf-8")
        assert "git: true" in content
        assert "Python" in content
        assert "Docker" in content

    def test_init_json(self, tmp_path):
        res = runner.invoke(app, ["init", str(tmp_path), "--json"])
        assert res.exit_code == 0
        assert '"git": false' in res.stdout


class TestDoctor:
    def test_doctor_ok(self, db):
        # db (fixture conftest) crea las tablas en test.db — el doctor usa la misma DB
        res = runner.invoke(app, ["doctor"])
        assert res.exit_code in (0, 1), res.stdout
        assert "Conciencia doctor" in res.stdout
        assert "Overall:" in res.stdout


class TestAgent:
    def test_agent_inspect_por_rol(self, db):
        from app.models.agent import Agent
        agent = Agent(name="DevBot", role="dev", status="idle")
        db.add(agent)
        db.commit()
        res = runner.invoke(app, ["agent", "inspect", "dev"])
        assert res.exit_code == 0, res.stdout
        assert "DevBot" in res.stdout

    def test_agent_run_generic(self, db):
        from app.models.agent import Agent
        agent = Agent(name="DevBot", role="dev", status="idle", runtime="generic")
        db.add(agent)
        db.commit()
        # Modo simulado sin API keys → generic adapter responde sin error
        res = runner.invoke(app, ["agent", "run", str(agent.id), "revisar el código"])
        assert res.exit_code == 0, res.stdout

    def test_agent_list_y_inspect_por_nombre_sin_secretos(self, db):
        from app.models.agent import Agent

        agent = Agent(
            name="ProjectManager",
            role="pm",
            status="idle",
            runtime="generic",
            config={"api_token": "never-print-me", "permissions": {"allow": ["read"]}},
        )
        db.add(agent)
        db.commit()
        listed = runner.invoke(app, ["agent", "list"])
        inspected = runner.invoke(app, ["agent", "inspect", "ProjectManager", "--json"])
        assert listed.exit_code == 0
        assert inspected.exit_code == 0
        assert "ProjectManager" in inspected.stdout
        assert "health_reason" in inspected.stdout
        assert "never-print-me" not in inspected.stdout


class TestWorkflowCli:
    def test_workflow_list_vacio(self):
        res = runner.invoke(app, ["workflow"])
        assert res.exit_code == 0

    def test_workflow_inspect_no_encontrado(self):
        res = runner.invoke(app, ["workflow-inspect", "no-existe"])
        assert res.exit_code != 0

    def test_workflow_group_and_legacy_aliases(self):
        assert runner.invoke(app, ["workflow", "list"]).exit_code == 0
        assert runner.invoke(app, ["workflow"]).exit_code == 0
        assert runner.invoke(app, ["workflow", "inspect", "no-existe"]).exit_code != 0
        assert runner.invoke(app, ["workflow-inspect", "no-existe"]).exit_code != 0

    def test_workflow_run_desde_mission(self, db, auth_headers, client):
        # crear misión + plan → genera workflow → correrlo por CLI
        res = client.post("/api/v1/missions/", headers=auth_headers, json={
            "name": "WF CLI", "objective": "Probar workflow run", "type": "research",
        })
        m = res.json()
        client.post(f"/api/v1/missions/{m['id']}/plan", headers=auth_headers)
        m2 = client.get(f"/api/v1/missions/{m['id']}", headers=auth_headers).json()
        wf_id = m2["workflow_id"]
        res = runner.invoke(app, ["workflow-run", wf_id])
        assert res.exit_code == 0, res.stdout
        assert "status=" in res.stdout


class TestRuntimesModels:
    def test_runtime_list(self):
        res = runner.invoke(app, ["runtime"])
        assert res.exit_code == 0, res.stdout
        assert "generic" in res.stdout

    def test_model_list(self, db):
        from app.models.agent import Agent
        db.add(Agent(name="Bot", role="dev", status="idle", provider="deepseek", model="deepseek-chat"))
        db.commit()
        res = runner.invoke(app, ["model"])
        assert res.exit_code == 0, res.stdout
        assert "deepseek" in res.stdout

    def test_tool_list(self):
        res = runner.invoke(app, ["tool"])
        assert res.exit_code == 0, res.stdout
        assert "email" in res.stdout
