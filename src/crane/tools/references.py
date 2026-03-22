"""
Reference management tools: add, list, get, search, remove, annotate references.
Thin MCP wrapper around ReferenceService.
"""

from pathlib import Path
from typing import Any

from crane.services.reference_service import ReferenceService
from crane.workspace import resolve_workspace


def register_tools(mcp):
    """Register reference management tools with the MCP server."""

    def _resolve_refs_dir(refs_dir: str, project_dir: str | None) -> str:
        refs_path = Path(refs_dir)
        if refs_path.is_absolute():
            return str(refs_path)

        workspace = resolve_workspace(project_dir)
        if refs_path == Path("references"):
            return workspace.references_dir

        return str(Path(workspace.project_root) / refs_path)

    def _get_service(refs_dir: str, project_dir: str | None) -> ReferenceService:
        """Get service instance for specified refs_dir."""
        return ReferenceService(_resolve_refs_dir(refs_dir, project_dir))

    @mcp.tool()
    def add_reference(
        key: str,
        title: str,
        authors: list[str],
        year: int,
        doi: str = "",
        venue: str = "",
        url: str = "",
        pdf_url: str = "",
        abstract: str = "",
        source: str = "manual",
        paper_type: str = "unknown",
        categories: list[str] | None = None,
        keywords: list[str] | None = None,
        refs_dir: str = "references",
        project_dir: str | None = None,
    ) -> str:
        """
        Add a reference to references/.
        Writes references/papers/{key}.yaml and appends to references/bibliography.bib.
        """
        service = _get_service(refs_dir, project_dir)
        return service.add(
            key=key,
            title=title,
            authors=authors,
            year=year,
            doi=doi,
            venue=venue,
            url=url,
            pdf_url=pdf_url,
            abstract=abstract,
            source=source,
            paper_type=paper_type,
            categories=categories,
            keywords=keywords,
        )

    @mcp.tool()
    def list_references(
        filter_keyword: str = "",
        filter_tag: str = "",
        limit: int = 50,
        refs_dir: str = "references",
        project_dir: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List all references in references/papers/.
        Supports keyword and tag filtering.
        Returns summary list (key, title, authors, year, venue).
        """
        service = _get_service(refs_dir, project_dir)
        return service.list(filter_keyword, filter_tag, limit)

    @mcp.tool()
    def get_reference(
        key: str,
        refs_dir: str = "references",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """
        Get full details of a single reference (including ai_annotations).
        Reads from references/papers/{key}.yaml.
        """
        service = _get_service(refs_dir, project_dir)
        return service.get(key)

    @mcp.tool()
    def search_references(
        query: str,
        refs_dir: str = "references",
        project_dir: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Full-text search across references/papers/*.yaml
        on title, authors, abstract, keywords.
        """
        service = _get_service(refs_dir, project_dir)
        return service.search(query)

    @mcp.tool()
    def remove_reference(
        key: str,
        delete_pdf: bool = False,
        refs_dir: str = "references",
        project_dir: str | None = None,
    ) -> str:
        """
        Remove a reference. Deletes YAML file, removes entry from
        bibliography.bib, optionally deletes PDF.
        """
        service = _get_service(refs_dir, project_dir)
        return service.remove(key, delete_pdf)

    @mcp.tool()
    def annotate_reference(
        key: str,
        summary: str = "",
        key_contributions: list[str] | None = None,
        methodology: str = "",
        relevance_notes: str = "",
        tags: list[str] | None = None,
        related_issues: list[int] | None = None,
        refs_dir: str = "references",
        project_dir: str | None = None,
    ) -> str:
        """
        Add or update AI annotations for a reference.
        Writes to the ai_annotations section of references/papers/{key}.yaml.
        """
        service = _get_service(refs_dir, project_dir)
        return service.annotate(
            key=key,
            summary=summary,
            key_contributions=key_contributions,
            methodology=methodology,
            relevance_notes=relevance_notes,
            tags=tags,
            related_issues=related_issues,
        )
