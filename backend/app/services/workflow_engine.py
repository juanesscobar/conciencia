"""Workflow Engine — ejecuta steps declarativos (secuenciales o en paralelo).

Cada step puede:
- requerir un agente (por id) o capabilities (matching posterior)
- ser un BLOQUE PARALELO: `{"name": ..., "parallel": true, "steps": [...]}`
  → los children corren concurrentemente (fan-out) y el bloque espera a todos
  (fan-in). El output agrega los resultados; si un child falla, el bloque
  falla pero conserva los outputs parciales.
- resolver agentes DENTRO de un team (team_id) antes que el registry global
- forzar runtime en el matching (step.runtime)
- requerir aprobación humana (approval: true → status waiting_approval)

Observabilidad (Fase H): cada ejecución produce un timeline estructurado en
`run.events` [{ts, type, step, agent, runtime, provider, model, tokens, cost,
duration_ms, actions, tool_calls, error}] y `step_results` enriquecidos con
tokens/runtime/provider/model/duration — un operador entiende exactamente qué
hizo la misión (DoD Phase H).

Nota (paralelismo + SQLAlchemy): cada child corre en su PROPIA sesión ligada
al mismo bind del engine (los threads no comparten sesión). Limitación: en
SQLite in-memory cada conexión vería una DB vacía; tests y dev usan archivo
(test.db / missioncontrol.db), prod usa Postgres → OK.
"""

import copy
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session, sessionmaker

from app.models.workflow import Workflow, WorkflowRun, start_run

log = logging.getLogger("workflows")


def execute_workflow(db: Session, workflow_id: str, run_id: str | None = None,
                     team_id: str | None = None,
                     harness_id: str | None = None,
                     mission_ctx: Optional[dict] = None,
                     agent_pool: Optional[List[str]] = None) -> WorkflowRun:
    """Ejecuta un workflow sincrónicamente (o continúa un run existente).

    team_id: contexto de team para resolver steps por capabilities dentro del
    team primero (Fase F — Mission coordina agentes de un team).
    harness_id: Harness versionado que formaliza CÓMO ejecutan los agentes
    (Fase G — instructions/context/tools/guardrails/runtime/output contract).
    agent_pool: IDs de agentes que la misión seleccionó explícitamente — se
    prefieren en el matching por capabilities (después del team, antes del
    registry global).
    """
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise ValueError("Workflow not found")

    harness = _load_harness(db, harness_id)
    if harness_id and not harness:
        raise ValueError(f"harness {harness_id} no encontrado")
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first() if run_id else None
    if not run:
        run = start_run(db, wf)
        _log_event(run, wf, "workflow_started", step=None)

    steps = wf.definition or []
    # deepcopy: si los dicts internos son los mismos objetos, SQLAlchemy no detecta el cambio JSON
    results = copy.deepcopy(run.step_results or [])

    for idx in range(run.current_step, len(steps)):
        if run.status == "cancelled":
            return run
        if run.status == "paused":
            run.paused_at = datetime.utcnow()
            db.commit()
            return run

        step = steps[idx]
        step_name = step.get("name", f"step_{idx + 1}")
        run.current_step = idx
        db.commit()
        _log_event(run, wf, "step_started", step=step_name, step_index=idx,
                   parallel=bool(step.get("parallel")))

        # approval gate
        if step.get("approval"):
            results.append({
                "step_index": idx,
                "step_name": step_name,
                "status": "waiting_approval",
                "output": None,
                "error": None,
                "cost": 0,
                "approval_token": uuid.uuid4().hex[:16],
            })
            run.step_results = results
            run.status = "paused"  # espera aprobación humana
            wf.status = "paused"
            run.paused_at = datetime.utcnow()
            db.commit()
            _log_event(run, wf, "approval_required", step=step_name, step_index=idx)
            log.info(f"workflow {wf.id} pausado en step {idx} ({step_name}) — aprobación requerida")
            return run

        # bloque paralelo (fan-out → fan-in)
        if step.get("parallel") and step.get("steps"):
            output, error, cost, children = _run_parallel_block(db, step, wf, team_id, harness, mission_ctx, agent_pool)
            results.append({
                "step_index": idx,
                "step_name": step_name,
                "status": "completed" if not error else "failed",
                "output": output,
                "error": error,
                "cost": cost,
                "parallel": True,
                "children": children,
            })
            run.step_results = results
            run.current_step = idx + 1
            if error:
                run.status = "failed"
                run.error = f"{step_name}: {error}"
                wf.status = "failed"
                wf.error = run.error
                wf.completed_at = datetime.utcnow()
                db.commit()
                _log_event(run, wf, "step_failed", step=step_name, step_index=idx,
                           error=run.error, cost=cost)
                _log_event(run, wf, "workflow_failed", step=step_name, error=run.error)
                return run
            _log_event(run, wf, "parallel_completed", step=step_name, step_index=idx,
                       cost=cost, children_ok=sum(1 for c in children if c["status"] == "completed"),
                       children_total=len(children))
            db.commit()
            continue

        # ejecutar el step (si tiene agente o task_text)
        output, error, cost, meta = _run_step(db, step, wf, team_id=team_id, harness=harness,
                                              mission_ctx=mission_ctx, agent_pool=agent_pool)
        entry = {
            "step_index": idx,
            "step_name": step_name,
            "status": "completed" if not error else "failed",
            "output": output,
            "error": error,
            "cost": cost,
        }
        entry.update(meta)
        results.append(entry)
        run.step_results = results
        run.current_step = idx + 1
        if error:
            run.status = "failed"
            run.error = f"{step_name}: {error}"
            wf.status = "failed"
            wf.error = run.error
            wf.completed_at = datetime.utcnow()
            db.commit()
            _log_event(run, wf, "step_failed", step=step_name, step_index=idx,
                       error=run.error, cost=cost, **{k: v for k, v in meta.items() if k != "error"})
            _log_event(run, wf, "workflow_failed", step=step_name, error=run.error)
            return run
        _log_event(run, wf, "step_completed", step=step_name, step_index=idx, cost=cost, **meta)
        db.commit()

    run.status = "completed"
    run.completed_at = datetime.utcnow()
    wf.status = "completed"
    wf.completed_at = datetime.utcnow()
    db.commit()
    _log_event(run, wf, "workflow_completed", step=None)
    return run


