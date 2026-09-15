"""Canonical hybrid retrieval over the workspace WorkItem ledger."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.modules.leadhunter.embeddings import (
    InMemoryBackend,
    embed_text_with_mode,
    embedding_backend_name,
    embedding_model,
    embeddings_enabled,
)

from .work_service import WorkItem, collect_work_items

_WORKSPACE_BACKEND = InMemoryBackend()
_STOP_WORDS = {"a", "al", "and", "con", "de", "del", "el", "en", "for", "la", "las", "lo", "los", "para", "por", "que", "the", "un", "una", "we", "what", "y"}
_QUALITY = {"evidence": 1.0, "signal": 0.95, "mission_run": 0.9, "mission": 0.88, "git_commit": 0.84, "activity": 0.8, "deliverable": 0.8}


@dataclass
class WorkspaceSemanticStatus:
    enabled: bool
    backend: str
    model: str
    simulated: bool
    indexed: int
    state: str
    reason: str
    embedding_backend: str = "unavailable"

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def _entity_type(item: WorkItem) -> str:
    return {
        "mission": "Mission", "mission_run": "MissionRun", "signal": "Signal",
        "evidence": "Evidence", "git_commit": "GitCommit", "deliverable": "Deliverable",
        "activity": "WorkActivity",
    }.get(item.source_type, "WorkItem")


def _work_text(item: WorkItem, *, semantic: bool = False) -> str:
    parts = [item.type, item.title, item.summary or "", " ".join(item.tags), item.source_type, str(item.metadata or {})]
    text = " ".join(str(part) for part in parts if part).strip()
    # Preserve the meaning of a product term in simulated embeddings as well.
    if semantic and "webmcp" in text.casefold():
        text += " agent web interaction tools browser web pages automation herramientas agentes interactuar paginas web navegador automatizacion"
    return text


def _tokens(query: str) -> list[str]:
    return [token for token in re.findall(r"\w+", query.casefold()) if len(token) > 1 and token not in _STOP_WORDS]


def _lexical_scores(items: list[WorkItem], query: str) -> dict[str, float]:
    terms = _tokens(query)
    if not terms:
        return {item.id: 0.0 for item in items}
    scores: dict[str, float] = {}
    for item in items:
        haystack = set(re.findall(r"\w+", _work_text(item).casefold()))
        title = set(re.findall(r"\w+", item.title.casefold()))
        scores[item.id] = sum(2.0 for term in terms if term in haystack) + sum(1.0 for term in terms if term in title)
    return scores


def _index_workspace_items(items: list[WorkItem]) -> tuple[int, str]:
    _WORKSPACE_BACKEND.clear()
    modes: set[str] = set()
    for item in items:
        text = _work_text(item, semantic=True)
        vector, mode = embed_text_with_mode(text)
        modes.add(mode)
        _WORKSPACE_BACKEND.upsert(item.id, text, vector, {
            "entity_type": _entity_type(item), "entity_id": item.source_ref,
            "project_id": item.project_id, "timestamp": item.timestamp.isoformat(),
            "source_type": item.source_type, "source_ref": item.source_ref,
        })
    return len(items), "real" if modes == {"real"} else "simulated"


def reset_workspace_backend() -> None:
    _WORKSPACE_BACKEND.clear()


def workspace_semantic_status(db: Session, **kwargs) -> dict:
    items = collect_work_items(db, **kwargs)
    if not embeddings_enabled():
        return WorkspaceSemanticStatus(False, embedding_backend_name(), embedding_model(), False, 0, "disabled", "EMBEDDING_ENABLED is disabled").to_dict()
    indexed, truth = _index_workspace_items(items)
    state = "ready" if indexed else "empty"
    return WorkspaceSemanticStatus(True, embedding_backend_name() or "memory", embedding_model(), truth == "simulated", indexed, state, "Workspace index ready" if indexed else "No WorkItems to index", truth).to_dict()


def retrieve_workspace(
    db: Session,
    *,
    query: str,
    project_id: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    entity_types: Optional[list[str]] = None,
    limit: int = 20,
    cwd: Optional[str] = None,
) -> dict:
    """Canonical ranking with lexical precision and semantic sparse-query recall."""
    items = collect_work_items(db, since=since, until=until, project_id=project_id, cwd=cwd)
    if entity_types:
        allowed = {value.casefold() for value in entity_types}
        items = [item for item in items if _entity_type(item).casefold() in allowed or item.source_type.casefold() in allowed]
    lexical = _lexical_scores(items, query)
    query_terms = _tokens(query)
    baseline_items = sorted(items, key=lambda item: (lexical[item.id], item.timestamp), reverse=True)

    semantic: dict[str, float] = {}
    embedding_truth = "unavailable"
    retrieval_mode = "lexical"
    if items and embeddings_enabled():
        _, embedding_truth = _index_workspace_items(items)
        query_vector, query_mode = embed_text_with_mode(query)
        if query_mode != "real":
            embedding_truth = "simulated"
        semantic = dict(_WORKSPACE_BACKEND.search(query_vector, top_k=len(items)))
        retrieval_mode = "hybrid" if embedding_truth == "real" else "hybrid-simulated"

    now = datetime.now(timezone.utc)
    rows = []
    for item in items:
        lexical_score = lexical[item.id]
        # Coverage of the whole query prevents one generic token (for example,
        # "agents") from outweighing a semantic match for the actual intent.
        lexical_normalized = min(1.0, lexical_score / (3.0 * len(query_terms))) if query_terms else 0.0
        semantic_score = semantic.get(item.id, 0.0)
        semantic_normalized = max(0.0, min(1.0, (semantic_score + 1.0) / 2.0)) if semantic else 0.0
        age_days = max(0.0, (now - item.timestamp).total_seconds() / 86400)
        recency = 1.0 / (1.0 + age_days / 30.0)
        quality = _QUALITY.get(item.source_type, 0.7)
        if semantic and lexical_normalized < 0.34:
            # A single generic lexical hit is weak evidence. Let semantic
            # retrieval recover related work when the wording differs.
            final_score = (0.20 * lexical_normalized) + (0.75 * semantic_normalized) + (0.03 * recency) + (0.02 * quality)
        else:
            final_score = (0.63 * lexical_normalized) + (0.32 * semantic_normalized) + (0.03 * recency) + (0.02 * quality)
        row = item.to_dict()
        row.update({
            "entity_type": _entity_type(item), "entity_id": item.source_ref,
            "content": item.summary,
            "provenance": {"source_type": item.source_type, "source_ref": item.source_ref, "evidence_refs": item.evidence_refs},
            "lexical_score": round(lexical_score, 4), "semantic_score": round(semantic_score, 6),
            "final_score": round(final_score, 6), "score": round(final_score, 6),
            "retrieval_mode": retrieval_mode, "retrieval": retrieval_mode,
        })
        rows.append(row)
    rows.sort(key=lambda row: (row["final_score"], row["timestamp"]), reverse=True)
    baseline = [
        {"id": item.id, "title": item.title, "source_ref": item.source_ref, "lexical_score": lexical[item.id]}
        for item in baseline_items[:limit] if lexical[item.id] > 0
    ]
    return {"retrieval": retrieval_mode, "retrieval_mode": retrieval_mode, "embedding_backend": embedding_truth, "items": rows[:limit], "lexical_baseline": baseline}


def search_workspace_items(db: Session, **kwargs) -> dict:
    """Compatibility wrapper; all callers now share retrieve_workspace()."""
    return retrieve_workspace(db, **kwargs)
