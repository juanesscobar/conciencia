"""Focused operational Home, connection and command-bar tests."""

import json

from typer.testing import CliRunner

from cli import app

runner = CliRunner()


def test_home_workforce_uses_canonical_readiness(db):
    from app.services.workspace_service import workspace_home

    home = workspace_home(db)
    assert {row["name"] for row in home["workforce"]} >= {"codex", "claude_code", "openclaw", "generic", "mcp"}
    assert all("ready" in row and "state" in row for row in home["workforce"])


def test_recommendations_are_deterministic_and_actionable(db):
    from app.models.mission import Mission
    from app.services.recommendation_service import recommendations

    db.add(Mission(name="Needs approval", objective="Review", status="waiting_approval"))
    db.commit()
    first = recommendations(db, cwd=".")
    second = recommendations(db, cwd=".")
    assert first == second
    assert first[0]["severity"] == "WARNING"
    assert all(row["command"].startswith(("conciencia", "git")) for row in first)


def test_connection_linteam_is_truthful_and_secret_free(db):
    result = runner.invoke(app, ["connection", "inspect", "linteam", "--json"])
    assert result.exit_code == 0, result.stdout
    row = json.loads(result.stdout)
    assert row["status"] == "contract_required"
    assert "secret" not in json.dumps(row).lower()


def test_connection_reference_redacts_secret_like_values(db):
    from app.models.connection import Connection
    from app.services.connection_service import inspect_connection

    db.add(Connection(name="Example", type="REST API", status="ready", config_reference="LINTEAM_TOKEN=do-not-print"))
    db.commit()
    assert inspect_connection(db, "Example")["config_reference"] == "[redacted configuration reference]"


def test_ask_operational_routes_do_not_create_missions(db):
    from app.models.mission import Mission

    for text, route in [
        ("¿Qué necesita mi atención?", "recommendation_query"),
        ("¿Qué herramientas de IA tengo disponibles?", "runtime_query"),
        ("Generá un informe de lo que hice hoy", "report_request"),
        ("Prepará este informe para enviarlo a LINTEAM", "external_action_request"),
    ]:
        result = runner.invoke(app, ["ask", "--json", text])
        assert result.exit_code == 0, result.stdout
        assert json.loads(result.stdout)["route"]["route"] == route
    assert db.query(Mission).count() == 0
