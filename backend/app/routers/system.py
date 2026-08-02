"""
Router de sistema — health, logs en tiempo real, info.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from app.models.user import User
from app.services.auth import get_current_user
from app.services.system_logger import get_logs, add_log

router = APIRouter(prefix="/api/v1/system", tags=["system"])


class LogEntry(BaseModel):
    timestamp: str
    level: str
    source: str
    message: str


class SystemInfo(BaseModel):
    name: str
    version: str
    status: str
    environment: str


@router.get("/info", response_model=SystemInfo)
def system_info():
    from app.config import ENVIRONMENT
    return SystemInfo(
        name="Mission Control",
        version="2.0.0-alpha",
        status="operational",
        environment=ENVIRONMENT,
    )


@router.get("/logs", response_model=List[LogEntry])
def system_logs(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
):
    return get_logs(min(max(limit, 1), 200))
