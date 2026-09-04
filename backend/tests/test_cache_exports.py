"""Tests Fase 10 — Cache (spec §36) + Exports (spec §38) + SearchQuery.source."""

import json
import time

import pytest

from app.core.cache import TTLCache, cache_get, cache_set, cache_delete, cache_clear, invalidate_prefix
from app.modules.leadhunter.models import Lead
from app.modules.leadhunter.search import SearchEngine, SearchQuery


@pytest.fixture(autouse=True)
def _clean_cache():
    """El cache de búsquedas es un singleton: limpiar entre tests (las filas
    de test.db se dropean pero el cache quedaría con datos stale)."""
    cache_clear()
    yield
    cache_clear()


def _seed(db, company="Farmacia San Roque", industry="farmacia", region="Asuncion", source="test"):
    lead = Lead(company=company, industry=industry, region=region, source=source, score=50)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


class TestTTLCache:
    def test_set_get(self):
        cache_clear()
        cache_set("a:1", {"x": 1}, ttl=60)
        assert cache_get("a:1") == {"x": 1}

    def test_expira(self):
        c = TTLCache(default_ttl=0)  # TTL 0 = expira al toque
        c.set("k", "v")
        time.sleep(0.01)
        assert c.get("k") is None

    def test_ttl_por_entrada(self):
        c = TTLCache(default_ttl=60)
        c.set("corto", "v", ttl=0)   # expira ya
        c.set("largo", "v", ttl=60)  # no expira
        assert c.get("corto") is None
        assert c.get("largo") == "v"

    def test_delete_y_clear(self):
        cache_clear()
        cache_set("x", 1, ttl=60)
        cache_delete("x")
        assert cache_get("x") is None
        cache_set("y", 2, ttl=60)
        cache_clear()
        assert cache_get("y") is None

    def test_invalidate_prefix(self):
        cache_clear()
        cache_set("search:abc", 1, ttl=60)
        cache_set("search:def", 2, ttl=60)
        cache_set("geo:x", 3, ttl=60)
        invalidate_prefix("search:")
        assert cache_get("search:abc") is None
        assert cache_get("search:def") is None
        assert cache_get("geo:x") == 3


class TestSearchCache:
    def test_segunda_consulta_hit(self, db):
        cache_clear()
        _seed(db)
        engine = SearchEngine()
        sq = SearchQuery(query="farmacia", page_size=10)
        engine.execute(db, sq)
        key = engine._cache_key(sq)
        assert cache_get(key) is not None, "la primera búsqueda debería quedar cacheada"

    def test_invalida_al_crear(self, client, auth_headers, db):
        cache_clear()
        _seed(db)
        engine = SearchEngine()
        sq = SearchQuery(query="farmacia")
        engine.execute(db, sq)
        key = engine._cache_key(sq)
        assert cache_get(key) is not None
        # crear un lead invalida el cache de búsquedas
        res = client.post("/api/v1/leads/", json={"company": "Farmacia Nueva SA", "industry": "farmacia"},
                          headers=auth_headers)
        assert res.status_code == 201
        assert cache_get(key) is None

    def test_search_source_filter(self, db):
        _seed(db, source="overpass")
        _seed(db, company="Manual SA", source="manual")
        res = SearchEngine().execute(db, SearchQuery(source="overpass"))
        assert res.total == 1
        assert res.items[0].source == "overpass"


class TestExportAPI:
    def test_export_csv(self, client, auth_headers, db):
        _seed(db)
        res = client.get("/api/v1/leads/export?format=csv", headers=auth_headers)
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/csv")
        text = res.text
        assert text.startswith("id,company")
        assert "Farmacia San Roque" in text

    def test_export_json(self, client, auth_headers, db):
        _seed(db, company="Exportame JSON SA")
        res = client.get("/api/v1/leads/export?format=json", headers=auth_headers)
        assert res.status_code == 200
        data = json.loads(res.text)
        assert any(i["company"] == "Exportame JSON SA" for i in data)
        assert "opportunity_score" in data[0]

    def test_export_filtros(self, client, auth_headers, db):
        _seed(db, company="Farmacia A", industry="farmacia")
        _seed(db, company="Logistica B", industry="logistica")
        res = client.get("/api/v1/leads/export?format=json&industry=logistica", headers=auth_headers)
        data = json.loads(res.text)
        assert len(data) == 1
        assert data[0]["company"] == "Logistica B"

    def test_export_requiere_auth(self, client):
        res = client.get("/api/v1/leads/export?format=csv")
        assert res.status_code in (401, 403)
