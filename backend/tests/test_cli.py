"""Tests Fase 6 — CLI `conciencia` (spec §19/§41).

Verifica que el CLI use la MISMA lógica de dominio que la API:
`conciencia search` debe devolver los mismos leads que POST /api/v1/leads/search.
Se apunta a la DB de test con DATABASE_URL.
"""

import json
import os

import pytest
from typer.testing import CliRunner

from cli import app
from app.modules.leadhunter.models import Lead

runner = CliRunner()

TEST_DB_URL = "sqlite:///./test.db"


@pytest.fixture(autouse=True)
def _cli_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DB_URL)
    yield
    # `config set` escribe os.environ directo (simula persistencia) — limpiar
    # SIN monkeypatch (su undo restauraría el valor). No contaminar test_geo.
    for k in list(os.environ):
        if k.startswith(("SEARCH_", "LEADHUNTER_", "EMBEDDING_", "RANKING_")):
            os.environ.pop(k, None)


def _seed(db, company="Farmacia San Roque", industry="farmacia", region="Asuncion",
          phone="021123456", email="ventas@sanroque.com.py", score=70):
    lead = Lead(company=company, industry=industry, region=region, phone=phone,
                email=email, source="test", score=score)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


class TestHealth:
    def test_health_ok(self):
        res = runner.invoke(app, ["health"])
        assert res.exit_code == 0
        assert "Base de datos" in res.stdout

    def test_search_json_misma_logica_que_api(self, db):
        _seed(db, company="Farmacia San Roque", industry="farmacia")
        _seed(db, company="Logistica Ruta 6", industry="logistica")
        res = runner.invoke(app, ["search", "farmacia", "--json"])
        assert res.exit_code == 0
        data = json.loads(res.stdout)
        assert data["total"] == 1
        assert data["items"][0]["company"] == "Farmacia San Roque"
        assert data["items"][0]["data_quality"] is not None

    def test_search_filtro_region(self, db):
        _seed(db, company="A Asuncion", region="Asuncion")
        _seed(db, company="B CDE", region="Ciudad del Este")
        res = runner.invoke(app, ["search", "", "--region", "Ciudad del Este", "--json"])
        assert res.exit_code == 0
        data = json.loads(res.stdout)
        assert data["total"] == 1
        assert data["items"][0]["company"] == "B CDE"


class TestLeads:
    def test_list_json(self, db):
        _seed(db, company="Comercio Uno", industry="comercio")
        res = runner.invoke(app, ["leads", "list", "--json"])
        assert res.exit_code == 0
        data = json.loads(res.stdout)
        assert any(i["company"] == "Comercio Uno" for i in data["items"])

    def test_export_json(self, db):
        _seed(db, company="Exportame SA", industry="comercio")
        res = runner.invoke(app, ["leads", "export", "--format", "json"])
        assert res.exit_code == 0
        data = json.loads(res.stdout)
        assert any(i["company"] == "Exportame SA" for i in data)

    def test_export_csv_archivo(self, db, tmp_path):
        _seed(db, company="CSV SA")
        out = tmp_path / "leads.csv"
        res = runner.invoke(app, ["leads", "export", "--format", "csv", "--out", str(out)])
        assert res.exit_code == 0
        content = out.read_text(encoding="utf-8")
        assert content.startswith("id,company")
        assert "CSV SA" in content


class TestLead:
    def test_inspect_json(self, db):
        lead = _seed(db, company="Inspeccioname SA")
        res = runner.invoke(app, ["lead", "inspect", lead.id, "--json"])
        assert res.exit_code == 0
        data = json.loads(res.stdout)
        assert data["company"] == "Inspeccioname SA"
        assert "reasons" in data

    def test_score_json(self, db):
        lead = _seed(db, company="Puntuame SA")
        res = runner.invoke(app, ["lead", "score", lead.id, "--json"])
        assert res.exit_code == 0
        data = json.loads(res.stdout)
        assert 0 <= data["lead_score"] <= 100
        assert "opportunity_score" in data
        assert data["reasons"]

    def test_inspect_no_existe(self):
        res = runner.invoke(app, ["lead", "inspect", "no-existe"])
        assert res.exit_code == 1


class TestConfig:
    def test_set_get(self):
        res = runner.invoke(app, ["config", "set", "search.country", "BR"])
        assert res.exit_code == 0
        res = runner.invoke(app, ["config", "get", "search.country"])
        assert res.exit_code == 0
        assert "BR" in res.stdout

    def test_get_todas(self, db):
        res = runner.invoke(app, ["config", "get"])
        assert res.exit_code == 0
        assert "Key" in res.stdout


class TestAgentesYModulos:
    def test_agents_json(self, db):
        res = runner.invoke(app, ["agents", "--json"])
        assert res.exit_code == 0
        assert isinstance(json.loads(res.stdout), list)

    def test_modules_json(self):
        res = runner.invoke(app, ["modules", "--json"])
        assert res.exit_code == 0
        mods = json.loads(res.stdout)
        assert any(m["id"] == "core" for m in mods)
        assert any(m["id"] == "leadhunter" for m in mods)


class TestHunt:
    def test_fuente_desconocida_error(self):
        res = runner.invoke(app, ["hunt", "--source", "no-existe"])
        assert res.exit_code == 1
        assert "Fuente desconocida" in res.stdout
