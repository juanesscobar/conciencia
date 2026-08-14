"""
Router de settings e integraciones — configuración persistente (API keys, proveedor LLM, GitHub).

Endpoints:
  GET   /api/v1/settings/                    — lista de settings (sin valores sensibles)
  GET   /api/v1/settings/integrations        — estado agrupado de integraciones (github, llm, leadhunter)
  PUT   /api/v1/settings/{key}               — upsert genérico (admin)
  DELETE /api/v1/settings/{key}              — borrar setting (admin)
  GET   /api/v1/settings/llm                 — config activa del proveedor LLM (sin key)
  POST  /api/v1/settings/llm/test            — probar conexión LLM (requiere key, no la guarda)
  GET   /api/v1/settings/deepseek            — estado DeepSeek (backward-compat)
  PUT   /api/v1/settings/deepseek            — guardar DEEPSEEK_API_KEY (backward-compat)
  DELETE /api/v1/settings/deepseek           — borrar la key (backward-compat)
  POST  /api/v1/settings/github/test         — probar token GitHub
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.setting import Setting
from app.services.auth import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

SENSITIVE_KEYS = {
    "LLM_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY", "OPENROUTER_API_KEY", "GITHUB_TOKEN", "RESEND_API_KEY", "SMTP_PASS",
}
VISIBLE_KEYS = {
    "LLM_PROVIDER", "LLM_MODEL", "LLM_BASE_URL", "LLM_FALLBACK_PROVIDERS",
    "GITHUB_USERNAME",
    "LEADHUNTER_CRON", "LEADHUNTER_BBOX", "LEADHUNTER_SCOPE",
    "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_FROM",
}


class KeyUpdate(BaseModel):
    value: str


class LLMConfigUpdate(BaseModel):
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None


class EmailTestRequest(BaseModel):
    to_email: Optional[str] = None


class SettingResponse(BaseModel):
    key: str
    configured: bool
    updated_at: Optional[str] = None


def require_admin(user: User):
    if user.role not in ("admin", "owner", "ceo"):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user


def _get(db: Session, key: str) -> Optional[Setting]:
    return db.query(Setting).filter(Setting.key == key).first()


def _upsert(db: Session, key: str, value: str) -> Setting:
    setting = _get(db, key)
    if setting:
        setting.value = value
        setting.updated_at = datetime.utcnow()
    else:
        setting = Setting(key=key, value=value)
        db.add(setting)
    db.commit()
    db.refresh(setting)
    # Aplicar en runtime (las claves de setting son también nombres de env var)
    import os
    os.environ[key] = value
    return setting


@router.get("/", response_model=List[SettingResponse])
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = db.query(Setting).all()
    return [
        SettingResponse(
            key=s.key,
            configured=bool(s.value),
            updated_at=s.updated_at.isoformat() if s.updated_at else None,
        )
        for s in settings
    ]


@router.get("/integrations")
def get_integrations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Estado agrupado de todas las integraciones (nunca expone valores)."""
    from app.services.llm import get_config
    from app.config import LEADHUNTER_CRON, LEADHUNTER_BBOX
    import os

    cfg = get_config()
    gh_token = os.getenv("GITHUB_TOKEN") or _db_setting("GITHUB_TOKEN")
    gh_user = os.getenv("GITHUB_USERNAME") or _db_setting("GITHUB_USERNAME") or "juanesscobar"

    return {
        "github": {
            "configured": bool(gh_token),
            "username": gh_user,
        },
        "llm": {
            "configured": bool(cfg["api_key"]),
            "provider": cfg["provider"],
            "model": cfg["model"],
            "base_url": cfg["base_url"],
            "simulated": not bool(cfg["api_key"]),
        },
        "leadhunter": {
            "cron": os.getenv("LEADHUNTER_CRON", LEADHUNTER_CRON),
            "bbox": os.getenv("LEADHUNTER_BBOX", LEADHUNTER_BBOX),
            "scope": os.getenv("LEADHUNTER_SCOPE", "bbox"),
        },
        "email": {
            "smtp_configured": bool(os.getenv("SMTP_HOST") or _db_setting("SMTP_HOST")),
            "host": os.getenv("SMTP_HOST") or _db_setting("SMTP_HOST") or None,
            "from": os.getenv("SMTP_FROM") or _db_setting("SMTP_FROM") or None,
        },
    }


