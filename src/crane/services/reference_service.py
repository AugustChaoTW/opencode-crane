"""
Reference management service.
Core business logic for YAML + BibTeX reference operations.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from crane.models.paper import ALLOWED_ANNOTATION_TAGS, AiAnnotations, Paper
from crane.utils.bibtex import append_entry, remove_entry
from crane.utils.yaml_io import (
    delete_paper_yaml,
    list_paper_keys,
    read_paper_yaml,
    write_paper_yaml,
)


class ReferenceService:
    """Service for reference CRUD operations with YAML + BibTeX persistence."""

    def __init__(self, refs_dir: str | Path = "references"):
        self.refs_path = Path(refs_dir)
        self.papers_dir = self.refs_path / "papers"
        self.pdfs_dir = self.refs_path / "pdfs"
        self.bib_path = self.refs_path / "bibliography.bib"

        # Ensure directories exist
        self.papers_dir.mkdir(parents=True, exist_ok=True)
        self.pdfs_dir.mkdir(parents=True, exist_ok=True)
        self.bib_path.parent.mkdir(parents=True, exist_ok=True)
        self.bib_path.touch(exist_ok=True)

    def _validate_annotation_inputs(
        self,
        summary: str,
        key_contributions: list[str] | None,
        methodology: str,
        relevance_notes: str,
        tags: list[str] | None,
        related_issues: list[int] | None,
    ) -> None:
        if len(summary) > 2000:
            raise ValueError("summary exceeds maximum length (2000)")
        if len(methodology) > 4000:
            raise ValueError("methodology exceeds maximum length (4000)")
        if len(relevance_notes) > 4000:
            raise ValueError("relevance_notes exceeds maximum length (4000)")

        if key_contributions is not None:
            if not isinstance(key_contributions, list):
                raise ValueError("key_contributions must be a list of strings")
            for contribution in key_contributions:
                if not isinstance(contribution, str):
                    raise ValueError("key_contributions must be a list of strings")
                if len(contribution) > 300:
                    raise ValueError("Each key contribution exceeds maximum length (300)")

        if tags is not None:
            invalid_tags = [tag for tag in tags if tag not in ALLOWED_ANNOTATION_TAGS]
            if invalid_tags:
                raise ValueError(
                    f"Invalid tags: {', '.join(invalid_tags)}. Allowed tags: {', '.join(sorted(ALLOWED_ANNOTATION_TAGS))}"
                )

        if related_issues is not None:
            if any(not isinstance(issue, int) or issue <= 0 for issue in related_issues):
                raise ValueError("related_issues must contain positive integers")

    def add(
        self,
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
        Add a reference to the collection.

        Args:
            key: BibTeX citation key (e.g., "vaswani2017-attention")
            title: Paper title
            authors: List of author names
            year: Publication year
            doi: Digital Object Identifier
            venue: Publication venue
            url: Paper URL
            pdf_url: PDF download URL
            abstract: Paper abstract
            source: Source system ("arxiv", "manual", etc.)
            paper_type: Type ("conference", "journal", etc.)
            categories: Subject categories
            keywords: Search keywords

        Returns:
            Confirmation message with key.
        """
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

        write_paper_yaml(str(self.papers_dir), key, paper.to_yaml_dict())
        append_entry(str(self.bib_path), paper.bibtex)

        return f"Added reference: {key}"

    def list(
        self,
        filter_keyword: str = "",
        filter_tag: str = "",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        List references with optional filtering.

        Args:
            filter_keyword: Filter by keyword in title/abstract/keywords
            filter_tag: Filter by AI annotation tag
            limit: Maximum results to return

        Returns:
            List of reference summary dicts.
        """
        keys = list_paper_keys(str(self.papers_dir))

        keyword_query = filter_keyword.strip().lower()
        tag_query = filter_tag.strip().lower()

        results: list[dict[str, Any]] = []
        for key in keys:
            data = read_paper_yaml(str(self.papers_dir), key)
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

    def get(self, key: str) -> dict[str, Any]:
        """
        Get full details of a single reference.

        Args:
            key: BibTeX citation key

        Returns:
            Complete reference dict including ai_annotations.

        Raises:
            ValueError: If reference not found.
        """
        data = read_paper_yaml(str(self.papers_dir), key)
        if data is None:
            raise ValueError(f"Reference not found: {key}")
        return data

    def search(self, query: str) -> list[dict[str, Any]]:
        """
        Full-text search across all references.

        Args:
            query: Search query (matches title, authors, abstract, keywords)

        Returns:
            List of matching reference dicts.
        """
        normalized_query = query.strip().lower()
        if not normalized_query:
            return []

        matches: list[dict[str, Any]] = []
        for key in list_paper_keys(str(self.papers_dir)):
            data = read_paper_yaml(str(self.papers_dir), key)
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

    def remove(self, key: str, delete_pdf: bool = False) -> str:
        """
        Remove a reference from the collection.

        Args:
            key: BibTeX citation key
            delete_pdf: Also delete the PDF file if it exists

        Returns:
            Confirmation message.
        """
        paper_data = read_paper_yaml(str(self.papers_dir), key)
        yaml_removed = delete_paper_yaml(str(self.papers_dir), key)
        bib_removed = remove_entry(str(self.bib_path), key)

        pdf_removed = False
        if delete_pdf:
            candidate_paths: list[Path] = []
            if paper_data is not None and paper_data.get("pdf_path"):
                candidate_paths.append(Path(str(paper_data["pdf_path"])))
            candidate_paths.append(self.pdfs_dir / f"{key}.pdf")

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

    def annotate(
        self,
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

        Args:
            key: BibTeX citation key
            summary: Paper summary
            key_contributions: List of key contributions
            methodology: Methodology description
            relevance_notes: Relevance to current research
            tags: Categorization tags
            related_issues: Related GitHub issue numbers

        Returns:
            Confirmation message.
        """
        data = read_paper_yaml(str(self.papers_dir), key)
        if data is None:
            raise ValueError(f"Reference not found: {key}")

        self._validate_annotation_inputs(
            summary=summary,
            key_contributions=key_contributions,
            methodology=methodology,
            relevance_notes=relevance_notes,
            tags=tags,
            related_issues=related_issues,
        )

        paper = Paper.from_yaml_dict(data)
        if paper.ai_annotations is None:
            paper.ai_annotations = AiAnnotations()

        if summary:
            paper.ai_annotations.summary = summary
        if key_contributions is not None:
            paper.ai_annotations.key_contributions.extend(key_contributions)
        if methodology:
            paper.ai_annotations.methodology = methodology
        if relevance_notes:
            paper.ai_annotations.relevance_notes = relevance_notes
        if tags is not None:
            paper.ai_annotations.tags.extend(tags)
        if related_issues is not None:
            paper.ai_annotations.related_issues.extend(related_issues)

        paper.ai_annotations.added_date = date.today().isoformat()
        write_paper_yaml(str(self.papers_dir), key, paper.to_yaml_dict())

        return f"Updated annotations for: {key}"

    def get_all_keys(self) -> list[str]:
        """Get all reference keys in the collection."""
        return list_paper_keys(str(self.papers_dir))