def _run_step(db: Session, step: dict, wf: Workflow,
              team_id: Optional[str] = None,
              harness: Optional[Any] = None,
              mission_ctx: Optional[dict] = None,
              agent_pool: Optional[List[str]] = None) -> Tuple[Optional[str], Optional[str], float, dict]:
    """Ejecuta un step. Devuelve (output, error, cost, meta_observabilidad).

    Resolución de agente (en orden):
      1. agent_id explícito
      2. capabilities dentro del team (si team_id y el team cubre >= 50%)
      3. capabilities dentro del pool de la misión (si agent_pool)
      4. capabilities global (registry)
    step.runtime (si existe) filtra el matching por runtime.
    harness: Harness versionado (Fase G) que formaliza instructions/context/
    tools/guardrails/runtime/output contract. step.harness_id overridea.
    """
    empty_meta: dict = {"runtime": None, "provider": None, "model": None,
                        "tokens": {}, "duration_ms": None, "simulated": False,
                        "actions": [], "tool_calls": [], "agent_name": None, "agent_id": None}
    task_text = step.get("task") or step.get("task_text")
    agent_id = step.get("agent_id")
    runtime_hint = step.get("runtime") or None

    # El override de step debe resolverse antes de cualquier dispatch, incluido WebMCP.
    active_harness = harness
    step_harness_id = step.get("harness_id")
    if step_harness_id and (
        not harness or str(getattr(harness, "id", "")) != str(step_harness_id)
    ):
        active_harness = _load_harness(db, step_harness_id)
        if not active_harness:
            return None, f"harness {step_harness_id} no encontrado", 0.0, empty_meta
    if active_harness and getattr(active_harness, "status", "active") != "active":
        return None, (f"harness '{active_harness.name}' no está activo "
                      f"(status={active_harness.status}) — activalo antes de ejecutar"), 0.0, empty_meta

    # --- Fase K: step WebMCP (tool/adapter — sin agente) ---
    if step.get("webmcp"):
        policy_error = _tool_policy_error(active_harness, "webmcp")
        if policy_error:
            return None, policy_error, 0.0, empty_meta
        return _run_webmcp_step(db, step)

    # Capability matching: team primero, registry global como fallback.
    # - required_capabilities (duro): sin agente → error (steps explícitos)
    # - capabilities (blando, default workflows): sin agente → declarativo
    hard_caps = step.get("required_capabilities")
    soft_caps = step.get("capabilities") if not hard_caps else None
    if not agent_id and (hard_caps or soft_caps):
        caps = hard_caps or soft_caps
        best = None
        if team_id:
            from app.services import team_service

            best = team_service.best_agent_in_team(
                db,
                team_id=team_id,
                required_capabilities=caps,
                runtime=runtime_hint,
            )
        if not best:
            from app.services.capability_matching import match_agents, best_agent

            if agent_pool:
                pool = set(agent_pool)
                for cand in match_agents(db, required_capabilities=caps, runtime=runtime_hint, min_score=50):
                    if cand["agent_id"] in pool:
                        best = cand
                        break
            if not best:
                best = best_agent(db, required_capabilities=caps, runtime=runtime_hint)
        if not best:
            if hard_caps:
                return None, f"No hay agente que cubra >=50% de {hard_caps}", 0.0, empty_meta
            return f"[{step.get('name','step')}] sin agente disponible (declarativo)", None, 0.0, empty_meta
        agent_id = best["agent_id"]

    if not task_text and not agent_id:
        return f"[{step.get('name','step')}] sin ejecución (declarativo)", None, 0.0, empty_meta

    if not agent_id:
        return None, "step define task pero no agent_id (capability matching pendiente)", 0.0, empty_meta

    # ejecutar vía adapter del agente
    from app.models.agent import Agent
    from app.adapters.registry import get_adapter
    from app.adapters.base import AgentIdentity
    from app.services.agent_soul import load_agent_persona

    agent = db.query(Agent).filter(Agent.id == uuid.UUID(str(agent_id))).first()
    if not agent:
        return None, f"agent {agent_id} no encontrado", 0.0, empty_meta

    runtime = getattr(agent, "runtime", "generic")
    runtime_name = runtime.value if hasattr(runtime, "value") else runtime
    adapter = get_adapter(runtime_name)
    if not adapter:
        return None, f"runtime {runtime_name} sin adapter", 0.0, empty_meta

    provider = getattr(agent, "provider", "deepseek")
    provider_name = provider.value if hasattr(provider, "value") else provider

    identity = AgentIdentity(
        agent_id=str(agent.id), name=agent.name,
        role=agent.role.value if hasattr(agent.role, "value") else str(agent.role),
        runtime=runtime_name, provider=provider_name, model=getattr(agent, "model", None),
        system_prompt=load_agent_persona(agent.role.value) or agent.system_prompt or "",
        capabilities=agent.capabilities or [], config=agent.config or {},
    )

    # --- Fase G: aplicar harness (step-level overridea el de la misión) ---
    final_context = step.get("context")
    if active_harness:
        from app.services import harness_service

        patch, herrors = harness_service.apply_harness(
            active_harness, agent, mission_context=mission_ctx or {}
        )
        if herrors:
            return None, "; ".join(herrors), 0.0, empty_meta
        if patch.get("system_prompt"):
            identity.system_prompt = patch["system_prompt"]
        if patch.get("context"):
            final_context = "\n\n".join(x for x in [final_context, patch["context"]] if x) or None
        identity.config = {**identity.config, **(patch.get("config") or {})}

    start = time.time()
    result = adapter.dispatch_task(identity, task_text, final_context)
    duration_ms = result.duration_ms or int((time.time() - start) * 1000)
    cost = 0.0
    tokens = {}
    if result.usage:
        tokens = {
            "prompt": result.usage.get("prompt_tokens") or 0,
            "completion": result.usage.get("completion_tokens") or 0,
            "total": result.usage.get("total_tokens") or 0,
        }
        if result.usage.get("cost_estimate_usd"):
            cost = float(result.usage["cost_estimate_usd"])

    meta = {
        "runtime": result.runtime or runtime_name,
        "provider": result.provider or provider_name,
        "model": result.model or getattr(agent, "model", None),
        "tokens": tokens,
        "duration_ms": duration_ms,
        "simulated": bool(result.simulated),
        "actions": list(result.meta.get("actions") or []),
        "tool_calls": list(result.meta.get("tool_calls") or []),
        "agent_name": agent.name,
        "agent_id": str(agent.id),
    }
    # Audit §22: provenance del harness usado (id + versión) para receipts
    if active_harness:
        meta["harness_id"] = str(active_harness.id)
        meta["harness_version"] = active_harness.version

    if result.status == "failed":
        return None, result.error, cost, meta

    # --- Fase G: validar output contra el contrato del harness ---
    if active_harness:
        from app.services import harness_service

        vok, verrors = harness_service.validate_output(active_harness, result.output)
        if not vok:
            return None, f"validación de harness ({active_harness.name} v{active_harness.version}): {'; '.join(verrors)}", cost, meta
    return result.output, None, cost, meta


