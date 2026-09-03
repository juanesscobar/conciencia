"""Tests Fase I — Signals + Evidence: hallazgos trazables de misiones.

DoD Phase I: "Mission findings can generate traceable Signals with Evidence."
"""

import pytest

from app.adapters.base import DispatchResult
from app.adapters.generic import GenericAgentAdapter
from app.models.agent import Agent, AgentProvider, AgentRole, AgentRuntime
from app.models.mission import Mission
from app.services import signal_service


def _seed_agent(db):
    a = Agent(name="ResearchBot", role=AgentRole.RD, capabilities=["research"],
              runtime=AgentRuntime.GENERIC, provider=AgentProvider.DEEPSEEK, status="idle")
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _create_mission(client, auth_headers, agent_id, type="research", objective="investigar X"):
    res = client.post("/api/v1/missions/", headers=auth_headers, json={
        "name": "Misión señales", "objective": objective, "type": type,
        "agent_ids": [agent_id],
    })
    return res.json()


# ---------------------------------------------------------------------------
# Parsing de marcadores
# ---------------------------------------------------------------------------

def test_extract_from_output_marcadores():
    output = (
        "## Resultados\n"
        "SIGNAL: risk| Mercado saturado | Alta competencia en refrigerado\n"
        "EVIDENCE: competidores con flota propia en Asunción\n"
        "EVIDENCE: https://ejemplo.com/mercado\n"
        "SIGNAL: oportunidad\n"
        "SIGNAL: insight| El backhaul de vehículos es la oportunidad | vía Chile\n"
    )
    signals = signal_service.extract_from_output(output)
    assert len(signals) == 3

    s0 = signals[0]
    assert s0["type"] == "risk"
    assert s0["title"] == "Mercado saturado"
    assert s0["summary"] == "Alta competencia en refrigerado"
    assert len(s0["evidences"]) == 2
    assert s0["evidences"][0]["content"] == "competidores con flota propia en Asunción"

    assert signals[1]["type"] == "finding"
    assert signals[1]["title"] == "oportunidad"
    assert signals[1]["evidences"] == []

    s2 = signals[2]
    assert s2["type"] == "insight"
    assert s2["title"] == "El backhaul de vehículos es la oportunidad"


def test_extract_from_output_sin_marcadores():
    assert signal_service.extract_from_output("informe normal sin señales") == []
    assert signal_service.extract_from_output("") == []


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

def test_create_signal_con_evidencia_vincula_mission(db):
    from app.services import mission_service

    a = _seed_agent(db)
    m = mission_service.create_mission(db, name="M", objective="O", agent_ids=[str(a.id)])
    sig = signal_service.create_signal(
        db,
        mission_id=str(m.id),
        title="Riesgo detectado",
        type="risk",
        summary="detalle",
        evidences=[{"kind": "quote", "content": "evidencia A"}, {"kind": "url", "content": "https://x.com"}],
    )
    assert sig.status == "new"
    assert len(sig.evidences) == 2
    # trazabilidad global: la misión agrega los evidence ids
    db.refresh(m)
    assert len(m.evidence_ids or []) == 2

    # add evidence después
    signal_service.add_evidence(db, sig, kind="quote", content="más evidencia")
    db.refresh(m)
    assert len(m.evidence_ids or []) == 3

    # status
    signal_service.update_signal_status(db, sig, "acknowledged")
    assert sig.status == "acknowledged"
    with pytest.raises(ValueError):
        signal_service.update_signal_status(db, sig, "no-existe")


def test_create_signal_valida_tipo_y_mision(db):
    with pytest.raises(ValueError):
        signal_service.create_signal(db, mission_id="00000000-0000-0000-0000-000000000000",
                                     title="X", type="nope")
    with pytest.raises(ValueError):
        signal_service.create_signal(db, mission_id="00000000-0000-0000-0000-000000000000",
                                     title="X")


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

