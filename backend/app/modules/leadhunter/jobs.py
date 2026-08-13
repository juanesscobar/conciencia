"""Ejecutor async de LeadHunterJobs: threading + estado cancelable + retry.

El job corre en un thread daemon para no bloquear el request HTTP.
El estado (pending/running/completed/failed/cancelled) vive en DB.
El progreso se expone como string (searching → extracting → validating → scoring → done).
"""

import logging
import threading
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .models import LeadHunterJob, LeadHunterJobStatus
from .sources import get_all_sources

log = logging.getLogger("leadhunter.jobs")

# job_id -> threading.Event de cancelación (en memoria, suficiente para un solo proceso)
_cancel_events: dict[str, threading.Event] = {}
_jobs_lock = threading.Lock()


def _new_event(job_id: str) -> threading.Event:
    ev = threading.Event()
    with _jobs_lock:
        _cancel_events[job_id] = ev
    return ev


def cancel_requested(job_id: str) -> bool:
    with _jobs_lock:
        ev = _cancel_events.get(job_id)
    return bool(ev and ev.is_set())


def request_cancel(job_id: str) -> None:
    with _jobs_lock:
        ev = _cancel_events.get(job_id)
    if ev:
        ev.set()


def _clear_cancel(job_id: str) -> None:
    with _jobs_lock:
        _cancel_events.pop(job_id, None)


def _source_names(criteria: Optional[dict]) -> list[str]:
    """Resuelve qué fuentes correr según los criterios del job.
    Si el usuario pide una fuente inexistente, levanta ValueError para que el job falle limpio."""
    sources = get_all_sources()
    if not criteria:
        return list(sources.keys())
    src = (criteria.get("source") or "").strip().lower()
    if src:
        if src not in sources:
            raise ValueError(f"Fuente desconocida: {src}. Disponibles: {', '.join(sources)}")
        return [src]
    return list(sources.keys())


def run_job(job_id: str) -> None:
    """Ejecuta el job en su propio thread (daemon). Cierra su propia sesión de DB."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        _execute(db, job_id)
    except Exception as e:  # noqa: BLE001
        log.exception(f"job {job_id} crash")
        job = db.query(LeadHunterJob).filter(LeadHunterJob.id == job_id).first()
        if job and job.status == LeadHunterJobStatus.RUNNING:
            job.status = LeadHunterJobStatus.FAILED
            job.error = str(e)[:500]
            job.completed_at = datetime.utcnow()
            db.commit()
    finally:
        _clear_cancel(job_id)
        db.close()


def _execute(db: Session, job_id: str) -> None:
    from .discovery import run_discovery
    from .models import Lead

    job = db.query(LeadHunterJob).filter(LeadHunterJob.id == job_id).first()
    if not job:
        return
    if job.status in (LeadHunterJobStatus.RUNNING, LeadHunterJobStatus.COMPLETED):
        return

    criteria = job.criteria or {}
    limit = criteria.get("limit")
    try:
        sources = _source_names(criteria)
    except ValueError as e:
        job.status = LeadHunterJobStatus.FAILED
        job.error = str(e)[:500]
        job.completed_at = datetime.utcnow()
        job.progress = None
        db.commit()
        log.info(f"job {job_id} falló: {e}")
        return

    job.status = LeadHunterJobStatus.RUNNING
    job.started_at = datetime.utcnow()
    job.error = None
    job.progress = "searching"
    db.commit()

    total_added = 0
    total_dupes = 0
    results = []

    for name in sources:
        if cancel_requested(job_id):
            job.status = LeadHunterJobStatus.CANCELLED
            job.progress = None
            job.completed_at = datetime.utcnow()
            db.commit()
            log.info(f"job {job_id} cancelado por el usuario")
            return

        job.progress = "extracting"
        db.commit()
        try:
            # run_discovery crea su propio LeadHuntRun por fuente y asocia job_id
            result = run_discovery(db, source=name, limit=limit, job_id=job.id)
            r = result["results"][0] if result["results"] else {"status": "error", "error": "sin resultados"}
            total_added += r.get("added", 0)
            total_dupes += r.get("duplicates", 0)
            results.append(r)
            db.commit()
        except Exception as e:  # noqa: BLE001
            job.status = LeadHunterJobStatus.FAILED
            job.error = str(e)[:500]
            job.completed_at = datetime.utcnow()
            job.progress = None
            db.commit()
            return

        job.progress = "validating"
        db.commit()

    if cancel_requested(job_id):
        job.status = LeadHunterJobStatus.CANCELLED
        job.progress = None
    else:
        job.status = LeadHunterJobStatus.COMPLETED
        job.progress = "done"

    job.results_count = total_added
    job.duplicates_count = total_dupes
    job.completed_at = datetime.utcnow()
    job.meta = {"results": results} if hasattr(job, "meta") else None
    db.commit()
    log.info(f"job {job_id} completado: +{total_added} leads ({total_dupes} dupes)")


def start_job(job_id: str) -> None:
    """Lanza el thread daemon que ejecuta el job."""
    _new_event(job_id)
    t = threading.Thread(target=run_job, args=(job_id,), daemon=True, name=f"lh-job-{job_id[:8]}")
    t.start()


def create_job(db: Session, *, name: Optional[str], project_id: Optional[str], criteria: Optional[dict]) -> LeadHunterJob:
    """Crea el job en estado pending y lo lanza."""
    job = LeadHunterJob(
        id=str(uuid.uuid4()),
        name=name or "Prospección",
        project_id=project_id,
        criteria=criteria or {},
        status=LeadHunterJobStatus.PENDING,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    start_job(job.id)
    return job
