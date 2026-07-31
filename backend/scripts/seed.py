import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal, engine, Base
from app.models import Project, Task, Agent, Activity, Metric, User, Sprint
from app.models.project import ProjectStatus, ProjectPriority, ProjectCategory
from app.models.task import TaskStatus, TaskPriority, TaskType
from app.models.agent import AgentRole, AgentStatus, AutonomyLevel, AgentType
from app.models.activity import ActivityType
from app.models.metric import MetricCategory, MetricPeriod
from app.models.sprint import SprintStatus
from app.services.auth import hash_password
from datetime import datetime, timedelta, date


def seed_data():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        existing = db.query(Project).first()
        if existing:
            print("Database already seeded")
            return

        # --- Users ---
        users = [
            User(
                email="toto@missioncontrol.ai",
                username="irontoto",
                hashed_password=hash_password("admin123"),
                display_name="Iron Toto",
                role="ceo",
            ),
            User(
                email="dev@missioncontrol.ai",
                username="devbot",
                hashed_password=hash_password("dev123"),
                display_name="DevBot",
                role="admin",
            ),
        ]
        for u in users:
            db.add(u)
        db.commit()
        for u in users:
            db.refresh(u)

        # --- Projects ---
        projects = [
            Project(
                name="OpenAgent",
                description="AI agent framework for autonomous software development",
                status=ProjectStatus.ACTIVE,
                priority=ProjectPriority.P0,
                category=ProjectCategory.CORE,
                github_repo="juanesscobar/openagent",
                tech_stack=["Python", "FastAPI", "LangChain", "React"],
                created_at=datetime.utcnow() - timedelta(days=90),
            ),
            Project(
                name="Mission Control",
                description="Software Factory + Project Governance System",
                status=ProjectStatus.ACTIVE,
                priority=ProjectPriority.P1,
                category=ProjectCategory.CORE,
                github_repo="juanesscobar/mission-control",
                tech_stack=["Python", "FastAPI", "React", "PostgreSQL"],
                created_at=datetime.utcnow() - timedelta(days=30),
            ),
            Project(
                name="Legacy Dashboard",
                description="Legacy analytics dashboard system",
                status=ProjectStatus.PAUSED,
                priority=ProjectPriority.P2,
                category=ProjectCategory.LEGACY,
                github_repo="juanesscobar/legacy-dashboard",
                tech_stack=["Vue.js", "Node.js", "MongoDB"],
                created_at=datetime.utcnow() - timedelta(days=365),
            ),
        ]

        for p in projects:
            db.add(p)
        db.commit()
        for p in projects:
            db.refresh(p)

        # --- Sprints ---
        sprints = [
            Sprint(
                project_id=projects[1].id,
                name="Sprint 1: Foundation",
                goal="Setup base architecture and dashboard",
                status=SprintStatus.COMPLETED,
                start_date=date(2026, 2, 16),
                end_date=date(2026, 2, 28),
                goals=["Setup FastAPI + PostgreSQL", "Dashboard read-only", "GitHub integration"],
            ),
            Sprint(
                project_id=projects[1].id,
                name="Sprint 2: Governance",
                goal="Task management and metrics",
                status=SprintStatus.PLANNING,
                start_date=date(2026, 3, 2),
                end_date=date(2026, 3, 15),
                goals=["Task CRUD", "Metrics dashboard", "Telegram bot"],
            ),
        ]
        for s in sprints:
            db.add(s)
        db.commit()
        for s in sprints:
            db.refresh(s)

        # --- Agents ---
        agents = [
            Agent(
                name="DevBot",
                emoji="🤖",
                role=AgentRole.DEV,
                type=AgentType.SYSTEM,
                status=AgentStatus.WORKING,
                personality="Helpful coding assistant focused on best practices",
                capabilities=["code_review", "bug_fixing", "refactoring"],
                autonomy_level=AutonomyLevel.PREVIEW,
                created_at=datetime.utcnow() - timedelta(days=60),
            ),
            Agent(
                name="QATester",
                emoji="🧪",
                role=AgentRole.QA,
                type=AgentType.SYSTEM,
                status=AgentStatus.IDLE,
                personality="Thorough testing specialist",
                capabilities=["unit_tests", "integration_tests", "e2e_tests"],
                autonomy_level=AutonomyLevel.APPROVAL,
                created_at=datetime.utcnow() - timedelta(days=45),
            ),
            Agent(
                name="ProjectManager",
                emoji="📊",
                role=AgentRole.PM,
                type=AgentType.SYSTEM,
                status=AgentStatus.WORKING,
                personality="Organized project coordination agent",
                capabilities=["task_tracking", "reporting", "sprint_planning"],
                autonomy_level=AutonomyLevel.FULL,
                created_at=datetime.utcnow() - timedelta(days=30),
            ),
        ]

        for a in agents:
            db.add(a)
        db.commit()
        for a in agents:
            db.refresh(a)

        # --- Tasks ---
        tasks = [
            Task(
                project_id=projects[0].id,
                sprint_id=sprints[0].id,
                title="Implement async agent communication",
                description="Add support for async message passing between agents",
                status=TaskStatus.IN_PROGRESS,
                priority=TaskPriority.HIGH,
                type=TaskType.FEATURE,
                assignee_id=agents[0].id,
                assignee_type="agent",
                created_at=datetime.utcnow() - timedelta(days=5),
            ),
            Task(
                project_id=projects[0].id,
                title="Add unit tests for core modules",
                description="Increase test coverage to 80%",
                status=TaskStatus.BACKLOG,
                priority=TaskPriority.MEDIUM,
                type=TaskType.FEATURE,
                assignee_id=agents[1].id,
                assignee_type="agent",
                created_at=datetime.utcnow() - timedelta(days=3),
            ),
            Task(
                project_id=projects[1].id,
                sprint_id=sprints[0].id,
                title="Setup CI/CD pipeline",
                description="Configure GitHub Actions for automated deployment",
                status=TaskStatus.DONE,
                priority=TaskPriority.HIGH,
                type=TaskType.OPS,
                assignee_id=agents[0].id,
                assignee_type="agent",
                created_at=datetime.utcnow() - timedelta(days=20),
                updated_at=datetime.utcnow() - timedelta(days=10),
            ),
            Task(
                project_id=projects[1].id,
                sprint_id=sprints[0].id,
                title="Design database schema",
                description="Define models for projects, tasks, agents, activities",
                status=TaskStatus.DONE,
                priority=TaskPriority.HIGH,
                type=TaskType.FEATURE,
                assignee_id=agents[2].id,
                assignee_type="agent",
                created_at=datetime.utcnow() - timedelta(days=25),
                updated_at=datetime.utcnow() - timedelta(days=15),
            ),
        ]

        for t in tasks:
            db.add(t)
        db.commit()

        # --- Activities ---
        activities = [
            Activity(
                project_id=projects[0].id,
                agent_id=agents[0].id,
                type=ActivityType.COMMIT,
                description="Add async agent communication layer",
                external_url="https://github.com/juanesscobar/openagent/commit/abc123",
                extra_data={"sha": "abc123", "author": "DevBot"},
                created_at=datetime.utcnow() - timedelta(hours=2),
            ),
            Activity(
                project_id=projects[1].id,
                agent_id=agents[1].id,
                type=ActivityType.TASK_CHANGE,
                description="Completed task: Setup CI/CD pipeline",
                extra_data={"task_id": str(tasks[2].id)},
                created_at=datetime.utcnow() - timedelta(days=10),
            ),
            Activity(
                project_id=projects[0].id,
                type=ActivityType.PR,
                description="PR opened: Add LangChain integration",
                external_url="https://github.com/juanesscobar/openagent/pull/45",
                created_at=datetime.utcnow() - timedelta(days=1),
            ),
        ]

        for a in activities:
            db.add(a)
        db.commit()

        # --- Metrics ---
        metrics = [
            Metric(
                project_id=projects[0].id,
                category=MetricCategory.PERSONAL,
                name="commits_daily",
                value=12.0,
                target=10.0,
                unit="commits",
                period=MetricPeriod.DAILY,
                source="github",
                recorded_at=datetime.utcnow(),
            ),
            Metric(
                project_id=projects[0].id,
                category=MetricCategory.PERSONAL,
                name="test_coverage",
                value=72.5,
                target=80.0,
                unit="percent",
                period=MetricPeriod.WEEKLY,
                source="coverage.py",
                recorded_at=datetime.utcnow(),
            ),
            Metric(
                project_id=projects[1].id,
                category=MetricCategory.PERSONAL,
                name="tasks_completed",
                value=8.0,
                target=12.0,
                unit="tasks",
                period=MetricPeriod.WEEKLY,
                source="internal",
                recorded_at=datetime.utcnow(),
            ),
        ]

        for m in metrics:
            db.add(m)
        db.commit()

        print("Seed data created successfully!")
        print(f"- {len(users)} users")
        print(f"- {len(projects)} projects")
        print(f"- {len(sprints)} sprints")
        print(f"- {len(agents)} agents")
        print(f"- {len(tasks)} tasks")
        print(f"- {len(activities)} activities")
        print(f"- {len(metrics)} metrics")

    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
