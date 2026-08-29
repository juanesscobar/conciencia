"""Fase 5 — Búsqueda semántica foundation (spec P6/§14).

Arquitectura lista para embeddings SIN introducir vector DB externa (scope §47):
- `VectorBackend` abstracto: upsert / search / delete.
- `InMemoryBackend`: cosine en numpy (SQLite dev, cero infra).
- `PgVectorBackend`: pgvector (solo si Postgres + extensión disponible; si no, fallback a memory).
- `embed_text()`: OpenAI (u otro provider compatible) si hay API key; si no, embedding
  SIMULADO determinístico (bag de n-grams hasheados, dim 384) → modo demo/test nunca rompe.

Endpoints (aditivos):
- POST /api/v1/leads/search/semantic → 501 si EMBEDDING_ENABLED no está activo.
- GET  /api/v1/leads/search/semantic/status → estado del backend + cantidad indexada.

Los documentos se guardan como JSONB en `leads.meta["semantic"]` (provenance:
text, model, dim, indexed_at) — sin migración de tabla en dev.
"""

import hashlib
import json
import os
import re
import threading
import unicodedata
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy.orm import Session

from .models import Lead

SIM_DIM = 384
DEFAULT_MODEL = "text-embedding-3-small"

_lock = threading.Lock()
_backend_cache: Dict[str, "VectorBackend"] = {}


def _db_setting(key: str) -> str:
    """Lee un setting persistente de la DB (tabla settings) con overlay de env."""
    try:
        from app.database import SessionLocal
        from app.models.setting import Setting
        db = SessionLocal()
        try:
            setting = db.query(Setting).filter(Setting.key == key).first()
            return setting.value if setting and setting.value else ""
        finally:
            db.close()
    except Exception:
        return ""


def _setting(key: str, default: str = "") -> str:
    return os.getenv(key) or _db_setting(key) or default


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def embeddings_enabled() -> bool:
    return _setting("EMBEDDING_ENABLED", "0").strip().lower() in ("1", "true", "yes", "on")


def embedding_model() -> str:
    return _setting("EMBEDDING_MODEL", DEFAULT_MODEL)


def embedding_provider() -> str:
    return _setting("EMBEDDING_PROVIDER", "openai").strip().lower()


def embedding_backend_name() -> str:
    return _setting("EMBEDDING_BACKEND", "memory").strip().lower()


def _api_key(provider: str) -> str:
    env_key = {
        "openai": "OPENAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "ollama": "",
    }.get(provider, f"{provider.upper()}_API_KEY")
    return os.getenv(env_key) or _db_setting(env_key) or ""


# ---------------------------------------------------------------------------
# Embedding: real (OpenAI-compatible) o simulado determinístico
# ---------------------------------------------------------------------------
def _norms(s: Optional[str]) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", s).strip()


def simulated_embedding(text: str, dim: int = SIM_DIM) -> List[float]:
    """Embedding determinístico: bag de n-grams (2-4) hasheados a `dim` floats.

    Textos parecidos comparten n-grams → vectores con cosine alto. Suficiente
    para modo demo/tests y para que el flujo E2E funcione sin API key.
    """
    vec = np.zeros(dim, dtype=np.float64)
    t = _norms(text)
    for n in (2, 3, 4):
        for i in range(len(t) - n + 1):
            gram = t[i:i + n]
            h = int(hashlib.md5(gram.encode("utf-8")).hexdigest()[:8], 16)
            idx = h % dim
            sign = 1.0 if (h >> 8) & 1 else -1.0
            vec[idx] += sign
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


def embed_text(text: str) -> List[float]:
    """Embedding real (OpenAI-compatible) si hay key; si no, simulado."""
    provider = embedding_provider()
    key = _api_key(provider)
    base_url = _setting("EMBEDDING_BASE_URL", "")
    model = embedding_model()

    if key and provider != "ollama":
        try:
            from openai import OpenAI
            kwargs: Dict[str, Any] = {"api_key": key}
            if base_url:
                kwargs["base_url"] = base_url
            client = OpenAI(**kwargs)
            res = client.embeddings.create(model=model, input=[text])
            return res.data[0].embedding
        except Exception:
            pass  # fallback silencioso a simulado
    return simulated_embedding(text)


