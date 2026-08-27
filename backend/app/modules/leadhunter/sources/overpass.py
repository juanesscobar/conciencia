"""Fuente Overpass API (OpenStreetMap) — descubre negocios reales sin API key.

Busca por categoría dentro de un bounding box (default: Gran Asunción) usando
la API pública de Overpass (https://overpass-api.de). Tags de OSM se mapean a
los sectores objetivo de la software factory: cooperativas, salud, farmacia,
distribuidoras, comercio, financiero e industria.
"""

import os
import re
import time
from typing import List, Optional

import httpx

from .base import BaseLeadSource, register_source
from ..exceptions import RateLimitError, SourceTimeoutError, SourceUnavailableError

OVERPASS_ENDPOINT = "https://overpass-api.de/api/interpreter"
OVERPASS_ENDPOINTS = [
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]

# Área de Paraguay (relation 2870777) para búsqueda a nivel país (LEADHUNTER_SCOPE=country)
PARAGUAY_AREA = 3602870777


def _build_global_query() -> str:
    """Query sin restricción geográfica (todo el mundo).

    SOLO se usa cuando el usuario pide scope global explícitamente (allow_global).
    """
    parts = [f"  {q};" for q, _, _ in CATEGORIES]
    body = "\n".join(parts)
    return (
        "[out:json][timeout:120];\n(\n"
        + body
        + "\n);\nout center tags;"
    )


def _build_area_query(area_id: int) -> str:
    """Query a nivel de un área/país cualquiera (usa la relación admin_level=2 de OSM)."""
    parts = []
    for q, industry, segment in CATEGORIES:
        q2 = q.replace("(", f"(area:{area_id})", 1)
        parts.append(f"  {q2};")
    body = "\n".join(parts)
    return (
        "[out:json][timeout:120];\n(\n"
        + body
        + "\n);\nout center tags;"
    )

# Entes públicos / postas de salud / no-B2B que ensucian el pipeline
EXCLUDE_NAME_RE = re.compile(
    r"^(ministerio|direcci|mspbs|senadis|inat|centro nacional|instituto nacional|"
    r"parque sanitario|complejo hospital|predio del|usf |unidad de salud familiar|"
    r"puesto de salud|unidad sanitaria|centro de salud|cuerpo de bomberos|cruz roja|"
    r"centro nacional de|liga contra|direccion general)",
    re.I,
)
EXCLUDE_COUNTRY_RE = re.compile(r"\b(clorinda|formosa|argentina)\b", re.I)

# (tag_query, industry, segment)
CATEGORIES = [
    # Salud
    ('node["amenity"="hospital"]', "salud", "mediana"),
    ('way["amenity"="hospital"]', "salud", "mediana"),
    ('node["amenity"="clinic"]', "salud", "pyme"),
    ('way["amenity"="clinic"]', "salud", "pyme"),
    ('node["amenity"="dentist"]', "salud", "pyme"),
    ('way["amenity"="dentist"]', "salud", "pyme"),
    ('node["amenity"="pharmacy"]', "farmacia", "pyme"),
    ('way["amenity"="pharmacy"]', "farmacia", "pyme"),
    # Financiero / cooperativas
    ('node["amenity"="bank"]', "financiero", "mediana"),
    ('way["amenity"="bank"]', "financiero", "mediana"),
    ('node["shop"="financial"]', "financiero", "pyme"),
    ('way["shop"="financial"]', "financiero", "pyme"),
    ('node["name"~"cooperativa",i]', "cooperativa", "mediana"),
    ('way["name"~"cooperativa",i]', "cooperativa", "mediana"),
    # Comercio / distribuidoras
    ('node["shop"="supermarket"]', "comercio", "pyme"),
    ('way["shop"="supermarket"]', "comercio", "pyme"),
    ('node["shop"="wholesale"]', "distribuidora", "pyme"),
    ('way["shop"="wholesale"]', "distribuidora", "pyme"),
    ('node["name"~"distribuidor",i]', "distribuidora", "pyme"),
    ('way["name"~"distribuidor",i]', "distribuidora", "pyme"),
    # Industria
    ('node["name"~"industria|fábrica|fabrica",i]', "industria", "mediana"),
    ('way["name"~"industria|fábrica|fabrica",i]', "industria", "mediana"),
]

