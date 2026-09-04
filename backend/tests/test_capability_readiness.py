"""Regression tests for canonical runtime, provider and planner readiness."""

import json

import pytest
from typer.testing import CliRunner

from app.adapters.base import AgentIdentity
from app.adapters.generic import GenericAgentAdapter
from app.models.project import Project
from app.services import llm
from app.services.capability_readiness import (
    execution_overview,
    provider_readiness,
    runtime_readiness,
)
from cli import app

runner = CliRunner()
API_KEY_NAMES = (
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "OPENROUTER_API_KEY",
)


@pytest.fixture(autouse=True)
def _cli_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")


def _without_llm_credentials(monkeypatch):
    for name in API_KEY_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.setattr(llm, "_db_setting", lambda _key: "")


def test_generic_runtime_is_blocked_without_selected_provider_credentials(db, monkeypatch):
    _without_llm_credentials(monkeypatch)
    provider = provider_readiness("deepseek", "deepseek-chat")
    runtime = runtime_readiness(db, "generic", provider="deepseek", model="deepseek-chat")
    overview = execution_overview(db)

    assert provider["state"] == "blocked"
    assert provider["credentials"] == "unavailable"
    assert runtime["state"] == "blocked"
    assert runtime["ready"] is False
    assert overview["overall"] == "BLOCKED FOR MISSION EXECUTION"


def test_detected_but_disabled_external_runtime_is_not_an_error(db, monkeypatch):
    from app.services import capability_readiness

    monkeypatch.setattr(capability_readiness.shutil, "which", lambda command: f"/bin/{command}")
    runtime = runtime_readiness(db, "codex")
    assert runtime["detected"] is True
    assert runtime["enabled"] is False
    assert runtime["state"] == "disabled"
    assert runtime["ready"] is False


def test_generic_executor_uses_same_blocking_reason(monkeypatch):
    _without_llm_credentials(monkeypatch)
    readiness = provider_readiness("deepseek", "deepseek-chat")
    identity = AgentIdentity(
        agent_id="agent-1",
        name="ResearchBot",
        role="rd",
        runtime="generic",
        provider="deepseek",
        model="deepseek-chat",
        capabilities=["research"],
        config={},
    )
    result = GenericAgentAdapter().dispatch_task(identity, "investigar WebMCP")
    assert result.status == "failed"
    assert readiness["reason"] in result.error
    assert result.meta["reason"] == "llm_not_ready"


def test_planner_reports_generic_blocked_before_creation(db, monkeypatch):
    from app.services import ask_service

    _without_llm_credentials(monkeypatch)
    proposal = ask_service.build_proposal(db, "investigar los requisitos del WebMCP Challenge")
    assert proposal["runtime"] == "generic"
    assert proposal["readiness"]["runtime"]["state"] == "blocked"
    assert proposal["readiness"]["runtime"]["ready"] is False
    assert "Credenciales" in proposal["readiness"]["runtime"]["reason"]


def test_doctor_model_and_runtime_agree_when_generic_is_blocked(db, monkeypatch):
    _without_llm_credentials(monkeypatch)
    doctor = runner.invoke(app, ["doctor", "--json"])
    models = runner.invoke(app, ["model", "--json"])
    runtimes = runner.invoke(app, ["runtime", "--json"])

    assert doctor.exit_code == 0, doctor.stdout
    doctor_data = json.loads(doctor.stdout)
    model_data = json.loads(models.stdout)
    runtime_data = json.loads(runtimes.stdout)
    generic = next(item for item in runtime_data if item["name"] == "generic")
    deepseek = next(item for item in model_data if item["provider"] == "deepseek")
    assert doctor_data["overall"] == "BLOCKED FOR MISSION EXECUTION"
    assert generic["state"] == "blocked"
    assert deepseek["state"] == "blocked"

    human = runner.invoke(app, ["doctor"])
    assert human.exit_code == 1
    assert "BLOCKED FOR MISSION EXECUTION" in human.stdout


def test_onboard_json_detects_without_enabling(db, monkeypatch):
    from app.models.setting import Setting
    from app.services import capability_readiness

    monkeypatch.setattr(capability_readiness.shutil, "which", lambda command: f"/bin/{command}")
    result = runner.invoke(app, ["onboard", "--json"])
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert "codex" in data["configurable"]
    assert db.query(Setting).filter(Setting.key == "AGENT_RUNTIMES").first() is None


def test_workspace_home_works_without_current_project(db, tmp_path, monkeypatch):
    from app.services.workspace_service import workspace_home

    _without_llm_credentials(monkeypatch)
    db.add(Project(name="Conciencia"))
    db.commit()
    home = workspace_home(db, cwd=tmp_path)
    assert home["current_project"] is None
    assert home["recent_projects"][0]["name"] == "Conciencia"
    assert home["execution"]["overall"] == "BLOCKED FOR MISSION EXECUTION"
