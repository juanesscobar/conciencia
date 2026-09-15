"""Tests Fase 11 — E2E final (spec §39/§50/§52).

Flujo completo del test §52:
interpret → filtros → search → ranking → detail → enrich (agente) → lista → export.
Todo lo que toca red (LLM, website) se mockea; el resto es E2E real sobre la API.
"""

import json

from app.adapters.base import DispatchResult
from app.models.agent import Agent, AgentRole, AgentType, AgentStatus, AutonomyLevel, AgentRuntime, AgentProvider
from app.modules.leadhunter.models import Lead


def _seed_agent(db):
    agent = Agent(
        name="ClassifyTest", emoji="🎯", role=AgentRole.BUSINESS_CLASSIFICATION,
        type=AgentType.SYSTEM, status=AgentStatus.IDLE,
        personality="Clasificador.", capabilities=["leads.read"],
        autonomy_level=AutonomyLevel.PREVIEW, runtime=AgentRuntime.GENERIC,
        provider=AgentProvider.DEEPSEEK, model="deepseek-chat",
        config={"permissions": {"allow": ["leads.read", "search.execute"], "deny": ["finance.write"]}},
        health_status="online",
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def _seed_lead(db, **kw):
    fields = dict(company="Auto CDE SRL", industry="automotriz", region="Ciudad del Este",
                  phone="+595981111222", email="ventas@autocde.com.py",
                  website="https://autocde.com.py", source="overpass", score=70)
    fields.update(kw)
    lead = Lead(**fields)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def _mock_agent_dispatch(monkeypatch):
    from app.adapters import registry as registry_mod

    class FakeAdapter:
        def dispatch_task(self, identity, task, context=None):
            return DispatchResult(
                ok=True, status="completed",
                output="1. Categoría: automotriz\n2. Subcategoría: used_car_dealer\n"
                       "3. Lead score: 85\n4. Oportunidad: 90\n5. Calidad: 80\n6. Razones: -",
                model="mock", provider="mock", runtime="generic",
                usage={"total_tokens": 20}, duration_ms=10, simulated=True,
            )

    monkeypatch.setattr(registry_mod, "get_adapter", lambda name: FakeAdapter())


class TestE2EFinal:
    """El test §52: 'playas de autos usados en Ciudad del Este' de punta a punta."""

    def test_flujo_completo_52(self, client, auth_headers, db, monkeypatch):
        _mock_agent_dispatch(monkeypatch)
        # dataset: una automotriz en CDE (matchea) y una farmacia en Asunción (no)
        lead_cde = _seed_lead(db)
        _seed_lead(db, company="Farmacia Central", industry="farmacia", region="Asuncion")

        # 1-2. NL → interpret
        res = client.post("/api/v1/leads/search/interpret",
                          json={"text": "playas de autos usados en Ciudad del Este"},
                          headers=auth_headers)
        assert res.status_code == 200
        sq = res.json()
        assert sq["category"] == "automotriz"
        assert sq["country"] == "PY"

        # 3-4. search con los filtros interpretados → ranking + calidad
        res = client.post("/api/v1/leads/search", json=sq, headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["id"] == lead_cde.id
        assert item["search_relevance"] is not None and item["search_relevance"] > 0
        assert item["data_quality"] is not None
        assert isinstance(item["reasons"], list) and item["reasons"]

        # 5. detail: sources + quality + reasons
        res = client.get(f"/api/v1/leads/{lead_cde.id}", headers=auth_headers)
        assert res.status_code == 200
        detail = res.json()
        assert detail["source"] == "overpass"
        assert detail["opportunity_score"] is not None
        assert detail["data_quality"] is not None
        assert detail["reasons"]

        # 6. enrich con agente (LLM mockeado)
        _seed_agent(db)
        res = client.post(f"/api/v1/leads/{lead_cde.id}/enrich/agent",
                          json={"action": "classify"}, headers=auth_headers)
        assert res.status_code == 200
        assert "output" in res.json()
        db.refresh(lead_cde)
        assert lead_cde.meta["agents"]["classify"]["output"]

        # 7. lista guardada + agregar lead
        res = client.post("/api/v1/leads/lists", json={"name": "Autos CDE"},
                          headers=auth_headers)
        assert res.status_code == 201
        list_id = res.json()["id"]
        res = client.post(f"/api/v1/leads/lists/{list_id}/leads",
                          json={"lead_id": lead_cde.id}, headers=auth_headers)
        assert res.status_code == 200
        res = client.get(f"/api/v1/leads/lists/{list_id}/leads", headers=auth_headers)
        assert res.status_code == 200
        assert any(l["id"] == lead_cde.id for l in res.json()["leads"])

        # 8. export JSON con el mismo criterio
        res = client.get("/api/v1/leads/export?format=json&industry=automotriz",
                         headers=auth_headers)
        assert res.status_code == 200
        exported = json.loads(res.text)
        assert any(e["id"] == lead_cde.id for e in exported)
        assert exported[0]["opportunity_score"] is not None
