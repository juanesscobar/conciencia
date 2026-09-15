"""Focused tests for canonical workspace hybrid retrieval and ContextPack adapter."""

from datetime import datetime, timezone

from app.services.work_service import WorkItem
from app.services import workspace_context, workspace_semantic


def _item(item_id, title, *, project_id=None, timestamp=None):
    timestamp = timestamp or datetime(2026, 9, 1, tzinfo=timezone.utc)
    return WorkItem(
        id=item_id, workspace_id="workspace", project_id=project_id,
        type="git.commit", title=title, summary=title, timestamp=timestamp,
        source_type="git_commit", source_ref=item_id.removeprefix("git:"),
        metadata={}, tags=["git"], evidence_refs=["evidence-1"], created_at=timestamp,
    )


def test_retrieve_lexical_fallback_preserves_exact_match(db, monkeypatch):
    items = [_item("git:web", "WebMCP adapter"), _item("git:other", "General tooling")]
    monkeypatch.setattr(workspace_semantic, "collect_work_items", lambda *args, **kwargs: items)
    monkeypatch.setenv("EMBEDDING_ENABLED", "0")

    result = workspace_semantic.retrieve_workspace(db, query="WebMCP")
    assert result["retrieval_mode"] == "lexical"
    assert result["embedding_backend"] == "unavailable"
    assert result["items"][0]["id"] == "git:web"
    assert result["items"][0]["provenance"]["source_ref"] == "web"
    assert result["lexical_baseline"][0]["id"] == "git:web"


def test_retrieve_hybrid_simulated_finds_semantic_alias_without_keyword(db, monkeypatch):
    items = [_item("git:web", "WebMCP adapter"), _item("git:other", "Invoice export")]
    monkeypatch.setattr(workspace_semantic, "collect_work_items", lambda *args, **kwargs: items)
    monkeypatch.setenv("EMBEDDING_ENABLED", "1")

    def fake_embed(text):
        return ([1.0, 0.0], "simulated") if "webmcp" in text.casefold() or "agentes" in text.casefold() else ([0.0, 1.0], "simulated")

    monkeypatch.setattr(workspace_semantic, "embed_text_with_mode", fake_embed)
    result = workspace_semantic.retrieve_workspace(db, query="herramientas para que agentes interactuen con paginas web")
    assert result["retrieval_mode"] == "hybrid-simulated"
    assert result["embedding_backend"] == "simulated"
    assert result["items"][0]["id"] == "git:web"
    assert result["items"][0]["lexical_score"] == 0
    assert result["items"][0]["semantic_score"] > 0


def test_retrieve_labels_real_embedding_backend(db, monkeypatch):
    monkeypatch.setattr(workspace_semantic, "collect_work_items", lambda *args, **kwargs: [_item("git:web", "WebMCP adapter")])
    monkeypatch.setenv("EMBEDDING_ENABLED", "1")
    monkeypatch.setattr(workspace_semantic, "embed_text_with_mode", lambda text: ([1.0, 0.0], "real"))

    result = workspace_semantic.retrieve_workspace(db, query="WebMCP")
    assert result["retrieval_mode"] == "hybrid"
    assert result["embedding_backend"] == "real"


def test_workspace_context_pack_is_bounded_and_preserves_provenance(db, monkeypatch):
    items = [_item("git:web", "WebMCP adapter"), _item("git:other", "Other change")]
    monkeypatch.setattr(workspace_semantic, "collect_work_items", lambda *args, **kwargs: items)
    monkeypatch.setenv("EMBEDDING_ENABLED", "0")

    result = workspace_context.create_workspace_context_pack(
        db, query="WebMCP", top_k=2, max_chars=700,
    )
    retrieval = result["pack"]["content"]["workspace_retrieval"]
    assert result["item_count"] <= 2
    assert result["approximate_chars"] <= 700
    assert retrieval["items"][0]["provenance"]["source_ref"] == "web"
