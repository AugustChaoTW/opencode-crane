from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from crane.services.research_pipeline_benchmark_service import ResearchPipelineBenchmarkService
from crane.workspace import resolve_workspace


def _resolve_paper_path(paper_path: str, project_dir: str | None) -> str:
    path = Path(paper_path)
    if path.is_absolute():
        return str(path)

    workspace = resolve_workspace(project_dir)
    return str(Path(workspace.project_root) / path)


def register_tools(mcp):
    @mcp.tool()
    def benchmark_research_pipeline(
        paper_path: str = "",
        manuscript_text: str = "",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        if not paper_path and not manuscript_text:
            raise ValueError("Provide either paper_path or manuscript_text")

        workspace = resolve_workspace(project_dir)
        service = ResearchPipelineBenchmarkService(refs_dir=workspace.references_dir)

        temp_path: Path | None = None
        try:
            if paper_path:
                resolved_path = _resolve_paper_path(paper_path, project_dir)
            else:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".tex", encoding="utf-8", delete=False
                ) as handle:
                    handle.write(manuscript_text)
                    temp_path = Path(handle.name)
                resolved_path = str(temp_path)

            report = service.evaluate_pipeline(resolved_path)
            return {
                "paper_path": report["paper_path"],
                "stages": report["stages"],
                "coherence_scores": report["coherence_scores"],
                "health_score": report["health_score"],
                "prediction": report["prediction"],
            }
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink()