def _run_webmcp_step(db: Session, step: dict) -> Tuple[Optional[str], Optional[str], float, dict]:
    """Ejecuta un step de tipo webmcp: interactúa con una app WebMCP-enabled.

    step.webmcp = {url, actions: [{type, selector, value}, ...], max_actions}
    Devuelve (output=snapshot renderizado, error, cost=0, meta con
    webmcp_evidence: action log + snapshot → evidencia preservada).
    """
    from app.services.webmcp import client as wm, render_snapshot

    spec = step.get("webmcp") or {}
    url = (spec.get("url") or "").strip()
    if not url:
        return None, "step webmcp sin 'url' (app WebMCP-enabled)", 0.0, {
            "runtime": "webmcp", "provider": None, "model": None, "tokens": {},
            "duration_ms": None, "simulated": False,
            "actions": [], "tool_calls": [], "agent_name": None, "agent_id": None,
        }
    actions = spec.get("actions") or []
    if not actions:
        return None, "step webmcp sin 'actions'", 0.0, {}

    start = time.time()
    try:
        evidence = wm.run_script(url, actions)
    except wm.WebMCPError as e:
        return None, f"webmcp: {e}", 0.0, {
            "runtime": "webmcp", "provider": None, "model": None, "tokens": {},
            "duration_ms": int((time.time() - start) * 1000), "simulated": False,
            "actions": [a.get("action") for a in actions],
            "tool_calls": [f"webmcp:{a.get('type')}:{a.get('selector')}" for a in actions],
            "agent_name": None, "agent_id": None,
            "webmcp_evidence": {"url": url, "actions_count": len(actions), "error": str(e)},
        }

    output = render_snapshot(evidence.get("snapshot") or {})
    meta = {
        "runtime": "webmcp", "provider": None, "model": None, "tokens": {},
        "duration_ms": int((time.time() - start) * 1000), "simulated": False,
        "actions": [a.get("action") for a in actions],
        "tool_calls": [f"webmcp:{a.get('type')}:{a.get('selector')}" for a in actions],
        "agent_name": None, "agent_id": None,
        "webmcp_evidence": evidence,
    }
    # acciones fallidas → el step falla (conserva la evidencia parcial)
    failed = [a for a in evidence.get("action_log") or [] if not a.get("ok")]
    if failed:
        err = "; ".join(f"{a['action']}: {a.get('error')}" for a in failed)
        return None, f"webmcp: {err}", 0.0, meta
    return output, None, 0.0, meta


