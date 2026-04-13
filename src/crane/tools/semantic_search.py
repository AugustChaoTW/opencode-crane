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

        query_embedding = service._embed_text(query, api_key=service.embedding_api_key)
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
    ) -> dict[str, Any]:
        """Build and cache embeddings for all references.

        Requires OPENAI_API_KEY environment variable.

        Args:
            refs_dir:    References directory path.
            project_dir: Project root directory.

        Returns:
            Dict with embedding status and count.
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {
                "status": "error",
                "message": "OPENAI_API_KEY environment variable not set",
                "embedding_count": 0,
            }

        service = _get_service(refs_dir, project_dir)
        embeddings = service.build_embeddings(api_key=api_key)

        return {
            "status": "success",
            "embedding_count": len(embeddings),
            "cache_file": str(service.embeddings_file),
            "model": service.embedding_model,
        }