def test_signals_api_crud(client, auth_headers, db):
    a = _seed_agent(db)
    m = client.post("/api/v1/missions/", headers=auth_headers, json={
        "name": "M", "objective": "O", "agent_ids": [str(a.id)],
    }).json()

    res = client.post("/api/v1/signals/", headers=auth_headers, json={
        "mission_id": m["id"], "title": "Hallazgo 1", "type": "insight",
        "summary": "resumen", "evidences": [{"kind": "quote", "content": "cita"}],
    })
    assert res.status_code == 201, res.text
    s = res.json()
    assert s["type"] == "insight"
    assert len(s["evidence"]) == 1

    res = client.get(f"/api/v1/signals/{s['id']}", headers=auth_headers)
    assert res.json()["title"] == "Hallazgo 1"

    res = client.get(f"/api/v1/signals/?mission_id={m['id']}", headers=auth_headers)
    assert len(res.json()) == 1

    res = client.patch(f"/api/v1/signals/{s['id']}", headers=auth_headers, json={"status": "dismissed"})
    assert res.json()["status"] == "dismissed"

    res = client.post(f"/api/v1/signals/{s['id']}/evidence", headers=auth_headers,
                      json={"kind": "url", "content": "https://x.com", "source": "web"})
    assert len(res.json()["evidence"]) == 2

    res = client.delete(f"/api/v1/signals/{s['id']}", headers=auth_headers)
    assert res.status_code == 204
    res = client.get(f"/api/v1/signals/{s['id']}", headers=auth_headers)
    assert res.status_code == 404
    mission = client.get(f"/api/v1/missions/{m['id']}", headers=auth_headers).json()
    assert mission["evidence_ids"] == []


def test_signals_api_extract_desde_mission(client, auth_headers, db, fake_dispatch_con_signals):
    a = _seed_agent(db)
    m = _create_mission(client, auth_headers, str(a.id), type="research")

    client.post(f"/api/v1/missions/{m['id']}/plan", headers=auth_headers)
    client.post(f"/api/v1/missions/{m['id']}/run", headers=auth_headers)

    res = client.post("/api/v1/signals/extract", headers=auth_headers, json={"mission_id": m["id"]})
    assert res.status_code == 200, res.text
    signals = res.json()
    assert len(signals) == 2  # una por step (research + synthesis)
    assert {s["type"] for s in signals} == {"risk", "opportunity"}
    # trazabilidad de origen
    assert all(s["source_step"] in ("research", "synthesis") for s in signals)
    assert all(s["agent_name"] == "ResearchBot" for s in signals)
    # evidence vinculada
    risk = next(s for s in signals if s["type"] == "risk")
    assert risk["evidence"][0]["content"] == "competidores con flota en Asunción"

    # la misión acumuló evidence_ids (el risk tiene evidencia vinculada)
    res = client.get(f"/api/v1/missions/{m['id']}", headers=auth_headers)
    assert len(res.json()["evidence_ids"]) >= 1

    # Repetir extraction sobre el mismo WorkflowRun es idempotente.
    again = client.post(
        "/api/v1/signals/extract", headers=auth_headers, json={"mission_id": m["id"]}
    )
    assert again.status_code == 200
    assert again.json() == []


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_dispatch_con_signals(monkeypatch):
    """Los outputs de los steps incluyen marcadores SIGNAL:/EVIDENCE:."""
    calls = {"n": 0}

    def dispatch(self, identity, task, context=None):
        calls["n"] += 1
        if calls["n"] == 1:  # step research
            output = ("# Análisis\n"
                      "SIGNAL: risk| Mercado saturado | Alta competencia\n"
                      "EVIDENCE: competidores con flota en Asunción\n")
        else:  # step synthesis
            output = "SIGNAL: opportunity| Backhaul vía Chile | aprovechar ruta de importación"
        return DispatchResult(ok=True, status="completed", output=output,
                              runtime="generic", provider="deepseek", model="deepseek-chat",
                              usage={"prompt_tokens": 10, "completion_tokens": 5,
                                     "total_tokens": 15, "cost_estimate_usd": 0.001},
                              duration_ms=5)

    monkeypatch.setattr(GenericAgentAdapter, "dispatch_task", dispatch)
