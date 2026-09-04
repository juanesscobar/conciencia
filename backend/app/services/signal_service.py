"""SignalService — hallazgos trazables de misiones con evidencia (master prompt §I).

CRUD + extracción automática: los outputs de los steps pueden incluir

    SIGNAL: <type>| <título>| <resumen>
    EVIDENCE: <contenido>          (0..N líneas, respaldan la signal)

Al completarse una misión (o bajo demanda con `extract_from_mission`), se
generan Signals con Evidence y se agregan los evidence_ids a la misión
(trazabilidad global, DoD Phase I).
"""

import logging
import re
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.signal import (
    Signal, Evidence,
    SIGNAL_TYPES, SIGNAL_STATUSES, EVIDENCE_KINDS,
)

log = logging.getLogger("signals")

# SIGNAL: <type>| <título>| <resumen>   (type opcional, default finding)
_SIGNAL_RE = re.compile(r"^\s*SIGNAL:\s*(.*)$", re.MULTILINE)
_EVIDENCE_RE = re.compile(r"^\s*EVIDENCE:\s*(.*)$", re.MULTILINE)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def create_signal(
    db: Session,
    *,
    mission_id: str,
    title: str,
    type: str = "finding",
    summary: Optional[str] = None,
    source_step: Optional[str] = None,
    agent_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    workflow_run_id: Optional[str] = None,
    mission_run_id: Optional[str] = None,
    evidences: Optional[List[dict]] = None,
    link_to_mission: bool = True,
) -> Signal:
    from app.models.mission import Mission

    if not title.strip():
        raise ValueError("Signal title requerido")
    if type not in SIGNAL_TYPES:
        raise ValueError(f"Tipo inválido: {type}. Válidos: {', '.join(SIGNAL_TYPES)}")
    mission = db.query(Mission).filter(Mission.id == uuid.UUID(str(mission_id))).first()
    if not mission:
        raise ValueError(f"Misión no encontrada: {mission_id}")

    signal = Signal(
        mission_id=mission.id,
        type=type,
        title=title.strip(),
        summary=summary,
        status="new",
        source_step=source_step,
        agent_id=uuid.UUID(str(agent_id)) if agent_id else None,
        agent_name=agent_name,
        workflow_run_id=workflow_run_id,
        mission_run_id=uuid.UUID(str(mission_run_id)) if mission_run_id else None,
    )
    db.add(signal)
    db.flush()

    for ev in evidences or []:
        kind = ev.get("kind") or "quote"
        if kind not in EVIDENCE_KINDS:
            raise ValueError(f"Evidence kind inválido: {kind}")
        db.add(Evidence(
            signal_id=signal.id,
            kind=kind,
            content=str(ev.get("content") or "").strip(),
            source=ev.get("source"),
        ))

    db.commit()
    db.refresh(signal)

    # trazabilidad global: evidence_ids de la misión
    if link_to_mission:
        _link_evidence_ids(db, mission, signal)
    log.info("signal creada: [%s] %s (misión %s)", signal.type, signal.title, mission_id)
    return signal


