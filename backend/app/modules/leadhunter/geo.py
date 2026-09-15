"""Geographic scope + GeoProvider abstraction (spec §7-10).

La geografía es first-class: país default configurable (PY), países permitidos,
jerarquía país → región → ciudad, y scope explícito (city|region|country|multi|global).
Global SOLO se permite si el usuario lo pide explícitamente (allow_global=True).

El provider geográfico está abstraído (GeoProvider) para poder agregar
Google Maps / Mapbox / Here / custom sin tocar el Search Engine.
"""

import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import httpx

# Áreas de Overpass (relation id + 3600000000) para queries a nivel país.
# Fuente: OpenStreetMap relations (admin_level=2).
COUNTRY_AREAS: Dict[str, int] = {
    "PY": 3602870777,   # Paraguay
    "BR": 36059470,     # Brazil
    "AR": 360446573,    # Argentina
    "UY": 360287072,    # Uruguay
}

COUNTRY_NAMES: Dict[str, str] = {
    "PY": "Paraguay",
    "BR": "Brazil",
    "AR": "Argentina",
    "UY": "Uruguay",
}

# Scopes válidos de búsqueda (spec §8)
VALID_SCOPES = ("city", "region", "country", "multi", "global")

GEO_CACHE_TTL = int(os.getenv("SEARCH_CACHE_TTL", "86400"))  # 24h


class GeoScopeError(ValueError):
    """Scope geográfico inválido o no permitido."""


@dataclass
class GeographicScope:
    """Ámbito geográfico vigente (spec §8-9). Se resuelve de Settings/env con defaults PY."""

    default_country: str = "PY"
    allowed_countries: List[str] = field(default_factory=lambda: ["PY", "BR", "AR", "UY"])
    default_region: Optional[str] = None
    default_city: Optional[str] = None
    scope: str = "country"  # city | region | country | multi | global

    @classmethod
    def from_env(cls) -> "GeographicScope":
        allowed = [
            c.strip().upper()
            for c in os.getenv("SEARCH_ALLOWED_COUNTRIES", "PY,BR,AR,UY").split(",")
            if c.strip()
        ]
        # SEARCH_SCOPE es el nuevo; LEADHUNTER_SCOPE (bbox|country) queda como compat
        scope = (
            os.getenv("SEARCH_SCOPE")
            or os.getenv("LEADHUNTER_SCOPE")
            or "country"
        ).strip().lower()
        if scope == "bbox":
            scope = "region"  # bbox = región con bbox por defecto (compat)
        if scope not in VALID_SCOPES:
            scope = "country"
        return cls(
            default_country=(os.getenv("SEARCH_DEFAULT_COUNTRY", "PY").strip().upper() or "PY"),
            allowed_countries=allowed or ["PY"],
            default_region=os.getenv("SEARCH_DEFAULT_REGION") or None,
            default_city=os.getenv("SEARCH_DEFAULT_CITY") or None,
            scope=scope,
        )

    def effective(
        self,
        country: Optional[str] = None,
        region: Optional[str] = None,
        city: Optional[str] = None,
        allow_global: bool = False,
    ) -> "GeographicScope":
        """Aplica defaults y valida: el usuario NO puede consultar el mundo por accidente (§9).

        - country default = default_country
        - scope=global solo si allow_global=True
        - país fuera de allowed_countries → error (salvo global explícito)
        """
        eff_country = (country or self.default_country or "PY").strip().upper()
        eff_region = region or self.default_region
        eff_city = city or self.default_city
        eff_scope = self.scope

        if eff_city and eff_scope == "country":
            eff_scope = "city"
        elif eff_region and eff_scope == "country":
            eff_scope = "region"

        if eff_scope == "global":
            if not allow_global:
                raise GeoScopeError(
                    "Scope 'global' requiere confirmación explícita (allow_global=true). "
                    "El default es el país configurado."
                )
        elif eff_country not in self.allowed_countries:
            raise GeoScopeError(
                f"País '{eff_country}' no está en SEARCH_ALLOWED_COUNTRIES "
                f"({', '.join(self.allowed_countries)}). "
                "Usá un país permitido o configurá el allowlist en Settings."
            )

        return GeographicScope(
            default_country=eff_country,
            allowed_countries=self.allowed_countries,
            default_region=eff_region,
            default_city=eff_city,
            scope=eff_scope,
        )

    def to_dict(self) -> dict:
        return {
            "default_country": self.default_country,
            "allowed_countries": self.allowed_countries,
            "default_region": self.default_region,
            "default_city": self.default_city,
            "scope": self.scope,
        }

    # ---------- helpers para fuentes ----------

    def area_id(self) -> Optional[int]:
        """Relation id de Overpass para el país efectivo (si se conoce)."""
        return COUNTRY_AREAS.get(self.default_country)

    def place_query(self) -> str:
        """Texto para geocodificar la región/ciudad efectiva (ej: 'Ciudad del Este, Alto Paraná, Paraguay')."""
        parts = []
        if self.default_city:
            parts.append(self.default_city)
        if self.default_region:
            parts.append(self.default_region)
        if self.scope in ("country", "region", "city") and self.default_country:
            parts.append(COUNTRY_NAMES.get(self.default_country, self.default_country))
        return ", ".join(parts)


