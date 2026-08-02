import re

path = "app/models/execution.py"
with open(path) as f:
    s = f.read()

s = s.replace(
    'task_id = Column(Uuid, ForeignKey("tasks.id"), nullable=False)',
    'task_id = Column(Uuid, ForeignKey("tasks.id"), nullable=True)',
)

with open(path, "w") as f:
    f.write(s)

print("execution.py actualizado:")
for line in s.splitlines():
    if "task_id" in line:
        print("  ", line.strip())
