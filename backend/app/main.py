from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from app.routers import projects, tasks, activities
from app.routers import github as github_router
from app.routers import metrics
from app.routers import auth as auth_router
from app.routers import agents as agents_router
from app.routers import memories as memories_router
from app.routers import settings as settings_router
from app.routers import system as system_router
from app.routers import reports as reports_router
from app.routers import sprints as sprints_router
from app.routers import audit as audit_router
from app.routers import workflows as workflows_router
from app.modules.jobscout.router import router as jobscout_router
from app.modules.leadhunter.router import router as leadhunter_router, intake_router as leadhunter_intake_router
from app.modules.leadhunter.scheduler import start_scheduler, stop_scheduler
from app.modules.whatsapp.router import router as whatsapp_router
from app.config import get_cors_origins, ENVIRONMENT
from app.services.system_logger import setup_logging
from app.database import Base, engine

# Crea tablas faltantes automáticamente (idempotente, no pisa migraciones alembic)
from app import models  # noqa: F401  (registra todos los modelos en Base.metadata)
Base.metadata.create_all(bind=engine)

from app.db_sync import sync_schema
sync_schema(engine, Base)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Mission Control",
    description="Software Factory + Project Governance System",
    version="2.0.0-alpha",
    lifespan=lifespan,
)

# Logging del sistema
setup_logging()

origins = get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(activities.router)
app.include_router(metrics.router)
app.include_router(github_router.router)
app.include_router(agents_router.router)
app.include_router(memories_router.router)
app.include_router(settings_router.router)
app.include_router(system_router.router)
app.include_router(reports_router.router)
app.include_router(sprints_router.router)
app.include_router(audit_router.router)
app.include_router(workflows_router.router)
app.include_router(jobscout_router)
app.include_router(leadhunter_router)
app.include_router(leadhunter_intake_router)
app.include_router(whatsapp_router)


@app.middleware("http")
async def log_requests(request, call_next):
    """Loguea cada request HTTP en el buffer del sistema."""
    import time
    from app.services.system_logger import add_log
    start = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start) * 1000)
    if request.url.path.startswith("/api"):
        add_log(
            "INFO",
            "http",
            f"{request.method} {request.url.path} → {response.status_code} ({duration_ms}ms)",
        )
    return response


@app.get("/")
async def root():
    return {
        "name": "Mission Control",
        "version": "2.0.0-alpha",
        "status": "operational",
        "ceo": "Iron Toto",
        "environment": ENVIRONMENT
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
