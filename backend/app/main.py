from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.routers import projects, tasks, activities
from app.routers import github as github_router

app = FastAPI(
    title="Mission Control",
    description="Software Factory + Project Governance System",
    version="1.0.0-alpha"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(activities.router)
app.include_router(github_router.router)

@app.get("/")
async def root():
    return {
        "name": "Mission Control",
        "version": "1.0.0-alpha",
        "status": "operational",
        "ceo": "Iron Toto"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
