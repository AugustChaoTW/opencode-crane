"""Journal strategy MCP tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from crane.services.journal_recommender import JournalRecommender
from crane.services.journal_strategy_service import JournalRecommendationService


def register_tools(mcp):
    """Register journal strategy tools with the MCP server."""

    @mcp.tool()
    def analyze_paper_for_journal(
        paper_path: str,
        output_path: str = "",
    ) -> dict[str, Any]:
        """
        Analyze paper attributes for journal recommendation.

        Determines paper type (application/system, theoretical, empirical, survey)
        and recommends suitable journals based on scope, impact factor, and fit.

        Args:
            paper_path: Path to LaTeX file
            output_path: Optional path to save analysis (YAML)

        Returns:
            Paper attributes and journal recommendations.
        """
        service = JournalRecommendationService()
        attrs = service.analyze_paper_attributes(paper_path)
        strategy = service.create_submission_strategy(attrs)
        result = service.to_dict(strategy)

        if output_path:
            import yaml

            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                yaml.dump(result, allow_unicode=True, default_flow_style=False), encoding="utf-8"
            )

        return result

    @mcp.tool()
    def generate_submission_checklist(
        paper_type: str = "application_system",
    ) -> list[str]:
        """
        Generate submission checklist for a paper type.

        Args:
            paper_type: One of application_system, theoretical_diagnostic,
                empirical_study, survey_review

        Returns:
            List of checklist items.
        """
        from crane.services.journal_strategy_service import PaperType

        try:
            ptype = PaperType(paper_type)
        except ValueError:
            ptype = PaperType.APPLICATION_SYSTEM

        service = JournalRecommendationService()
        return service._generate_submission_checklist(ptype)

    @mcp.tool()
    def find_similar_papers_in_journal(
        paper_keywords: list[str],
        journal_name: str,
        max_results: int = 10,
    ) -> dict[str, Any]:
        """
        Find similar papers in a specific journal.

        Searches for papers in the target journal that match your keywords.
        Returns match statistics to help assess journal fit.

        Args:
            paper_keywords: Keywords from your paper (e.g., ["sentiment", "repair", "validation"])
            journal_name: Journal name or abbreviation (e.g., "TNNLS", "ESWA", "IEEE Transactions")
            max_results: Maximum papers to return (default 10)

        Returns:
            Dict with:
            - similar_papers: List of matching papers with metadata
            - match_count: Number of similar papers found
            - match_rate: Percentage of searched papers that matched
            - keywords_matched: Which keywords were found
            - recommendation: Human-readable fit assessment
        """
        recommender = JournalRecommender()
        return recommender.find_similar_papers_in_journal(paper_keywords, journal_name, max_results)
