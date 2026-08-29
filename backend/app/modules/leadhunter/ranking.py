"""Fase 4 — Ranking + Scoring separados + Data Quality (spec §15/§16/§34/§35).

Separación conceptual (spec §16):
- **SearchRelevance**: dependiente de la query (category/geo/keyword match).
- **LeadScore**: independiente de la query (completitud + industria + fuente + metadata).
- **OpportunityScore**: señales comerciales (website + email + tel + contacto + actividad + calidad).
- **DataQualityScore**: completitud + frescura + confiabilidad de fuente + consistencia (0-100).
- **RankingWeights**: configurables desde Settings (`RANKING_WEIGHTS`, JSON) con defaults en código.
- **explain()**: razones legibles para "Why this lead matches" (spec §34).

Todo es aditivo: `compute_score` (service.py) conserva su contrato exacto; estos
cálculos se exponen como campos nuevos en las respuestas.
"""

import json
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from .models import Lead

# ---------------------------------------------------------------------------
# Pesos por defecto (0-1 por bloque; cada bloque se normaliza a su share de 100)
# ---------------------------------------------------------------------------
DEFAULT_RANKING_WEIGHTS: Dict[str, Dict[str, float]] = {
    "relevance": {
        "category_match": 0.35,
        "geo_match": 0.30,
        "keyword_match": 0.35,
    },
    "lead": {
        "completeness": 0.30,
        "industry": 0.25,
        "source": 0.15,
        "metadata": 0.20,
        "freshness": 0.10,
    },
    "opportunity": {
        "website": 25,
        "email": 20,
        "phone": 20,
        "contact": 10,
        "activity": 15,
        "quality": 10,
    },
}

SETTING_KEY = "RANKING_WEIGHTS"

# Confiabilidad de fuente 0-1 (spec §35: source reliability)
SOURCE_RELIABILITY = {
    "conciencia": 1.0,
    "referral": 1.0,
    "linkedin": 0.8,
    "web": 0.7,
    "overpass": 0.6,
    "manual": 0.5,
}

STOPWORDS = {
    "de", "la", "el", "en", "y", "a", "los", "las", "del", "con", "que",
    "por", "para", "un", "una", "su", "sus", "al", "como", "más", "mas",
    "empresas", "empresa", "negocio", "negocios", "buscar", "busca",
    "necesito", "quiero", "hay", "tengan", "tiene", "son", "ser",
}


