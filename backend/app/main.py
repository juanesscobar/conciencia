from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.routers import projects, tasks, activities
from app.routers import github as github_router
from app.routers import metrics
from app.modules.jobscout.router import router as jobscout_router
from app.config import get_cors_origins, ENVIRONMENT
from app.database import engine, Base

app = FastAPI(
    title="Mission Control",
    description="Software Factory + Project Governance System",
    version="1.0.0-alpha"
)

origins = get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(activities.router)
app.include_router(metrics.router)
app.include_router(github_router.router)
app.include_router(jobscout_router)

@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)

@app.get("/")
async def root():
    return {
        "name": "Mission Control",
        "version": "1.0.0-alpha",
        "status": "operational",
        "ceo": "Iron Toto",
        "environment": ENVIRONMENT
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
