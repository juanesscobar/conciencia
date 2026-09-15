"""Canonical professional report projections over the existing Work ledger."""

from __future__ import annotations

import os
from collections import Counter
from datetime import datetime, time, timezone

from app.models.project import Project
from app.models.setting import Setting
from app.services.report_dates import parse_report_date
from app.services.work_service import WorkItem, collect_work_items


def _safe_responsible(db) -> str | None:
    setting = db.query(Setting).filter(Setting.key == "REPORT_RESPONSIBLE").first()
    return (setting.value if setting and setting.value else os.getenv("CONCIENCIA_RESPONSIBLE", "")).strip() or None


def _clean(values: list[str], limit: int = 8) -> list[str]:
    seen: set[str] = set()
    output = []
    for value in values:
        cleaned = " ".join((value or "").split())
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            output.append(cleaned)
        if len(output) >= limit:
            break
    return output


def _text(item: WorkItem) -> str:
    if item.source_type == "evidence":
        return item.title
    if not item.summary or item.summary.strip() == item.title.strip():
        return item.title
    return " ".join(part for part in (item.title, item.summary) if part)


def _classify(items: list[WorkItem]) -> dict:
    categories = {key: [] for key in ("completed_work", "major_results", "technical_changes", "tests_and_validation", "deployments", "problems_resolved", "pending_work")}
    for item in items:
        value = _text(item)
        kind = item.type.casefold()
        # Reports are prior projections, not work outcomes for the next report.
        if item.source_type == "evidence" or kind == "deliverable.report":
            continue
        if kind.startswith(("mission.completed", "run.completed")):
            categories["completed_work"].append(value)
            categories["problems_resolved"].append(value)
        elif kind.startswith("deliverable."):
            categories["major_results"].append(value)
        elif "deploy" in kind or "release" in kind:
            categories["deployments"].append(value)
        elif "test" in kind or "validation" in kind:
            categories["tests_and_validation"].append(value)
        elif kind.startswith(("mission.failed", "run.failed")) or "risk" in kind:
            categories["pending_work"].append(value)
        elif kind.startswith("mission.") and not kind.endswith(("completed", "failed", "cancelled")):
            categories["pending_work"].append(value)
        elif kind.startswith("git.commit") or kind.startswith("activity."):
            categories["technical_changes"].append(value)
    return {key: _clean(values) for key, values in categories.items()}


def _metrics(items: list[WorkItem]) -> dict:
    types = Counter(item.type for item in items)
    sources = Counter(item.source_type for item in items)
    return {
        "work_items": len(items),
        "git_commits": sources.get("git_commit", 0),
        "missions_completed": sum(count for kind, count in types.items() if kind == "mission.completed"),
        "missions_failed": sum(count for kind, count in types.items() if kind == "mission.failed"),
        "runs": sum(count for kind, count in types.items() if kind.startswith("run.")),
        "reports": sum(count for kind, count in types.items() if kind == "deliverable.report"),
        "deployments": sum(count for kind, count in types.items() if "deploy" in kind or "release" in kind),
        "validation_records": sum(count for kind, count in types.items() if "test" in kind or "validation" in kind),
    }


def _provenance(items: list[WorkItem]) -> list[dict]:
    return [{"source": item.source_type, "work_type": item.type, "title": "Evidence recorded" if item.source_type == "evidence" else item.title, "timestamp": item.timestamp.isoformat()} for item in items[:30]]


def _blockers_and_priorities(db, *, cwd) -> tuple[list[str], list[str]]:
    from app.services.connection_service import list_connections
    from app.services.recommendation_service import recommendations

    rows = recommendations(db, cwd=cwd, limit=7)
    blockers = [row["reason"] for row in rows if row["severity"] == "WARNING"]
    for connection in list_connections(db):
        if connection["status"] == "contract_required":
            blockers.append(f"{connection['name']} connection requires an API contract.")
    return _clean(blockers, 7), _clean([row["recommended_action"] for row in rows], 7)


def _project_summary(project: Project | None, items: list[WorkItem]) -> dict:
    classification = _classify(items)
    name = project.name if project else "Unassigned / workspace-level work"
    status = getattr(project.status, "value", str(project.status)) if project else "workspace-level"
    return {"project": name, "status": status, **classification, "next_steps": ["Review pending work and approval gates."] if classification["pending_work"] else ["Continue with the next planned objective."], "metrics": _metrics(items)}


