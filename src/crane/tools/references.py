"""
Reference management tools: add, list, get, search, remove, annotate references.
All data persisted in references/papers/*.yaml + references/bibliography.bib.
"""

from datetime import date
from pathlib import Path
from typing import Any

from crane.models.paper import AiAnnotations, Paper
from crane.utils.bibtex import append_entry, remove_entry
from crane.utils.yaml_io import (
    delete_paper_yaml,
    list_paper_keys,
    read_paper_yaml,
    write_paper_yaml,
)


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
        refs_dir: str = "references",
    ) -> str:
        """
        Add a reference to references/.
        Writes references/papers/{key}.yaml and appends to references/bibliography.bib.
        """
        papers_dir = str(Path(refs_dir) / "papers")
        bib_path = str(Path(refs_dir) / "bibliography.bib")

        paper = Paper(
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
            categories=categories or [],
            keywords=keywords or [],
        )
        paper.bibtex = paper.to_bibtex()

        write_paper_yaml(papers_dir, key, paper.to_yaml_dict())
        append_entry(bib_path, paper.bibtex)

        return f"Added reference: {key}"

    @mcp.tool()
    def list_references(
        filter_keyword: str = "",
        filter_tag: str = "",
        limit: int = 50,
        refs_dir: str = "references",
    ) -> list[dict[str, Any]]:
        """
        List all references in references/papers/.
        Supports keyword and tag filtering.
        Returns summary list (key, title, authors, year, venue).
        """
        papers_dir = str(Path(refs_dir) / "papers")
        keys = list_paper_keys(papers_dir)

        keyword_query = filter_keyword.strip().lower()
        tag_query = filter_tag.strip().lower()

        results: list[dict[str, Any]] = []
        for key in keys:
            data = read_paper_yaml(papers_dir, key)
            if data is None:
                continue

            if keyword_query:
                title = str(data.get("title", ""))
                abstract = str(data.get("abstract", ""))
                keywords = data.get("keywords", [])
                keyword_text = " ".join(str(item) for item in keywords)
                haystack = f"{title} {abstract} {keyword_text}".lower()
                if keyword_query not in haystack:
                    continue

            if tag_query:
                ai_annotations = data.get("ai_annotations", {}) or {}
                tags = ai_annotations.get("tags", [])
                normalized_tags = [str(tag).lower() for tag in tags]
                if tag_query not in normalized_tags:
                    continue

            results.append(
                {
                    "key": data.get("key", key),
                    "title": data.get("title", ""),
                    "authors": data.get("authors", []),
                    "year": data.get("year"),
                    "venue": data.get("venue", ""),
                }
            )

        if limit <= 0:
            return []
        return results[:limit]

    @mcp.tool()
    def get_reference(key: str, refs_dir: str = "references") -> dict[str, Any]:
        """
        Get full details of a single reference (including ai_annotations).
        Reads from references/papers/{key}.yaml.
        """
        papers_dir = str(Path(refs_dir) / "papers")
        data = read_paper_yaml(papers_dir, key)
        if data is None:
            raise ValueError(f"Reference not found: {key}")
        return data

    @mcp.tool()
    def search_references(query: str, refs_dir: str = "references") -> list[dict[str, Any]]:
        """
        Full-text search across references/papers/*.yaml
        on title, authors, abstract, keywords.
        """
        papers_dir = str(Path(refs_dir) / "papers")
        normalized_query = query.strip().lower()
        if not normalized_query:
            return []

        matches: list[dict[str, Any]] = []
        for key in list_paper_keys(papers_dir):
            data = read_paper_yaml(papers_dir, key)
            if data is None:
                continue

            title = str(data.get("title", ""))
            authors = " ".join(str(author) for author in data.get("authors", []))
            abstract = str(data.get("abstract", ""))
            keywords = " ".join(str(keyword) for keyword in data.get("keywords", []))
            haystack = f"{title} {authors} {abstract} {keywords}".lower()

            if normalized_query in haystack:
                matches.append(data)

        return matches

    @mcp.tool()
    def remove_reference(
        key: str,
        delete_pdf: bool = False,
        refs_dir: str = "references",
    ) -> str:
        """
        Remove a reference. Deletes YAML file, removes entry from
        bibliography.bib, optionally deletes PDF.
        """
        refs_path = Path(refs_dir)
        papers_dir = str(refs_path / "papers")
        bib_path = str(refs_path / "bibliography.bib")

        paper_data = read_paper_yaml(papers_dir, key)
        yaml_removed = delete_paper_yaml(papers_dir, key)
        bib_removed = remove_entry(bib_path, key)

        pdf_removed = False
        if delete_pdf:
            candidate_paths: list[Path] = []
            if paper_data is not None and paper_data.get("pdf_path"):
                candidate_paths.append(Path(str(paper_data["pdf_path"])))
            candidate_paths.append(refs_path / "pdfs" / f"{key}.pdf")

            for pdf_path in candidate_paths:
                if pdf_path.exists():
                    pdf_path.unlink()
                    pdf_removed = True
                    break

        if not yaml_removed and not bib_removed and not pdf_removed:
            return f"Reference not found: {key}"

        parts = [f"Removed reference: {key}"]
        if delete_pdf:
            parts.append("PDF removed" if pdf_removed else "PDF not found")
        return "; ".join(parts)

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
    ) -> str:
        """
        Add or update AI annotations for a reference.
        Writes to the ai_annotations section of references/papers/{key}.yaml.
        """
        papers_dir = str(Path(refs_dir) / "papers")
        data = read_paper_yaml(papers_dir, key)
        if data is None:
            raise ValueError(f"Reference not found: {key}")

        paper = Paper.from_yaml_dict(data)
        if paper.ai_annotations is None:
            paper.ai_annotations = AiAnnotations()

        if summary:
            paper.ai_annotations.summary = summary
        if key_contributions is not None:
            paper.ai_annotations.key_contributions = key_contributions
        if methodology:
            paper.ai_annotations.methodology = methodology
        if relevance_notes:
            paper.ai_annotations.relevance_notes = relevance_notes
        if tags is not None:
            paper.ai_annotations.tags = tags
        if related_issues is not None:
            paper.ai_annotations.related_issues = related_issues

        paper.ai_annotations.added_date = date.today().isoformat()
        write_paper_yaml(papers_dir, key, paper.to_yaml_dict())

        return f"Updated annotations for: {key}"
