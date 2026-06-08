"""
Script para agregar EduKit como proyecto en Mission Control
Ejecutar: python seed_edukit.py
"""

import sys
sys.path.insert(0, 'C:\\Users\\juane\\.openclaw\\workspace\\mission-control\\backend')

from app.database import SessionLocal, engine
from app.models.project import Project, ProjectStatus, ProjectPriority, ProjectCategory
from app.models.task import Task, TaskStatus
from app.models.agent import Agent
from app.models.activity import Activity
import uuid
from datetime import datetime

def seed_edukit():
    db = SessionLocal()
    
    try:
        # Verificar si ya existe
        existing = db.query(Project).filter(Project.name == "EduKit").first()
        if existing:
            print(f"⚠️  EduKit ya existe (ID: {existing.id})")
            return
        
        # Crear proyecto EduKit
        edukit = Project(
            id=uuid.uuid4(),
            name="EduKit",
            description="Sistema integral de educación asistida por IA para escuelas en zonas remotas. Hardware + Software con proyección, voz y gestión de clases.",
            status=ProjectStatus.ACTIVE,
            priority=ProjectPriority.P0,  # Alta prioridad
            category=ProjectCategory.EDUCATION,
            github_repo="juanesscobar/edukit",
            tech_stack=["Python", "FastAPI", "React", "Raspberry Pi", "LLM", "STT/TTS"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(edukit)
        db.flush()  # Para obtener el ID
        
        # Crear tareas iniciales
        tasks = [
            Task(
                id=uuid.uuid4(),
                title="Definir especificaciones de hardware",
                description="Seleccionar componentes: Raspberry Pi 5, proyector mini, micrófono, batería, carcasa",
                status=TaskStatus.TODO,
                priority="p0",
                project_id=edukit.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            Task(
                id=uuid.uuid4(),
                title="Diseñar arquitectura de software",
                description="Definir módulos: AI Tutor, Classroom Management, Offline Sync, Teacher Dashboard",
                status=TaskStatus.TODO,
                priority="p0",
                project_id=edukit.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            Task(
                id=uuid.uuid4(),
                title="Prototipo de hardware (v0.1)",
                description="Ensamblar primer prototipo funcional con proyección y audio",
                status=TaskStatus.TODO,
                priority="p1",
                project_id=edukit.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            Task(
                id=uuid.uuid4(),
                title="Integrar STT/TTS local",
                description="Implementar Whisper + Coqui TTS para funcionamiento offline",
                status=TaskStatus.TODO,
                priority="p1",
                project_id=edukit.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            Task(
                id=uuid.uuid4(),
                title="MVP AI Tutor",
                description="Primer asistente de IA para matemáticas básicas (primaria)",
                status=TaskStatus.TODO,
                priority="p0",
                project_id=edukit.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
        ]
        
        for task in tasks:
            db.add(task)
        
        # Crear actividad inicial
        activity = Activity(
            id=uuid.uuid4(),
            type="project_created",
            description="Proyecto EduKit creado - IA + Hardware para educación rural",
            project_id=edukit.id,
            created_at=datetime.utcnow()
        )
        db.add(activity)
        
        db.commit()
        
        print(f"✅ EduKit creado exitosamente!")
        print(f"   ID: {edukit.id}")
        print(f"   Nombre: {edukit.name}")
        print(f"   Prioridad: {edukit.priority.value}")
        print(f"   Tareas creadas: {len(tasks)}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_edukit()
