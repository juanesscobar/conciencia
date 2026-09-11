"""Professional report structure, dates and portable exporters."""

import json
import uuid
from datetime import datetime
from pathlib import Path

from typer.testing import CliRunner

from cli import app

runner = CliRunner()


def _seed_report(db, tmp_path, report_id: str, title: str):
    from app.models.deliverable import Deliverable, DeliverableStatus, DeliverableType
    from app.models.project import Project

    project = db.query(Project).filter(Project.name == "Report refs").first()
    if not project:
        project = Project(name="Report refs")
        db.add(project)
        db.commit()
    path = tmp_path / f"{report_id}.json"
    path.write_text(json.dumps({"title": title, "project": project.name, "period_from": "2026-08-27", "period_to": "2026-09-04", "executive_summary": [], "completed_work": [], "major_results": [], "technical_changes": [], "tests_and_validation": [], "deployments": [], "problems_resolved": [], "pending_work": [], "next_steps": [], "evidence_summary": {"coverage": "none", "item_count": 0}}), encoding="utf-8")
    report = Deliverable(id=uuid.UUID(report_id), project_id=project.id, title=title, type=DeliverableType.REPORT, status=DeliverableStatus.FINAL, url=str(path))
    db.add(report)
    db.commit()
    return report


def test_report_dates_are_unambiguous():
    from app.services.report_dates import parse_report_date

    assert parse_report_date("27.08.26").isoformat() == "2026-08-27"
    assert parse_report_date("27/08/2026").isoformat() == "2026-08-27"
    assert parse_report_date("2026-08-27").isoformat() == "2026-08-27"


def test_professional_report_filters_evidence_content_and_has_neutral_payload(db):
    from app.models.activity import Activity, ActivityType
    from app.models.mission import Mission
    from app.models.project import Project
    from app.models.signal import Evidence, Signal
    from app.services.report_service import build_professional_report, to_external_payload

    project = Project(name="Reports")
    mission = Mission(name="Completed work", objective="Ship", status="completed", project=project)
    db.add_all([project, mission])
    db.commit()
    db.add(Activity(project=project, type=ActivityType.TASK_CHANGE, description="Implemented portable reporting"))
    signal = Signal(mission_id=mission.id, title="Verified", summary="ok")
    db.add(signal)
    db.commit()
    db.add(Evidence(signal_id=signal.id, content="API_SECRET=must-not-appear"))
    db.commit()

    report = build_professional_report(db, project_id=project.id, since="2026-08-27", until="2026-09-04")
    serialized = json.dumps(report)
    assert "API_SECRET" not in serialized
    assert "provenance_refs" in report
    external = to_external_payload(report)
    assert "provenance_refs" not in external
    assert "project" in external


def test_workspace_report_discovers_active_projects_and_keeps_unassigned_work(db):
    from datetime import datetime, timedelta, timezone

    from app.models.activity import Activity, ActivityType
    from app.models.project import Project
    from app.services.report_service import build_professional_report

    first = Project(name="First active")
    second = Project(name="Second active")
    inactive = Project(name="No period activity")
    db.add_all([first, second, inactive])
    db.commit()
    db.add_all([
        Activity(project=first, type=ActivityType.TASK_CHANGE, description="First project change"),
        Activity(project=second, type=ActivityType.TASK_CHANGE, description="Second project change"),
        Activity(project_id=None, type=ActivityType.TASK_CHANGE, description="Workspace-wide change"),
    ])
    db.commit()

    # ventana relativa a HOY: las actividades se crean ahora (test date-independent)
    today = datetime.now(timezone.utc).date()
    report = build_professional_report(
        db,
        since=(today - timedelta(days=1)).isoformat(),
        until=(today + timedelta(days=1)).isoformat(),
    )
    assert report["scope"] == "workspace"
    names = {project["project"] for project in report["projects"]}
    assert {"First active", "Second active", "Unassigned / workspace-level work"} <= names
    assert "No period activity" not in names
    assert report["metrics"]["projects_touched"] == 2


def test_workspace_report_does_not_recursively_include_prior_report_content(db):
    from app.models.deliverable import Deliverable, DeliverableStatus, DeliverableType
    from app.models.project import Project
    from app.services.report_service import build_professional_report

    project = Project(name="Prior report project")
    db.add(project)
    db.commit()
    db.add(Deliverable(project=project, title="Prior report", description="API_SECRET=not-professional-content", type=DeliverableType.REPORT, status=DeliverableStatus.FINAL))
    db.commit()
    report = build_professional_report(db, since="2026-08-27", until="2026-09-05")
    assert "API_SECRET" not in json.dumps(report)