# Junk emails típicos de templates de websites
JUNK_EMAIL_RE = re.compile(
    r"(example|yourname|your-?email|someone|domain|test|sample|sentry|"
    r"wixpress|godaddy|1und1|\.png|\.jpg|\.jpeg|\.gif|\.webp|\.svg|@2x)",
    re.I,
)


def _clean_url(url: str) -> Optional[str]:
    if not url:
        return None
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    if " " in url or len(url) > 200:
        return None
    return url


def _clean_phone(phone: str) -> Optional[str]:
    if not phone:
        return None
    phone = phone.strip()
    # Solo números, + y espacios/guiones
    if not re.search(r"\d{6,}", phone):
        return None
    return phone[:40]


def _tag(tags: dict, *keys: str) -> Optional[str]:
    for k in keys:
        if tags.get(k):
            return tags[k]
    return None


def _industry_for(category: str) -> str:
    return category.split("|")[1] if "|" in category else "comercio"


def _build_query(bbox: str) -> str:
    parts = []
    for q, industry, segment in CATEGORIES:
        parts.append(f'  {q}({bbox});')
    body = "\n".join(parts)
    return (
        "[out:json][timeout:60];\n(\n"
        + body
        + "\n);\nout center tags;"
    )


def _build_country_query(area_id: int) -> str:
    """Query a nivel país (sin restricción geográfica local): usa el área de Paraguay.

    Compat: equivalente a _build_area_query; se mantiene por retrocompatibilidad.
    """
    return _build_area_query(area_id)


