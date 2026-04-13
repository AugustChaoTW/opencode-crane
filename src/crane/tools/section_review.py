"""Section-level paper review MCP tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from crane.services.section_review_service import ReviewType, SectionReviewService


def register_tools(mcp):
    """Register section review tools with the MCP server."""

    @mcp.tool()
    def review_paper_sections(
        paper_path: str,
        sections: list[str] | None = None,
        review_types: list[str] | None = None,
        output_path: str = "",
    ) -> dict[str, Any]:
        """
        Review paper sections for issues before submission.

        Detects common problems that lead to rejection:
        - Logic errors (Python code, algorithm correctness)
        - Data inconsistencies (percentages, costs, latencies)
        - Framing issues (overclaiming, weak justification)
        - Completeness gaps (missing baselines, limitations)
        - AI writing patterns (filler phrases, vague quantifiers)
        - Figure quality (complexity, caption completeness)

        PREREQUISITES:
            Paper file must exist locally (LaTeX .tex or PDF).
            Check readiness with: check_prerequisites("review_paper_sections")

        Args:
            paper_path: Path to LaTeX file (absolute or relative to project root)
            sections: Specific sections to review (None = all)
            review_types: Review types to apply (None = all)
                Options: logic, data, framing, completeness, writing, figures
            output_path: Optional path to save review report (YAML)

        Returns:
            Review report with issues, scores, and recommendations.
        """
        service = SectionReviewService()

        if review_types is None:
            review_types_enum = list(ReviewType)
        else:
            review_types_enum = [ReviewType(rt) for rt in review_types]

        review = service.review_paper(paper_path, sections, review_types_enum)
        result = service.to_dict(review)

        if output_path:
            import yaml

            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                yaml.dump(result, allow_unicode=True, default_flow_style=False), encoding="utf-8"
            )

        return result

    @mcp.tool()
    def parse_paper_structure(
        paper_path: str,
    ) -> dict[str, Any]:
        """
        Parse LaTeX paper structure.

        Args:
            paper_path: Path to LaTeX file

        Returns:
            Paper structure with title, abstract, sections, appendices.
        """
        from crane.services.latex_parser import parse_latex_sections

        structure = parse_latex_sections(paper_path)

        def section_to_dict(s):
            return {
                "name": s.name,
                "level": s.level,
                "start_line": s.start_line,
                "end_line": s.end_line,
                "subsections": [section_to_dict(sub) for sub in s.subsections],
            }

        return {
            "title": structure.title,
            "abstract": structure.abstract[:200] + "..."
            if len(structure.abstract) > 200
            else structure.abstract,
            "sections": [section_to_dict(s) for s in structure.sections],
            "appendices": [section_to_dict(s) for s in structure.appendices],
            "total_sections": len(structure.sections),
            "total_appendices": len(structure.appendices),
        }
