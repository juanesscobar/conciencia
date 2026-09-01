"""WebMCP evidence — preserva la evidencia de interacción WebMCP (Fase K).

Un step `webmcp` deja en step_results su `webmcp_evidence` (action log +
snapshot). Al completarse la misión, esa evidencia se promueve a
Signal + Evidence (Fase I) — así la interacción con la app web queda
trazable y vinculada a la misión (DoD Phase K).
"""

import logging

from sqlalchemy.orm import Session

log = logging.getLogger("webmcp.evidence")


def promote_step_evidence(db: Session, mission, wf_run) -> int:
    """Crea Signals+Evidence para cada step con webmcp_evidence.

    Devuelve la cantidad de signals creadas (0 si no hay steps webmcp).
    """
    from app.services import signal_service

    created = 0
    for step in (wf_run.step_results or []):
        evidence = step.get("webmcp_evidence")
        if not evidence:
            continue
        url = evidence.get("url") or "?"
        actions = evidence.get("action_log") or []
        snap = evidence.get("snapshot") or {}

        # Evidence rows: una por acción + snapshot final
        evidences: list = []
        for a in actions:
            detail = a.get("result") if a.get("ok") else f"error: {a.get('error')}"
            evidences.append({
                "kind": "tool_result",
                "content": f"{a.get('action')} → {detail}",
                "source": f"webmcp:{url}",
            })
        snap_text = _snapshot_to_text(snap)
        if snap_text:
            evidences.append({"kind": "output", "content": snap_text[:1000], "source": f"webmcp:{url}"})
        if not evidences:
            evidences = [{"kind": "tool_result", "content": f"interacción WebMCP con {url}", "source": url}]

        try:
            signal_service.create_signal(
                db,
                mission_id=str(mission.id),
                title=f"WebMCP: {step.get('step_name', 'interacción')}",
                type="finding",
                summary=f"{len(actions)} acción(es) contra {url}",
                source_step=step.get("step_name"),
                agent_name=step.get("agent_name"),
                workflow_run_id=str(wf_run.id),
                evidences=evidences,
            )
            created += 1
        except Exception:  # noqa: BLE001 — la promoción nunca rompe el run
            log.warning("no se pudo promover evidencia WebMCP del step %s", step.get("step_name"), exc_info=True)
    return created


def _snapshot_to_text(snap: dict) -> str:
    state = (snap or {}).get("state") or {}
    if not state:
        return ""
    try:
        import json
        return json.dumps(state, ensure_ascii=False)[:2000]
    except Exception:  # noqa: BLE001
        return str(state)[:2000]
