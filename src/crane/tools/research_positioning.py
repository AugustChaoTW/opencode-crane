from __future__ import annotations

from pathlib import Path
from typing import Any

from crane.services.research_positioning_service import ResearchPositioningService
from crane.workspace import resolve_workspace


def register_tools(mcp):
    def _resolve_paper_path(paper_path: str, project_dir: str | None) -> str:
        path = Path(paper_path)
        if path.is_absolute():
            return str(path)
        workspace = resolve_workspace(project_dir)
        return str(Path(workspace.project_root) / path)

    @mcp.tool()
    def analyze_research_positioning(
        paper_path: str = "",
        research_topic: str = "",
        domain: str = "",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        if not paper_path and not research_topic:
            raise ValueError("Provide either paper_path or research_topic")

        workspace = resolve_workspace(project_dir)
        service = ResearchPositioningService(project_dir=workspace.project_root)

        resolved_path = _resolve_paper_path(paper_path, project_dir) if paper_path else None
        return service.analyze_positioning(
            paper_path=resolved_path,
            research_topic=research_topic,
            domain=domain,
        )
