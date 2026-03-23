"""Q1 paper evaluation MCP tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from crane.services.q1_evaluation_service import Q1EvaluationService


def register_tools(mcp):
    """Register Q1 evaluation tools with the MCP server."""

    @mcp.tool()
    def evaluate_q1_standards(
        paper_path: str,
        output_path: str = "",
    ) -> dict[str, Any]:
        """
        Evaluate paper against Q1 journal standards.

        Checks 7 categories:
        - Writing Quality: Academic tone, clarity, logical flow
        - Methodology: Research design, technical rigor
        - Novelty: Contribution statement, comparison with prior work
        - Evaluation: Baselines, statistical significance
        - Presentation: Figures, tables
        - Limitations: Acknowledged limitations, future work
        - Reproducibility: Code availability, implementation details

        Args:
            paper_path: Path to LaTeX file
            output_path: Optional path to save evaluation report (YAML)

        Returns:
            Q1 evaluation report with scores, readiness, and suggestions.
        """
        service = Q1EvaluationService()
        evaluation = service.evaluate(paper_path)
        result = service.to_dict(evaluation)

        if output_path:
            import yaml

            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                yaml.dump(result, allow_unicode=True, default_flow_style=False), encoding="utf-8"
            )

        return result
