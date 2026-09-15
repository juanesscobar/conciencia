"""Tests Fase E - Mission Planning: `conciencia ask` (master prompt §9/§E).

Texto natural → intent → propuesta (agentes/runtime/workflow/costo) → confirmación
humana → creación de Misión. Sin LLM: 100% por reglas.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from typer.testing import CliRunner

from cli import app

runner = CliRunner()
TEST_DB_URL = "sqlite:///./test.db"


@pytest.fixture(autouse=True)
def _cli_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DB_URL)
    yield


def _seed_agent(db, name="ResearchBot", role="rd", caps=None, model="deepseek-chat"):
    from app.models.agent import Agent
    a = Agent(
        name=name, role=role, status="idle", runtime="generic",
        provider="deepseek", model=model, capabilities=caps or ["research"],
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


# ---------------------------------------------------------------------------
# 1. Intent classification (reglas, sin LLM)
# ---------------------------------------------------------------------------

def test_classify_intent_reglas():
    from app.services.ask_service import classify_intent
    cases = [
        ("auditar la deuda técnica del repo", "technical-audit"),
        ("hacer code review del PR 42", "code-review"),
        ("hay un bug en el login, no funciona", "debugging"),
        ("escribir tests e2e con coverage", "testing"),
        ("desplegar a producción", "deployment"),
        ("cazar leads de farmacias en Asunción", "lead-research"),
        ("preparar propuesta técnica para el cliente", "technical-proposal"),
        ("investigar alternativas open source de MCP", "research"),
    ]
    for text, expected in cases:
        assert classify_intent(text) == expected, text


def test_classify_intent_fallback_research():
    from app.services.ask_service import classify_intent
    assert classify_intent("cualquier cosa sin keywords") == "research"
    assert classify_intent("") == "research"


def test_classify_devpost_submission_is_not_infrastructure_deployment():
    from app.services.ask_service import classify_intent_details

    submission = classify_intent_details("Preparar submission de Devpost y demo para el jurado")
    deployment = classify_intent_details("Desplegar la API a produccion")
    assert submission["type"] == "technical-proposal"
    assert submission["confidence"] >= 0.9
    assert deployment["type"] == "deployment"


# ---------------------------------------------------------------------------
# 2. Propuesta (service)
# ---------------------------------------------------------------------------

def test_build_proposal_con_agentes(db):
    from app.services import ask_service
    a = _seed_agent(db)
    p = ask_service.build_proposal(db, "investigar el mercado de asistentes de IA")
    assert p["mission_type"] == "research"
    assert p["name"]
    assert p["objective"]
    assert p["runtime"] == "generic"
    assert p["agents"], "debería sugerir el agente con capability research"
    assert p["agents"][0]["agent_id"] == str(a.id)
    assert p["agents"][0]["coverage"] == 100
    assert p["workflow"], "workflow por defecto del tipo"
    assert p["cost_estimate"]["cost_usd"] >= 0
    assert p["success_criteria"]


def test_build_proposal_runtime_y_workflow_por_tipo(db):
    from app.services import ask_service
    p = ask_service.build_proposal(db, "implementar un módulo de reportes")
    assert p["mission_type"] == "software-development"
    assert p["runtime"] == "claude_code"
    names = [s["name"] for s in p["workflow"]]
    assert "implement" in names or "plan" in names
    assert p["readiness"]["workflow"]["resolvable"] is True
    assert p["readiness"]["runtime"]["resolvable"] is False
    assert p["readiness"]["runtime"]["state"] == "disabled"


def test_create_from_proposal_crea_mission(db):
    from app.models.mission import Mission
    from app.services import ask_service
    _seed_agent(db, caps=["code", "refactoring"])
    p = ask_service.build_proposal(db, "implementar un módulo de reportes")
    m = ask_service.create_from_proposal(db, p)
    assert m.status == "draft"
    assert m.type == "software-development"
    assert m.runtime == "claude_code"
    assert m.agent_ids == [p["agents"][0]["agent_id"]]
    assert m.success_criteria == p["success_criteria"]
    assert db.query(Mission).count() == 1


# ---------------------------------------------------------------------------
# 3. API
# ---------------------------------------------------------------------------

def test_ask_api_propuesta(client, auth_headers):
    res = client.post("/api/v1/ask", headers=auth_headers, json={"text": "auditar la arquitectura del backend"})
    assert res.status_code == 200, res.text
    p = res.json()
    assert p["mission_type"] == "technical-audit"
    assert p["runtime"] == "generic"
    assert p["workflow"]
    assert p["cost_estimate"]


def test_ask_api_rechaza_texto_vacio(client, auth_headers):
    res = client.post("/api/v1/ask", headers=auth_headers, json={"text": "   "})
    assert res.status_code == 400


def test_ask_api_create_mision(client, auth_headers):
    res = client.post("/api/v1/ask", headers=auth_headers, json={"text": "auditar la arquitectura del backend"})
    p = res.json()
    res = client.post("/api/v1/ask/create", headers=auth_headers, json={"proposal": p, "confirmed": True})
    assert res.status_code == 200, res.text
    m = res.json()
    assert m["status"] == "draft"
    assert m["mission"]["type"] == "technical-audit"

    res = client.get("/api/v1/missions/", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_ask_api_create_sin_confirmacion(client, auth_headers):
    res = client.post("/api/v1/ask", headers=auth_headers, json={"text": "investigar agentes"})
    p = res.json()
    res = client.post("/api/v1/ask/create", headers=auth_headers, json={"proposal": p, "confirmed": False})
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# 4. CLI (Fase E DoD: lenguaje natural → misión estructurada, con confirmación)
# ---------------------------------------------------------------------------

def test_ask_cli_json_no_crea(db):
    _seed_agent(db)
    res = runner.invoke(app, ["ask", "--json", "investigar frameworks de asistentes open source"])
    assert res.exit_code == 0, res.stdout
    import json
    p = json.loads(res.stdout)
    assert p["mission_type"] == "research"
    assert p["agents"]
    # --json no crea nada
    from app.models.mission import Mission
    db.expire_all()
    assert db.query(Mission).count() == 0


def test_ask_cli_json_largo_es_parseable(db):
    import json

    text = "Preparar presentación, demo, submission y documentación para jueces " * 3
    res = runner.invoke(app, ["ask", "--json", text])
    assert res.exit_code == 0, res.stdout
    proposal = json.loads(res.stdout)
    assert proposal["objective"] == text
    assert proposal["mission_type"] == "technical-proposal"


def test_ask_cli_yes_crea_mision(db):
    _seed_agent(db, caps=["code", "refactoring"])
    res = runner.invoke(app, ["ask", "--yes", "implementar un módulo de reportes"])
    assert res.exit_code == 0, res.stdout
    assert "Misión creada" in res.stdout
    assert "software-development" in res.stdout or "claude_code" in res.stdout

    from app.models.mission import Mission
    db.expire_all()
    m = db.query(Mission).first()
    assert m is not None
    assert m.type == "software-development"
    assert m.runtime == "claude_code"
    assert m.agent_ids


def test_ask_cli_cancelado(db):
    _seed_agent(db)
    res = runner.invoke(app, ["ask", "investigar agentes"], input="n\n")
    assert res.exit_code == 0, res.stdout
    assert "Cancelado" in res.stdout
    from app.models.mission import Mission
    db.expire_all()
    assert db.query(Mission).count() == 0


def test_ask_cli_interactivo_sin_texto(db):
    _seed_agent(db)
    res = runner.invoke(app, ["ask"], input="investigar agentes\nn\n")
    assert res.exit_code == 0, res.stdout
    assert "Qué querés lograr" in res.stdout
    assert "Cancelado" in res.stdout
