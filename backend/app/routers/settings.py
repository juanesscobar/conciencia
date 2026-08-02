"""
Router de settings — configuración persistente (API keys, preferencias).

Endpoints:
  GET  /api/v1/settings/             — lista de settings (sin valores sensibles)
  GET  /api/v1/settings/deepseek     — estado de la config DeepSeek
  PUT  /api/v1/settings/deepseek     — guardar DEEPSEEK_API_KEY (admin)
  DELETE /api/v1/settings/deepseek   — borrar la key
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.user import User
from app.models.setting import Setting
from app.services.auth import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

SENSITIVE_KEYS = {"DEEPSEEK_API_KEY", "GITHUB_TOKEN", "OPENAI_API_KEY"}


class DeepSeekUpdate(BaseModel):
    api_key: str


class SettingResponse(BaseModel):
    key: str
    configured: bool
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


def require_admin(user: User):
    if user.role not in ("admin", "owner"):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user


@router.get("/", response_model=List[SettingResponse])
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = db.query(Setting).all()
    result = []
    for s in settings:
        if s.key in SENSITIVE_KEYS:
            result.append(SettingResponse(
                key=s.key,
                configured=bool(s.value),
                updated_at=s.updated_at.isoformat() if s.updated_at else None,
            ))
        else:
            result.append(SettingResponse(
                key=s.key,
                configured=bool(s.value),
                updated_at=s.updated_at.isoformat() if s.updated_at else None,
            ))
    return result


@router.get("/deepseek", response_model=SettingResponse)
def get_deepseek_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    setting = db.query(Setting).filter(Setting.key == "DEEPSEEK_API_KEY").first()
    return SettingResponse(
        key="DEEPSEEK_API_KEY",
        configured=bool(setting and setting.value),
        updated_at=setting.updated_at.isoformat() if setting and setting.updated_at else None,
    )


@router.put("/deepseek", response_model=SettingResponse)
def update_deepseek_key(
    req: DeepSeekUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    api_key = req.api_key.strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="API key cannot be empty")

    setting = db.query(Setting).filter(Setting.key == "DEEPSEEK_API_KEY").first()
    if setting:
        setting.value = api_key
    else:
        setting = Setting(key="DEEPSEEK_API_KEY", value=api_key)
        db.add(setting)
    db.commit()

    # Aplicar en runtime para el motor de agentes
    try:
        import os
        os.environ["DEEPSEEK_API_KEY"] = api_key
    except Exception:
        pass

    return SettingResponse(
        key="DEEPSEEK_API_KEY",
        configured=True,
        updated_at=setting.updated_at.isoformat() if setting.updated_at else None,
    )


@router.delete("/deepseek", response_model=SettingResponse)
def delete_deepseek_key(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    setting = db.query(Setting).filter(Setting.key == "DEEPSEEK_API_KEY").first()
    if setting:
        db.delete(setting)
        db.commit()
    try:
        import os
        os.environ.pop("DEEPSEEK_API_KEY", None)
    except Exception:
        pass
    return SettingResponse(key="DEEPSEEK_API_KEY", configured=False, updated_at=None)
