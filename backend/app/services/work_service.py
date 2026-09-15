"""Workspace work ledger and summary helpers.

This phase reuses existing first-class entities instead of introducing a new
database table:
- Project, Mission, MissionRun, Activity, Signal, Evidence, Deliverable
- Git history via `git log`

The service produces a normalized activity stream that can be used for:
- `conciencia work timeline`
- `conciencia work search`
- `conciencia work summarize`
- `conciencia report create --from-work`
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.deliverable import Deliverable
from app.models.mission import Mission, MissionRun
from app.models.project import Project
from app.models.signal import Evidence, Signal

_SEARCH_STOP_WORDS = {
    "a", "al", "and", "como", "con", "de", "del", "el", "en", "for", "how",
    "la", "las", "lo", "los", "me", "para", "por", "que", "que", "se", "the",
    "todo", "una", "un", "what", "we", "y",
}


@dataclass
class WorkItem:
    id: str
    workspace_id: str
    project_id: Optional[str]
    type: str
    title: str
    summary: str
    timestamp: datetime
    source_type: str
    source_ref: str
    metadata: dict
    tags: list[str]
    evidence_refs: list[str]
    created_at: datetime

    def to_dict(self) -> dict:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["created_at"] = self.created_at.isoformat()
        return data


def _parse_dt(value: Optional[str | date | datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    raw = str(value).strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            from app.services.report_dates import parse_report_date
            parsed = datetime.combine(parse_report_date(raw), time.min)
        except ValueError:
            return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _project_uuid(project_id: Optional[str | uuid.UUID]) -> Optional[uuid.UUID]:
    if project_id is None:
        return None
    if isinstance(project_id, uuid.UUID):
        return project_id
    raw = str(project_id).strip()
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        return None


def _normalize_item(item: WorkItem) -> WorkItem:
    item.timestamp = _utc(item.timestamp) or item.timestamp
    item.created_at = _utc(item.created_at) or item.created_at
    return item


def _in_range(ts: Optional[datetime], since: Optional[datetime], until: Optional[datetime]) -> bool:
    ts = _utc(ts)
    since = _utc(since)
    until = _utc(until)
    if ts is None:
        return False
    if since and ts < since:
        return False
    if until and ts > until:
        return False
    return True


def _project_name(db: Session, project_id: Optional[str]) -> Optional[str]:
    project_uuid = _project_uuid(project_id)
    if not project_uuid:
        return None
    project = db.query(Project).filter(Project.id == project_uuid).first()
    return project.name if project else None


def _workspace_id(db: Session) -> str:
    # Stable local workspace identifier without introducing new storage.
    return os.path.basename(os.path.abspath(os.getcwd())) or "workspace"


def _git_commits(cwd: Optional[str], since: Optional[datetime], until: Optional[datetime]) -> list[WorkItem]:
    root = Path(cwd or os.getcwd()).resolve()
    if not (root / ".git").exists():
        return []
    cmd = [
        "git",
        "-C",
        str(root),
        "log",
        "--date=iso-strict",
        "--pretty=format:%H|%an|%ad|%s",
    ]
    since = _utc(since)
    until = _utc(until)
    if since:
        cmd.extend(["--since", since.isoformat()])
    if until:
        cmd.extend(["--until", until.isoformat()])
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except Exception:
        return []
    if proc.returncode != 0:
        return []
    items: list[WorkItem] = []
    for line in proc.stdout.splitlines():
        parts = line.split("|", 3)
        if len(parts) != 4:
            continue
        sha, author, ts, message = parts
        try:
            timestamp = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        timestamp = _utc(timestamp) or timestamp
        items.append(
            WorkItem(
                id=f"git:{sha}",
                workspace_id=root.name,
                project_id=None,
                type="git.commit",
                title=message[:120] or sha[:8],
                summary=message,
                timestamp=timestamp,
                source_type="git_commit",
                source_ref=sha,
                metadata={"author": author, "message": message},
                tags=["git", "commit"],
                evidence_refs=[],
                created_at=timestamp,
            )
        )
    return items


def _activity_items(db: Session, since: Optional[datetime], until: Optional[datetime], project_id: Optional[str]) -> list[WorkItem]:
    project_uuid = _project_uuid(project_id)
    q = db.query(Activity)
    if project_uuid:
        q = q.filter(Activity.project_id == project_uuid)
    items: list[WorkItem] = []
    for row in q.order_by(Activity.created_at.desc()).all():
        created_at = _utc(row.created_at)
        if not _in_range(created_at, since, until):
            continue
        meta = dict(row.extra_data or {})
        items.append(
            WorkItem(
                id=f"activity:{row.id}",
                workspace_id=_workspace_id(db),
                project_id=str(row.project_id) if row.project_id else None,
                type=f"activity.{getattr(row.type, 'value', str(row.type))}",
                title=row.description[:120],
                summary=row.description,
                timestamp=created_at or row.created_at,
                source_type="activity",
                source_ref=str(row.id),
                metadata=meta,
                tags=list(meta.get("tags") or []),
                evidence_refs=list(meta.get("evidence_refs") or []),
                created_at=created_at or row.created_at,
            )
        )
    return items


def _mission_items(db: Session, since: Optional[datetime], until: Optional[datetime], project_id: Optional[str]) -> list[WorkItem]:
    project_uuid = _project_uuid(project_id)
    q = db.query(Mission)
    if project_uuid:
        q = q.filter(Mission.project_id == project_uuid)
    items: list[WorkItem] = []
    for mission in q.order_by(Mission.created_at.desc()).all():
        created = _utc(mission.created_at or mission.started_at)
        if _in_range(created, since, until):
            items.append(
                WorkItem(
                    id=f"mission:{mission.id}:created",
                    workspace_id=_workspace_id(db),
                    project_id=str(mission.project_id) if mission.project_id else None,
                    type="mission.created",
                    title=mission.name,
                    summary=f"{mission.type} mission created: {mission.objective}",
                    timestamp=created,
                    source_type="mission",
                    source_ref=str(mission.id),
                    metadata={"status": mission.status, "type": mission.type, "objective": mission.objective},
                    tags=[mission.type, mission.status],
                    evidence_refs=list(mission.evidence_ids or []),
                    created_at=created,
                )
            )
        completed_at = _utc(mission.completed_at)
        if completed_at and _in_range(completed_at, since, until):
            summary_text = None
            if isinstance(mission.outcome, dict):
                summary_text = mission.outcome.get("summary")
            summary_text = summary_text or mission.objective or mission.name or mission.status
            items.append(
                WorkItem(
                    id=f"mission:{mission.id}:done",
                    workspace_id=_workspace_id(db),
                    project_id=str(mission.project_id) if mission.project_id else None,
                    type=f"mission.{mission.status}",
                    title=mission.name,
                    summary=summary_text,
                    timestamp=completed_at,
                    source_type="mission",
                    source_ref=str(mission.id),
                    metadata={"status": mission.status, "outcome": mission.outcome or {}},
                    tags=[mission.type, mission.status],
                    evidence_refs=list(mission.evidence_ids or []),
                    created_at=completed_at,
                )
            )
    return items


def _run_items(db: Session, since: Optional[datetime], until: Optional[datetime], project_id: Optional[str]) -> list[WorkItem]:
    project_uuid = _project_uuid(project_id)
    q = db.query(MissionRun).join(Mission, MissionRun.mission_id == Mission.id)
    if project_uuid:
        q = q.filter(Mission.project_id == project_uuid)
    items: list[WorkItem] = []
    for run in q.order_by(MissionRun.started_at.desc()).all():
        started_at = _utc(run.started_at)
        completed_at = _utc(run.completed_at)
        if not _in_range(started_at, since, until) and not _in_range(completed_at, since, until):
            continue
        mission = run.mission
        ts = completed_at or started_at
        if ts is None:
            continue
        items.append(
            WorkItem(
                id=f"mission-run:{run.id}",
                workspace_id=_workspace_id(db),
                project_id=str(mission.project_id) if mission and mission.project_id else None,
                type=f"run.{run.status}",
                title=mission.name if mission else str(run.id),
                summary=run.error or f"Run {run.status} for {mission.name if mission else 'mission'}",
                timestamp=ts,
                source_type="mission_run",
                source_ref=str(run.id),
                metadata={"status": run.status, "workflow_run_id": run.workflow_run_id, "cost_usd": run.cost_usd or {}, "tokens": run.tokens or {}},
                tags=[run.status],
                evidence_refs=list(getattr(mission, "evidence_ids", []) or []),
                created_at=started_at or ts,
            )
        )
    return items


def _signal_items(db: Session, since: Optional[datetime], until: Optional[datetime], project_id: Optional[str]) -> list[WorkItem]:
    project_uuid = _project_uuid(project_id)
    q = db.query(Signal)
    if project_uuid:
        q = q.join(Mission, Signal.mission_id == Mission.id).filter(Mission.project_id == project_uuid)
    items: list[WorkItem] = []
    for signal in q.order_by(Signal.created_at.desc()).all():
        created_at = _utc(signal.created_at)
        if not _in_range(created_at, since, until):
            continue
        items.append(
            WorkItem(
                id=f"signal:{signal.id}",
                workspace_id=_workspace_id(db),
                project_id=str(signal.mission.project_id) if signal.mission and signal.mission.project_id else None,
                type=f"signal.{signal.type}",
                title=signal.title,
                summary=signal.summary or signal.title,
                timestamp=created_at or signal.created_at,
                source_type="signal",
                source_ref=str(signal.id),
                metadata={"status": signal.status, "mission_id": str(signal.mission_id)},
                tags=[signal.type, signal.status],
                evidence_refs=[str(e.id) for e in signal.evidences],
                created_at=created_at or signal.created_at,
            )
        )
    return items


def _evidence_items(db: Session, since: Optional[datetime], until: Optional[datetime], project_id: Optional[str]) -> list[WorkItem]:
    project_uuid = _project_uuid(project_id)
    q = db.query(Evidence).join(Signal, Evidence.signal_id == Signal.id)
    if project_uuid:
        q = q.join(Mission, Signal.mission_id == Mission.id).filter(Mission.project_id == project_uuid)
    items: list[WorkItem] = []
    for ev in q.order_by(Evidence.created_at.desc()).all():
        created_at = _utc(ev.created_at)
        if not _in_range(created_at, since, until):
            continue
        mission = ev.signal.mission if ev.signal else None
        items.append(
            WorkItem(
                id=f"evidence:{ev.id}",
                workspace_id=_workspace_id(db),
                project_id=str(mission.project_id) if mission and mission.project_id else None,
                type=f"evidence.{ev.kind}",
                title=ev.content[:120],
                summary=ev.content,
                timestamp=created_at or ev.created_at,
                source_type="evidence",
                source_ref=str(ev.id),
                metadata={"signal_id": str(ev.signal_id), "source": ev.source},
                tags=[ev.kind],
                evidence_refs=[str(ev.id)],
                created_at=created_at or ev.created_at,
            )
        )
    return items


def _deliverable_items(db: Session, since: Optional[datetime], until: Optional[datetime], project_id: Optional[str]) -> list[WorkItem]:
    project_uuid = _project_uuid(project_id)
    q = db.query(Deliverable)
    if project_uuid:
        q = q.filter(Deliverable.project_id == project_uuid)
    items: list[WorkItem] = []
    for row in q.order_by(Deliverable.created_at.desc()).all():
        created_at = _utc(row.created_at)
        if not _in_range(created_at, since, until):
            continue
        items.append(
            WorkItem(
                id=f"deliverable:{row.id}",
                workspace_id=_workspace_id(db),
                project_id=str(row.project_id) if row.project_id else None,
                type=f"deliverable.{getattr(row.type, 'value', str(row.type))}",
                title=row.title,
                summary=row.description or row.title,
                timestamp=created_at or row.created_at,
                source_type="deliverable",
                source_ref=str(row.id),
                metadata={"status": getattr(row.status, 'value', str(row.status)), "url": row.url, "external_id": row.external_id},
                tags=[getattr(row.type, 'value', str(row.type)), getattr(row.status, 'value', str(row.status))],
                evidence_refs=[],
                created_at=created_at or row.created_at,
            )
        )
    return items


def collect_work_items(
    db: Session,
    *,
    since: Optional[str | date | datetime] = None,
    until: Optional[str | date | datetime] = None,
    project_id: Optional[str] = None,
    cwd: Optional[str] = None,
) -> list[WorkItem]:
    since_dt = _parse_dt(since)
    until_dt = _parse_dt(until)
    items: list[WorkItem] = []
    items.extend(_activity_items(db, since_dt, until_dt, project_id))
    items.extend(_mission_items(db, since_dt, until_dt, project_id))
    items.extend(_run_items(db, since_dt, until_dt, project_id))
    items.extend(_signal_items(db, since_dt, until_dt, project_id))
    items.extend(_evidence_items(db, since_dt, until_dt, project_id))
    items.extend(_deliverable_items(db, since_dt, until_dt, project_id))
    items.extend(_git_commits(cwd, since_dt, until_dt))
    items = [_normalize_item(item) for item in items]
    items.sort(key=lambda item: item.timestamp, reverse=True)
    return items


def search_work_items(
    db: Session,
    *,
    query: str,
    since: Optional[str | date | datetime] = None,
    until: Optional[str | date | datetime] = None,
    project_id: Optional[str] = None,
    limit: int = 20,
    cwd: Optional[str] = None,
) -> list[dict]:
    items = collect_work_items(db, since=since, until=until, project_id=project_id, cwd=cwd)
    terms = [
        token for token in re.findall(r"\w+", query.casefold())
        if len(token) > 1 and token not in _SEARCH_STOP_WORDS
    ]
    if not terms:
        return [item.to_dict() for item in items[:limit]]

    scored: list[tuple[int, WorkItem]] = []
    for item in items:
        hay = " ".join(
            part
            for part in (
                item.type,
                item.title,
                item.summary or "",
                json.dumps(item.metadata, ensure_ascii=False),
                " ".join(item.tags),
                item.source_type,
                item.source_ref,
            )
            if part
        ).lower()
        score = 0
        for term in terms:
            if term in hay:
                score += 2
            if term in item.title.lower():
                score += 1
        if score:
            scored.append((score, item))
    scored.sort(key=lambda pair: (pair[0], pair[1].timestamp), reverse=True)
    return [item.to_dict() | {"score": score} for score, item in scored[:limit]]


def summarize_work(
    db: Session,
    *,
    since: Optional[str | date | datetime] = None,
    until: Optional[str | date | datetime] = None,
    project_id: Optional[str] = None,
    cwd: Optional[str] = None,
) -> dict:
    since_dt = _parse_dt(since)
    until_dt = _parse_dt(until) or datetime.now(timezone.utc)
    items = collect_work_items(db, since=since_dt, until=until_dt, project_id=project_id, cwd=cwd)

    projects = Counter()
    accomplishments: list[str] = []
    changes: list[str] = []
    decisions: list[str] = []
    tests: list[str] = []
    deployments: list[str] = []
    failures: list[str] = []
    resolved: list[str] = []
    docs: list[str] = []
    pending: list[str] = []
    evidence: list[str] = []
    sources = Counter(item.source_type for item in items)

    for item in items:
        if item.project_id:
            projects[item.project_id] += 1
        evidence.append(f"{item.source_type}:{item.source_ref}")
        text = f"{item.title} — {item.summary or ''}".strip(" —")
        if item.type.startswith("mission.completed") or item.type.startswith("run.completed"):
            accomplishments.append(text)
            resolved.append(text)
        elif item.type.startswith("mission.failed") or item.type.startswith("run.failed") or "risk" in item.type:
            failures.append(text)
        elif item.type.startswith("mission.") and not item.type.endswith(("completed", "failed")):
            pending.append(text)
        elif item.type.startswith("git.commit"):
            changes.append(text)
        elif item.type.startswith("signal.decision"):
            decisions.append(text)
        elif "deploy" in item.type or "release" in item.type:
            deployments.append(text)
        elif "test" in item.type:
            tests.append(text)
        elif item.type.startswith("deliverable.") or item.type.startswith("evidence."):
            docs.append(text)

    project_names = []
    if project_id:
        project_uuid = _project_uuid(project_id)
        if project_uuid:
            project = db.query(Project).filter(Project.id == project_uuid).first()
            if project:
                project_names.append(project.name)
    elif projects:
        ids = [pid for pid in (_project_uuid(pid) for pid in projects.keys()) if pid is not None]
        if ids:
            rows = db.query(Project).filter(Project.id.in_(ids)).all()
            project_names.extend([p.name for p in rows])

    coverage = "full" if (sources.get("git_commit") and sources.get("mission")) else "partial"
    if not items:
        coverage = "none"

    return {
        "period": {
            "since": since_dt.isoformat() if since_dt else None,
            "until": until_dt.isoformat() if until_dt else None,
        },
        "coverage": coverage,
        "sources": dict(sources),
        "projects": sorted(set(project_names)),
        "major_accomplishments": accomplishments[:10],
        "features_changes": changes[:15],
        "architecture_decisions": decisions[:10],
        "tests_validation": tests[:10],
        "deployments": deployments[:10],
        "failures_discovered": failures[:10],
        "resolved_problems": resolved[:10],
        "documents_deliverables": docs[:10],
        "pending_work": pending[:10],
        "evidence": evidence[:30],
        "item_count": len(items),
    }


def summarize_work_text(summary: dict) -> str:
    def _section(title: str, values: Iterable[str]) -> list[str]:
        values = [v for v in values if v]
        if not values:
            return [f"{title}", "  - none found"]
        return [f"{title}"] + [f"  - {v}" for v in values]

    lines: list[str] = []
    period = summary.get("period", {})
    lines.append("WORK SUMMARY")
    lines.append(f"{period.get('since') or 'unknown'} -> {period.get('until') or 'today'}")
    lines.append(f"Coverage: {summary.get('coverage', 'partial')}")
    lines.append("")
    lines.extend(_section("Projects", summary.get("projects", [])))
    lines.append("")
    lines.extend(_section("Major accomplishments", summary.get("major_accomplishments", [])))
    lines.append("")
    lines.extend(_section("Features / changes", summary.get("features_changes", [])))
    lines.append("")
    lines.extend(_section("Architecture decisions", summary.get("architecture_decisions", [])))
    lines.append("")
    lines.extend(_section("Tests and validation", summary.get("tests_validation", [])))
    lines.append("")
    lines.extend(_section("Deployments", summary.get("deployments", [])))
    lines.append("")
    lines.extend(_section("Failures / problems discovered", summary.get("failures_discovered", [])))
    lines.append("")
    lines.extend(_section("Resolved problems", summary.get("resolved_problems", [])))
    lines.append("")
    lines.extend(_section("Documents / deliverables", summary.get("documents_deliverables", [])))
    lines.append("")
    lines.extend(_section("Pending work", summary.get("pending_work", [])))
    lines.append("")
    lines.extend(_section("Evidence", summary.get("evidence", [])))
    return "\n".join(lines)
