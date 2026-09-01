"""Context Retrieval — contexto relevante y acotado para agentes (master prompt §J).

DoD Phase J: "Agents receive relevant context without loading unnecessary
project data."

Estrategia (sin LLM, costo cero):
  1. retrieve_packs: ranking de ContextPacks por relevancia a un query
     (score = título 3x + claves del contenido 2x + valores 1x, con match de
     términos normalizados). Filtro opcional por proyecto.
  2. assemble_context: arma el contexto final desde los top-K packs, acotado
     a max_chars (truncado por pack, no carga datos que no entran).
  3. context_for_mission: si la misión tiene context_pack_id explícito lo usa;
     si no, recupera los top-2 por el objetivo de la misión (retrieval
     eficiente — nunca el proyecto entero).
"""

import json
import re
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.context_pack import ContextPack

# términos de ruido que no aportan al scoring
_STOPWORDS = {
    "de", "la", "el", "los", "las", "del", "para", "con", "por", "una", "un",
    "que", "y", "en", "a", "the", "of", "and", "to", "or", "an", "is", "are",
    "context", "pack", "proyecto", "project", "conciencia",
}


def _normalize(text: str) -> List[str]:
    """Términos normalizados (lowercase, sin acentos ni puntuación)."""
    text = (text or "").lower()
    text = text.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return [t for t in text.split() if t and t not in _STOPWORDS]


def _flatten(content: dict) -> str:
    """Aplana el contenido canónico a texto plano para scoring/render."""
    parts: List[str] = []
    for k, v in content.items():
        if isinstance(v, (dict, list)):
            parts.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
        else:
            parts.append(f"{k}: {v}")
    return "\n".join(parts)


def render_context_pack(pack: ContextPack, max_chars: int = 8000) -> str:
    """Renderiza un pack como texto plano para el prompt del agente."""
    content = getattr(pack, "content", None) or {}
    parts: List[str] = []
    if isinstance(content, dict):
        for k, v in content.items():
            if isinstance(v, (dict, list)):
                rendered = json.dumps(v, ensure_ascii=False)
            else:
                rendered = str(v)
            parts.append(f"{k}: {rendered}")
        text = "\n".join(parts)
    else:
        text = str(content)
    return text[:max_chars]


def retrieve_packs(
    db: Session,
    *,
    query: str,
    project_id: Optional[str] = None,
    limit: int = 3,
) -> List[dict]:
    """ContextPacks rankeados por relevancia al query.

    Cada resultado: {pack_id, title, target, score, matched_terms, why}.
    """
    terms = _normalize(query)
    if not terms:
        return []

    results: List[dict] = []
    q = db.query(ContextPack)
    if project_id:
        q = q.filter(ContextPack.project_id == project_id)
    for pack in q.all():
        title_terms = _normalize(pack.title)
        flat = _flatten(pack.content or {})
        flat_terms = _normalize(flat)

        score = 0
        matched: List[str] = []
        for t in terms:
            if t in title_terms:
                score += 3
                matched.append(f"{t} (título)")
            if t in flat_terms:
                score += 1
                matched.append(t)
        # claves del contenido pesan 2x
        for key in (pack.content or {}).keys():
            if _normalize(str(key)) and any(t in _normalize(str(key)) for t in terms):
                score += 2
                matched.append(f"{key} (clave)")
        if score == 0:
            continue
        results.append({
            "pack_id": str(pack.id),
            "title": pack.title,
            "target": pack.target,
            "project_id": pack.project_id,
            "score": score,
            "matched_terms": sorted(set(matched)),
            "why": f"{len(set(matched))} término(s) en común con el objetivo",
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]


def assemble_context(
    db: Session,
    *,
    query: str,
    project_id: Optional[str] = None,
    limit: int = 3,
    max_chars: int = 6000,
) -> dict:
    """Ensambla contexto acotado desde los packs más relevantes.

    Devuelve {context, packs, truncated} — solo carga lo que entra en max_chars.
    """
    packs = retrieve_packs(db, query=query, project_id=project_id, limit=limit)
    budget = max_chars
    parts: List[str] = []
    used: List[dict] = []
    truncated = False
    for p in packs:
        pack = db.query(ContextPack).filter(ContextPack.id == p["pack_id"]).first()
        if not pack:
            continue
        header = f"## Context Pack: {pack.title}"
        body = render_context_pack(pack, max_chars=budget - len(header) - 10)
        block = f"{header}\n{body}"
        if len(parts) > 0 and len("\n\n".join(parts + [block])) > max_chars:
            truncated = True
            break
        parts.append(block)
        used.append({"pack_id": p["pack_id"], "title": pack.title, "score": p["score"]})
        budget -= len(block)

    return {
        "context": "\n\n".join(parts),
        "packs": used,
        "truncated": truncated,
        "total_chars": len("\n\n".join(parts)),
    }


def context_for_mission(
    db: Session,
    *,
    objective: str,
    project_id: Optional[str] = None,
    context_pack_id: Optional[str] = None,
    max_chars: int = 6000,
) -> Tuple[str, List[dict]]:
    """Contexto para una misión: pack explícito o retrieval eficiente por objetivo.

    Devuelve (context_string, packs_usados).
    """
    if context_pack_id:
        pack = db.query(ContextPack).filter(ContextPack.id == context_pack_id).first()
        if pack:
            return render_context_pack(pack, max_chars=max_chars), [
                {"pack_id": str(pack.id), "title": pack.title, "score": None, "why": "context_pack_id explícito"}
            ]
    if objective:
        assembled = assemble_context(
            db, query=objective, project_id=project_id, limit=2, max_chars=max_chars
        )
        return assembled["context"], assembled["packs"]
    return "", []