def _load_harness(db: Session, harness_id: Optional[str]):
    """Carga el harness por id; devuelve None si falta o el id es inválido."""
    if not harness_id:
        return None
    from app.services.harness_service import get_harness

    try:
        return get_harness(db, harness_id)
    except (TypeError, ValueError):
        return None


def _tool_policy_error(harness: Optional[Any], tool_name: str) -> Optional[str]:
    """Aplica allow/deny del Harness antes de invocar un tool directo."""
    if not harness:
        return None
    policy = ((harness.spec or {}).get("tools") or {})
    allowed = {str(v).strip().lower() for v in policy.get("allow") or []}
    denied = {str(v).strip().lower() for v in policy.get("deny") or []}
    name = tool_name.strip().lower()
    if name in denied or "*" in denied:
        return f"tool '{tool_name}' denegado por harness '{harness.name}'"
    if allowed and name not in allowed and "*" not in allowed:
        return f"tool '{tool_name}' no permitido por harness '{harness.name}'"
    return None


# ---------------------------------------------------------------------------
# Bloques paralelos (Fase F)
# ---------------------------------------------------------------------------

def _new_session(db: Session) -> Session:
    """Sesión nueva ligada al MISMO bind que la sesión padre (thread-safe)."""
    return sessionmaker(bind=db.get_bind(), autoflush=False, autocommit=False)()


