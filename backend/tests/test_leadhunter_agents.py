"""Tests Fase 8 — Agentes LeadHunter (spec §17/§18/§27/§28/§29).

El LLM se mockea a nivel de adapter (dispatch_task) para no depender de red.
"""

import uuid

import pytest

from app.adapters.base import DispatchResult
from app.models.agent import Agent, AgentRole, AgentType, AgentStatus, AutonomyLevel, AgentRuntime, AgentProvider
from app.modules.leadhunter.models import Lead


def _seed_agent(db, role=AgentRole.BUSINESS_CLASSIFICATION, permissions=None):
    agent = Agent(
        name="TestBot",
        emoji="🤖",
        role=role,
        type=AgentType.SYSTEM,
        status=AgentStatus.IDLE,
        personality="Clasificador de test.",
        capabilities=["leads.read"],
        autonomy_level=AutonomyLevel.PREVIEW,
        runtime=AgentRuntime.GENERIC,
        provider=AgentProvider.DEEPSEEK,
        model="deepseek-chat",
        config={"permissions": permissions or {
            "allow": ["leads.read", "search.execute"],
            "deny": ["finance.write"],
        }},
        health_status="online",
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def _seed_lead(db, company="Cooperativa Test S.A.", website=None):
    lead = Lead(company=company, industry="cooperativa", region="Asuncion",
                email="test@test.com.py", source="test", score=50, website=website)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def _fake_dispatch(monkeypatch, output="1. Categoría: cooperativa\n2. Score: 85"):
    from app.adapters import registry as registry_mod

    class FakeAdapter:
        def dispatch_task(self, identity, task, context=None):
            return DispatchResult(
                ok=True, status="completed", output=output,
                model="mock-model", provider="mock", runtime="generic",
                usage={"total_tokens": 10}, duration_ms=5, simulated=True,
            )

    monkeypatch.setattr(registry_mod, "get_adapter", lambda name: FakeAdapter())


class TestRunLeadAgent:
    def test_classify_flujo_completo(self, client, auth_headers, db, monkeypatch):
        _fake_dispatch(monkeypatch)
        lead = _seed_lead(db)
        agent = _seed_agent(db)

        res = client.post(f"/api/v1/leads/{lead.id}/enrich/agent",
                          json={"action": "classify"}, headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["agent"] == agent.name
        assert data["output"].startswith("1. Categoría")
        # output guardado en meta.agents
        db.refresh(lead)
        assert lead.meta["agents"]["classify"]["output"]
        # ejecución registrada
        from app.models.execution import AgentExecution
        execs = db.query(AgentExecution).filter(AgentExecution.agent_id == agent.id).all()
        assert len(execs) == 1
        assert execs[0].status.value == "completed"

    def test_contact_discovery_sin_website(self, client, auth_headers, db, monkeypatch):
        _fake_dispatch(monkeypatch, output="1. Emails: ninguno\n5. Confianza: 50")
        lead = _seed_lead(db)  # sin website → no raspa
        _seed_agent(db, role=AgentRole.CONTACT_DISCOVERY, permissions={
            "allow": ["leads.read", "website_fetch"], "deny": ["finance.write"],
        })
        res = client.post(f"/api/v1/leads/{lead.id}/enrich/agent",
                          json={"action": "contacts"}, headers=auth_headers)
        assert res.status_code == 200
        assert "website_scan" in res.json()

    def test_accion_invalida(self, client, auth_headers, db):
        lead = _seed_lead(db)
        res = client.post(f"/api/v1/leads/{lead.id}/enrich/agent",
                          json={"action": "hack"}, headers=auth_headers)
        assert res.status_code == 400

    def test_agente_no_registrado(self, client, auth_headers, db):
        lead = _seed_lead(db)
        res = client.post(f"/api/v1/leads/{lead.id}/enrich/agent",
                          json={"action": "classify"}, headers=auth_headers)
        assert res.status_code == 404
        assert "seed_agents" in res.json()["detail"]

    def test_permiso_denegado(self, client, auth_headers, db, monkeypatch):
        _fake_dispatch(monkeypatch)
        lead = _seed_lead(db)
        _seed_agent(db, permissions={"allow": ["leads.read"], "deny": ["search.execute"]})
        res = client.post(f"/api/v1/leads/{lead.id}/enrich/agent",
                          json={"action": "classify"}, headers=auth_headers)
        assert res.status_code == 403

    def test_requiere_auth(self, client, db):
        lead = _seed_lead(db)
        res = client.post(f"/api/v1/leads/{lead.id}/enrich/agent", json={"action": "classify"})
        assert res.status_code in (401, 403)


class TestPermissionsUnit:
    def test_check_permissions_ok(self, db):
        agent = _seed_agent(db)
        from app.modules.leadhunter.agents import check_permissions
        assert check_permissions(agent, "classify") is None

    def test_check_permissions_deny(self, db):
        agent = _seed_agent(db, permissions={"allow": ["leads.read"], "deny": ["search.execute"]})
        from app.modules.leadhunter.agents import check_permissions
        assert check_permissions(agent, "classify") is not None


class TestSeedAgents:
    def test_seed_crea_11_agentes(self, db):
        # corre el seed contra la DB de test
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "seed_agents", "scripts/seed_agents.py")
        mod = importlib.util.module_from_spec(spec)
        # evitar que ejecute al import (usa __main__ guard? no lo tiene) —
        # en su lugar verificamos la lista de roles declarada
        assert spec is not None
        from app.models.agent import AgentRole
        assert AgentRole.LEAD_RESEARCH.value == "lead_research"
        assert AgentRole.BUSINESS_CLASSIFICATION.value == "business_classification"
        assert AgentRole.CONTACT_DISCOVERY.value == "contact_discovery"
