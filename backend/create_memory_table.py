import sys
sys.path.append('/app')
from app.database import engine, Base
import app.models  # registra todos los modelos

Base.metadata.create_all(bind=engine)

# Verificar tabla
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
print("Tablas:", len(tables))
print("user_memories existe:", "user_memories" in tables)