def _run_parallel_block(db: Session, step: dict, wf: Workflow,
                        team_id: Optional[str],
                        harness: Optional[Any] = None,
                        mission_ctx: Optional[dict] = None,
                        agent_pool: Optional[List[str]] = None) -> Tuple[str, Optional[str], float, List[dict]]:
    """Fan-out: corre los children del bloque en threads y espera a todos.

    Devuelve (output_summary, error, cost_total, children_results).
    Si algún child falla, el bloque falla pero conserva outputs parciales.
    """
    children: List[dict] = step.get("steps") or []
    total_cost = 0.0
    child_results: List[dict] = []

    if not children:
        return "[parallel] sin steps", None, 0.0, []

    def _run_child(child: dict) -> dict:
        child_session = _new_session(db)
        try:
            output, error, cost, meta = _run_step(child_session, child, wf, team_id=team_id,
                                                  harness=harness, mission_ctx=mission_ctx,
                                                  agent_pool=agent_pool)
            return {
                "name": child.get("name", "child"),
                "status": "completed" if not error else "failed",
                "output": output,
                "error": error,
                "cost": cost,
                **meta,
            }
        except Exception as e:  # noqa: BLE001 — un child no debe matar al bloque
            return {
                "name": child.get("name", "child"),
                "status": "failed",
                "output": None,
                "error": str(e)[:300],
                "cost": 0.0,
                "tokens": {}, "runtime": None, "duration_ms": None, "simulated": False,
            }
        finally:
            child_session.close()

    max_workers = min(len(children), int(step.get("max_parallel") or len(children)) or len(children))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_run_child, c) for c in children]
        child_results = [f.result() for f in futures]

    ok = 0
    errors: List[str] = []
    for r in child_results:
        total_cost += float(r.get("cost") or 0.0)
        if r["status"] == "completed":
            ok += 1
        else:
            errors.append(f"{r['name']}: {r['error']}")

    summary = f"[parallel] {ok}/{len(child_results)} steps completados"
    error = "; ".join(errors) if errors else None
    return summary, error, round(total_cost, 4), child_results


# ---------------------------------------------------------------------------
# Observabilidad (Fase H): timeline estructurado
# ---------------------------------------------------------------------------

def _log_event(run: WorkflowRun, wf: Workflow, etype: str, **kw: Any) -> None:
    """Agrega un evento estructurado al timeline del run (persistido)."""
    events = list(run.events or [])
    events.append({
        "ts": datetime.utcnow().isoformat() + "Z",
        "type": etype,
        "workflow_id": str(wf.id),
        **kw,
    })
    run.events = events
    try:
        from sqlalchemy.orm.session import object_session
        s = object_session(run)
        if s is not None:
            s.commit()
    except Exception:  # noqa: BLE001 — observabilidad nunca rompe la ejecución
        log.warning("no se pudo persistir evento %s", etype, exc_info=True)


# ---------------------------------------------------------------------------
# Control de runs
# ---------------------------------------------------------------------------

def approve_step(db: Session, run: WorkflowRun, step_index: int, approved: bool,
                 team_id: Optional[str] = None,
                 harness_id: Optional[str] = None,
                 mission_ctx: Optional[dict] = None,
                 agent_pool: Optional[List[str]] = None) -> WorkflowRun:
    """Aprueba/rechaza el step que esperaba aprobación y continúa.

    Guard (audit §12): solo runs PAUSADOS esperando aprobación pueden aprobarse.
    Aprobar un run ya completado/failed/cancelled sería re-ejecutarlo — se
    rechaza con error claro (evita ejecuciones duplicadas).
    """
    if run.status != "paused":
        raise ValueError(f"el run {run.id} no está esperando aprobación (status={run.status})")
    wf = db.query(Workflow).filter(Workflow.id == run.workflow_id).first()
    results = copy.deepcopy(run.step_results or [])
    target = None
    for r in results:
        if r.get("step_index") == step_index and r.get("status") == "waiting_approval":
            target = r
            break
    if target is None:
        raise ValueError(f"step {step_index} no está esperando aprobación en el run {run.id}")
    target["status"] = "approved" if approved else "rejected"
    target["approved_at"] = datetime.utcnow().isoformat()
    run.step_results = results
    run.status = "running" if approved else "cancelled"
    run.paused_at = None
    # avanzar el puntero para que execute_workflow continúe DESPUÉS del step aprobado
    run.current_step = step_index + 1

    if wf:
        if approved:
            wf.status = "running"
            wf.current_step = step_index + 1
        else:
            wf.status = "cancelled"
            wf.completed_at = datetime.utcnow()
    db.commit()
    _log_event(run, wf, "approval_approved" if approved else "approval_rejected",
               step_index=step_index)
    if approved:
        execute_workflow(db, run.workflow_id, run.id, team_id=team_id,
                         harness_id=harness_id, mission_ctx=mission_ctx,
                         agent_pool=agent_pool)
    return run


def pause_run(db: Session, run: WorkflowRun) -> WorkflowRun:
    run.status = "paused"
    run.paused_at = datetime.utcnow()
    wf = db.query(Workflow).filter(Workflow.id == run.workflow_id).first()
    if wf:
        wf.status = "paused"
    db.commit()
    return run


def cancel_run(db: Session, run: WorkflowRun) -> WorkflowRun:
    run.status = "cancelled"
    run.completed_at = datetime.utcnow()
    wf = db.query(Workflow).filter(Workflow.id == run.workflow_id).first()
    if wf:
        wf.status = "cancelled"
        wf.completed_at = datetime.utcnow()
    db.commit()
    return run
