"""Sync de esquema idempotente para DBs viejas (create_all no altera tablas existentes).
Se ejecuta en startup (main.py) y en scripts de seed. Cubre:
1) ALTER TABLE ADD COLUMN para columnas faltantes
2) Normalización de enums almacenados en mayúsculas → lowercase (valores de los modelos)
"""
from sqlalchemy import inspect, text

_ENUM_LOWERCASE_COLS = [
    "activities.type", "agents.role", "agents.type", "agents.status", "agents.autonomy_level",
    "tasks.status", "tasks.priority", "tasks.type", "projects.status", "projects.priority",
    "projects.category", "sprints.status", "agent_executions.status", "metrics.category", "metrics.period",
]


def sync_schema(engine, base) -> None:
    try:
        insp = inspect(engine)
        existing = set(insp.get_table_names())

        for table in base.metadata.sorted_tables:
            if table.name not in existing:
                continue
            db_cols = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in db_cols:
                    continue
                try:
                    coltype = col.type.compile(dialect=engine.dialect)
                    with engine.begin() as conn:
                        conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN "{col.name}" {coltype}'))
                except Exception:  # noqa: BLE001
                    pass

        # Normalizar enums a MAYÚSCULAS (esta versión de SQLAlchemy persiste por nombre,
        # ej: 'DEV', 'NEW', 'COMMIT'). Corrige filas viejas con valores en minúsculas.
        with engine.begin() as conn:
            for table_col in _ENUM_LOWERCASE_COLS:
                table, col = table_col.split(".")
                if table not in existing or col not in {c["name"] for c in insp.get_columns(table)}:
                    continue
                try:
                    conn.execute(text(f"UPDATE {table} SET {col} = upper({col}) WHERE {col} != upper({col})"))
                except Exception:  # noqa: BLE001
                    pass

            # Valores de enums viejos que ya no existen en los modelos (ej: 'ACTIVE')
            try:
                conn.execute(text(
                    "UPDATE agents SET status='IDLE' WHERE status NOT IN ('IDLE','WORKING','PAUSED','ERROR')"
                ))
            except Exception:  # noqa: BLE001
                pass

            # TaskPriority viejo (P0-P3) -> CRITICAL/HIGH/MEDIUM/LOW
            for old, new in [("P0", "CRITICAL"), ("P1", "HIGH"), ("P2", "MEDIUM"), ("P3", "LOW")]:
                try:
                    conn.execute(text(f"UPDATE tasks SET priority='{new}' WHERE priority='{old}'"))
                except Exception:  # noqa: BLE001
                    pass

            # Tasks viejas sin tipo/status/prioridad -> defaults
            try:
                conn.execute(text("UPDATE tasks SET type='FEATURE' WHERE type IS NULL OR type=''"))
            except Exception:  # noqa: BLE001
                pass
            try:
                conn.execute(text("UPDATE tasks SET status='BACKLOG' WHERE status IS NULL OR status=''"))
            except Exception:  # noqa: BLE001
                pass
            try:
                conn.execute(text("UPDATE tasks SET priority='MEDIUM' WHERE priority IS NULL OR priority=''"))
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001
        pass
