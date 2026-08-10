"""Base para fuentes de prospección de leads."""

from typing import Dict, List, Optional, Type


class BaseLeadSource:
    """Contrato mínimo de una fuente: fetch() -> lista de dicts normalizados."""

    name: str = "base"
    label: str = "Base"
    description: str = ""
    enabled: bool = True

    def fetch(self, limit: Optional[int] = None) -> List[dict]:
        raise NotImplementedError


SOURCES: Dict[str, Type[BaseLeadSource]] = {}


def register_source(cls: Type[BaseLeadSource]) -> Type[BaseLeadSource]:
    SOURCES[cls.name] = cls
    return cls


def get_source(name: str) -> Optional[BaseLeadSource]:
    cls = SOURCES.get(name)
    return cls() if cls else None


def get_all_sources() -> Dict[str, BaseLeadSource]:
    return {name: cls() for name, cls in SOURCES.items() if cls().enabled}


def run_all_sources(limit: Optional[int] = None) -> Dict[str, List[dict]]:
    return {name: src.fetch(limit=limit) for name, src in get_all_sources().items()}