class GeoProvider(ABC):
    """Contrato de provider geográfico (spec §10). Los adapters deben respetar
    rate limits, caching, attribution y políticas de uso del proveedor."""

    name: str = "base"

    @abstractmethod
    def geocode(self, query: str, country: Optional[str] = None, limit: int = 1) -> List[dict]:
        """Geocodifica un texto (ciudad/región/país) → lista de lugares con lat/lon/bbox."""

    def bounding_box_for(self, scope: GeographicScope) -> Optional[Tuple[float, float, float, float]]:
        """Bounding box (sur, oeste, norte, este) del scope efectivo, o None si no se puede resolver."""
        q = scope.place_query()
        if not q:
            return None
        results = self.geocode(q, country=scope.default_country, limit=1)
        if not results:
            return None
        bb = results[0].get("boundingbox")
        if not bb or len(bb) < 4:
            return None
        try:
            return (float(bb[0]), float(bb[2]), float(bb[1]), float(bb[3]))
        except (TypeError, ValueError):
            return None


class OpenStreetMapProvider(GeoProvider):
    """Adapter Nominatim/OSM. Sin API key; respeta uso razonable (1 req/s) + cache TTL."""

    name = "osm"
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    MIN_INTERVAL = 1.0  # segundos entre requests (política de uso de Nominatim)

    def __init__(self):
        self._cache: Dict[tuple, tuple] = {}  # (query, country) -> (ts, results)
        self._last_request = 0.0

    def _throttle(self) -> None:
        now = time.monotonic()
        wait = self.MIN_INTERVAL - (now - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

    def geocode(self, query: str, country: Optional[str] = None, limit: int = 1) -> List[dict]:
        if not query or not query.strip():
            return []
        key = (query.strip().lower(), (country or "").upper(), limit)
        hit = self._cache.get(key)
        if hit and (time.time() - hit[0]) < GEO_CACHE_TTL:
            return hit[1]

        self._throttle()
        params = {
            "q": query.strip(),
            "format": "json",
            "limit": limit,
            "addressdetails": 1,
        }
        if country:
            params["countrycodes"] = country.lower()
        try:
            resp = httpx.get(
                self.NOMINATIM_URL,
                params=params,
                timeout=15,
                headers={"User-Agent": "ConcienciaPlatform-LeadHunter/2.1 (contact: juanesscobar)"},
            )
            resp.raise_for_status()
            results = resp.json()
            self._cache[key] = (time.time(), results)
            return results
        except (httpx.HTTPError, ValueError):
            return []


_PROVIDERS: Dict[str, GeoProvider] = {}


def get_geo_provider(name: Optional[str] = None) -> GeoProvider:
    """Factory: devuelve el provider configurado (SEARCH_GEO_PROVIDER, default osm)."""
    name = (name or os.getenv("SEARCH_GEO_PROVIDER", "osm")).strip().lower()
    if name not in _PROVIDERS:
        if name == "osm":
            _PROVIDERS[name] = OpenStreetMapProvider()
        else:
            raise GeoScopeError(f"GeoProvider desconocido: {name}. Disponibles: osm")
    return _PROVIDERS[name]


def build_geo_context(
    country: Optional[str] = None,
    region: Optional[str] = None,
    city: Optional[str] = None,
    allow_global: bool = False,
    scope: Optional[GeographicScope] = None,
) -> dict:
    """Construye el contexto geográfico efectivo para una corrida de fuentes.

    Devuelve un dict con: scope (GeographicScope), country, region, city,
    bbox (tuple sur,oeste,norte,este | None), area_id (int | None), is_global (bool).
    """
    base = scope or GeographicScope.from_env()
    eff = base.effective(country=country, region=region, city=city, allow_global=allow_global)
    provider = get_geo_provider()

    ctx: dict = {
        "scope": eff,
        "country": eff.default_country,
        "region": eff.default_region,
        "city": eff.default_city,
        "bbox": None,
        "area_id": None,
        "is_global": eff.scope == "global",
    }

    if ctx["is_global"]:
        return ctx

    ctx["area_id"] = eff.area_id()
    if eff.scope in ("region", "city") and (eff.default_region or eff.default_city):
        ctx["bbox"] = provider.bounding_box_for(eff)
    if ctx["bbox"] is None and eff.scope == "region":
        # Fallback compat: bbox configurado (Gran Asunción por defecto)
        raw = os.getenv("LEADHUNTER_BBOX", "-25.55,-57.75,-25.15,-57.40")
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) == 4:
            try:
                ctx["bbox"] = tuple(float(p) for p in parts)  # type: ignore[assignment]
            except ValueError:
                ctx["bbox"] = None
    return ctx
