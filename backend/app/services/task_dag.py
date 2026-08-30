"""Servicio de dependencias de tareas (DAG): evaluar bloqueos, desbloquear, ciclos."""

import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.task import Task, TaskStatus
from app.models.task_dependency import TaskDependency


def _uuid(value: str) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def _get_task(db: Session, task_id: str) -> Optional[Task]:
    return db.get(Task, _uuid(task_id))


def add_dependency(db: Session, task_id: str, depends_on_id: str, kind: str = "finish_to_start") -> TaskDependency:
    """Crea un arco task_id → depends_on_id (task_id espera a depends_on_id)."""
    # Normalizar a UUID real: las columnas son Uuid y SQLite exige objetos UUID
    # (Postgres castea str automáticamente, por eso prod nunca falló).
    task_id = _uuid(task_id)
    depends_on_id = _uuid(depends_on_id)
    if task_id == depends_on_id:
        raise ValueError("Una tarea no puede depender de sí misma")

    task = _get_task(db, task_id)
    dep = _get_task(db, depends_on_id)
    if not task or not dep:
        raise ValueError("task_id o depends_on_id no existe")

    if _would_create_cycle(db, task_id, depends_on_id):
        raise ValueError("La dependencia crearía un ciclo en el DAG")

    existing = (
        db.query(TaskDependency)
        .filter(TaskDependency.task_id == task_id, TaskDependency.depends_on_id == depends_on_id)
        .first()
    )
    if existing:
        return existing

    dep_row = TaskDependency(task_id=task_id, depends_on_id=depends_on_id, kind=kind)
    db.add(dep_row)
    db.flush()  # visible para las queries de _dependency_status (sesiones con autoflush=False)
    refresh_task_status(db, task)
    db.commit()
    db.refresh(dep_row)
    return dep_row


def remove_dependency(db: Session, task_id: str, depends_on_id: str) -> None:
    task_id = _uuid(task_id)
    depends_on_id = _uuid(depends_on_id)
    row = (
        db.query(TaskDependency)
        .filter(TaskDependency.task_id == task_id, TaskDependency.depends_on_id == depends_on_id)
        .first()
    )
    if row:
        db.delete(row)
        db.commit()
        task = _get_task(db, task_id)
        if task:
            refresh_task_status(db, task)
            db.commit()


def _would_create_cycle(db: Session, task_id: str, depends_on_id: str) -> bool:
    """DFS desde depends_on_id: si llegamos a task_id, hay ciclo."""
    task_id = _uuid(task_id)
    depends_on_id = _uuid(depends_on_id)

    def dfs(current: str, visited: set) -> bool:
        if current == task_id:
            return True
        if current in visited:
            return False
        visited.add(current)
        for row in db.query(TaskDependency).filter(TaskDependency.task_id == current).all():
            if dfs(row.depends_on_id, visited):
                return True
        return False

    return dfs(depends_on_id, set())


def _dependency_status(db: Session, task_id: str) -> List[dict]:
    """Estado de las dependencias directas de una tarea."""
    task_id = _uuid(task_id)
    rows = db.query(TaskDependency).filter(TaskDependency.task_id == task_id).all()
    out = []
    for row in rows:
        dep_task = _get_task(db, row.depends_on_id)
        if not dep_task:
            continue
        out.append({
            "depends_on_id": row.depends_on_id,
            "title": dep_task.title,
            "status": dep_task.status.value if hasattr(dep_task.status, "value") else str(dep_task.status),
            "satisfied": dep_task.status in (TaskStatus.DONE, TaskStatus.CANCELLED),
        })
    return out


def blocked_dependencies(db: Session, task_id: str) -> List[dict]:
    """Dependencias no satisfechas (bloquean la tarea)."""
    return [d for d in _dependency_status(db, task_id) if not d["satisfied"]]


def is_unblocked(db: Session, task_id: str) -> bool:
    return len(blocked_dependencies(db, task_id)) == 0


def refresh_task_status(db: Session, task: Task) -> Task:
    """Re-evalúa el estado de una tarea según sus dependencias.

    - Si tiene dependencias sin cumplir y está READY/ASSIGNED/IN_PROGRESS → BLOCKED
    - Si las cumplió y estaba BLOCKED → READY (o ASSIGNED si tiene asignado)
    Devuelve la tarea actualizada (sin commit).
    """
    deps = _dependency_status(db, str(task.id))
    has_blockers = any(not d["satisfied"] for d in deps)
    current = task.status.value if hasattr(task.status, "value") else str(task.status)

    if has_blockers and current not in ("done", "cancelled", "backlog", "blocked", "review"):
        task.status = TaskStatus.BLOCKED
    elif not has_blockers and current == "blocked":
        task.status = TaskStatus.ASSIGNED if task.assignee_id else TaskStatus.READY
    return task


def propagate(db: Session, changed_task_id: str) -> List[str]:
    """Cuando una tarea cambia, actualiza a sus dependientes directos.

    Devuelve los ids de tareas actualizadas.
    """
    changed_task_id = _uuid(changed_task_id)
    updated: List[str] = []
    dependents = db.query(TaskDependency).filter(TaskDependency.depends_on_id == changed_task_id).all()
    for row in dependents:
        task = _get_task(db, row.task_id)
        if not task:
            continue
        before = task.status.value if hasattr(task.status, "value") else str(task.status)
        refresh_task_status(db, task)
        after = task.status.value if hasattr(task.status, "value") else str(task.status)
        if before != after:
            updated.append(task.id)
    if updated:
        db.commit()
    return updated


def task_dag(db: Session, task_id: str) -> dict:
    """Vista del DAG de una tarea: dependencias directas + transitivas (2 niveles)."""
    task_id = _uuid(task_id)
    deps = _dependency_status(db, task_id)
    return {"task_id": task_id, "dependencies": deps, "blocked_by": blocked_dependencies(db, task_id)}
