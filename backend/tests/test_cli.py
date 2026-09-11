"""Tests Fase 6 — CLI `conciencia` (spec §19/§41).

Verifica que el CLI use la MISMA lógica de dominio que la API:
`conciencia search` debe devolver los mismos leads que POST /api/v1/leads/search.
Se apunta a la DB de test con DATABASE_URL.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli import app
from app.modules.leadhunter.models import Lead

runner = CliRunner()

TEST_DB_URL = "sqlite:///./test.db"


@pytest.fixture(autouse=True)
def _cli_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DB_URL)
    yield
    # `config set` escribe os.environ directo (simula persistencia) — limpiar
    # SIN monkeypatch (su undo restauraría el valor). No contaminar test_geo.
    for k in list(os.environ):
        if k.startswith(("SEARCH_", "LEADHUNTER_", "EMBEDDING_", "RANKING_")):
            os.environ.pop(k, None)


def _seed(db, company="Farmacia San Roque", industry="farmacia", region="Asuncion",
          phone="021123456", email="ventas@sanroque.com.py", score=70):
    lead = Lead(company=company, industry=industry, region=region, phone=phone,
                email=email, source="test", score=score)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


class TestHealth:
    def test_cli_relative_sqlite_url_is_independent_of_cwd(self):
        import cli as cli_module

        resolved = cli_module._cli_database_url("sqlite:///./missioncontrol.db")
        assert resolved.replace("\\", "/").endswith("backend/missioncontrol.db")

    def test_health_ok(self):
        res = runner.invoke(app, ["health"])
        assert res.exit_code == 0
        assert "Base de datos" in res.stdout

    def test_search_json_misma_logica_que_api(self, db):
        _seed(db, company="Farmacia San Roque", industry="farmacia")
        _seed(db, company="Logistica Ruta 6", industry="logistica")
        res = runner.invoke(app, ["search", "farmacia", "--json"])
        assert res.exit_code == 0
        data = json.loads(res.stdout)
        assert data["total"] == 1
        assert data["items"][0]["company"] == "Farmacia San Roque"
        assert data["items"][0]["data_quality"] is not None

    def test_search_filtro_region(self, db):
        _seed(db, company="A Asuncion", region="Asuncion")
        _seed(db, company="B CDE", region="Ciudad del Este")
        res = runner.invoke(app, ["search", "", "--region", "Ciudad del Este", "--json"])
        assert res.exit_code == 0
        data = json.loads(res.stdout)
        assert data["total"] == 1
        assert data["items"][0]["company"] == "B CDE"


class TestLeads:
    def test_list_json(self, db):
        _seed(db, company="Comercio Uno", industry="comercio")
        res = runner.invoke(app, ["leads", "list", "--json"])
        assert res.exit_code == 0
        data = json.loads(res.stdout)
        assert any(i["company"] == "Comercio Uno" for i in data["items"])

    def test_export_json(self, db):
        _seed(db, company="Exportame SA", industry="comercio")
        res = runner.invoke(app, ["leads", "export", "--format", "json"])
        assert res.exit_code == 0
        data = json.loads(res.stdout)
        assert any(i["company"] == "Exportame SA" for i in data)

    def test_export_csv_archivo(self, db, tmp_path):
        _seed(db, company="CSV SA")
        out = tmp_path / "leads.csv"
        res = runner.invoke(app, ["leads", "export", "--format", "csv", "--out", str(out)])
        assert res.exit_code == 0
        content = out.read_text(encoding="utf-8")
        assert content.startswith("id,company")
        assert "CSV SA" in content


class TestLead:
    def test_inspect_json(self, db):
        lead = _seed(db, company="Inspeccioname SA")
        res = runner.invoke(app, ["lead", "inspect", lead.id, "--json"])
        assert res.exit_code == 0
        data = json.loads(res.stdout)
        assert data["company"] == "Inspeccioname SA"
        assert "reasons" in data

    def test_score_json(self, db):
        lead = _seed(db, company="Puntuame SA")
        res = runner.invoke(app, ["lead", "score", lead.id, "--json"])
        assert res.exit_code == 0
        data = json.loads(res.stdout)
        assert 0 <= data["lead_score"] <= 100
        assert "opportunity_score" in data
        assert data["reasons"]

    def test_inspect_no_existe(self):
        res = runner.invoke(app, ["lead", "inspect", "no-existe"])
        assert res.exit_code == 1


class TestConfig:
    def test_set_get(self):
        res = runner.invoke(app, ["config", "set", "search.country", "BR"])
        assert res.exit_code == 0
        res = runner.invoke(app, ["config", "get", "search.country"])
        assert res.exit_code == 0
        assert "BR" in res.stdout

    def test_get_todas(self, db):
        res = runner.invoke(app, ["config", "get"])
        assert res.exit_code == 0
        assert "Key" in res.stdout

    def test_config_default_reads_safe_settings(self, db):
        res = runner.invoke(app, ["config"])
        assert res.exit_code == 0
        assert "Settings" in res.stdout


class TestWorkspaceHome:
    def test_root_command_shows_global_home_without_project(self, monkeypatch, tmp_path):
        outside = Path(os.environ["TEMP"]) / f"conciencia-outside-{tmp_path.name}"
        outside.mkdir(parents=True, exist_ok=True)
        monkeypatch.chdir(outside)
        res = runner.invoke(app, [])
        assert res.exit_code == 0, res.stdout
        assert "CONCIENCIA" in res.stdout
        assert "Global workspace" in res.stdout
        assert "QUICK ACTIONS" in res.stdout

    def test_root_home_surfaces_project_attention_and_recent_work(self, db, monkeypatch, tmp_path):
        from app.models.activity import Activity, ActivityType
        from app.models.mission import Mission
        from app.models.project import Project

        project = Project(name="Mission Control", description="Control plane")
        db.add(project)
        db.add(Mission(name="Blocked work", objective="Fix it", status="failed", project=project))
        db.add(Activity(project=project, type=ActivityType.TASK_CHANGE, description="Implemented workspace home"))
        db.commit()
        (tmp_path / ".conciencia").mkdir()
        (tmp_path / ".conciencia" / "project.yaml").write_text("name: mission-control\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        res = runner.invoke(app, [])
        assert res.exit_code == 0, res.stdout
        assert "Mission Control" in res.stdout
        assert "NEEDS ATTENTION" in res.stdout
        assert "RECENT WORK" in res.stdout
        assert str(project.id) not in res.stdout


class TestTerminalV1:
    def _seed_waiting_approval(self, db, pending_steps):
        from app.models.mission import Mission, MissionRun
        from app.models.workflow import Workflow, WorkflowRun

        definition = [
            {"name": f"step_{index}", "approval": True}
            for index, _name in pending_steps
        ]
        workflow = Workflow(name="Approval workflow", definition=definition, status="paused")
        db.add(workflow)
        db.commit()
        mission = Mission(
            name="Approval mission",
            objective="Approve the next gate",
            status="waiting_approval",
            workflow_id=workflow.id,
        )
        db.add(mission)
        db.commit()
        workflow_run = WorkflowRun(
            workflow_id=workflow.id,
            status="paused",
            current_step=pending_steps[0][0],
            step_results=[
                {
                    "step_index": index,
                    "step_name": name,
                    "status": "waiting_approval",
                    "approval_token": f"token-{index}",
                }
                for index, name in pending_steps
            ],
        )
        db.add(workflow_run)
        db.commit()
        run = MissionRun(
            mission_id=mission.id,
            workflow_run_id=workflow_run.id,
            status="waiting_approval",
        )
        db.add(run)
        db.commit()
        return mission

    def test_mission_default_lists_missions_with_human_refs(self, db):
        from app.models.mission import Mission

        mission = Mission(name="CLI UX", objective="Improve terminal", status="draft")
        db.add(mission)
        db.commit()

        res = runner.invoke(app, ["mission"])
        assert res.exit_code == 0, res.stdout
        assert "CLI UX" in res.stdout
        assert f"M-{str(mission.id)[:8]}" in res.stdout

    def test_approvals_lists_pending_steps_and_next_action(self, db):
        mission = self._seed_waiting_approval(db, [(3, "External research")])

        res = runner.invoke(app, ["approvals"])
        assert res.exit_code == 0, res.stdout
        assert f"M-{str(mission.id)[:8]}" in res.stdout
        assert "External research" in res.stdout
        assert "conciencia approve" in res.stdout

    def test_approve_infers_single_pending_step(self, db):
        mission = self._seed_waiting_approval(db, [(0, "Human gate")])

        res = runner.invoke(app, ["approve", f"M-{str(mission.id)[:8]}"])
        assert res.exit_code == 0, res.stdout
        assert "Aprobado step 0" in res.stdout

    def test_approve_multiple_pending_steps_is_actionable(self, db):
        mission = self._seed_waiting_approval(db, [(3, "Research"), (6, "Communication")])

        res = runner.invoke(app, ["approve", f"M-{str(mission.id)[:8]}"])
        assert res.exit_code == 1, res.stdout
        assert "2 approvals pendientes" in res.stdout
        assert "conciencia approve" in res.stdout
        assert "Research" in res.stdout

    def test_actions_and_nav_are_machine_readable(self, db):
        from app.models.activity import Activity, ActivityType

        db.add(Activity(type=ActivityType.TASK_CHANGE, description="Implemented WebMCP terminal navigator"))
        db.commit()

        actions = runner.invoke(app, ["actions", "--json"])
        assert actions.exit_code == 0, actions.stdout
        assert any(row["id"] == "work.search" for row in json.loads(actions.stdout))

        nav = runner.invoke(app, ["nav", "WebMCP", "--json"])
        assert nav.exit_code == 0, nav.stdout
        payload = json.loads(nav.stdout)
        assert payload["items"]
        assert payload["retrieval"] in {"lexical", "hybrid", "hybrid-simulated"}


class TestProjects:
    def test_project_inspect_uses_current_workspace_context(self, db, monkeypatch, tmp_path):
        from app.models.project import Project

        project = Project(name="Conciencia", description="Workspace main project")
        db.add(project)
        db.commit()
        (tmp_path / ".conciencia").mkdir()
        (tmp_path / ".conciencia" / "project.yaml").write_text(
            "name: Conciencia\npath: C:\\temp\\conciencia\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)

        res = runner.invoke(app, ["project", "inspect"])
        assert res.exit_code == 0, res.stdout
        assert "Workspace main project" in res.stdout
        assert "missions_count" in res.stdout or "Missions" in res.stdout

    def test_project_inspect_matches_repository_slug_to_display_name(self, db, monkeypatch, tmp_path):
        from app.models.project import Project

        project = Project(name="Mission Control", description="Current workspace project")
        db.add(project)
        db.commit()
        (tmp_path / ".conciencia").mkdir()
        (tmp_path / ".conciencia" / "project.yaml").write_text(
            "name: mission-control\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)

        res = runner.invoke(app, ["project", "inspect", "--json"])
        assert res.exit_code == 0, res.stdout
        assert json.loads(res.stdout)["id"] == str(project.id)


class TestWorkAndReports:
    def test_work_defaults_to_workspace_history_and_accepts_explicit_project(self, db):
        from app.models.activity import Activity, ActivityType
        from app.models.project import Project

        project = Project(name="Scoped")
        db.add(project)
        db.commit()
        db.add_all([
            Activity(project_id=project.id, type=ActivityType.TASK_CHANGE, description="Scoped activity"),
            Activity(project_id=None, type=ActivityType.TASK_CHANGE, description="Workspace-only activity"),
        ])
        db.commit()

        workspace = runner.invoke(app, ["work", "timeline", "--json"])
        assert workspace.exit_code == 0, workspace.stdout
        workspace_titles = {item["title"] for item in json.loads(workspace.stdout)}
        assert {"Scoped activity", "Workspace-only activity"} <= workspace_titles

        scoped = runner.invoke(app, ["work", "timeline", "--project", "Scoped", "--json"])
        assert scoped.exit_code == 0, scoped.stdout
        scoped_titles = {item["title"] for item in json.loads(scoped.stdout)}
        assert "Scoped activity" in scoped_titles
        assert "Workspace-only activity" not in scoped_titles

    def test_work_collect_handles_mixed_datetime_semantics(self, db, monkeypatch):
        from app.services import work_service
        from app.services.work_service import WorkItem

        naive = datetime(2026, 8, 27, 12, 0, 0)
        aware = datetime(2026, 8, 28, 12, 0, 0, tzinfo=timezone.utc)

        monkeypatch.setattr(work_service, "_activity_items", lambda *args, **kwargs: [
            WorkItem(
                id="a-1",
                workspace_id="workspace",
                project_id=None,
                type="activity.commit",
                title="naive",
                summary="naive timestamp",
                timestamp=naive,
                source_type="activity",
                source_ref="1",
                metadata={},
                tags=[],
                evidence_refs=[],
                created_at=naive,
            )
        ])
        monkeypatch.setattr(work_service, "_mission_items", lambda *args, **kwargs: [
            WorkItem(
                id="m-1",
                workspace_id="workspace",
                project_id=None,
                type="mission.created",
                title="aware",
                summary="aware timestamp",
                timestamp=aware,
                source_type="mission",
                source_ref="2",
                metadata={},
                tags=[],
                evidence_refs=[],
                created_at=aware,
            )
        ])
        monkeypatch.setattr(work_service, "_run_items", lambda *args, **kwargs: [])
        monkeypatch.setattr(work_service, "_signal_items", lambda *args, **kwargs: [])
        monkeypatch.setattr(work_service, "_evidence_items", lambda *args, **kwargs: [])
        monkeypatch.setattr(work_service, "_deliverable_items", lambda *args, **kwargs: [])
        monkeypatch.setattr(work_service, "_git_commits", lambda *args, **kwargs: [])

        items = work_service.collect_work_items(db, since="2026-08-27", until="2026-08-29")
        assert [item.id for item in items] == ["m-1", "a-1"]
        assert all(item.timestamp.tzinfo is not None for item in items)
        assert all(item.created_at.tzinfo is not None for item in items)

    def test_work_summary_and_report_create(self, db):
        from app.models.activity import Activity, ActivityType
        from app.models.project import Project

        project = Project(name="Conciencia", description="Workspace main project")
        db.add(project)
        db.commit()
        db.add(Activity(project_id=project.id, type=ActivityType.PROJECT_CREATED, description="Workspace initialized", extra_data={"source_type": "manual"}))
        db.commit()

        summary = runner.invoke(app, ["work", "summarize", "--project", "Conciencia", "--json"])
        assert summary.exit_code == 0, summary.stdout
        payload = json.loads(summary.stdout)
        assert payload["summary"]["item_count"] >= 1
        assert payload["summary"]["coverage"] in {"partial", "full"}

        report = runner.invoke(app, ["report", "create", "--project", "Conciencia", "--json"])
        assert report.exit_code == 0, report.stdout
        report_payload = json.loads(report.stdout)
        assert report_payload["report"]["title"]
        assert report_payload["report"]["project_id"] == str(project.id)

    def test_work_search_uses_semantic_when_enabled(self, db, monkeypatch):
        from app.models.activity import Activity, ActivityType
        from app.models.project import Project

        monkeypatch.setenv("EMBEDDING_ENABLED", "1")
        project = Project(name="Conciencia", description="Workspace main project")
        db.add(project)
        db.commit()
        db.add(Activity(project_id=project.id, type=ActivityType.TASK_CHANGE, description="Implemented WebMCP workspace search", extra_data={"source_type": "manual"}))
        db.commit()

        res = runner.invoke(app, ["work", "search", "WebMCP", "--project", "Conciencia", "--json"])
        assert res.exit_code == 0, res.stdout
        payload = json.loads(res.stdout)
        assert payload["retrieval"] in {"hybrid", "hybrid-simulated"}
        assert payload["embedding_backend"] in {"real", "simulated"}
        assert payload["items"]
        assert any("WebMCP" in row["title"] for row in payload["items"])

    def test_work_inspect(self, db):
        from app.models.activity import Activity, ActivityType
        from app.models.project import Project

        project = Project(name="Conciencia", description="Workspace main project")
        db.add(project)
        db.commit()
        activity = Activity(project_id=project.id, type=ActivityType.PROJECT_CREATED, description="Workspace initialized", extra_data={"source_type": "manual"})
        db.add(activity)
        db.commit()

        res = runner.invoke(app, ["work", "inspect", f"activity:{activity.id}", "--project", "Conciencia", "--json"])
        assert res.exit_code == 0, res.stdout
        payload = json.loads(res.stdout)
        assert payload["id"].startswith("activity:")
        assert payload["summary"] == "Workspace initialized"

    def test_report_create_accepts_project_name_and_uuid(self, db):
        from app.models.project import Project

        project = Project(name="Conciencia", description="Workspace main project")
        db.add(project)
        db.commit()

        by_name = runner.invoke(app, ["report", "create", "--project", "Conciencia", "--json"])
        assert by_name.exit_code == 0, by_name.stdout
        payload_name = json.loads(by_name.stdout)
        assert payload_name["report"]["project_id"] == str(project.id)

        by_uuid = runner.invoke(app, ["report", "create", "--project", str(project.id), "--json"])
        assert by_uuid.exit_code == 0, by_uuid.stdout
        payload_uuid = json.loads(by_uuid.stdout)
        assert payload_uuid["report"]["project_id"] == str(project.id)

    def test_ask_routes_workspace_summary(self, db):
        from app.models.activity import Activity, ActivityType
        from app.models.project import Project
        from app.models.mission import Mission

        project = Project(name="Conciencia", description="Workspace main project")
        db.add(project)
        db.commit()
        db.add(Activity(project_id=project.id, type=ActivityType.PROJECT_CREATED, description="Workspace initialized", extra_data={"source_type": "manual"}))
        db.commit()

        res = runner.invoke(app, ["ask", "--json", "Resumime todo lo que desarrollé desde 2026-08-27 hasta hoy"])
        assert res.exit_code == 0, res.stdout
        payload = json.loads(res.stdout)
        assert payload["route"]["route"] == "workspace_summary"
        assert payload["summary"]["coverage"] in {"partial", "full", "none"}
        assert db.query(Mission).count() == 0

    def test_ask_routes_webmcp_question_to_workspace_query(self, db):
        from app.models.activity import Activity, ActivityType
        from app.models.mission import Mission

        db.add(Activity(type=ActivityType.TASK_CHANGE, description="Implemented WebMCP support"))
        db.commit()

        res = runner.invoke(app, ["ask", "--json", "¿Qué hicimos para WebMCP?"])
        assert res.exit_code == 0, res.stdout
        payload = json.loads(res.stdout)
        assert payload["route"]["route"] == "workspace_query"
        assert payload["items"]
        assert any("WebMCP" in item["title"] for item in payload["items"])
        assert db.query(Mission).count() == 0


class TestAgentesYModulos:
    def test_agents_json(self, db):
        res = runner.invoke(app, ["agents", "--json"])
        assert res.exit_code == 0
        assert isinstance(json.loads(res.stdout), list)

    def test_modules_json(self):
        res = runner.invoke(app, ["modules", "--json"])
        assert res.exit_code == 0
        mods = json.loads(res.stdout)
        assert any(m["id"] == "core" for m in mods)
        assert any(m["id"] == "leadhunter" for m in mods)


class TestHunt:
    def test_fuente_desconocida_error(self):
        res = runner.invoke(app, ["hunt", "--source", "no-existe"])
        assert res.exit_code == 1
        assert "Fuente desconocida" in res.stdout
