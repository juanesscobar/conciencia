"""EconomicsService — economía de misiones inspeccionable (master prompt §L).

DoD Phase L: "Mission economics can be inspected without implementing billing."

Registra y agrega: runs, actions, models, tokens, tools, external cost y
outcomes. Fuentes: MissionRun (tokens/cost_usd/external_costs) + step_results
(por step: provider/model/tokens/cost/actions/tool_calls) + cost_records
(costos LLM globales del harness).
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

log = logging.getLogger("economics")


# ---------------------------------------------------------------------------
# Costo externo (tools/servicios fuera del LLM)
# ---------------------------------------------------------------------------

def record_external_cost(
    db: Session,
    *,
    mission_run_id: str,
    tool: str,
    cost_usd: float,
    detail: Optional[str] = None,
) -> dict:
    """Registra un costo externo (herramienta/servicio) en un MissionRun.

    Actualiza cost_usd.tools/total y el timeline external_costs. Devuelve
    el entry registrado.
    """
    from app.models.mission import MissionRun

    run = db.query(MissionRun).filter(MissionRun.id == uuid.UUID(str(mission_run_id))).first()
    if not run:
        raise ValueError(f"MissionRun no encontrado: {mission_run_id}")

    entry = {
        "tool": tool,
        "cost_usd": round(float(cost_usd), 6),
        "detail": detail,
        "ts": datetime.utcnow().isoformat() + "Z",
    }
    costs = list(run.external_costs or [])
    costs.append(entry)
    run.external_costs = costs

    cost_usd_total = float((run.cost_usd or {}).get("total") or 0.0) + float(cost_usd)
    tools_total = float((run.cost_usd or {}).get("tools") or 0.0) + float(cost_usd)
    run.cost_usd = {
        "llm": round(float((run.cost_usd or {}).get("llm") or 0.0), 4),
        "tools": round(tools_total, 6),
        "total": round(cost_usd_total, 6),
    }
    db.commit()
    db.refresh(run)
    return entry


# ---------------------------------------------------------------------------
# Agregación por misión
# ---------------------------------------------------------------------------

def mission_economics(db: Session, mission_id: str) -> dict:
    """Economía de una misión: runs + agregados (tokens/costo/modelos/acciones)."""
    from app.models.mission import Mission, MissionRun

    mission = db.query(Mission).filter(Mission.id == uuid.UUID(str(mission_id))).first()
    if not mission:
        raise ValueError(f"Misión no encontrada: {mission_id}")

    runs = (
        db.query(MissionRun)
        .filter(MissionRun.mission_id == mission.id)
        .order_by(MissionRun.started_at.desc())
        .all()
    )

    by_provider: Dict[str, dict] = {}
    by_model: Dict[str, dict] = {}
    by_runtime: Dict[str, int] = {}
    total_tokens = {"prompt": 0, "completion": 0, "total": 0}
    total_cost = 0.0
    total_external = 0.0
    actions = 0
    tool_calls = 0
    outcomes: Dict[str, int] = {}
    run_summaries: List[dict] = []

    for run in runs:
        outcome = run.status
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
        t = run.tokens or {}
        total_tokens["prompt"] += t.get("prompt") or 0
        total_tokens["completion"] += t.get("completion") or 0
        total_tokens["total"] += t.get("total") or 0
        total_cost += float((run.cost_usd or {}).get("total") or 0.0)
        for ext in run.external_costs or []:
            total_external += float(ext.get("cost_usd") or 0.0)
        run_summaries.append({
            "id": str(run.id),
            "status": run.status,
            "tokens": t,
            "cost_usd": run.cost_usd,
            "external_costs": run.external_costs or [],
            "started_at": run.started_at.isoformat() if run.started_at else None,
        })

        # desglose por step (workflow run)
        if run.workflow_run_id:
            from app.models.workflow import WorkflowRun

            wr = db.query(WorkflowRun).filter(WorkflowRun.id == run.workflow_run_id).first()
            if wr:
                sa, st = _aggregate_steps(wr.step_results or [], by_provider, by_model, by_runtime)
                actions += sa
                tool_calls += st

    return {
        "mission_id": str(mission.id),
        "mission_name": mission.name,
        "type": mission.type,
        "status": mission.status,
        "runs_count": len(runs),
        "runs": run_summaries,
        "tokens": total_tokens,
        "cost_usd": {
            "llm": round(total_cost - total_external, 6),
            "tools": round(total_external, 6),
            "total": round(total_cost, 6),
        },
        "cost_by_provider": _sorted_costs(by_provider),
        "cost_by_model": _sorted_costs(by_model),
        "runtime_usage": dict(sorted(by_runtime.items(), key=lambda kv: -kv[1])),
        "actions_count": actions,
        "tool_calls_count": tool_calls,
        "outcomes": outcomes,
    }


# ---------------------------------------------------------------------------
# Agregación de plataforma
# ---------------------------------------------------------------------------

def platform_economics(db: Session, days: int = 30) -> dict:
    """Economía global (últimos N días): misiones, runs, costos, tokens, outcomes."""
    from app.models.mission import Mission, MissionRun

    since = datetime.utcnow() - timedelta(days=max(days, 1))
    missions = db.query(Mission).filter(Mission.created_at >= since).all()
    runs = (
        db.query(MissionRun)
        .filter(MissionRun.started_at >= since)
        .order_by(MissionRun.started_at.desc())
        .all()
    )

    by_provider: Dict[str, dict] = {}
    by_model: Dict[str, dict] = {}
    by_runtime: Dict[str, int] = {}
    total_tokens = {"prompt": 0, "completion": 0, "total": 0}
    total_cost = 0.0
    total_external = 0.0
    actions = 0
    tool_calls = 0
    outcomes: Dict[str, int] = {}
    by_type: Dict[str, int] = {}

    for run in runs:
        outcomes[run.status] = outcomes.get(run.status, 0) + 1
        t = run.tokens or {}
        total_tokens["prompt"] += t.get("prompt") or 0
        total_tokens["completion"] += t.get("completion") or 0
        total_tokens["total"] += t.get("total") or 0
        total_cost += float((run.cost_usd or {}).get("total") or 0.0)
        for ext in run.external_costs or []:
            total_external += float(ext.get("cost_usd") or 0.0)
        if run.workflow_run_id:
            from app.models.workflow import WorkflowRun

            wr = db.query(WorkflowRun).filter(WorkflowRun.id == run.workflow_run_id).first()
            if wr:
                sa, st = _aggregate_steps(wr.step_results or [], by_provider, by_model, by_runtime)
                actions += sa
                tool_calls += st

    for m in missions:
        by_type[m.type] = by_type.get(m.type, 0) + 1

    # costos LLM globales del harness (cost_records) en el período
    from app.models.cost_record import CostRecord

    llm_total = 0.0
    llm_tokens = 0
    for cr in db.query(CostRecord).filter(CostRecord.timestamp >= since).all():
        llm_total += float(cr.cost_usd or 0.0)
        llm_tokens += int(cr.total_tokens or 0)

    return {
        "period_days": days,
        "since": since.isoformat() + "Z",
        "missions_count": len(missions),
        "missions_by_type": dict(sorted(by_type.items(), key=lambda kv: -kv[1])),
        "runs_count": len(runs),
        "outcomes": outcomes,
        "tokens": total_tokens,
        "cost_usd": {
            "llm": round(total_cost - total_external, 6),
            "tools": round(total_external, 6),
            "total": round(total_cost, 6),
        },
        "llm_cost_records": round(llm_total, 6),
        "llm_tokens_records": llm_tokens,
        "cost_by_provider": _sorted_costs(by_provider),
        "cost_by_model": _sorted_costs(by_model),
        "runtime_usage": dict(sorted(by_runtime.items(), key=lambda kv: -kv[1])),
        "actions_count": actions,
        "tool_calls_count": tool_calls,
        "note": "sin billing — solo inspección",
    }


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _aggregate_steps(step_results: list, by_provider: dict, by_model: dict,
                     by_runtime: dict):
    """Acumula costos/tokens/acciones de step_results (incluye children paralelos).

    Devuelve (actions_count, tool_calls_count) acumulados.
    """
    actions = 0
    tool_calls = 0
    for s in step_results:
        provider = s.get("provider") or "unknown"
        model = s.get("model") or "unknown"
        runtime = s.get("runtime") or "unknown"
        cost = float(s.get("cost") or 0.0)
        tokens = s.get("tokens") or {}
        _add(by_provider, provider, cost, tokens)
        _add(by_model, model, cost, tokens)
        by_runtime[runtime] = by_runtime.get(runtime, 0) + 1
        actions += len(s.get("actions") or [])
        tool_calls += len(s.get("tool_calls") or [])
        for child in s.get("children") or []:
            cprovider = child.get("provider") or "unknown"
            cmodel = child.get("model") or "unknown"
            cruntime = child.get("runtime") or "unknown"
            ccost = float(child.get("cost") or 0.0)
            ctokens = child.get("tokens") or {}
            _add(by_provider, cprovider, ccost, ctokens)
            _add(by_model, cmodel, ccost, ctokens)
            by_runtime[cruntime] = by_runtime.get(cruntime, 0) + 1
            actions += len(child.get("actions") or [])
            tool_calls += len(child.get("tool_calls") or [])
    return actions, tool_calls


def _add(acc: dict, key: str, cost: float, tokens: dict) -> None:
    entry = acc.setdefault(key, {"cost_usd": 0.0, "tokens": 0, "calls": 0})
    entry["cost_usd"] = round(entry["cost_usd"] + cost, 6)
    entry["tokens"] += int(tokens.get("total") or 0)
    entry["calls"] += 1


def _sorted_costs(acc: dict) -> List[dict]:
    return [
        {"key": k, **v}
        for k, v in sorted(acc.items(), key=lambda kv: -kv[1]["cost_usd"])
    ]
