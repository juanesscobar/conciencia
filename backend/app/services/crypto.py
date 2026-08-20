"""Cifrado simétrico para secrets en DB (Fernet, derivado de SECRET_KEY).

Uso:
    from app.services.crypto import encrypt_secret, decrypt_secret

- encrypt_secret: cifra texto plano -> token Fernet (str).
- decrypt_secret: descifra token -> texto plano. Si el valor NO es un
  token Fernet válido (ej. credencial legacy en texto plano), lo devuelve
  tal cual para no romper cuentas creadas antes del cifrado.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import SECRET_KEY

_PREFIX = "enc:"


def _fernet() -> Fernet:
    digest = hashlib.sha256(SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plain: str) -> str:
    """Cifra un secret. Devuelve '' si la entrada está vacía."""
    if not plain:
        return plain
    token = _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")
    return f"{_PREFIX}{token}"


def decrypt_secret(stored: str) -> str:
    """Descifra un secret. Tolera valores legacy en texto plano."""
    if not stored:
        return stored
    if stored.startswith(_PREFIX):
        raw = stored[len(_PREFIX):]
        try:
            return _fernet().decrypt(raw.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError):
            return stored  # token inválido: devolver tal cual (no romper)
    return stored  # legacy: texto plano
