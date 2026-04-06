from __future__ import annotations

from pathlib import Path

from crane.services.paper_code_alignment_service import PaperCodeAlignmentService
from crane.workspace import resolve_workspace


def register_tools(mcp):
    def _resolve_refs_dir(refs_dir: str, project_dir: str | None) -> str:
        refs_path = Path(refs_dir)
        if refs_path.is_absolute():
            return str(refs_path)

        workspace = resolve_workspace(project_dir)
        if refs_path == Path("references"):
            return workspace.references_dir

        return str(Path(workspace.project_root) / refs_path)

    def _resolve_path(path_str: str, project_dir: str | None) -> str:
        path = Path(path_str)
        if path.is_absolute():
            return str(path)

        workspace = resolve_workspace(project_dir)
        return str(Path(workspace.project_root) / path)

    def _get_service(refs_dir: str, project_dir: str | None) -> PaperCodeAlignmentService:
        return PaperCodeAlignmentService(_resolve_refs_dir(refs_dir, project_dir))

    @mcp.tool()
    def verify_paper_code_alignment(
        paper_path: str,
        code_path: str,
        refs_dir: str = "references",
        project_dir: str | None = None,
    ) -> dict[str, object]:
        """
        Verify whether paper experiment settings align with implementation code.

        Args:
            paper_path: Path to LaTeX manuscript file.
            code_path: Path to Python code file or directory.
            refs_dir: References directory path.
            project_dir: Optional project root override for workspace resolution.

        Returns:
            Structured report containing extracted settings and alignment summary.

        Raises:
            ValueError: If required input paths are not provided.
            FileNotFoundError: If paper_path or code_path does not exist.
        """
        if not paper_path:
            raise ValueError("paper_path is required")
        if not code_path:
            raise ValueError("code_path is required")

        service = _get_service(refs_dir, project_dir)
        return service.generate_alignment_report(
            latex_path=_resolve_path(paper_path, project_dir),
            code_path=_resolve_path(code_path, project_dir),
        )
