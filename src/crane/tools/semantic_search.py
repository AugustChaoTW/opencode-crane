"""Semantic search tools: find similar papers by query or by anchor paper."""

import os
from pathlib import Path
from typing import Any

from crane.services.semantic_search_service import SemanticSearchService
from crane.workspace import resolve_workspace


def register_tools(mcp):
    """Register semantic search tools with the MCP server."""

    def _resolve_refs_dir(refs_dir: str, project_dir: str | None) -> str:
        refs_path = Path(refs_dir)
        if refs_path.is_absolute():
            return str(refs_path)

        workspace = resolve_workspace(project_dir)
        if refs_path == Path("references"):
            return workspace.references_dir

        return str(Path(workspace.project_root) / refs_path)

    def _get_service(refs_dir: str, project_dir: str | None) -> SemanticSearchService:
        """Get service instance for specified refs_dir."""
        resolved_dir = _resolve_refs_dir(refs_dir, project_dir)
        api_key = os.getenv("OPENAI_API_KEY")
        return SemanticSearchService(refs_dir=resolved_dir, embedding_api_key=api_key)

    @mcp.tool()
    def semantic_search(
        query: str = "",
        anchor_paper_key: str = "",
        k: int = 5,
        refs_dir: str = "references",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Find similar papers by query text or by an anchor paper.

        Provide either *query* (free-text) or *anchor_paper_key* (BibTeX key).
        When both are given, *anchor_paper_key* takes precedence.

        PREREQUISITES:
            build_embeddings() must be called first.
            Check readiness with: check_prerequisites("semantic_search")

        Args:
            query:            Free-text search (e.g. "attention mechanisms").
                              Ignored when anchor_paper_key is provided.
            anchor_paper_key: BibTeX key of a paper already in your library.
                              Returns papers similar to that paper, excluding itself.
            k:                Number of similar papers to return (default 5).
            refs_dir:         References directory path.
            project_dir:      Project root directory.

        Returns:
            Dict with status, matches list, and either query or anchor_paper_key echoed.
            matches: [{key, similarity, title, authors, year, abstract}, ...]
        """
        service = _get_service(refs_dir, project_dir)

        # ── anchor-paper mode ──────────────────────────────────────────────
        if anchor_paper_key:
            if anchor_paper_key not in service.references:
                return {
                    "anchor_paper_key": anchor_paper_key,
                    "status": "not_found",
                    "message": f"Reference not found: {anchor_paper_key}",
                    "matches": [],
                }
            if not service.embeddings or anchor_paper_key not in service.embeddings:
                return {
                    "anchor_paper_key": anchor_paper_key,
                    "status": "no_embedding",
                    "message": f"No embedding for {anchor_paper_key}. Run build_embeddings first.",
                    "matches": [],
                }
            matches = service.find_similar_by_paper(paper_key=anchor_paper_key, k=k)
            return {
                "anchor_paper_key": anchor_paper_key,
                "status": "success",
                "match_count": len(matches),
                "matches": matches,
            }

        # ── query-text mode ────────────────────────────────────────────────
        if not service.embeddings:
            return {
                "query": query,
                "status": "no_embeddings",
                "message": "No embeddings found. Run build_embeddings first.",
                "matches": [],
            }

        query_embedding = service._embed_query(query)
        if not query_embedding:
            return {
                "query": query,
                "status": "embedding_failed",
                "message": "Could not embed query text. Check API key or network.",
                "matches": [],
            }

        matches = service.search_similar(
            query_text=query,
            query_embedding=query_embedding,
            k=k,
        )
        return {
            "query": query,
            "status": "success",
            "match_count": len(matches),
            "matches": matches,
        }

    @mcp.tool()
    def build_embeddings(
        refs_dir: str = "references",
        project_dir: str | None = None,
        provider: str = "openai",
        model: str = "",
        ollama_url: str = "http://localhost:11434",
    ) -> dict[str, Any]:
        """Build and cache embeddings for all references.

        Supports OpenAI (default) and local Ollama.

        Args:
            refs_dir:    References directory path.
            project_dir: Project root directory.
            provider:    ``"openai"`` (default) or ``"ollama"``.
                         Use ``"ollama"`` to embed with a local model — no API
                         key needed, but Ollama must be running.
            model:       Model name override.
                         OpenAI default: ``text-embedding-3-small``
                         Ollama default: ``nomic-embed-text``
            ollama_url:  Ollama server URL (default ``http://localhost:11434``).
                         Only used when provider is ``"ollama"``.

        Returns:
            Dict with embedding status, count, provider, and model used.

        Examples:
            build_embeddings()
                # OpenAI, reads OPENAI_API_KEY from env

            build_embeddings(provider="ollama")
                # Local nomic-embed-text via Ollama (no API key needed)

            build_embeddings(provider="ollama", model="mxbai-embed-large")
                # Local mxbai-embed-large (1024 dims)
        """
        if provider == "ollama":
            service = _get_service(refs_dir, project_dir)
            effective_model = model or "nomic-embed-text"
            embeddings = service.build_embeddings(
                provider="ollama",
                model=effective_model,
                ollama_url=ollama_url,
            )
            return {
                "status": "success",
                "provider": "ollama",
                "model": effective_model,
                "ollama_url": ollama_url,
                "embedding_count": len(embeddings),
                "embedding_dim": service.embedding_dim,
                "cache_file": str(service.embeddings_file),
            }

        # OpenAI path
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {
                "status": "error",
                "provider": "openai",
                "message": (
                    "OPENAI_API_KEY environment variable not set. "
                    "To use a local model instead, call: "
                    'build_embeddings(provider="ollama")'
                ),
                "embedding_count": 0,
            }

        service = _get_service(refs_dir, project_dir)
        effective_model = model or None  # service uses its default
        embeddings = service.build_embeddings(api_key=api_key, model=effective_model)

        return {
            "status": "success",
            "provider": "openai",
            "model": service.embedding_model,
            "embedding_count": len(embeddings),
            "embedding_dim": service.embedding_dim,
            "cache_file": str(service.embeddings_file),
        }
