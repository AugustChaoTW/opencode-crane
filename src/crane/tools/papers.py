"""
Paper search and retrieval tools: search_papers, download_paper, read_paper
Thin MCP wrapper around PaperService.
"""

from pathlib import Path

from crane.services.paper_service import PaperService
from crane.workspace import resolve_workspace

# Shared service instance
_paper_service = PaperService()


def _resolve_save_dir(save_dir: str, project_dir: str | None) -> str:
    save_path = Path(save_dir)
    if save_path.is_absolute():
        return str(save_path)

    workspace = resolve_workspace(project_dir)
    if save_path == Path("references") / "pdfs":
        return workspace.pdfs_dir

    return str(Path(workspace.project_root) / save_path)


def register_tools(mcp):
    """Register paper search tools with the MCP server."""

    @mcp.tool()
    def search_papers(
        query: str,
        max_results: int = 10,
        source: str = "arxiv",
    ) -> list[dict[str, object]]:
        """
        Search academic papers. Returns list with title, authors, abstract,
        doi, url, pdf_url, published_date, categories.
        Supported sources: arxiv (google_scholar, semantic_scholar planned).
        """
        return _paper_service.search(query, max_results, source)

    @mcp.tool()
    def download_paper(
        paper_id: str,
        save_dir: str = "references/pdfs",
        project_dir: str | None = None,
    ) -> str:
        """
        Download paper PDF to references/pdfs/ directory.
        Returns local file path.
        """
        path = _paper_service.download(paper_id, _resolve_save_dir(save_dir, project_dir))
        return str(path)

    @mcp.tool()
    def read_paper(
        paper_id: str,
        save_dir: str = "references/pdfs",
        project_dir: str | None = None,
    ) -> str:
        """
        Read paper PDF and extract full text.
        Auto-downloads if PDF doesn't exist locally.
        Returns plain text content.
        """
        return _paper_service.read(paper_id, _resolve_save_dir(save_dir, project_dir))
