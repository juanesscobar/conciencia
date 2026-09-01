"""Tests Fase J — Context Packs: retrieval eficiente y acotado.

DoD Phase J: "Agents receive relevant context without loading unnecessary
project data."
"""

import pytest

from app.adapters.base import DispatchResult
from app.adapters.generic import GenericAgentAdapter
from app.models.agent import Agent, AgentProvider, AgentRole, AgentRuntime
from app.models.context_pack import ContextPack
from app.services import context_retrieval


def _seed_pack(db, title="Pack Logística", content=None, project_id=None):
    pack = ContextPack(
        title=title,
        project_id=project_id,
        target="json",
        content=content or {
            "summary": "Mercado de logística refrigerada en Paraguay",
            "competitors": ["Cerka", "Rutazo"],
            "regulatory": "DINATRAN habilitación",
        },
    )
    db.add(pack)
    db.commit()
    db.refresh(pack)
    return pack


# ---------------------------------------------------------------------------
# Retrieval (scoring por keywords)
# ---------------------------------------------------------------------------

def test_retrieve_rankea_por_relevancia(db):
    _seed_pack(db, title="Pack Logística", content={"summary": "logística refrigerada", "x": "y"})
    _seed_pack(db, title="Pack Finanzas", content={"summary": "presupuestos y costos", "x": "y"})

    # solo los packs con match rankean (sin match → excluidos, no cargados)
    packs = context_retrieval.retrieve_packs(db, query="logística refrigerada en Paraguay")
    assert len(packs) == 1
    assert packs[0]["title"] == "Pack Logística"
    assert "logística" in packs[0]["matched_terms"] or "refrigerada" in packs[0]["matched_terms"]

    # query de otro dominio → rankea el pack financiero
    packs = context_retrieval.retrieve_packs(db, query="presupuesto anual de costos")
    assert len(packs) == 1
    assert packs[0]["title"] == "Pack Finanzas"


def test_retrieve_filtra_por_proyecto(db):
    _seed_pack(db, title="Pack Logística", project_id="proj-a")
    _seed_pack(db, title="Pack Logística 2", project_id="proj-b")

    packs = context_retrieval.retrieve_packs(db, query="logística", project_id="proj-a")
    assert len(packs) == 1
    assert packs[0]["project_id"] == "proj-a"


def test_retrieve_sin_match_no_devuelve_nada(db):
    _seed_pack(db, title="Pack Logística")
    assert context_retrieval.retrieve_packs(db, query="cosmología cuántica") == []
    assert context_retrieval.retrieve_packs(db, query="") == []


# ---------------------------------------------------------------------------
# Ensamblado acotado
# ---------------------------------------------------------------------------

def test_assemble_acota_y_selecciona(db):
    _seed_pack(db, title="Pack Logística", content={"summary": "logística refrigerada", "detalle": "x" * 5000})
    _seed_pack(db, title="Pack Finanzas", content={"summary": "presupuestos"})

    result = context_retrieval.assemble_context(
        db, query="logística refrigerada", limit=2, max_chars=6000
    )
    assert result["packs"], "debe seleccionar el pack relevante"
    assert result["packs"][0]["title"] == "Pack Logística"
    # acotado: nunca supera el presupuesto (más overhead de headers)
    assert result["total_chars"] <= 6000 + 200
    assert "logística refrigerada" in result["context"]

    # límite estricto → truncado
    tiny = context_retrieval.assemble_context(db, query="logística", limit=1, max_chars=50)
    assert tiny["total_chars"] <= 250  # header + body acotado por pack


def test_context_for_mission_pack_explicito_vs_retrieval(db):
    explicit = _seed_pack(db, title="Pack Específico", content={"summary": "contexto fijo"})
    other = _seed_pack(db, title="Pack Logística", content={"summary": "logística refrigerada"})

    # pack explícito gana
    text, packs = context_retrieval.context_for_mission(
        db, objective="logística refrigerada", context_pack_id=str(explicit.id)
    )
    assert packs[0]["pack_id"] == str(explicit.id)
    assert "contexto fijo" in text

    # sin pack explícito → retrieval por objetivo
    text, packs = context_retrieval.context_for_mission(
        db, objective="logística refrigerada", context_pack_id=None
    )
    assert packs and packs[0]["pack_id"] == str(other.id)
    assert "logística refrigerada" in text

    # sin query ni pack → vacío
    text, packs = context_retrieval.context_for_mission(db, objective="")
    assert text == "" and packs == []


