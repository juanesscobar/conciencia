"""Interfaces del core (spec §10/§11/§14) — protocolos para abstracciones.

Documentan los contracts que los adapters deben cumplir (ya implementados en
`leadhunter/geo.py` (GeoProvider), `leadhunter/embeddings.py` (VectorBackend)
y `leadhunter/sources/` (LeadSource)). Permitirán agregar providers sin tocar
el search engine (GoogleMaps, Qdrant, registry CSV, ...).
"""

from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable


@runtime_checkable
class GeoProvider(Protocol):
    """Abstracción del proveedor geográfico (spec §10).

    Implementación actual: OpenStreetMapProvider (leadhunter/geo.py).
    Futuros: GoogleMapsProvider, MapboxProvider, HereProvider.
    """
    name: str

    def search_places(self, query: str, **kwargs) -> List[Dict[str, Any]]: ...
    def geocode(self, place: str) -> Optional[Dict[str, Any]]: ...
    def reverse_geocode(self, lat: float, lon: float) -> Dict[str, Any]: ...
    def resolve_region(self, name: str) -> Optional[Dict[str, Any]]: ...
    def resolve_country(self, code: str) -> Optional[Dict[str, Any]]: ...
    def resolve_city(self, name: str) -> Optional[Dict[str, Any]]: ...


@runtime_checkable
class VectorBackend(Protocol):
    """Backend vectorial abstracto (spec §14).

    Implementaciones: InMemoryBackend (numpy, dev) y PgVectorBackend (pgvector).
    Futuros: Qdrant, Weaviate, Milvus.
    """
    name: str

    def upsert(self, lead_id: str, text: str, vector: List[float], meta: Optional[dict] = None) -> None: ...
    def search(self, vector: List[float], top_k: int = 20) -> List[Tuple[str, float]]: ...
    def delete(self, lead_id: str) -> None: ...
    def count(self) -> int: ...
    def clear(self) -> None: ...


@runtime_checkable
class LeadSource(Protocol):
    """Fuente de datos de leads (spec §11: DataSource con provenance).

    Implementaciones: OverpassSource (leadhunter/sources/overpass.py).
    Futuras: Google Maps, registros públicos, CSV import, APIs.
    """
    name: str
    label: str
    description: str
    enabled: bool

    def fetch(self, limit: Optional[int] = None, geo: Optional[dict] = None) -> List[Dict[str, Any]]: ...