@router.get("/providers")
def get_providers_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Estado de todos los providers LLM (configurado o no, sin exponer keys)."""
    import os

    providers = {
        "deepseek": {
            "configured": bool(os.getenv("DEEPSEEK_API_KEY") or _db_setting("DEEPSEEK_API_KEY")),
            "default_model": "deepseek-chat",
            "default_base_url": "https://api.deepseek.com",
        },
        "openai": {
            "configured": bool(os.getenv("OPENAI_API_KEY") or _db_setting("OPENAI_API_KEY")),
            "default_model": "gpt-4o-mini",
            "default_base_url": "https://api.openai.com/v1",
        },
        "anthropic": {
            "configured": bool(os.getenv("ANTHROPIC_API_KEY") or _db_setting("ANTHROPIC_API_KEY")),
            "default_model": "claude-sonnet-4-20250514",
            "default_base_url": "",
        },
        "google": {
            "configured": bool(os.getenv("GOOGLE_API_KEY") or _db_setting("GOOGLE_API_KEY")),
            "default_model": "gemini-2.0-flash",
            "default_base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        },
        "ollama": {
            "configured": True,  # local, no requiere key
            "default_model": "llama3.2",
            "default_base_url": "http://localhost:11434/v1",
        },
        "openrouter": {
            "configured": bool(os.getenv("OPENROUTER_API_KEY") or _db_setting("OPENROUTER_API_KEY")),
            "default_model": "deepseek/deepseek-chat",
            "default_base_url": "https://openrouter.ai/api/v1",
        },
    }

    return providers


@router.put("/{key}", response_model=SettingResponse)
def set_setting(
    key: str,
    req: KeyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    if key not in SENSITIVE_KEYS and key not in VISIBLE_KEYS:
        raise HTTPException(status_code=400, detail=f"Setting no permitido: {key}")
    value = req.value.strip()
    if not value:
        raise HTTPException(status_code=400, detail="Value cannot be empty")
    setting = _upsert(db, key, value)
    return SettingResponse(key=key, configured=True, updated_at=setting.updated_at.isoformat() if setting.updated_at else None)


@router.delete("/{key}", response_model=SettingResponse)
def delete_setting(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    setting = _get(db, key)
    if setting:
        db.delete(setting)
        db.commit()
    import os
    os.environ.pop(key, None)
    return SettingResponse(key=key, configured=False, updated_at=None)


@router.get("/llm")
def get_llm_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.llm import get_config
    cfg = get_config()
    return {
        "provider": cfg["provider"],
        "model": cfg["model"],
        "base_url": cfg["base_url"],
        "configured": bool(cfg["api_key"]),
        "simulated": not bool(cfg["api_key"]),
    }


@router.post("/llm/test")
def test_llm(
    req: LLMConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Prueba una conexión LLM (con la config pasada o la activa). No persiste nada."""
    from app.services.llm import test_connection
    result = test_connection(
        provider=req.provider,
        api_key=req.api_key,
        model=req.model,
        base_url=req.base_url,
    )
    return result


@router.post("/email/test")
def test_email(
    req: EmailTestRequest = EmailTestRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Envía un email de prueba por SMTP con la config guardada. No persiste nada."""
    from app.modules.leadhunter.delivery import send_email
    import os

    to = (req.to_email or "").strip()
    if not to:
        to = (os.getenv("SMTP_FROM") or _db_setting("SMTP_FROM") or os.getenv("SMTP_USER") or _db_setting("SMTP_USER") or "").strip()
    if not to:
        raise HTTPException(status_code=400, detail="No hay destinatario: configurá SMTP_FROM/SMTP_USER o pasá to_email")

    result = send_email(
        to_email=to,
        subject="🧪 Test de conexión — Mission Control",
        body=(
            "Hola! 👋\n\n"
            "Este es un email de prueba desde Mission Control.\n"
            "Si lo estás viendo, la integración de correo (SMTP) funciona correctamente.\n\n"
            "— Mission Control"
        ),
    )
    return result


@router.post("/github/test")
def test_github(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verifica que el GITHUB_TOKEN funciona contra la API de GitHub."""
    import os
    import httpx

    token = os.getenv("GITHUB_TOKEN") or _db_setting("GITHUB_TOKEN")
    if not token:
        return {"ok": False, "error": "GITHUB_TOKEN no configurado"}

    try:
        resp = httpx.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            return {"ok": True, "login": data.get("login"), "name": data.get("name")}
        return {"ok": False, "error": f"GitHub respondió {resp.status_code}: {resp.text[:150]}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:300]}


def _db_setting(key: str) -> str:
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        s = db.query(Setting).filter(Setting.key == key).first()
        return s.value if s and s.value else ""
    finally:
        db.close()


# ===== Backward-compat DeepSeek =====


class DeepSeekUpdate(BaseModel):
    api_key: str


@router.get("/deepseek", response_model=SettingResponse)
def get_deepseek_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    setting = _get(db, "DEEPSEEK_API_KEY")
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
    setting = _upsert(db, "DEEPSEEK_API_KEY", api_key)
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
    setting = _get(db, "DEEPSEEK_API_KEY")
    if setting:
        db.delete(setting)
        db.commit()
    try:
        import os
        os.environ.pop("DEEPSEEK_API_KEY", None)
    except Exception:
        pass
    return SettingResponse(key="DEEPSEEK_API_KEY", configured=False, updated_at=None)
