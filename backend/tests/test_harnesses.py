"""Tests Fase G — Harness Layer: contratos versionados y reutilizables.

DoD Phase G: "Harnesses can be versioned and reused across Missions."
"""

import json

import pytest

from app.adapters.base import DispatchResult
from app.adapters.generic import GenericAgentAdapter
from app.models.agent import Agent, AgentProvider, AgentRole, AgentRuntime
from app.services import harness_service


def _seed_agent(db, name="ResearchBot", caps=None, runtime=AgentRuntime.GENERIC):
    a = Agent(
        name=name,
        role=AgentRole.RD,
        capabilities=caps or ["research"],
        runtime=runtime,
        provider=AgentProvider.DEEPSEEK,
        status="idle",
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _json_harness_spec(required_fields=("summary", "findings"), instructions="Eres un investigador."):
    return {
        "instructions": instructions,
        "context": {"template": "Objetivo: {objective}\nProyecto: {project_name}", "max_chars": 2000},
        "tools": {"allow": ["web_search", "read"], "deny": ["write"]},
        "guardrails": ["no_network", "max_tokens_2000"],
        "runtime": {"default": "generic", "allowed": ["generic", "claude_code"]},
        "output_contract": {"format": "json", "required_fields": list(required_fields), "description": "hallazgos"},
    }


# ---------------------------------------------------------------------------
# CRUD + versionado
# ---------------------------------------------------------------------------

def test_harness_crud_y_versionado(db):
    h = harness_service.create_harness(
        db, name="Research Harness", spec=_json_harness_spec(), description="para research"
    )
    assert h.status == "draft"
    assert h.version == "1.0.0"
    assert h.spec["output_contract"]["required_fields"] == ["summary", "findings"]

    # update + version bump → snapshot al historial
    patch = {"spec": {**h.spec, "guardrails": ["no_network"]}}
    h = harness_service.update_harness(db, h, patch=patch, new_version="2.0.0", changes="guardrails ajustados")
    assert h.version == "2.0.0"
    assert len(h.versions) == 1
    assert h.versions[0]["version"] == "1.0.0"
    assert h.versions[0]["changes"] == "guardrails ajustados"

    # no permite version actual
    with pytest.raises(ValueError):
        harness_service.update_harness(db, h, patch={}, new_version="2.0.0")

    # status
    h = harness_service.set_status(db, h, "active")
    assert h.status == "active"
    assert len(harness_service.list_harnesses(db, status="active")) == 1

    harness_service.delete_harness(db, h)
    assert harness_service.list_harnesses(db) == []


def test_harness_api_crud(client, auth_headers):
    res = client.post("/api/v1/harnesses/", headers=auth_headers, json={
        "name": "Research Harness",
        "spec": _json_harness_spec(),
    })
    assert res.status_code == 201, res.text
    h = res.json()
    assert h["status"] == "draft"

    res = client.get("/api/v1/harnesses/", headers=auth_headers)
    assert len(res.json()) == 1

    res = client.patch(f"/api/v1/harnesses/{h['id']}", headers=auth_headers,
                       json={"new_version": "1.1.0", "changes": "fix", "spec": {"instructions": "nueva"}})
    assert res.status_code == 200
    assert res.json()["version"] == "1.1.0"
    assert res.json()["spec"]["instructions"] == "nueva"
    assert len(res.json()["versions"]) == 1

    res = client.post(f"/api/v1/harnesses/{h['id']}/activate", headers=auth_headers)
    assert res.json()["status"] == "active"

    # solo activos válidos para misiones (lo valida mission create)
    res = client.post("/api/v1/missions/", headers=auth_headers, json={
        "name": "M", "objective": "O", "harness_id": h["id"],
    })
    assert res.status_code == 201, res.text
    assert res.json()["harness_id"] == h["id"]

    # archive → ya no se puede usar
    client.post(f"/api/v1/harnesses/{h['id']}/archive", headers=auth_headers)
    res = client.post("/api/v1/missions/", headers=auth_headers, json={
        "name": "M2", "objective": "O", "harness_id": h["id"],
    })
    assert res.status_code == 400


def test_harness_validate_endpoint(client, auth_headers):
    h = client.post("/api/v1/harnesses/", headers=auth_headers, json={
        "name": "Json Harness", "spec": _json_harness_spec(),
    }).json()
    ok = client.post(f"/api/v1/harnesses/{h['id']}/validate", headers=auth_headers,
                     json={"output": '{"summary": "x", "findings": ["a"]}'}).json()
    assert ok["ok"] is True
    bad = client.post(f"/api/v1/harnesses/{h['id']}/validate", headers=auth_headers,
                      json={"output": "no json"}).json()
    assert bad["ok"] is False
    assert any("JSON" in e for e in bad["errors"])


# ---------------------------------------------------------------------------
# Aplicación del harness
# ---------------------------------------------------------------------------

def test_apply_harness_instructions_y_guardrails(db):
    h = harness_service.create_harness(db, name="H", spec=_json_harness_spec())
    a = _seed_agent(db)
    patch, errors = harness_service.apply_harness(
        h, a, mission_context={"objective": "investigar X", "project_name": "conciencia"}
    )
    assert errors == []
    assert "Eres un investigador." in patch["system_prompt"]
    assert "Objetivo: investigar X" in patch["context"]
    assert "Proyecto: conciencia" in patch["context"]
    cfg = patch["config"]["harness"]
    assert cfg["harness_name"] == "H"
    assert cfg["tools"]["allow"] == ["web_search", "read"]
    assert "no_network" in cfg["guardrails"]
    assert cfg["output_contract"]["format"] == "json"


def test_apply_harness_runtime_guardrail(db):
    h = harness_service.create_harness(db, name="H", spec={
        "runtime": {"allowed": ["claude_code"]},
    })
    a = _seed_agent(db, runtime=AgentRuntime.GENERIC)  # generic NO permitido
    patch, errors = harness_service.apply_harness(h, a, mission_context={})
    assert errors and "no permitido" in errors[0]
    assert patch == {}


def test_validate_output_contract(db):
    h = harness_service.create_harness(db, name="H", spec=_json_harness_spec())
    ok, errors = harness_service.validate_output(h, '{"summary": "s", "findings": []}')
    assert ok is True and errors == []

    ok, errors = harness_service.validate_output(h, '{"summary": "s"}')
    assert ok is False
    assert any("findings" in e for e in errors)

    ok, errors = harness_service.validate_output(h, "texto plano")
    assert ok is False


def test_validate_output_markdown_y_reglas(db):
    h = harness_service.create_harness(db, name="H", spec={
        "output_contract": {"format": "markdown", "required_fields": []},
        "validation": {"output": {"min_length": 10, "required_substring": "conclusión"}},
    })
    ok, errors = harness_service.validate_output(h, "# Resumen\n\nconclusión: listo")
    assert ok is True, errors
    ok, errors = harness_service.validate_output(h, "corto")
    assert ok is False


# ---------------------------------------------------------------------------
# Workflow + misión con harness
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_dispatch(monkeypatch):
    calls = []

    def dispatch(self, identity, task, context=None):
        calls.append({
            "agent_id": identity.agent_id,
            "system_prompt": identity.system_prompt,
            "context": context,
            "config": identity.config,
        })
        return DispatchResult(
            ok=True, status="completed",
            output='{"summary": "ok", "findings": ["a"]}',
            runtime="generic", provider=identity.provider,
            usage={"cost_estimate_usd": 0.01}, duration_ms=5,
        )

    monkeypatch.setattr(GenericAgentAdapter, "dispatch_task", dispatch)
    return calls


def _create_wf(client, auth_headers, steps, name="wf-harness"):
    res = client.post("/api/v1/workflows/", headers=auth_headers, json={"name": name, "steps": steps})
    assert res.status_code == 201, res.text
    return res.json()


def test_workflow_step_con_harness_aplica_instrucciones(client, auth_headers, db, fake_dispatch):
    h = harness_service.create_harness(db, name="H", spec=_json_harness_spec())
    harness_service.set_status(db, h, "active")
    a = _seed_agent(db)

    wf = _create_wf(client, auth_headers, [
        {"name": "research", "task": "investigar", "agent_id": str(a.id), "harness_id": str(h.id)},
    ])
    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    assert run["status"] == "completed"
    call = fake_dispatch[0]
    assert "Eres un investigador." in call["system_prompt"]
    assert call["config"]["harness"]["harness_name"] == "H"
    assert call["config"]["harness"]["harness_version"] == "1.0.0"


def test_workflow_output_contract_falla_la_validacion(client, auth_headers, db, fake_dispatch, monkeypatch):
    h = harness_service.create_harness(db, name="H", spec=_json_harness_spec())
    harness_service.set_status(db, h, "active")
    a = _seed_agent(db)

    # output sin el campo requerido "findings"
    def bad_dispatch(self, identity, task, context=None):
        return DispatchResult(ok=True, status="completed", output='{"summary": "solo"}',
                              runtime="generic", provider="deepseek", usage={"cost_estimate_usd": 0.01}, duration_ms=5)

    monkeypatch.setattr(GenericAgentAdapter, "dispatch_task", bad_dispatch)

    wf = _create_wf(client, auth_headers, [
        {"name": "research", "task": "investigar", "agent_id": str(a.id), "harness_id": str(h.id)},
    ])
    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    assert run["status"] == "failed"
    assert "validación de harness" in run["error"]
    assert "findings" in run["error"]


def test_workflow_harness_runtime_guardrail_bloquea(client, auth_headers, db, fake_dispatch):
    h = harness_service.create_harness(db, name="H", spec={"runtime": {"allowed": ["claude_code"]}})
    harness_service.set_status(db, h, "active")
    a = _seed_agent(db, runtime=AgentRuntime.GENERIC)  # generic no permitido

    wf = _create_wf(client, auth_headers, [
        {"name": "research", "task": "investigar", "agent_id": str(a.id), "harness_id": str(h.id)},
    ])
    run = client.post(f"/api/v1/workflows/{wf['id']}/run", headers=auth_headers).json()
    assert run["status"] == "failed"
    assert "no permitido por harness" in run["error"]


def test_mission_agent_pool_preferido_en_empate(client, auth_headers, db, fake_dispatch):
    """Los agentes que la misión seleccionó se prefieren en el matching por
    capabilities aunque haya empate de score con el registry global."""
    a1 = Agent(
        name="PoolAgent", role=AgentRole.RD, capabilities=["research"],
        runtime=AgentRuntime.GENERIC, provider=AgentProvider.DEEPSEEK, status="idle",
    )
    a2 = Agent(
        name="GlobalTie", role=AgentRole.RD, capabilities=["research"],
        runtime=AgentRuntime.GENERIC, provider=AgentProvider.DEEPSEEK, status="idle",
    )
    db.add_all([a1, a2])  # a2 primero en el registry → ganaría el empate global
    db.commit()
    db.refresh(a1)
    db.refresh(a2)

    res = client.post("/api/v1/missions/", headers=auth_headers, json={
        "name": "M", "objective": "investigar", "type": "research",
        "agent_ids": [str(a1.id)],
    })
    m = res.json()
    client.post(f"/api/v1/missions/{m['id']}/plan", headers=auth_headers)
    run = client.post(f"/api/v1/missions/{m['id']}/run", headers=auth_headers).json()
    assert run["status"] == "waiting_approval"
    assert fake_dispatch[-1]["agent_id"] == str(a1.id)


def test_mission_con_harness_reusa_contrato(client, auth_headers, db, fake_dispatch):
    """DoD: harness versionado reutilizado en una misión (instructions + contexto)."""
    h = harness_service.create_harness(db, name="Research Harness", spec=_json_harness_spec())
    harness_service.set_status(db, h, "active")
    a = _seed_agent(db)

    res = client.post("/api/v1/missions/", headers=auth_headers, json={
        "name": "Misión con harness",
        "objective": "investigar el mercado de IA",
        "type": "research",
        "harness_id": str(h.id),
        "agent_ids": [str(a.id)],
    })
    m = res.json()
    assert m["harness_id"] == str(h.id)

    client.post(f"/api/v1/missions/{m['id']}/plan", headers=auth_headers)
    run = client.post(f"/api/v1/missions/{m['id']}/run", headers=auth_headers).json()
    assert run["status"] == "waiting_approval"  # research: 2 steps + approval gate

    call = fake_dispatch[-1]
    assert "Eres un investigador." in call["system_prompt"]
    assert "Objetivo: investigar el mercado de IA" in call["context"]
    assert call["config"]["harness"]["harness_id"] == str(h.id)