def list_signals(
    db: Session,
    mission_id: Optional[str] = None,
    type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> List[Signal]:
    q = db.query(Signal).order_by(Signal.created_at.desc())
    if mission_id:
        q = q.filter(Signal.mission_id == uuid.UUID(str(mission_id)))
    if type:
        q = q.filter(Signal.type == type)
    if status:
        q = q.filter(Signal.status == status)
    return q.limit(limit).all()


def get_signal(db: Session, signal_id: str) -> Optional[Signal]:
    return db.query(Signal).filter(Signal.id == uuid.UUID(str(signal_id))).first()


def update_signal_status(db: Session, signal: Signal, status: str) -> Signal:
    if status not in SIGNAL_STATUSES:
        raise ValueError(f"Status inválido: {status}. Válidos: {', '.join(SIGNAL_STATUSES)}")
    signal.status = status
    db.commit()
    db.refresh(signal)
    return signal


def add_evidence(db: Session, signal: Signal, *, kind: str = "quote",
                 content: str, source: Optional[str] = None) -> Evidence:
    if not content.strip():
        raise ValueError("Evidence content requerido")
    if kind not in EVIDENCE_KINDS:
        raise ValueError(f"Evidence kind inválido: {kind}")
    ev = Evidence(signal_id=signal.id, kind=kind, content=content.strip(), source=source)
    db.add(ev)
    db.commit()
    db.refresh(ev)
    # actualizar evidence_ids de la misión
    from app.models.mission import Mission

    mission = db.query(Mission).filter(Mission.id == signal.mission_id).first()
    if mission:
        _link_evidence_ids(db, mission, signal)
    return ev


def delete_signal(db: Session, signal: Signal) -> None:
    from app.models.mission import Mission

    evidence_ids = {str(ev.id) for ev in signal.evidences}
    mission = db.query(Mission).filter(Mission.id == signal.mission_id).first()
    if mission and evidence_ids:
        mission.evidence_ids = [
            str(eid) for eid in (mission.evidence_ids or [])
            if str(eid) not in evidence_ids
        ]
    db.delete(signal)
    db.commit()


# ---------------------------------------------------------------------------
# Extracción automática desde outputs de steps
# ---------------------------------------------------------------------------

def extract_from_output(output: str) -> List[dict]:
    """Parsea un output de step → lista de {title, type, summary, evidences[]}.

    Formato:
      SIGNAL: <type>| <título>| <resumen>
      EVIDENCE: <contenido>          (0..N líneas después de cada SIGNAL)
    """
    if not output:
        return []
    signals: List[dict] = []
    # dividimos el texto en bloques por línea SIGNAL
    matches = list(_SIGNAL_RE.finditer(output))
    for i, m in enumerate(matches):
        raw = m.group(1).strip()
        if not raw:
            continue
        parts = [p.strip() for p in raw.split("|")]
        stype = parts[0].strip().lower() if parts and parts[0].strip().lower() in SIGNAL_TYPES else "finding"
        title = parts[1].strip() if len(parts) > 1 and parts[1].strip() else (raw if stype == "finding" else raw)
        summary = parts[2].strip() if len(parts) > 2 and parts[2].strip() else None
        if stype == "finding" and "|" not in raw:
            title = raw

        # evidencias: líneas EVIDENCE: entre esta SIGNAL y la siguiente
        block_start = m.end()
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(output)
        evidences = [
            {"kind": "quote", "content": e.group(1).strip()}
            for e in _EVIDENCE_RE.finditer(output, block_start, block_end)
            if e.group(1).strip()
        ]
        signals.append({
            "type": stype,
            "title": title[:200],
            "summary": summary,
            "evidences": evidences,
        })
    return signals


def extract_from_mission(db: Session, mission, mission_run=None) -> List[Signal]:
    """Genera Signals desde los step_results del último workflow run de la misión.

    Devuelve las signals creadas (vacía si no hay marcadores).
    """
    from app.models.workflow import WorkflowRun

    created: List[Signal] = []
    if not mission.workflow_id:
        return created
    wf_run = None
    if mission_run and mission_run.workflow_run_id:
        wf_run = db.query(WorkflowRun).filter(WorkflowRun.id == mission_run.workflow_run_id).first()
    if not wf_run:
        wf_run = (
            db.query(WorkflowRun)
            .filter(WorkflowRun.workflow_id == mission.workflow_id)
            .order_by(WorkflowRun.started_at.desc())
            .first()
        )
    if not wf_run:
        return created

    for step in (wf_run.step_results or []):
        output = step.get("output") or ""
        parsed = extract_from_output(output)
        for p in parsed:
            if _already_extracted(db, mission.id, str(wf_run.id), step.get("step_name"), p):
                continue
            signal = create_signal(
                db,
                mission_id=str(mission.id),
                title=p["title"],
                type=p["type"],
                summary=p["summary"],
                source_step=step.get("step_name"),
                agent_id=step.get("agent_id"),
                agent_name=step.get("agent_name"),
                workflow_run_id=str(wf_run.id),
                mission_run_id=str(mission_run.id) if mission_run else None,
                evidences=p["evidences"],
            )
            created.append(signal)
        # children de bloques paralelos
        for child in step.get("children") or []:
            cparsed = extract_from_output(child.get("output") or "")
            for p in cparsed:
                source_step = f"{step.get('step_name')} > {child.get('name')}"
                if _already_extracted(db, mission.id, str(wf_run.id), source_step, p):
                    continue
                signal = create_signal(
                    db,
                    mission_id=str(mission.id),
                    title=p["title"],
                    type=p["type"],
                    summary=p["summary"],
                    source_step=source_step,
                    agent_id=child.get("agent_id"),
                    agent_name=child.get("agent_name"),
                    workflow_run_id=str(wf_run.id),
                    mission_run_id=str(mission_run.id) if mission_run else None,
                    evidences=p["evidences"],
                )
                created.append(signal)
    return created


def _already_extracted(db: Session, mission_id, workflow_run_id: str,
                       source_step: Optional[str], parsed: dict) -> bool:
    """Evita duplicar una Signal al reintentar extraction del mismo output."""
    return db.query(Signal.id).filter(
        Signal.mission_id == mission_id,
        Signal.workflow_run_id == workflow_run_id,
        Signal.source_step == source_step,
        Signal.type == parsed["type"],
        Signal.title == parsed["title"],
    ).first() is not None


def _link_evidence_ids(db: Session, mission, signal: Signal) -> None:
    """Agrega los evidence ids de la signal a missions.evidence_ids (trazabilidad)."""
    ids = [str(i) for i in (mission.evidence_ids or [])]
    changed = False
    for ev in signal.evidences:
        if str(ev.id) not in ids:
            ids.append(str(ev.id))
            changed = True
    if changed:
        mission.evidence_ids = ids
        db.commit()
