import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal, engine, Base
from app.models import Project, Task, Agent, Activity, Metric
from app.models.project import ProjectStatus, ProjectPriority, ProjectCategory
from app.models.task import TaskStatus, TaskPriority
from app.models.agent import AgentRole, AgentStatus, AutonomyLevel
from app.models.activity import ActivityType
from app.models.metric import MetricCategory, MetricPeriod
from datetime import datetime, timedelta

def seed_data():
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        existing = db.query(Project).first()
        if existing:
            print("Database already seeded")
            return
        
        projects = [
            Project(
                name="OpenAgent",
                description="AI agent framework for autonomous software development",
                status=ProjectStatus.ACTIVE,
                priority=ProjectPriority.P0,
                category=ProjectCategory.CORE,
                github_repo="juanesscobar/openagent",
                tech_stack=["Python", "FastAPI", "LangChain", "React"],
                created_at=datetime.utcnow() - timedelta(days=90)
            ),
            Project(
                name="Mission Control",
                description="Software Factory + Project Governance System",
                status=ProjectStatus.ACTIVE,
                priority=ProjectPriority.P1,
                category=ProjectCategory.CORE,
                github_repo="juanesscobar/mission-control",
                tech_stack=["Python", "FastAPI", "React", "PostgreSQL"],
                created_at=datetime.utcnow() - timedelta(days=30)
            ),
            Project(
                name="Legacy Dashboard",
                description="Legacy analytics dashboard system",
                status=ProjectStatus.PAUSED,
                priority=ProjectPriority.P2,
                category=ProjectCategory.LEGACY,
                github_repo="juanesscobar/legacy-dashboard",
                tech_stack=["Vue.js", "Node.js", "MongoDB"],
                created_at=datetime.utcnow() - timedelta(days=365)
            ),
        ]
        
        for p in projects:
            db.add(p)
        
        db.commit()
        
        for p in projects:
            db.refresh(p)
        
        agents = [
            Agent(
                name="DevBot",
                emoji="🤖",
                role=AgentRole.DEV,
                status=AgentStatus.ACTIVE,
                personality="Helpful coding assistant focused on best practices",
                capabilities=["code_review", "bug_fixing", "refactoring"],
                autonomy_level=AutonomyLevel.PREVIEW,
                created_at=datetime.utcnow() - timedelta(days=60)
            ),
            Agent(
                name="QATester",
                emoji="🧪",
                role=AgentRole.QA,
                status=AgentStatus.ACTIVE,
                personality="Thorough testing specialist",
                capabilities=["unit_tests", "integration_tests", "e2e_tests"],
                autonomy_level=AutonomyLevel.APPROVAL,
                created_at=datetime.utcnow() - timedelta(days=45)
            ),
            Agent(
                name="ProjectManager",
                emoji="📊",
                role=AgentRole.PM,
                status=AgentStatus.ACTIVE,
                personality="Organized project coordination agent",
                capabilities=["task_tracking", "reporting", "sprint_planning"],
                autonomy_level=AutonomyLevel.FULL,
                created_at=datetime.utcnow() - timedelta(days=30)
            ),
        ]
        
        for a in agents:
            db.add(a)
        
        db.commit()
        
        for a in agents:
            db.refresh(a)
        
        tasks = [
            Task(
                project_id=projects[0].id,
                title="Implement async agent communication",
                description="Add support for async message passing between agents",
                status=TaskStatus.IN_PROGRESS,
                priority=TaskPriority.HIGH,
                assignee="DevBot",
                created_at=datetime.utcnow() - timedelta(days=5)
            ),
            Task(
                project_id=projects[0].id,
                title="Add unit tests for core modules",
                description="Increase test coverage to 80%",
                status=TaskStatus.BACKLOG,
                priority=TaskPriority.MEDIUM,
                assignee="QATester",
                created_at=datetime.utcnow() - timedelta(days=3)
            ),
            Task(
                project_id=projects[1].id,
                title="Setup CI/CD pipeline",
                description="Configure GitHub Actions for automated deployment",
                status=TaskStatus.DONE,
                priority=TaskPriority.HIGH,
                assignee="DevBot",
                created_at=datetime.utcnow() - timedelta(days=20),
                updated_at=datetime.utcnow() - timedelta(days=10)
            ),
            Task(
                project_id=projects[1].id,
                title="Design database schema",
                description="Define models for projects, tasks, agents, activities",
                status=TaskStatus.DONE,
                priority=TaskPriority.HIGH,
                assignee="ProjectManager",
                created_at=datetime.utcnow() - timedelta(days=25),
                updated_at=datetime.utcnow() - timedelta(days=15)
            ),
        ]
        
        for t in tasks:
            db.add(t)
        
        db.commit()
        
        activities = [
            Activity(
                project_id=projects[0].id,
                agent_id=agents[0].id,
                type=ActivityType.COMMIT,
                description="Add async agent communication layer",
                external_url="https://github.com/juanesscobar/openagent/commit/abc123",
                extra_data={"sha": "abc123", "author": "DevBot"},
                created_at=datetime.utcnow() - timedelta(hours=2)
            ),
            Activity(
                project_id=projects[1].id,
                agent_id=agents[1].id,
                type=ActivityType.TASK_CHANGE,
                description="Completed task: Setup CI/CD pipeline",
                extra_data={"task_id": tasks[2].id},
                created_at=datetime.utcnow() - timedelta(days=10)
            ),
            Activity(
                project_id=projects[0].id,
                type=ActivityType.PR,
                description="PR opened: Add LangChain integration",
                external_url="https://github.com/juanesscobar/openagent/pull/45",
                created_at=datetime.utcnow() - timedelta(days=1)
            ),
        ]
        
        for a in activities:
            db.add(a)
        
        db.commit()
        
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
                recorded_at=datetime.utcnow()
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
                recorded_at=datetime.utcnow()
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
                recorded_at=datetime.utcnow()
            ),
        ]
        
        for m in metrics:
            db.add(m)
        
        db.commit()
        
        print("Seed data created successfully!")
        print(f"- {len(projects)} projects")
        print(f"- {len(agents)} agents")
        print(f"- {len(tasks)} tasks")
        print(f"- {len(activities)} activities")
        print(f"- {len(metrics)} metrics")
        
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
