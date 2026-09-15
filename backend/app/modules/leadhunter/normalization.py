"""Normalización de entidades para dedupe v2 (spec §12).

Extrae y mejora las funciones de normalización que vivían en discovery.py:
nombre de empresa (sin sufijos legales/acentos), dominio, teléfono (E.164-ish),
email y dirección. Todo queda en un solo módulo reutilizable por
discovery/import/CLI/agentes.
"""

import re
import unicodedata
from typing import Optional

# Sufijos legales que no cuentan para dedupe
LEGAL_SUFFIX_RE = re.compile(
    r"\b(s\.?a\.?|s\.?r\.?l\.?|s\.?a\.?c\.?i\.?|e\.?i\.?r\.?l\.?|"
    r"ltda?\.?|inc\.?|corp\.?|co\.?|sociedad anonima|sociedad de responsabilidad limitada)\b",
    re.I,
)

# Palabras genéricas que se descartan del nombre normalizado (no discriminan)
GENERIC_WORDS_RE = re.compile(
    r"\b(empresa|empresas|negocio|negocios|sociedad|comercial|corporacion|corporación|"
    r"grupo|grupos|centro|instituto|servicios|servicio|multiservicios|general|sa|srl|sac|ci|ltda)\b",
    re.I,
)

URL_RE = re.compile(r"https?://(?:www\.)?([^/]+)", re.I)


def _strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c))


def normalize_company(name: Optional[str]) -> str:
    """Nombre normalizado para dedupe: 'Cooperativa Ypacarai S.A.' → 'cooperativa ypacarai'."""
    if not name:
        return ""
    name = _strip_accents(name)
    name = LEGAL_SUFFIX_RE.sub(" ", name)
    name = re.sub(r"[^a-z0-9 ]", " ", name.lower())
    name = GENERIC_WORDS_RE.sub(" ", name)
    return re.sub(r"\s+", " ", name).strip()


def domain_of(url: Optional[str]) -> Optional[str]:
    """Dominio raíz de una URL: 'https://www.example.com.py/x' → 'example.com.py'."""
    if not url:
        return None
    m = URL_RE.match(url.strip())
    return m.group(1).lower() if m else None


def norm_phone(phone: Optional[str]) -> str:
    """Teléfono normalizado E.164-ish: solo dígitos, últimos 8 (número local PY).

    '(+595) 21 123-4567' → '211234567' → key '1234567'? No: devolvemos los
    últimos 8 dígitos: '211234567' tiene 9 dígitos → se recorta a '11234567'.
    Para comparar teléfonos PY (8 dígitos locales + prefijo 0xx o 595xx) se usa
    la cola de 8 dígitos como clave de dedupe.
    """
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    return digits[-8:] if digits else ""


def norm_email(email: Optional[str]) -> str:
    """Email normalizado: minúsculas, sin espacios."""
    if not email:
        return ""
    return email.strip().lower()


def norm_address(addr: Optional[str]) -> str:
    """Dirección normalizada: minúsculas, sin acentos, espacios colapsados."""
    if not addr:
        return ""
    a = _strip_accents(addr)
    a = re.sub(r"[^a-z0-9 ]", " ", a.lower())
    return re.sub(r"\s+", " ", a).strip()