def test_project_and_workspace_reports_have_distinct_scopes_and_blockers(db):
    from app.models.activity import Activity, ActivityType
    from app.models.mission import Mission
    from app.models.project import Project
    from app.services.report_service import build_professional_report

    project = Project(name="Scoped report")
    db.add(project)
    db.commit()
    db.add_all([
        Activity(project=project, type=ActivityType.TASK_CHANGE, description="Scoped work"),
        Mission(name="Awaiting approval", objective="Review", status="waiting_approval", project=project),
    ])
    db.commit()
    scoped = build_professional_report(db, project_id=project.id, since="2026-08-27", until="2026-09-05")
    workspace = build_professional_report(db, since="2026-08-27", until="2026-09-05")
    assert scoped["scope"] == "project"
    assert scoped["project"] == "Scoped report"
    assert workspace["scope"] == "workspace"
    assert any("approval" in blocker.casefold() for blocker in workspace["workspace_blockers"])


def test_report_create_and_exports_are_versioned(db, monkeypatch, tmp_path):
    from app.models.activity import Activity, ActivityType
    from app.models.project import Project

    project = Project(name="Conciencia")
    db.add(project)
    db.commit()
    db.add(Activity(project=project, type=ActivityType.TASK_CHANGE, description="Professional report feature", created_at=datetime(2026, 8, 28, 12, 0, 0)))
    db.commit()
    monkeypatch.chdir(tmp_path)

    created = runner.invoke(app, ["report", "create", "--since", "27.08.26", "--until", "04/09/2026", "--project", "Conciencia", "--json"])
    assert created.exit_code == 0, created.stdout
    payload = json.loads(created.stdout)
    assert payload["professional_report"]["period_from"] == "2026-08-27"
    assert payload["professional_report"]["period_to"] == "2026-09-04"
    assert (tmp_path / payload["canonical_path"]).is_file()

    for format in ("txt", "md", "json", "pdf"):
        exported = runner.invoke(app, ["report", "export", "latest", "--format", format, "--json"])
        assert exported.exit_code == 0, exported.stdout
        path = tmp_path / json.loads(exported.stdout)["path"]
        assert path.is_file()
        assert path.stat().st_size > 0
        if format == "txt":
            assert "#Executive summary" not in path.read_text(encoding="utf-8")


def test_report_create_without_project_persists_workspace_scope(db, monkeypatch, tmp_path):
    from app.models.activity import Activity, ActivityType

    db.add(Activity(type=ActivityType.TASK_CHANGE, description="Workspace report work"))
    db.commit()
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["report", "create", "--since", "2026-08-27", "--until", "2026-09-05", "--json"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["report"]["project_id"] is None
    assert payload["professional_report"]["scope"] == "workspace"


def test_report_references_cover_root_inspect_and_export(db, tmp_path):
    report = _seed_report(db, tmp_path, "a92e91f4-74fa-4d74-b18d-8e5917d8eeb5", "Reference report")

    for args in (["report", "--json"], ["report", "list", "--json"]):
        result = runner.invoke(app, args)
        assert result.exit_code == 0, result.stdout
        assert json.loads(result.stdout)[0]["id"] == str(report.id)
    for ref in ("latest", str(report.id)[:8], str(report.id)):
        inspected = runner.invoke(app, ["report", "inspect", ref, "--json"])
        assert inspected.exit_code == 0, inspected.stdout
        assert json.loads(inspected.stdout)["id"] == str(report.id)
        exported = runner.invoke(app, ["report", "export", ref, "--format", "txt", "--json"])
        assert exported.exit_code == 0, exported.stdout
        assert Path(json.loads(exported.stdout)["path"]).is_file()


def test_report_reference_errors_are_clear_and_never_choose_ambiguous(db, tmp_path):
    _seed_report(db, tmp_path, "a92e0000-0000-4000-8000-000000000001", "First")
    _seed_report(db, tmp_path, "a92e1111-0000-4000-8000-000000000002", "Second")

    missing = runner.invoke(app, ["report", "inspect", "nope"])
    assert missing.exit_code == 1
    assert "Report not found: nope" in missing.stdout
    ambiguous = runner.invoke(app, ["report", "inspect", "a92e"])
    assert ambiguous.exit_code == 1
    assert "Ambiguous report reference: a92e" in ambiguous.stdout
