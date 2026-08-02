import sys
sys.path.append('/app')
from app.database import Base, engine
from app.models import user, project, agent, task, activity, sprint, metric, execution
Base.metadata.create_all(bind=engine)
print('✅ Tablas creadas')