# ---------------------------------------------------------------------------
# Backends vectoriales
# ---------------------------------------------------------------------------
class VectorBackend(ABC):
    name: str = "base"

    @abstractmethod
    def upsert(self, lead_id: str, text: str, vector: List[float], meta: Optional[dict] = None) -> None: ...

    @abstractmethod
    def search(self, vector: List[float], top_k: int = 20) -> List[Tuple[str, float]]: ...

    @abstractmethod
    def delete(self, lead_id: str) -> None: ...

    @abstractmethod
    def count(self) -> int: ...

    @abstractmethod
    def clear(self) -> None: ...


class InMemoryBackend(VectorBackend):
    """Cosine en numpy — SQLite dev / modo simulado (cero infraestructura)."""

    name = "memory"

    def __init__(self) -> None:
        self._docs: Dict[str, Tuple[str, np.ndarray, Optional[dict]]] = {}

    def upsert(self, lead_id: str, text: str, vector: List[float], meta: Optional[dict] = None) -> None:
        arr = np.asarray(vector, dtype=np.float64)
        n = np.linalg.norm(arr)
        self._docs[lead_id] = (text, arr / n if n > 0 else arr, meta)

    def search(self, vector: List[float], top_k: int = 20) -> List[Tuple[str, float]]:
        q = np.asarray(vector, dtype=np.float64)
        nq = np.linalg.norm(q)
        if nq > 0:
            q = q / nq
        scored: List[Tuple[str, float]] = []
        for lid, (_, arr, _) in self._docs.items():
            if arr.size == 0:
                continue
            scored.append((lid, float(np.dot(q, arr))))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def delete(self, lead_id: str) -> None:
        self._docs.pop(lead_id, None)

    def count(self) -> int:
        return len(self._docs)

    def clear(self) -> None:
        self._docs.clear()


class PgVectorBackend(VectorBackend):
    """pgvector (Postgres). Se activa solo si la extensión está disponible.

    DDL autocontenido (CREATE EXTENSION + tabla) — sin migración alembic; si
    algo falla (SQLite, sin privilegio), se cae a InMemoryBackend.
    """

    name = "pgvector"

    def __init__(self) -> None:
        self._ready = False
        self._conn = None

    def _ensure(self) -> bool:
        if self._ready:
            return True
        try:
            from sqlalchemy import create_engine, text
            url = os.getenv("DATABASE_URL", "")
            if not url or url.startswith("sqlite"):
                return False
            engine = create_engine(url)
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.execute(text(
                    "CREATE TABLE IF NOT EXISTS business_documents ("
                    "  lead_id TEXT PRIMARY KEY,"
                    "  content TEXT NOT NULL,"
                    "  embedding vector(%d) NOT NULL,"
                    "  meta JSONB"
                    ")" % SIM_DIM
                ))
                conn.commit()
            self._conn = engine.connect()
            self._ready = True
            return True
        except Exception:
            return False

    def upsert(self, lead_id: str, text: str, vector: List[float], meta: Optional[dict] = None) -> None:
        if not self._ensure():
            return
        from sqlalchemy import text
        self._conn.execute(text(
            "INSERT INTO business_documents (lead_id, content, embedding, meta) "
            "VALUES (:id, :content, :vec::vector, :meta::jsonb) "
            "ON CONFLICT (lead_id) DO UPDATE SET content=EXCLUDED.content, embedding=EXCLUDED.embedding, meta=EXCLUDED.meta"
        ), {"id": lead_id, "content": text, "vec": json.dumps(vector), "meta": json.dumps(meta or {})})
        self._conn.commit()

    def search(self, vector: List[float], top_k: int = 20) -> List[Tuple[str, float]]:
        if not self._ensure():
            return []
        from sqlalchemy import text
        rows = self._conn.execute(text(
            "SELECT lead_id, 1 - (embedding <=> :vec::vector) AS sim "
            "FROM business_documents ORDER BY embedding <=> :vec::vector LIMIT :k"
        ), {"vec": json.dumps(vector), "k": top_k}).fetchall()
        return [(r[0], float(r[1])) for r in rows]

    def delete(self, lead_id: str) -> None:
        if not self._ensure():
            return
        from sqlalchemy import text
        self._conn.execute(text("DELETE FROM business_documents WHERE lead_id = :id"), {"id": lead_id})
        self._conn.commit()

    def count(self) -> int:
        if not self._ensure():
            return 0
        from sqlalchemy import text
        return int(self._conn.execute(text("SELECT count(*) FROM business_documents")).scalar())

    def clear(self) -> None:
        if not self._ensure():
            return
        from sqlalchemy import text
        self._conn.execute(text("DELETE FROM business_documents"))
        self._conn.commit()