def _norm(s: Optional[str]) -> str:
    """Minúsculas, sin acentos, espacios colapsados."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", s).strip()


def _tokens(s: Optional[str]) -> List[str]:
    """Tokens útiles (sin stopwords ni puntuación)."""
    words = re.findall(r"[a-z0-9áéíóúñü]+", _norm(s))
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


# ---------------------------------------------------------------------------
# Carga de pesos desde Settings (RANKING_WEIGHTS JSON) con merge de defaults
# ---------------------------------------------------------------------------
def _merge_weights(base: Dict[str, Dict[str, float]], override: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    merged = {k: dict(v) for k, v in base.items()}
    for block, values in (override or {}).items():
        if block in merged and isinstance(values, dict):
            for k, v in values.items():
                if k in merged[block] and isinstance(v, (int, float)):
                    merged[block][k] = float(v)
    return merged


def get_ranking_weights(db: Optional[Session] = None) -> Dict[str, Dict[str, float]]:
    """Lee RANKING_WEIGHTS de la tabla Setting; si no existe, devuelve defaults."""
    if db is None:
        return _merge_weights(DEFAULT_RANKING_WEIGHTS, {})
    try:
        from app.models.setting import Setting
        row = db.query(Setting).filter(Setting.key == SETTING_KEY).first()
        if row and row.value:
            raw = json.loads(row.value)
            return _merge_weights(DEFAULT_RANKING_WEIGHTS, raw)
    except Exception:
        pass
    return _merge_weights(DEFAULT_RANKING_WEIGHTS, {})


def set_ranking_weights(db: Session, weights: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    """Persiste RANKING_WEIGHTS validado (merge con defaults para no perder bloques)."""
    merged = _merge_weights(DEFAULT_RANKING_WEIGHTS, weights)
    from app.models.setting import Setting
    row = db.query(Setting).filter(Setting.key == SETTING_KEY).first()
    payload = json.dumps(merged, ensure_ascii=False)
    if row:
        row.value = payload
    else:
        db.add(Setting(key=SETTING_KEY, value=payload))
    db.commit()
    return merged


# ---------------------------------------------------------------------------
# Data Quality Score (spec §35) — 0-100
# ---------------------------------------------------------------------------
def source_reliability(source: Optional[str]) -> float:
    return SOURCE_RELIABILITY.get((source or "").lower(), 0.4)


def freshness_score(created_at: Optional[datetime], updated_at: Optional[datetime] = None,
                    now: Optional[datetime] = None) -> float:
    """Frescura 0-1: 90 días = fresco; decae hasta ~730 días."""
    now = now or datetime.utcnow()
    ref = updated_at or created_at
    if not ref:
        return 0.3
    try:
        days = (now - ref).days
    except TypeError:
        return 0.3
    if days < 0:
        return 1.0
    if days <= 90:
        return 1.0 - (days / 90) * 0.25
    if days <= 730:
        return 0.75 * (1 - (days - 90) / 640)
    return 0.05


def data_quality_score(lead: Lead) -> int:
    """0-100: completitud (70) + frescura (15) + confiabilidad de fuente (15)."""
    completeness = 0
    if lead.email:
        completeness += 15
    if lead.phone:
        completeness += 12
    if lead.website:
        completeness += 12
    if lead.contact_name:
        completeness += 8
    if lead.region:
        completeness += 8
    if lead.industry:
        completeness += 8
    if lead.segment:
        completeness += 7
    completeness = min(70, completeness)

    fresh = freshness_score(lead.created_at, lead.updated_at) * 15
    rel = source_reliability(lead.source) * 15
    return max(0, min(100, round(completeness + fresh + rel)))


# ---------------------------------------------------------------------------
# Lead Score (independiente de la query) — reusa los bloques de service.compute_score
# ---------------------------------------------------------------------------
def _blocks(company: str = "", industry: str = "", source: str = "manual",
            email: str = "", phone: str = "", notes: str = "",
            metadata: Optional[dict] = None) -> Dict[str, float]:
    """Bloques base del scoring (mismos valores que compute_score histórico).

    - completeness: email 20 + phone 15 + company 10 → máx 45
    - industry: primera keyword de HIGH_VALUE_INDUSTRY → máx 25
    - source: SOURCE_BONUS → máx 20
    - metadata: ≥3 respuestas → máx 10
    """
    from .service import HIGH_VALUE_INDUSTRY, SOURCE_BONUS

    completeness = 0.0
    if email:
        completeness += 20
    if phone:
        completeness += 15
    if company:
        completeness += 10

    haystack = f"{company} {industry} {notes or ''}".lower()
    industry_pts = 0.0
    for keyword, points in HIGH_VALUE_INDUSTRY.items():
        if keyword in haystack:
            industry_pts = float(points)
            break

    source_pts = float(SOURCE_BONUS.get(source, 0))

    meta_pts = 0.0
    if metadata and isinstance(metadata, dict):
        n_answers = sum(1 for v in metadata.values() if v)
        if n_answers >= 3:
            meta_pts = 10.0

    return {
        "completeness": completeness,
        "industry": industry_pts,
        "source": source_pts,
        "metadata": meta_pts,
    }


def lead_score(lead: Lead, weights: Optional[Dict[str, Dict[str, float]]] = None) -> int:
    """Lead Score 0-100 ponderado por RANKING_WEIGHTS.lead.

    Cada bloque se normaliza a su máximo (45/25/20/10) y se pondera sobre 100;
    la frescura (0-10) entra como bloque adicional.
    """
    w = (weights or DEFAULT_RANKING_WEIGHTS)["lead"]
    b = _blocks(
        company=lead.company or "",
        industry=lead.industry or "",
        source=lead.source or "manual",
        email=lead.email or "",
        phone=lead.phone or "",
        notes=lead.notes or "",
        metadata=lead.meta,
    )
    fresh = freshness_score(lead.created_at, lead.updated_at) * 10

    scaled = (
        (b["completeness"] / 45.0) * w.get("completeness", 0.3) * 100
        + (b["industry"] / 25.0) * w.get("industry", 0.25) * 100
        + (b["source"] / 20.0) * w.get("source", 0.15) * 100
        + (b["metadata"] / 10.0) * w.get("metadata", 0.20) * 100
        + (fresh / 10.0) * w.get("freshness", 0.10) * 100
    )
    return max(0, min(100, round(scaled)))


# ---------------------------------------------------------------------------
# Opportunity Score (spec §16) — 0-100, señales comerciales
# ---------------------------------------------------------------------------
def opportunity_score(lead: Lead, weights: Optional[Dict[str, Dict[str, float]]] = None) -> int:
    w = (weights or DEFAULT_RANKING_WEIGHTS)["opportunity"]
    score = 0.0
    if lead.website:
        score += w.get("website", 25)
    if lead.email:
        score += w.get("email", 20)
    if lead.phone:
        score += w.get("phone", 20)
    if lead.contact_name:
        score += w.get("contact", 10)
    activity = freshness_score(lead.created_at, lead.updated_at)
    score += w.get("activity", 15) * activity
    score += w.get("quality", 10) * (data_quality_score(lead) / 100.0)
    return max(0, min(100, round(score)))


# ---------------------------------------------------------------------------
# Search Relevance (spec §15) — dependiente de la query, 0-100
# ---------------------------------------------------------------------------
def search_relevance(lead: Lead, sq: Any, weights: Optional[Dict[str, Dict[str, float]]] = None) -> int:
    """Qué tan bien matchea el lead con la query canónica (SearchQuery)."""
    w = (weights or DEFAULT_RANKING_WEIGHTS)["relevance"]
    parts: Dict[str, float] = {"category_match": 0.0, "geo_match": 0.0, "keyword_match": 0.0}

    # --- category / industry ---
    cat = getattr(sq, "category", None) or getattr(sq, "industry", None)
    if cat:
        ncat = _norm(cat)
        nind = _norm(lead.industry)
        if nind == ncat:
            parts["category_match"] = 1.0
        elif ncat and ncat in nind or nind and nind in ncat:
            parts["category_match"] = 0.7
        elif any(t in nind for t in _tokens(cat)):
            parts["category_match"] = 0.5

    # --- geografía ---
    geo = getattr(sq, "region", None) or getattr(sq, "city", None)
    if geo and lead.region:
        ngeo = _norm(geo)
        nreg = _norm(lead.region)
        if ngeo == nreg or ngeo in nreg or nreg in ngeo:
            parts["geo_match"] = 1.0
        elif any(ngeo in _norm(part) for part in str(lead.region).split(",")):
            parts["geo_match"] = 1.0

    # --- keyword match sobre el texto de la query ---
    qtext = getattr(sq, "query", None)
    if qtext:
        qtoks = _tokens(qtext)
        hay = " ".join(_tokens(f"{lead.company} {lead.industry or ''} {lead.notes or ''} {lead.region or ''}"))
        if qtoks:
            hits = sum(1 for t in qtoks if t in hay)
            parts["keyword_match"] = hits / len(qtoks)

    total = sum(parts[k] * w.get(k, 0) for k in parts)
    return max(0, min(100, round(total * 100)))


# ---------------------------------------------------------------------------
# Why this lead matches (spec §34)
# ---------------------------------------------------------------------------
def explain(lead: Lead, sq: Any = None, weights: Optional[Dict[str, Dict[str, float]]] = None) -> List[str]:
    """Razones legibles de por qué un lead aparece/matchea."""
    reasons: List[str] = []
    w = weights or get_ranking_weights(None)

    if sq is not None:
        cat = getattr(sq, "category", None) or getattr(sq, "industry", None)
        if cat and _norm(cat) and (_norm(cat) in _norm(lead.industry or "") or _norm(lead.industry or "") in _norm(cat)):
            reasons.append(f"Categoría: {lead.industry or 'sin categoría'} (match con '{cat}')")
        geo = getattr(sq, "region", None) or getattr(sq, "city", None)
        if geo and lead.region and _norm(geo) in _norm(lead.region):
            reasons.append(f"Ubicación: {lead.region} (match con '{geo}')")
        qtext = getattr(sq, "query", None)
        if qtext:
            hits = [t for t in _tokens(qtext) if t in _tokens(f"{lead.company} {lead.industry or ''} {lead.notes or ''}")]
            if hits:
                reasons.append(f"Menciona: {', '.join(hits[:4])}")

    if lead.website:
        reasons.append("Tiene website")
    if lead.email:
        reasons.append("Tiene email")
    if lead.phone:
        reasons.append("Tiene teléfono")
    if lead.contact_name:
        reasons.append(f"Contacto identificado: {lead.contact_name}")

    dq = data_quality_score(lead)
    opp = opportunity_score(lead, w)
    ls = lead_score(lead, w)
    reasons.append(f"Lead score {ls}/100 · Oportunidad {opp}/100 · Calidad de datos {dq}/100")
    return reasons


# ---------------------------------------------------------------------------
# Helper para enriquecer respuestas (router + search engine)
# ---------------------------------------------------------------------------
def enrich_lead_dict(lead: Lead, db: Optional[Session] = None, sq: Any = None) -> Dict[str, Any]:
    """Añade los campos de Fase 4 al dict del lead (aditivo, no rompe to_dict)."""
    d = lead.to_dict()
    weights = get_ranking_weights(db)
    d["data_quality"] = data_quality_score(lead)
    d["opportunity_score"] = opportunity_score(lead, weights)
    d["search_relevance"] = search_relevance(lead, sq, weights) if sq is not None else None
    d["reasons"] = explain(lead, sq, weights)
    return d
