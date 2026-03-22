"""
Citation verification tools: check_citations.
Validates citation consistency between manuscripts and reference library.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from crane.services.citation_service import CitationService
from crane.workspace import resolve_workspace


def register_tools(mcp):
    """Register citation verification tools with the MCP server."""

    def _resolve_refs_dir(refs_dir: str, project_dir: str | None) -> str:
        refs_path = Path(refs_dir)
        if refs_path.is_absolute():
            return str(refs_path)

        workspace = resolve_workspace(project_dir)
        if refs_path == Path("references"):
            return workspace.references_dir

        return str(Path(workspace.project_root) / refs_path)

    def _resolve_manuscript_path(manuscript_path: str, project_dir: str | None) -> str:
        path = Path(manuscript_path)
        if path.is_absolute():
            return str(path)

        workspace = resolve_workspace(project_dir)
        return str(Path(workspace.project_root) / path)

    def _get_service(refs_dir: str, project_dir: str | None) -> CitationService:
        """Get service instance for specified refs_dir."""
        return CitationService(_resolve_refs_dir(refs_dir, project_dir))

    @mcp.tool()
    def check_citations(
        manuscript_path: str = "",
        manuscript_text: str = "",
        refs_dir: str = "references",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """
        Check citation consistency between manuscript and reference library.

        Validates that all \\cite{key} references in the manuscript exist
        in the references/ directory. Also identifies unused references.

        Args:
            manuscript_path: Path to LaTeX manuscript file
            manuscript_text: Direct text content (alternative to path)
            refs_dir: References directory path

        Returns:
            Dict with:
            - valid: bool (True if all citations exist)
            - total_citations: int
            - found: list[str] (keys that exist)
            - missing: list[str] (keys NOT found - ERROR)
            - unused: list[str] (references not cited)
        """
        if not manuscript_path and not manuscript_text:
            raise ValueError("Provide either manuscript_path or manuscript_text")

        service = _get_service(refs_dir, project_dir)

        if manuscript_path:
            return service.check_local_consistency(
                _resolve_manuscript_path(manuscript_path, project_dir),
                manuscript_text,
            )
        else:
            return service.check_local_consistency(
                manuscript_path="<inline>",
                manuscript_text=manuscript_text,
            )

    @mcp.tool()
    def verify_reference(
        key: str,
        expected_doi: str = "",
        expected_year: int | None = None,
        expected_title: str = "",
        refs_dir: str = "references",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """
        Verify reference metadata matches expected values.

        Useful for validating that a reference's DOI, year, or title
        matches what you expect (e.g., from a citation in a paper).

        Args:
            key: Reference citation key
            expected_doi: Expected DOI to verify
            expected_year: Expected publication year
            expected_title: Expected title (substring match)
            refs_dir: References directory path

        Returns:
            Dict with:
            - valid: bool (True if all checks pass)
            - key: str
            - checks: dict with field-level results (doi/year/title)
        """
        service = _get_service(refs_dir, project_dir)
        return service.check_metadata(
            key=key,
            expected_doi=expected_doi,
            expected_year=expected_year,
            expected_title=expected_title,
        )

    @mcp.tool()
    def check_all_references(
        manuscript_path: str = "",
        manuscript_text: str = "",
        refs_dir: str = "references",
        project_dir: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Check metadata completeness for all references.

        Validates that all references have required fields (title, authors, year).
        If manuscript provided, only checks cited references.

        Args:
            manuscript_path: Path to manuscript file (optional)
            manuscript_text: Direct text content (optional)
            refs_dir: References directory path

        Returns:
            List of per-reference check results with field presence validation.
        """
        service = _get_service(refs_dir, project_dir)

        if manuscript_path and not manuscript_text:
            path = Path(_resolve_manuscript_path(manuscript_path, project_dir))
            if path.exists():
                manuscript_text = path.read_text(encoding="utf-8")

        text = manuscript_text if manuscript_text else None
        path = _resolve_manuscript_path(manuscript_path, project_dir) if manuscript_path else None

        return service.check_all_metadata(
            manuscript_text=text,
            manuscript_path=path,
        )
