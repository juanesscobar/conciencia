"""Enriquecimiento automático: raspa el website del lead buscando email y teléfono."""

import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from .models import Lead
from .exceptions import RateLimitError

JUNK_EMAIL_RE = re.compile(
    r"(example|yourname|your-?email|someone|domain|test|sample|sentry|"
    r"wixpress|godaddy|1und1|\.png|\.jpg|\.jpeg|\.gif|\.webp|\.svg|@2x|\.js)",
    re.I,
)
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(
    r"(?:\+?595|0)\s?\d{1,2}\s?\d{2,3}[\s-]?\d{2,4}[\s-]?\d{2,4}|"
    r"\(\+?595\)\s?\d{1,2}[\s-]?\d{2,3}[\s-]?\d{2,4}",
)

# Dominios sociales / sin datos de contacto
SOCIAL_DOMAINS = ("facebook.com", "instagram.com", "twitter.com", "x.com", "linkedin.com", "youtube.com", "tiktok.com")


def _valid_phone(raw: str) -> bool:
    digits = re.sub(r"\D", "", raw)
    if not digits or len(digits) < 6 or len(digits) > 13:
        return False
    if digits.startswith(("000", "800", "900", "123")):
        return False
    if len(digits) >= 9 and not (digits.startswith("595") or digits.startswith("0")):
        return False
    return True

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MissionControl-LeadHunter/2.0",
    "Accept": "text/html,application/xhtml+xml",
}


def enrich_from_website(lead: Lead) -> dict:
    """Busca email/telefono en el sitio del lead y actualiza los campos vacíos."""
    if not lead.website:
        return {"changed": False, "reason": "sin website"}

    url = lead.website if lead.website.startswith(("http://", "https://")) else f"https://{lead.website}"
    host = (url.split("//")[-1].split("/")[0] or "").lower()
    if any(s in host for s in SOCIAL_DOMAINS):
        return {"changed": False, "reason": "red social, sin datos de contacto", "fetched": False}

    found = {"email": None, "phone": None, "fetched": False}

    try:
        resp = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 60))
            raise RateLimitError("website_enrichment", retry_after)
        resp.raise_for_status()
        found["fetched"] = True
        text = resp.text

        # Emails (excluye imagenes/junk)
        emails = [e.lower() for e in EMAIL_RE.findall(text)]
        emails = [e for e in emails if not JUNK_EMAIL_RE.search(e)]
        # Preferir mailto: y dominios propios
        own_domain = re.sub(r"^www\.", "", (lead.website.split("//")[-1].split("/")[0] or "").lower())
        emails.sort(key=lambda e: (own_domain not in e, len(e)))
        if emails:
            found["email"] = emails[0]

        # Teléfonos
        phones = PHONE_RE.findall(text)
        if phones:
            found["phone"] = next((p.strip().replace(" ", "") for p in phones if _valid_phone(p)), None)

        # Fallback: pagina de contacto
        if not (found["email"] or found["phone"]):
            for path in ("/contacto", "/contact", "/contactenos", "/contact-us"):
                try:
                    r = httpx.get(url.rstrip("/") + path, headers=HEADERS, timeout=10, follow_redirects=True)
                    if r.status_code == 200:
                        text = r.text
                        emails = [e.lower() for e in EMAIL_RE.findall(text)]
                        emails = [e for e in emails if not JUNK_EMAIL_RE.search(e)]
                        if emails:
                            found["email"] = emails[0]
                        phones = PHONE_RE.findall(text)
                        if phones:
                            found["phone"] = next((p.strip().replace(" ", "") for p in phones if _valid_phone(p)), None)
                        if found["email"] or found["phone"]:
                            break
                except Exception:  # noqa: BLE001
                    continue
    except Exception as e:  # noqa: BLE001
        return {"changed": False, "reason": str(e)[:200], **found}

    changed = False
    if found["email"] and not lead.email:
        lead.email = found["email"]
        changed = True
    if found["phone"] and not lead.phone:
        lead.phone = found["phone"]
        changed = True
    if changed:
        from .service import compute_score

        lead.score = compute_score(
            company=lead.company or "",
            industry=lead.industry or "",
            source=lead.source or "manual",
            email=lead.email or "",
            phone=lead.phone or "",
            notes=lead.notes or "",
            metadata=lead.meta,
        )

    return {"changed": changed, **found}
