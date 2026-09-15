"""Tests Fase 4 — Ranking + Scoring separados + Data Quality (spec §15/§16/§34/§35)."""

from datetime import datetime, timedelta

from app.modules.leadhunter.ranking import (
    DEFAULT_RANKING_WEIGHTS,
    data_quality_score,
    explain,
    get_ranking_weights,
    lead_score,
    opportunity_score,
    search_relevance,
    set_ranking_weights,
)
from app.modules.leadhunter.models import Lead
from app.modules.leadhunter.search import SearchQuery


def _lead(db, **kwargs):
    fields = dict(
        company="Cooperativa Ypacarai",
        industry="cooperativa",
        region="Asuncion",
        source="conciencia",
        email="info@ypacarai.com.py",
        phone="+59521123456",
        website="https://ypacarai.com.py",
        contact_name="Juan Perez",
    )
    fields.update(kwargs)
    lead = Lead(**fields)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


class TestRankingWeights:
    def test_defaults(self):
        w = get_ranking_weights(None)
        assert set(w) == {"relevance", "lead", "opportunity"}
        assert abs(sum(w["lead"].values()) - 1.0) < 0.001

    def test_persist_and_merge(self, db):
        set_ranking_weights(db, {"lead": {"completeness": 0.5}})
        w = get_ranking_weights(db)
        assert w["lead"]["completeness"] == 0.5
        # bloques no tocados conservan defaults
        assert w["lead"]["industry"] == DEFAULT_RANKING_WEIGHTS["lead"]["industry"]
        assert w["relevance"]["geo_match"] == DEFAULT_RANKING_WEIGHTS["relevance"]["geo_match"]

    def test_persist_invalid_block_ignored(self, db):
        set_ranking_weights(db, {"nope": {"x": 1}})
        w = get_ranking_weights(db)
        assert "nope" not in w


class TestDataQuality:
    def test_completa_alta(self, db):
        lead = _lead(db)
        assert data_quality_score(lead) >= 70

    def test_incompleta_baja(self, db):
        lead = _lead(db, email=None, phone=None, website=None, contact_name=None,
                     region=None, industry=None, segment=None, source="otra")
        assert data_quality_score(lead) < 40

    def test_fresca_suma(self, db):
        vieja = _lead(db, company="Vieja SA")
        vieja.created_at = datetime.utcnow() - timedelta(days=400)
        vieja.updated_at = datetime.utcnow() - timedelta(days=400)
        db.commit()
        nueva = _lead(db, company="Nueva SA")
        assert data_quality_score(nueva) > data_quality_score(vieja)


class TestLeadScore:
    def test_independiente_de_query(self, db):
        lead = _lead(db)
        ls1 = lead_score(lead)
        ls2 = lead_score(lead, get_ranking_weights(db))
        assert ls1 == ls2

    def test_industria_valiosa_suma(self, db):
        baja = _lead(db, company="Ferreteria X", industry="comercio")
        alta = _lead(db, company="Cooperativa Y", industry="cooperativa")
        assert lead_score(alta) > lead_score(baja)

    def test_rango(self, db):
        lead = _lead(db, email=None, phone=None, website=None, source="manual")
        assert 0 <= lead_score(lead) <= 100


class TestSearchRelevance:
    def test_category_match(self, db):
        lead = _lead(db, industry="farmacia")
        sq = SearchQuery(category="farmacia")
        assert search_relevance(lead, sq) > 0

    def test_geo_match(self, db):
        lead = _lead(db, region="Ciudad del Este")
        sq = SearchQuery(region="Ciudad del Este")
        assert search_relevance(lead, sq) > 0

    def test_keyword_match(self, db):
        lead = _lead(db, company="Logistica Ruta 6", notes="transporte de cargas")
        sq = SearchQuery(query="empresas logistica")
        assert search_relevance(lead, sq) > 0

    def test_sin_match(self, db):
        lead = _lead(db, company="Panaderia La Central", industry="comercio",
                     region="San Lorenzo")
        sq = SearchQuery(category="distribuidora", region="Ciudad del Este", query="playas de autos")
        assert search_relevance(lead, sq) < 30


class TestOpportunity:
    def test_con_canales_alta(self, db):
        lead = _lead(db)
        assert opportunity_score(lead) >= 60

    def test_sin_canales_baja(self, db):
        lead = _lead(db, email=None, phone=None, website=None, contact_name=None)
        assert opportunity_score(lead) < 40


class TestExplain:
    def test_razones_query(self, db):
        lead = _lead(db, industry="farmacia", region="Asuncion")
        sq = SearchQuery(query="farmacia asuncion", category="farmacia", region="Asuncion")
        reasons = explain(lead, sq)
        assert any("Categoría" in r for r in reasons)
        assert any("Ubicación" in r for r in reasons)
        assert any("Tiene website" in r for r in reasons)
        assert any("Lead score" in r for r in reasons)


class TestAPI:
    def test_detail_tiene_campos_fase4(self, client, auth_headers, db):
        lead = _lead(db)
        res = client.get(f"/api/v1/leads/{lead.id}", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["data_quality"] is not None
        assert data["opportunity_score"] is not None
        assert isinstance(data["reasons"], list) and data["reasons"]

    def test_search_devuelve_relevance(self, client, auth_headers, db):
        _lead(db, industry="farmacia", region="Asuncion")
        res = client.post("/api/v1/leads/search", json={
            "category": "farmacia", "region": "Asuncion",
        }, headers=auth_headers)
        assert res.status_code == 200
        item = res.json()["items"][0]
        assert item["search_relevance"] is not None and item["search_relevance"] > 0

    def test_list_incluye_quality(self, client, auth_headers, db):
        _lead(db)
        res = client.get("/api/v1/leads/", headers=auth_headers)
        assert res.status_code == 200
        item = res.json()["items"][0]
        assert item["data_quality"] is not None
        assert item["opportunity_score"] is not None

    def test_weights_endpoint(self, client, auth_headers):
        res = client.get("/api/v1/leads/ranking/weights", headers=auth_headers)
        assert res.status_code == 200
        assert "relevance" in res.json()

    def test_weights_update_requiere_admin(self, client, auth_headers):
        res = client.put("/api/v1/leads/ranking/weights", json={
            "lead": {"completeness": 0.4},
        }, headers=auth_headers)
        assert res.status_code == 403
