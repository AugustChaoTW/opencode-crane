"""Knowledge gap evaluation tools: classify gaps and suggest Q1 elevation strategies."""

from __future__ import annotations

from typing import Any


def register_tools(mcp):
    """Register knowledge gap tools with the MCP server."""

    @mcp.tool()
    def evaluate_knowledge_gaps(
        paper_path: str,
        top_n: int = 5,
    ) -> dict[str, Any]:
        """Evaluate knowledge gaps and their potential to elevate research to Q1.

        Analyses the paper's knowledge graph and citation graph to surface
        concept-pair gaps, classifies them as field / domain / paper level,
        and generates concrete reframe suggestions for boosting journal tier.

        Args:
            paper_path: Path to a .tex or .pdf paper file.
            top_n:      Maximum total number of gaps to surface (default 5).

        Returns:
            Dict with field_level_gaps, domain_level_gaps, paper_level_gaps
            (each a list of gap dicts) and trace_updated (bool).
        """
        from crane.services.knowledge_gap_elevation_service import (
            GapLevel,
            KnowledgeGapElevationService,
        )

        svc = KnowledgeGapElevationService()
        gaps = svc.evaluate(paper_path=paper_path, top_n=top_n)

        def _gap_to_dict(g):
            return {
                "concept_a": g.concept_a,
                "concept_b": g.concept_b,
                "gap_description": g.gap_description,
                "level": g.level.value,
                "elevation_potential": g.elevation_potential,
                "reframe_suggestion": g.reframe_suggestion,
                "supporting_evidence": g.supporting_evidence,
            }

        field_gaps = [_gap_to_dict(g) for g in gaps if g.level == GapLevel.FIELD]
        domain_gaps = [_gap_to_dict(g) for g in gaps if g.level == GapLevel.DOMAIN]
        paper_gaps = [_gap_to_dict(g) for g in gaps if g.level == GapLevel.PAPER]

        return {
            "field_level_gaps": field_gaps,
            "domain_level_gaps": domain_gaps,
            "paper_level_gaps": paper_gaps,
            "trace_updated": True,
        }
