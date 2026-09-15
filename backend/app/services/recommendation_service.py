"""Deterministic, read-only operational recommendations."""

from __future__ import annotations

from pathlib import Path
import subprocess

from app.models.mission import Mission, MissionRun
from app.services.capability_readiness import execution_overview


def _item(severity: str, reason: str, source: str, action: str, command: str) -> dict:
    return {"severity": severity, "reason": reason, "source": source, "recommended_action": action, "command": command}


def _dirty_repository(cwd: str | Path | None) -> bool:
    root = Path(cwd or Path.cwd())
    if not (root / ".git").exists():
        return False
    try:
        return bool(subprocess.run(["git", "-C", str(root), "status", "--porcelain"], capture_output=True, text=True, timeout=2).stdout.strip())
    except OSError:
        return False


def recommendations(db, *, cwd: str | Path | None = None, limit: int = 5) -> list[dict]:
    """Stable rules ordered by urgency, without LLMs or mutations."""
    rows: list[dict] = []
    approvals = db.query(Mission).filter(Mission.status == "waiting_approval").count()
    if approvals:
        rows.append(_item("WARNING", f"{approvals} approval(s) are waiting.", "missions", "Review pending approval gates.", "conciencia approvals"))
    failed = db.query(Mission).filter(Mission.status == "failed").count()
    if failed:
        rows.append(_item("WARNING", f"{failed} mission(s) failed.", "missions", "Inspect the failed mission and its latest run.", "conciencia mission list --status failed"))
    blocked_runs = db.query(MissionRun).filter(MissionRun.status == "failed").count()
    if blocked_runs and not failed:
        rows.append(_item("WARNING", f"{blocked_runs} run(s) failed.", "runs", "Inspect failed execution details.", "conciencia run list --status failed"))
    missing_criteria = db.query(Mission).filter(Mission.status.in_(["draft", "planned", "ready"])).all()
    missing_criteria = [mission for mission in missing_criteria if not mission.success_criteria]
    if missing_criteria:
        rows.append(_item("RECOMMENDED", f"{len(missing_criteria)} active mission(s) have no success criteria.", "missions", "Define success criteria before execution.", "conciencia mission list"))
    if _dirty_repository(cwd):
        rows.append(_item("INFO", "The current repository has uncommitted changes.", "git", "Review the working tree before switching work.", "git status --short"))
    if not execution_overview(db)["ready"]:
        rows.append(_item("RECOMMENDED", "No execution runtime is ready.", "runtimes", "Review runtime readiness and enable only approved runtimes.", "conciencia doctor"))
    from app.services.workspace_semantic import workspace_semantic_status
    semantic = workspace_semantic_status(db, cwd=str(cwd) if cwd else None)
    if semantic["state"] == "disabled":
        rows.append(_item("INFO", "Workspace retrieval is lexical because embeddings are unavailable.", "workspace retrieval", "Review optional embedding configuration.", "conciencia doctor"))
    return rows[:limit]
