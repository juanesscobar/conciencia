"""Tests Fase 5 — Búsqueda semántica foundation (spec §14)."""

import os

import numpy as np
import pytest

from app.modules.leadhunter.embeddings import (
    InMemoryBackend,
    simulated_embedding,
    embed_text,
    index_lead,
    semantic_search,
    reset_backend,
)
from app.modules.leadhunter.models import Lead


@pytest.fixture(autouse=True)
def _clean_backend():
    reset_backend()
    yield
    reset_backend()


def _seed(db, company="Farmacia San Roque", industry="farmacia", region="Asuncion", notes=""):
    lead = Lead(company=company, industry=industry, region=region, notes=notes or None,
                source="test", score=50)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


class TestSimulatedEmbedding:
    def test_deterministico(self):
        v1 = simulated_embedding("farmacia san roque asuncion")
        v2 = simulated_embedding("farmacia san roque asuncion")
        assert v1 == v2

    def test_similares_alta_cosine(self):
        a = np.array(simulated_embedding("distribuidora de bebidas"))
        b = np.array(simulated_embedding("distribuidora de bebidas al por mayor"))
        c = np.array(simulated_embedding("playa de autos usados"))
        sim_ab = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
        sim_ac = float(np.dot(a, c) / (np.linalg.norm(a) * np.linalg.norm(c)))
        assert sim_ab > sim_ac

    def test_dim(self):
        assert len(simulated_embedding("x")) == 384

    def test_embed_text_simulado_sin_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        v = embed_text("logistica paraguay")
        assert len(v) == 384


class TestInMemoryBackend:
    def test_upsert_search_orden(self):
        b = InMemoryBackend()
        b.upsert("a", "farmacia", simulated_embedding("farmacia"))
        b.upsert("b", "logistica", simulated_embedding("logistica"))
        hits = b.search(simulated_embedding("farmacia"), top_k=2)
        assert hits[0][0] == "a"
        assert hits[0][1] > hits[1][1]

    def test_count_delete_clear(self):
        b = InMemoryBackend()
        b.upsert("a", "x", simulated_embedding("x"))
        assert b.count() == 1
        b.delete("a")
        assert b.count() == 0
        b.upsert("a", "x", simulated_embedding("x"))
        b.clear()
        assert b.count() == 0


class TestSemanticSearchFunc:
    def test_encuentra_por_semantica(self, db):
        farmacia = _seed(db, company="Farmacia San Roque", industry="farmacia")
        _seed(db, company="Logistica Ruta 6", industry="logistica", notes="transporte de cargas")
        index_lead(db, farmacia)
        for l in db.query(Lead).all():
            index_lead(db, l)
        db.commit()
        hits = semantic_search(db, "farmacias en asuncion", top_k=5)
        assert hits, "debería encontrar algo"
        assert hits[0][0].id == farmacia.id

    def test_top_k_respetado(self, db):
        leads = []
        for i in range(5):
            leads.append(_seed(db, company=f"Comercio {i}", industry="comercio"))
        for l in leads:
            index_lead(db, l)
        db.commit()
        hits = semantic_search(db, "comercio", top_k=3)
        assert len(hits) <= 3

    def test_no_encuentra_si_vacio(self, db):
        hits = semantic_search(db, "cualquier cosa", top_k=5)
        assert hits == []


class TestSemanticAPI:
    def test_disabled_devuelve_501(self, client, auth_headers, monkeypatch):
        monkeypatch.delenv("EMBEDDING_ENABLED", raising=False)
        res = client.post("/api/v1/leads/search/semantic", json={"query": "farmacias"},
                          headers=auth_headers)
        assert res.status_code == 501

    def test_enabled_flujo_completo(self, client, auth_headers, db, monkeypatch):
        monkeypatch.setenv("EMBEDDING_ENABLED", "1")
        farmacia = _seed(db, company="Farmacia San Roque", industry="farmacia")
        _seed(db, company="Logistica Ruta 6", industry="logistica", notes="transporte")

        res = client.post("/api/v1/leads/search/semantic", json={"query": "farmacias", "top_k": 5},
                          headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["backend"] == "memory"
        assert data["simulated"] is True
        assert data["total"] >= 1
        first = data["items"][0]
        assert first["id"] == farmacia.id
        assert first["search_relevance"] is not None
        assert any("semántico" in r for r in first["reasons"])

    def test_status_endpoint(self, client, auth_headers, monkeypatch):
        monkeypatch.setenv("EMBEDDING_ENABLED", "1")
        res = client.get("/api/v1/leads/search/semantic/status", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["enabled"] is True
        assert "indexed" in res.json()

    def test_requiere_auth(self, client):
        res = client.post("/api/v1/leads/search/semantic", json={"query": "x"})
        assert res.status_code in (401, 403)
