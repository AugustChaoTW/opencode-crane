"""
Paper search and retrieval tools: search_papers, download_paper, read_paper
"""


def register_tools(mcp):
    """Register paper search tools with the MCP server."""

    @mcp.tool()
    def search_papers(
        query: str,
        max_results: int = 10,
        source: str = "arxiv",
    ) -> list[dict]:
        """
        Search academic papers. Returns list with title, authors, abstract,
        doi, url, pdf_url, published_date, categories.
        Supported sources: arxiv (google_scholar, semantic_scholar planned).
        """
        raise NotImplementedError

    @mcp.tool()
    def download_paper(
        paper_id: str,
        save_dir: str = "references/pdfs",
    ) -> str:
        """
        Download paper PDF to references/pdfs/ directory.
        Returns local file path.
        """
        raise NotImplementedError

    @mcp.tool()
    def read_paper(
        paper_id: str,
        save_dir: str = "references/pdfs",
    ) -> str:
        """
        Read paper PDF and extract full text.
        Auto-downloads if PDF doesn't exist locally.
        Returns plain text content.
        """
        raise NotImplementedError