def get_backend() -> VectorBackend:
    """Singleton por nombre de backend (memory | pgvector)."""
    name = embedding_backend_name()
    with _lock:
        if name not in _backend_cache:
            if name == "pgvector":
                backend = PgVectorBackend()
                if not backend._ensure():
                    backend = InMemoryBackend()
            else:
                backend = InMemoryBackend()
            _backend_cache[name] = backend
        return _backend_cache[name]


def reset_backend() -> None:
    """Para tests: limpia el cache de singletons."""
    with _lock:
        _backend_cache.clear()


# ---------------------------------------------------------------------------
# Indexación + búsqueda
# ---------------------------------------------------------------------------
def document_text(lead: Lead) -> str:
    """Texto canónico del BusinessDocument (spec §14): empresa + sector + descripción + ubicación."""
    meta = lead.meta if isinstance(lead.meta, dict) else {}
    parts = [
        lead.company or "",
        lead.industry or "",
        lead.segment or "",
        lead.region or "",
        lead.notes or "",
        meta.get("description") or "",
    ]
    return " ".join(p for p in parts if p).strip()


def index_lead(db: Session, lead: Lead) -> None:
    """Indexa (o reindexa) un lead en el backend activo + provenance en meta."""
    text = document_text(lead)
    if not text:
        return
    vector = embed_text(text)
    backend = get_backend()
    backend.upsert(lead.id, text, vector, {"model": embedding_model()})

    meta = dict(lead.meta) if isinstance(lead.meta, dict) else {}
    meta["semantic"] = {
        "text": text[:500],
        "model": embedding_model(),
        "dim": len(vector),
        "indexed_at": datetime.utcnow().isoformat(),
    }
    lead.meta = meta


def reindex_all(db: Session, limit: int = 10000) -> int:
    """Indexa los leads que falten (lazy). Devuelve cuántos indexó."""
    indexed = 0
    for lead in db.query(Lead).limit(limit).all():
        meta = lead.meta if isinstance(lead.meta, dict) else {}
        if meta.get("semantic"):
            continue
        index_lead(db, lead)
        indexed += 1
    if indexed:
        db.commit()
    return indexed


def reindex_if_needed(db: Session) -> int:
    """Reindexa solo si hay leads sin indexar (comparación O(1) con el contador)."""
    try:
        total = db.query(Lead).count()
    except Exception:
        return 0
    if get_backend().count() >= total:
        return 0
    return reindex_all(db)


def semantic_search(db: Session, query: str, top_k: int = 20) -> List[Tuple[Lead, float]]:
    """Embed query → busca en backend → devuelve (lead, sim) filtrando huérfanos."""
    qvec = embed_text(query)
    backend = get_backend()
    hits = backend.search(qvec, top_k=top_k * 3)
    if not hits:
        return []

    ids = [lid for lid, _ in hits]
    leads = {l.id: l for l in db.query(Lead).filter(Lead.id.in_(ids)).all()}
    out: List[Tuple[Lead, float]] = []
    for lid, sim in hits:
        lead = leads.get(lid)
        if lead is not None:
            out.append((lead, sim))
        else:
            backend.delete(lid)  # limpieza de huérfanos
        if len(out) >= top_k:
            break
    return out
