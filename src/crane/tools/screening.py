"""Screening and comparison workflow MCP tools."""

from __future__ import annotations

from typing import Any

from crane.services.screening_service import ScreeningService
from crane.workspace import resolve_workspace


def register_tools(mcp):
    """Register screening tools with the MCP server."""

    def _get_service(refs_dir: str) -> ScreeningService:
        return ScreeningService(refs_dir)

    @mcp.tool()
    def screen_reference(
        paper_key: str,
        decision: str,
        reason: str = "",
        criteria: list[str] | None = None,
        refs_dir: str = "references",
    ) -> dict[str, Any]:
        """
        Record a screening decision for a reference.

        Args:
            paper_key: Reference key to screen
            decision: "include", "exclude", or "maybe"
            reason: Reason for the decision
            criteria: List of criteria applied
            refs_dir: References directory

        Returns:
            Screening result dict.
        """
        service = _get_service(refs_dir)
        result = service.screen(paper_key, decision, reason, criteria)
        return {
            "paper_key": result.paper_key,
            "decision": result.decision.value,
            "reason": result.reason,
            "criteria": result.criteria,
            "timestamp": result.timestamp,
        }

    @mcp.tool()
    def list_screened_references(
        decision: str = "",
        refs_dir: str = "references",
    ) -> list[dict[str, Any]]:
        """
        List all screened references with optional decision filter.

        Args:
            decision: Filter by decision ("include", "exclude", "maybe")
            refs_dir: References directory

        Returns:
            List of screened reference summaries.
        """
        service = _get_service(refs_dir)
        return service.list_screened(decision or None)

    @mcp.tool()
    def compare_papers(
        paper_keys: list[str],
        dimensions: list[str] | None = None,
        refs_dir: str = "references",
    ) -> dict[str, Any]:
        """
        Create a comparison matrix for multiple papers.

        Args:
            paper_keys: List of reference keys to compare
            dimensions: Comparison dimensions (default: year, authors, venue, methodology, dataset, metric, result)
            refs_dir: References directory

        Returns:
            Comparison matrix dict.
        """
        service = _get_service(refs_dir)
        matrix = service.compare(paper_keys, dimensions)
        return matrix.to_dict()