def _period(since, until) -> tuple:
    start = parse_report_date(since) or datetime.now(timezone.utc).date()
    end = parse_report_date(until) or datetime.now(timezone.utc).date()
    if end < start:
        raise ValueError("Report end date must be on or after the start date.")
    return start, end


def build_professional_report(db, *, project_id=None, since=None, until=None, cwd=None, title: str | None = None) -> dict:
    """Build a project or workspace projection without assigning unscoped WorkItems."""
    start, end = _period(since, until)
    until_dt = datetime.combine(end, time.max, tzinfo=timezone.utc)
    all_items = collect_work_items(db, since=start.isoformat(), until=until_dt.isoformat(), project_id=project_id, cwd=cwd)
    # A report is a prior projection, never source content for another report.
    items = [item for item in all_items if item.type.casefold() != "deliverable.report"]
    report_count = _metrics(all_items)["reports"]
    if project_id is not None:
        project = db.query(Project).filter(Project.id == project_id).first()
        classification = _classify(items)
        return {
            "title": title or f"Professional work report - {project.name if project else 'Project'}",
            "scope": "project", "kind": "professional", "responsible_person": _safe_responsible(db),
            "project": project.name if project else "Project", "period_from": start.isoformat(), "period_to": end.isoformat(),
            "executive_summary": [f"{len(items)} work item(s) were recorded."] + ([f"Completed outcomes: {len(classification['completed_work'])}."] if classification["completed_work"] else []),
            **classification,
            "next_steps": ["Review pending work and approval gates."] if classification["pending_work"] else ["Continue with the next planned objective."],
            "metrics": _metrics(items) | {"reports": report_count},
            "evidence_summary": {"coverage": "full" if len({item.source_type for item in items}) > 1 else ("partial" if items else "none"), "item_count": len(items), "sources": dict(Counter(item.source_type for item in items))},
            "provenance_refs": _provenance(items),
        }

    projects = {str(project.id): project for project in db.query(Project).all()}
    groups: dict[str | None, list[WorkItem]] = {}
    for item in items:
        groups.setdefault(item.project_id, []).append(item)
    summaries = [_project_summary(projects.get(project_id), group) for project_id, group in groups.items()]
    summaries.sort(key=lambda row: (row["project"] == "Unassigned / workspace-level work", row["project"].casefold()))
    blockers, priorities = _blockers_and_priorities(db, cwd=cwd)
    metrics = _metrics(items) | {"reports": report_count, "projects_touched": len([row for row in summaries if row["status"] != "workspace-level"])}
    results = _clean([f"{row['project']}: {row['metrics']['work_items']} work item(s)." for row in summaries if row["metrics"]["work_items"]])
    return {
        "title": title or "Professional workspace report", "scope": "workspace", "kind": "professional", "responsible_person": _safe_responsible(db),
        "period_from": start.isoformat(), "period_to": end.isoformat(),
        "executive_summary": [f"{metrics['work_items']} work item(s) across {metrics['projects_touched']} project(s)."] + ([f"Current blockers: {len(blockers)}."] if blockers else []),
        "projects": summaries, "workspace_results": results, "workspace_blockers": blockers,
        "workspace_next_priorities": priorities[:7], "metrics": metrics,
        "evidence_summary": {"coverage": "full" if len({item.source_type for item in items}) > 1 else ("partial" if items else "none"), "item_count": len(items), "sources": dict(Counter(item.source_type for item in items))},
        "provenance_refs": _provenance(items),
    }


def to_external_payload(report: dict) -> dict:
    """Connector-neutral payload: no vendor fields, credentials, or internal IDs."""
    shared = ("title", "scope", "kind", "responsible_person", "period_from", "period_to", "executive_summary", "metrics", "evidence_summary")
    scoped = ("projects", "workspace_results", "workspace_blockers", "workspace_next_priorities") if report.get("scope") == "workspace" else ("project", "completed_work", "major_results", "technical_changes", "tests_and_validation", "deployments", "problems_resolved", "pending_work", "next_steps")
    return {key: report[key] for key in (*shared, *scoped) if key in report}
