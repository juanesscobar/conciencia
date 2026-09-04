"""master-prompt-cli §7/§8 — short IDs (M-xxxx) y resolución contextual de misión."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import uuid

import pytest
from typer.testing import CliRunner

from cli import app, _resolve_uuid, _short_id, _active_mission_or_pick

runner = CliRunner()
TEST_DB_URL = "sqlite:///./test.db"


@pytest.fixture(autouse=True)
def _cli_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DB_URL)
    yield


def _seed_mission(db, name="Misión test", objective="objetivo", type="research", status="draft"):
    from app.models.mission import Mission
    m = Mission(name=name, objective=objective, type=type, status=status)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def test_short_id_format():
    assert _short_id("mission", "6998bc52-08b6-42d6-9024-321a95dbcb00") == "M-6998bc52"
    assert _short_id("run", "abcd1234-0000-0000-0000-000000000000") == "R-abcd1234"
    assert _short_id("team", "12345678-0000-0000-0000-000000000000") == "T-12345678"


def test_resolve_uuid_acepta_full_y_corto(db):
    m = _seed_mission(db, name="Research logística")
    full = str(m.id)

    assert _resolve_uuid(db, full, "mission") == full
    assert _resolve_uuid(db, f"M-{full}", "mission") == full
    assert _resolve_uuid(db, f"M-{full[:8]}", "mission") == full
    # corto sin prefijo → rechazado (ambigüedad entre tipos)
    with pytest.raises(ValueError):
        _resolve_uuid(db, full[:8], "mission")


def test_resolve_uuid_prefijo_equivocado(db):
    m = _seed_mission(db)
    with pytest.raises(ValueError):
        _resolve_uuid(db, f"T-{str(m.id)[:8]}", "mission")  # T es de team


def test_resolve_uuid_ambiguo_y_ausente(db):
    # dos misiones que comparten los primeros 8 hex
    m1 = _seed_mission(db, name="A")
    m2 = _seed_mission(db, name="B")
    # forzamos colisión de prefijo solo si fuera posible; si no, ausente:
    with pytest.raises(ValueError):
        _resolve_uuid(db, "M-00000000", "mission")  # no existe
    _ = (m1, m2)


def test_active_mission_contexto(db):
    # sin misiones activas → hint
    _seed_mission(db, status="completed")
    mission, hint = _active_mission_or_pick(db)
    assert mission is None and "No hay misiones activas" in hint

    # exactamente una activa → la devuelve
    act = _seed_mission(db, name="La activa", status="waiting_approval")
    mission, hint = _active_mission_or_pick(db)
    assert mission is not None and mission.id == act.id and hint is None

    # varias → pide elegir
    _seed_mission(db, name="Otra activa", status="running")
    mission, hint = _active_mission_or_pick(db)
    assert mission is None and "elegí una explícitamente" in hint


def test_cli_mission_inspect_sin_id_usa_contexto(db):
    from app.models.mission import Mission
    # limpiar: dejar UNA activa
    for m in db.query(Mission).all():
        db.delete(m)
    db.commit()
    act = _seed_mission(db, name="Única activa", objective="x", status="draft")

    result = runner.invoke(app, ["mission", "inspect"])
    assert result.exit_code == 0, result.output
    assert "Única activa" in result.output
    assert str(act.id)[:8] in result.output


def test_cli_mission_inspect_con_short_id(db):
    m = _seed_mission(db, name="Corta", objective="y")
    result = runner.invoke(app, ["mission", "inspect", f"M-{str(m.id)[:8]}"])
    assert result.exit_code == 0, result.output
    assert "Corta" in result.output

    result = runner.invoke(app, ["mission", "inspect", "M-00000000"])
    assert result.exit_code != 0
    assert "No existe" in result.output or "no encontrada" in result.output
