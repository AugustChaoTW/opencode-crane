"""
Reference management tools: add, list, get, search, remove, annotate references.
All data persisted in references/papers/*.yaml + references/bibliography.bib.
"""


def register_tools(mcp):
    """Register reference management tools with the MCP server."""

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
    ) -> str:
        """
        Add a reference to references/.
        Writes references/papers/{key}.yaml and appends to references/bibliography.bib.
        """
        raise NotImplementedError

    @mcp.tool()
    def list_references(
        filter_keyword: str = "",
        filter_tag: str = "",
        limit: int = 50,
    ) -> list[dict]:
        """
        List all references in references/papers/.
        Supports keyword and tag filtering.
        Returns summary list (key, title, authors, year, venue).
        """
        raise NotImplementedError

    @mcp.tool()
    def get_reference(key: str) -> dict:
        """
        Get full details of a single reference (including ai_annotations).
        Reads from references/papers/{key}.yaml.
        """
        raise NotImplementedError

    @mcp.tool()
    def search_references(query: str) -> list[dict]:
        """
        Full-text search across references/papers/*.yaml
        on title, authors, abstract, keywords.
        """
        raise NotImplementedError

    @mcp.tool()
    def remove_reference(key: str, delete_pdf: bool = False) -> str:
        """
        Remove a reference. Deletes YAML file, removes entry from
        bibliography.bib, optionally deletes PDF.
        """
        raise NotImplementedError

    @mcp.tool()
    def annotate_reference(
        key: str,
        summary: str = "",
        key_contributions: list[str] | None = None,
        methodology: str = "",
        relevance_notes: str = "",
        tags: list[str] | None = None,
        related_issues: list[int] | None = None,
    ) -> str:
        """
        Add or update AI annotations for a reference.
        Writes to the ai_annotations section of references/papers/{key}.yaml.
        """
        raise NotImplementedError
