"""Screening and comparison workflow MCP tools."""

from __future__ import annotations

from typing import Any

from crane.services.picos_screening_service import PICOSCriteria, PICOSScreeningService
from crane.services.screening_service import ScreeningService


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
            dimensions: Comparison dimensions (default: year, authors, venue,
                methodology, dataset, metric, result)
            refs_dir: References directory

        Returns:
            Comparison matrix dict.
        """
        service = _get_service(refs_dir)
        matrix = service.compare(paper_keys, dimensions)
        return matrix.to_dict()

    @mcp.tool()
    def screen_papers_by_picos(
        population: str = "",
        intervention: str = "",
        comparison: str = "",
        outcome: str = "",
        study_design: str = "",
        threshold: float = 0.5,
        refs_dir: str = "references",
    ) -> dict[str, Any]:
        picos_service = PICOSScreeningService(refs_dir)
        ref_service = picos_service.ref_service

        criteria = PICOSCriteria(
            population=population,
            intervention=intervention,
            comparison=comparison,
            outcome=outcome,
            study_design=study_design,
        )
        paper_keys = ref_service.get_all_keys()
        results = picos_service.screen_papers(paper_keys, criteria, threshold)

        return {
            "criteria": {
                "population": criteria.population,
                "intervention": criteria.intervention,
                "comparison": criteria.comparison,
                "outcome": criteria.outcome,
                "study_design": criteria.study_design,
            },
            "threshold": threshold,
            "total_papers": len(paper_keys),
            "included": [item.paper_key for item in results if item.decision == "include"],
            "maybe": [item.paper_key for item in results if item.decision == "maybe"],
            "excluded": [item.paper_key for item in results if item.decision == "exclude"],
            "results": [
                {
                    "paper_key": item.paper_key,
                    "title": item.title,
                    "decision": item.decision,
                    "overall_score": item.match.overall_score,
                    "scores": {
                        "population": item.match.population_score,
                        "intervention": item.match.intervention_score,
                        "comparison": item.match.comparison_score,
                        "outcome": item.match.outcome_score,
                        "study_design": item.match.study_design_score,
                    },
                    "matched_terms": item.match.matched_terms,
                    "extracted_picos": {
                        "population": item.extracted_picos.population,
                        "intervention": item.extracted_picos.intervention,
                        "comparison": item.extracted_picos.comparison,
                        "outcome": item.extracted_picos.outcome,
                        "study_design": item.extracted_picos.study_design,
                    },
                }
                for item in results
            ],
        }
