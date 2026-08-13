"""Task DAG: dependencias entre tareas (n-n) con estados READY/BLOCKED.

Una tarea se desbloquea cuando todas sus dependencias directas están DONE
(o CANCELLED — no bloquea). Los estados del pipeline:

BACKLOG → READY → ASSIGNED → RUNNING → REVIEW → DONE
                      └→ BLOCKED (dependencia sin cumplir)
"""

from sqlalchemy import Column, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class TaskDependency(Base):
    """Arco del DAG: task_id depende de depends_on_id."""

    __tablename__ = "task_dependencies"
    __table_args__ = (UniqueConstraint("task_id", "depends_on_id", name="uq_task_dep"),)

    id = Column(String, primary_key=True, default=lambda: __import__("uuid").uuid4().hex)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    depends_on_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String, default="finish_to_start")  # finish_to_start (único por ahora)

    task = relationship("Task", foreign_keys=[task_id], back_populates="dependencies")
    depends_on = relationship("Task", foreign_keys=[depends_on_id])

    def to_dict(self) -> dict:
        return {"id": self.id, "task_id": self.task_id, "depends_on_id": self.depends_on_id, "kind": self.kind}