# ---------------------------------------------------------------------------
# Integración con misión + harness
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_dispatch(monkeypatch):
    calls = []

    def dispatch(self, identity, task, context=None):
        calls.append({"context": context, "system_prompt": identity.system_prompt})
        return DispatchResult(ok=True, status="completed", output="ok",
                              runtime="generic", provider="deepseek", model="deepseek-chat",
                              usage={"prompt_tokens": 5, "completion_tokens": 3,
                                     "total_tokens": 8, "cost_estimate_usd": 0.0001},
                              duration_ms=2)

    monkeypatch.setattr(GenericAgentAdapter, "dispatch_task", dispatch)
    return calls


def test_mission_con_harness_recibe_contexto_relevante(client, auth_headers, db, fake_dispatch):
    """El harness con template {context_pack} recibe el pack relevante al objetivo."""
    from app.services import harness_service

    _seed_pack(db, title="Pack Logística", content={"summary": "Mercado de logística refrigerada en Paraguay"})
    harness = harness_service.create_harness(db, name="H", spec={
        "instructions": "Eres investigador. Objetivo: {objective}",
        "context": {"template": "## Contexto\n{context_pack}", "max_chars": 4000},
    })
    harness_service.set_status(db, harness, "active")

    a = Agent(name="ResearchBot", role=AgentRole.RD, capabilities=["research"],
              runtime=AgentRuntime.GENERIC, provider=AgentProvider.DEEPSEEK, status="idle")
    db.add(a)
    db.commit()
    db.refresh(a)

    res = client.post("/api/v1/missions/", headers=auth_headers, json={
        "name": "M", "objective": "investigar logística refrigerada en Paraguay",
        "type": "research", "harness_id": str(harness.id), "agent_ids": [str(a.id)],
    })
    m = res.json()
    client.post(f"/api/v1/missions/{m['id']}/plan", headers=auth_headers)
    client.post(f"/api/v1/missions/{m['id']}/run", headers=auth_headers)

    assert fake_dispatch, "debe haber dispatch"
    ctx = fake_dispatch[-1]["context"] or ""
    assert "Mercado de logística refrigerada" in ctx  # pack relevante por retrieval
    assert "## Contexto" in ctx


def test_mission_con_context_pack_id_explicito(client, auth_headers, db, fake_dispatch):
    """La misión con context_pack_id usa ese pack (no retrieval)."""
    from app.services import harness_service

    pack = _seed_pack(db, title="Pack Fijo", content={"summary": "contexto canónico fijo"})
    harness = harness_service.create_harness(db, name="H", spec={
        "context": {"template": "{context_pack}", "max_chars": 4000},
    })
    harness_service.set_status(db, harness, "active")

    a = Agent(name="ResearchBot", role=AgentRole.RD, capabilities=["research"],
              runtime=AgentRuntime.GENERIC, provider=AgentProvider.DEEPSEEK, status="idle")
    db.add(a)
    db.commit()
    db.refresh(a)

    res = client.post("/api/v1/missions/", headers=auth_headers, json={
        "name": "M", "objective": "investigar otra cosa totalmente distinta",
        "type": "research", "harness_id": str(harness.id),
        "context_pack_id": str(pack.id), "agent_ids": [str(a.id)],
    })
    m = res.json()
    assert m["context_pack_id"] == str(pack.id)
    client.post(f"/api/v1/missions/{m['id']}/plan", headers=auth_headers)
    client.post(f"/api/v1/missions/{m['id']}/run", headers=auth_headers)

    ctx = fake_dispatch[-1]["context"] or ""
    assert "contexto canónico fijo" in ctx


def test_context_packs_api_retrieve_assemble(client, auth_headers, db):
    _seed_pack(db, title="Pack Logística", content={"summary": "logística refrigerada"})
    _seed_pack(db, title="Pack Finanzas", content={"summary": "presupuestos"})

    res = client.get("/api/v1/context-packs/retrieve?query=logística refrigerada", headers=auth_headers)
    assert res.status_code == 200
    packs = res.json()
    assert packs[0]["title"] == "Pack Logística"

    res = client.post("/api/v1/context-packs/assemble", headers=auth_headers, json={
        "query": "logística refrigerada", "limit": 2, "max_chars": 4000,
    })
    assert res.status_code == 200
    body = res.json()
    assert body["packs"][0]["title"] == "Pack Logística"
    assert "logística refrigerada" in body["context"]
    assert body["total_chars"] <= 4000 + 200
