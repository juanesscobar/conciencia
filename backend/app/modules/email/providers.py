"""Presets de proveedores de email (multi-proveedor)."""

from typing import Dict, Optional


PROVIDERS: Dict[str, dict] = {
    "gmail": {
        "label": "Gmail",
        "imap_host": "imap.gmail.com",
        "imap_port": 993,
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "requires_app_password": True,
        "note": "Requiere App Password (2FA activo): cuenta.google.com → Seguridad → App passwords",
    },
    "outlook": {
        "label": "Outlook / Office 365",
        "imap_host": "outlook.office365.com",
        "imap_port": 993,
        "smtp_host": "smtp.office365.com",
        "smtp_port": 587,
        "requires_app_password": False,
        "note": "Puede requerir App Password si hay MFA activo.",
    },
    "generic": {
        "label": "IMAP/SMTP genérico",
        "imap_host": "",
        "imap_port": 993,
        "smtp_host": "",
        "smtp_port": 587,
        "requires_app_password": False,
        "note": "Cualquier proveedor con IMAP + SMTP. Completá hosts/puertos manualmente.",
    },
}


def resolve_provider(provider: str, account: dict) -> dict:
    """Resuelve la config efectiva de una cuenta (preset + overrides)."""
    preset = PROVIDERS.get((provider or "generic").lower(), PROVIDERS["generic"])
    return {
        "imap_host": (account.get("imap_host") or "").strip() or preset["imap_host"],
        "imap_port": account.get("imap_port") or preset["imap_port"],
        "smtp_host": (account.get("smtp_host") or "").strip() or preset["smtp_host"],
        "smtp_port": account.get("smtp_port") or preset["smtp_port"],
    }


def list_providers() -> list:
    return [
        {"id": pid, **{k: v for k, v in p.items() if k != "note"}}
        for pid, p in PROVIDERS.items()
    ]
