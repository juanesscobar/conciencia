"""Tests API de Search canónico: /search/interpret y /search (aditivos)."""

from app.modules.leadhunter.search import SearchEngine, SearchQuery
from app.modules.leadhunter.models import Lead


def _seed_lead(db, company="Farmacia San Roque", industry="farmacia",
               region="Asuncion", phone=None, website=None, email=None,
               score=50):
    lead = Lead(
        company=company,
        industry=industry,
        region=region,
        phone=phone,
        website=website,
        email=email,
        score=score,
        source="test",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


class TestSearchInterpretAPI:
    def test_interpret_endpoint(self, client, auth_headers):
        res = client.post("/api/v1/leads/search/interpret", json={
            "text": "playas de autos usados en Ciudad del Este",
        }, headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["category"] == "automotriz"
        assert data["country"] == "PY"

    def test_interpret_requires_auth(self, client):
        res = client.post("/api/v1/leads/search/interpret", json={"text": "farmacias"})
        assert res.status_code in (401, 403)


class TestSearchAPI:
    def test_search_filters_by_industry(self, client, auth_headers, db):
        _seed_lead(db, industry="farmacia", region="Asuncion")
        _seed_lead(db, industry="distribuidora", region="Central")
        res = client.post("/api/v1/leads/search", json={
            "industry": "farmacia",
        }, headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["industry"] == "farmacia"

    def test_search_required_fields(self, client, auth_headers, db):
        _seed_lead(db, phone="021123456")
        _seed_lead(db, company="Sin Telefono SRL", industry="comercio")
        res = client.post("/api/v1/leads/search", json={
            "required_fields": ["phone"],
        }, headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["phone"] == "021123456"

    def test_search_region_normalized(self, client, auth_headers, db):
        _seed_lead(db, region="Asunción")
        _seed_lead(db, company="CDE SA", region="Ciudad del Este")
        res = client.post("/api/v1/leads/search", json={
            "region": "Asuncion",  # sin acento
        }, headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["total"] == 1

    def test_search_text_query(self, client, auth_headers, db):
        _seed_lead(db, company="Farmacia San Roque")
        _seed_lead(db, company="Ferreteria El Clavo", industry="construccion")
        res = client.post("/api/v1/leads/search", json={
            "query": "san roque",
        }, headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["total"] == 1
        assert res.json()["items"][0]["company"] == "Farmacia San Roque"

    def test_search_requires_auth(self, client):
        res = client.post("/api/v1/leads/search", json={"query": "x"})
        assert res.status_code in (401, 403)


class TestSearchEngine:
    def test_engine_cursor_pagination(self, db):
        for i in range(5):
            _seed_lead(db, company=f"Empresa {i}", industry="comercio")
        sq = SearchQuery(sort="newest", page_size=2)
        res1 = SearchEngine().execute(db, sq)
        assert len(res1.items) == 2
        assert res1.next_cursor is not None
        res2 = SearchEngine().execute(db, SearchQuery(sort="newest", page_size=2, cursor=res1.next_cursor))
        assert len(res2.items) == 2
        ids1 = {l.id for l in res1.items}
        ids2 = {l.id for l in res2.items}
        assert not ids1 & ids2

    def test_engine_min_score(self, db):
        _seed_lead(db, score=80)
        _seed_lead(db, company="Bajo", score=20)
        sq = SearchQuery(min_score=50)
        res = SearchEngine().execute(db, sq)
        assert res.total == 1
        assert res.items[0].score >= 50
