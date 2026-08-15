"""Scheduler de Lead Hunter: corre el descubrimiento con cron configurable."""

import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

log = logging.getLogger("leadhunter.scheduler")

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    """Inicia el scheduler con LEADHUNTER_CRON (ej: '0 9 * * 1' = lunes 09:00)."""
    global _scheduler

    expr = os.getenv("LEADHUNTER_CRON", "0 9 * * 1").strip()
    if not expr or expr.lower() in ("off", "none", "disabled", "0"):
        log.info("Lead Hunter scheduler deshabilitado (LEADHUNTER_CRON vacío)")
        return

    try:
        trigger = CronTrigger.from_crontab(expr)
    except Exception as e:  # noqa: BLE001
        log.error(f"LEADHUNTER_CRON inválido ('{expr}'): {e}. Scheduler deshabilitado.")
        return

    _scheduler = BackgroundScheduler(timezone="America/Asuncion")
    _scheduler.add_job(
        _run_job,
        trigger,
        id="leadhunter_discovery",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    log.info(f"Lead Hunter scheduler activo — descubrimiento programado: '{expr}' (America/Asuncion)")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def _run_job() -> None:
    from . import jobs
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        job = jobs.create_job(
            db,
            name="Scheduled Discovery",
            project_id=None,
            criteria={"source": "overpass"},
        )
        log.info(f"Lead Hunter scheduled job created: {job.id}")
    except Exception as e:  # noqa: BLE001
        log.error(f"Lead Hunter scheduled job failed: {e}")
    finally:
        db.close()
