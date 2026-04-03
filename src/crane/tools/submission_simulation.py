"""Submission outcome simulation MCP tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from crane.services.submission_simulation_service import SubmissionSimulationService
from crane.workspace import resolve_workspace


def register_tools(mcp):
    """Register submission simulation tools with the MCP server."""

    def _resolve_paper_path(paper_path: str, project_dir: str | None) -> str:
        path = Path(paper_path)
        if path.is_absolute():
            return str(path)

        workspace = resolve_workspace(project_dir)
        return str(Path(workspace.project_root) / path)

    @mcp.tool()
    def simulate_submission_outcome(
        paper_path: str,
        target_journal: str = "",
        revision_status: str = "current",
        num_scenarios: int = 5,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """
        Simulate paper submission outcomes using LeCun World Model reasoning.

        Analyzes the paper's structure, estimates journal fit, and generates
        multiple outcome scenarios with probabilities, timelines, and
        second-order effect predictions.

        Args:
            paper_path: Path to LaTeX paper file
            target_journal: Target journal name (e.g., "IEEE TPAMI", "JMLR")
            revision_status: Current revision state ("current", "post_revision", "final")
            num_scenarios: Number of scenarios to generate (3-7, default 5)
            project_dir: Project root directory (optional, auto-detected)

        Returns:
            Dict with scenarios, world_model_analysis, and recommendation.
        """
        resolved_paper_path = _resolve_paper_path(paper_path, project_dir)
        service = SubmissionSimulationService(project_dir=project_dir)
        return service.simulate_outcomes(
            paper_path=resolved_paper_path,
            target_journal=target_journal,
            revision_status=revision_status,
            num_scenarios=num_scenarios,
        )
