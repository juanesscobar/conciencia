"""Adapter from bounded workspace retrieval into the existing ContextPack model."""

from __future__ import annotations

import json
from typing import Optional

from sqlalchemy.orm import Session

from app.models.context_pack import ContextPack

from .workspace_semantic import retrieve_workspace


def create_workspace_context_pack(
    db: Session,
    *,
    query: str,
    project_id: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    top_k: int = 6,
    max_chars: int = 6000,
    cwd: Optional[str] = None,
) -> dict:
    """Persist only the highest-ranked Work evidence that fits the budget."""
    result = retrieve_workspace(
        db, query=query, project_id=project_id, since=since, until=until,
        limit=top_k, cwd=cwd,
    )
    selected: list[dict] = []
    used_chars = 0
    truncated = False
    for item in result["items"]:
        entry = {
            "entity_type": item["entity_type"], "entity_id": item["entity_id"],
            "title": item["title"], "content": item["content"],
            "timestamp": item["timestamp"], "project_id": item["project_id"],
            "source_type": item["source_type"], "source_ref": item["source_ref"],
            "tags": item["tags"], "provenance": item["provenance"],
            "final_score": item["final_score"], "lexical_score": item["lexical_score"],
            "semantic_score": item["semantic_score"],
        }
        entry_chars = len(json.dumps(entry, ensure_ascii=False))
        if selected and used_chars + entry_chars > max_chars:
            truncated = True
            break
        if entry_chars > max_chars:
            entry["content"] = (entry["content"] or "")[:max_chars]
            entry_chars = len(json.dumps(entry, ensure_ascii=False))
            truncated = True
        selected.append(entry)
        used_chars += entry_chars

    content = {
        "workspace_retrieval": {
            "query": query, "retrieval_mode": result["retrieval_mode"],
            "embedding_backend": result["embedding_backend"], "project_id": str(project_id) if project_id else None,
            "since": since, "until": until, "items": selected,
            "item_count": len(selected), "budget_chars": max_chars,
            "approximate_chars": used_chars, "truncated": truncated,
        }
    }
    pack = ContextPack(
        title=f"Workspace context: {query[:150]}", project_id=str(project_id) if project_id else None,
        source="workspace_retrieval", target="json", content=content,
    )
    db.add(pack)
    db.commit()
    db.refresh(pack)
    return {"pack": pack.to_dict(), **content["workspace_retrieval"]}
