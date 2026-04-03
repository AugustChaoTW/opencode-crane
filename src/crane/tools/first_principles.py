from __future__ import annotations

from pathlib import Path
from typing import Any

from crane.services.first_principles_service import FirstPrinciplesService
from crane.workspace import resolve_workspace


def register_tools(mcp):
    @mcp.tool()
    def deconstruct_conventional_wisdom(
        domain: str,
        specific_belief: str = "",
        paper_path: str = "",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """
        Deconstruct conventional wisdom using First Principles reasoning.

        Implements LeCun's intellectual tradition of questioning everything.
        Identifies widely-held beliefs in a domain, challenges their foundations,
        and rebuilds understanding from first principles to find contrarian
        opportunities.

        Args:
            domain: Research domain (e.g., "AI/ML", "NLP", "Computer Vision")
            specific_belief: Specific belief/wisdom to deconstruct (optional)
            paper_path: Path to paper to extract domain context from (optional)
            project_dir: Project root directory (optional, auto-detected)

        Returns:
            Dict with conventional wisdom analysis, first principles, and opportunities.
        """
        if not domain and not paper_path:
            raise ValueError("Provide either domain or paper_path")

        workspace = resolve_workspace(project_dir)
        service = FirstPrinciplesService(project_dir=workspace.project_root)

        resolved_paper_path = paper_path
        if paper_path and not Path(paper_path).is_absolute():
            resolved_paper_path = str(Path(workspace.project_root) / paper_path)

        return service.deconstruct(
            domain=domain,
            specific_belief=specific_belief,
            paper_path=resolved_paper_path,
        )