@register_source
class OverpassSource(BaseLeadSource):
    name = "overpass"
    label = "OpenStreetMap (Overpass)"
    description = "Negocios del Gran Asunción por categoría (salud, cooperativas, distribuidoras, comercio...). Sin API key."
    enabled = True

    def __init__(self):
        self.bbox = os.getenv("LEADHUNTER_BBOX", "-25.55,-57.75,-25.15,-57.40")
        self.scope = os.getenv("LEADHUNTER_SCOPE", "bbox").strip().lower()

    def _resolve_query(self, geo: Optional[dict]) -> str:
        """Elige la query Overpass según el contexto geográfico efectivo (geo.build_geo_context).

        Prioridad:
          1. geo global → sin restricción de área (solo si allow_global explícito)
          2. area_id conocido (país) → query a nivel país
          3. bbox resuelto (región/ciudad) → query por bbox
          4. fallback → bbox de env (compat: Gran Asunción)
        """
        if geo is not None:
            if geo.get("is_global"):
                return _build_global_query()
            area_id = geo.get("area_id")
            if area_id:
                return _build_area_query(area_id)
            bbox = geo.get("bbox")
            if bbox and len(bbox) == 4:
                return _build_query(",".join(str(x) for x in bbox))
            # scope multi/global sin bbox → país default como salvaguarda
            country = (geo.get("scope") or {}).default_country
            area_id = geo.get("area_id")
            if not area_id:
                from ..geo import COUNTRY_AREAS

                area_id = COUNTRY_AREAS.get(country or "PY")
            if area_id:
                return _build_area_query(area_id)
        # Fallback compat: env
        if self.scope == "country":
            return _build_country_query(PARAGUAY_AREA)
        return _build_query(self.bbox)

    def fetch(self, limit: Optional[int] = None, geo: Optional[dict] = None) -> List[dict]:
        query = self._resolve_query(geo)
        timeout = 150 if (geo is None and self.scope == "country") or (geo and not geo.get("bbox")) else 120
        last_error: Optional[Exception] = None

        for endpoint in OVERPASS_ENDPOINTS:
            for attempt in range(3):
                try:
                    resp = httpx.post(
                        endpoint,
                        data={"data": query},
                        timeout=timeout,
                        headers={"User-Agent": "ConcienciaPlatform-LeadHunter/2.1 (contact: juanesscobar)"},
                    )
                    if resp.status_code == 429:
                        retry_after = int(resp.headers.get("Retry-After", 60))
                        raise RateLimitError("overpass", retry_after)
                    resp.raise_for_status()
                    data = resp.json()
                    elements = data.get("elements", [])
                    leads = self._parse_elements(elements)
                    return leads[:limit] if limit else leads
                except RateLimitError:
                    raise
                except httpx.TimeoutException as e:
                    last_error = SourceTimeoutError("overpass", timeout)
                    time.sleep(2 ** attempt)
                    continue
                except httpx.HTTPStatusError as e:
                    last_error = e
                    time.sleep(2 ** attempt)
                    continue
                except Exception as e:  # noqa: BLE001
                    last_error = e
                    time.sleep(2 ** attempt)
                    continue

        raise SourceUnavailableError("overpass", str(last_error))

    def _parse_elements(self, elements: list) -> List[dict]:
        leads: List[dict] = []
        seen: set = set()

        for el in elements:
            tags = el.get("tags") or {}
            name = (tags.get("name") or "").strip()
            if not name or len(name) < 3 or ";" in name:
                continue
            if EXCLUDE_NAME_RE.match(name):
                continue
            if tags.get("office") == "government" or tags.get("amenity") == "government":
                continue
            phone_raw = _tag(tags, "phone", "contact:phone", "contact:mobile") or ""
            address_raw = _tag(tags, "addr:street", "addr:city") or ""
            if phone_raw.strip().startswith("+54") or EXCLUDE_COUNTRY_RE.search(name + " " + address_raw):
                continue
            if (tags.get("addr:country") or "").upper() == "AR":
                continue

            key = re.sub(r"[^a-z0-9]", "", name.lower())
            if key in seen:
                continue
            seen.add(key)

            lat = el.get("lat")
            lon = el.get("lon")
            if lat is None and el.get("center"):
                lat = el["center"].get("lat")
                lon = el["center"].get("lon")

            phone = _clean_phone(phone_raw)
            email = _tag(tags, "email", "contact:email")
            if email and JUNK_EMAIL_RE.search(email):
                email = None
            website = _clean_url(
                _tag(tags, "website", "contact:website", "url", "contact:webcam")
            )

            addr_parts = [
                tags.get("addr:street") or "",
                tags.get("addr:housenumber") or "",
                tags.get("addr:city") or "",
            ]
            address = ", ".join([p for p in addr_parts if p]).strip() or None

            # Región: ciudad, luego suburbio, luego localidad del address
            region = tags.get("addr:city") or tags.get("addr:suburb") or tags.get("addr:town") or None
            if not region and address:
                region = address.split(",")[-1].strip() or None
            if region:
                region = region[:80]

            industry = _industry_for(tags.get("industry") or "comercio")
            # Inferir industria por tags reales
            if tags.get("amenity") == "hospital":
                industry = "salud"
            elif tags.get("amenity") == "clinic":
                industry = "salud"
            elif tags.get("amenity") == "pharmacy":
                industry = "farmacia"
            elif tags.get("amenity") == "bank":
                industry = "financiero"
            elif tags.get("shop") == "supermarket":
                industry = "comercio"
            elif tags.get("shop") == "wholesale":
                industry = "distribuidora"
            if re.search(r"cooperativa", name, re.I):
                industry = "cooperativa"
            if re.search(r"distribuidor", name, re.I):
                industry = "distribuidora"

            segment = "mediana" if industry in ("salud", "financiero", "cooperativa", "industria") else "pyme"

            leads.append({
                "company": name,
                "industry": industry,
                "segment": segment,
                "region": region,
                "phone": phone,
                "email": email,
                "website": website,
                "address": address,
                "meta": {
                    "source_detail": "overpass",
                    "osm_type": el.get("type"),
                    "osm_id": el.get("id"),
                    "lat": lat,
                    "lon": lon,
                    "address": address,
                    "region": region,
                },
            })

        return leads
