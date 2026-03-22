"""
Paper search, download, and read service.
Core business logic for arXiv paper operations, independent of MCP layer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import feedparser  # pyright: ignore[reportMissingImports]
import PyPDF2  # pyright: ignore[reportMissingImports]
import requests

ARXIV_API_URL = "http://export.arxiv.org/api/query"


class PaperService:
    """Service for paper search, download, and text extraction."""

    def search(
        self,
        query: str,
        max_results: int = 10,
        source: str = "arxiv",
    ) -> list[dict[str, Any]]:
        """
        Search academic papers from supported sources.

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            source: Paper source ("arxiv" supported, others planned)

        Returns:
            List of paper dicts with title, authors, abstract, doi, url,
            pdf_url, published_date, categories, paper_id.
        """
        if source != "arxiv":
            raise ValueError(f"Unsupported source: {source}")

        params = {
            "search_query": query,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        response = requests.get(ARXIV_API_URL, params=params)
        response.raise_for_status()

        feed = feedparser.parse(response.content)
        entries = cast(list[dict[str, Any]], feed.get("entries", []))
        results: list[dict[str, Any]] = []

        for entry in entries:
            entry_id = str(entry.get("id", "")).split("/")[-1]
            links = cast(list[dict[str, Any]], entry.get("links", []))
            authors = cast(list[dict[str, Any]], entry.get("authors", []))
            tags = cast(list[dict[str, Any]], entry.get("tags", []))
            pdf_url = next(
                (
                    str(link.get("href", ""))
                    for link in links
                    if link.get("type") == "application/pdf"
                ),
                "",
            )
            results.append(
                {
                    "title": str(entry.get("title", "")).replace("\n", " ").strip(),
                    "authors": [str(author.get("name", "")) for author in authors],
                    "abstract": str(entry.get("summary", "")).replace("\n", " ").strip(),
                    "doi": entry.get("doi", f"arxiv:{entry_id}"),
                    "url": str(entry.get("id", "")),
                    "pdf_url": pdf_url,
                    "published_date": str(entry.get("published", "")).split("T")[0],
                    "categories": [str(tag.get("term", "")) for tag in tags],
                    "paper_id": entry_id,
                }
            )

        return results

    def download(
        self,
        paper_id: str,
        save_dir: str | Path = "references/pdfs",
    ) -> Path:
        """
        Download paper PDF to specified directory.

        Args:
            paper_id: arXiv paper ID (e.g., "2301.00001")
            save_dir: Directory to save PDF

        Returns:
            Path to downloaded PDF file.
        """
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)

        pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"
        output_path = save_path / f"{paper_id}.pdf"

        response = requests.get(pdf_url)
        response.raise_for_status()
        output_path.write_bytes(response.content)

        return output_path

    def read(
        self,
        paper_id: str,
        save_dir: str | Path = "references/pdfs",
    ) -> str:
        """
        Read paper PDF and extract full text.
        Auto-downloads if PDF doesn't exist locally.

        Args:
            paper_id: arXiv paper ID
            save_dir: Directory containing PDFs

        Returns:
            Plain text content extracted from PDF.
        """
        pdf_path = Path(save_dir) / f"{paper_id}.pdf"
        if not pdf_path.exists():
            pdf_path = self.download(paper_id, save_dir)

        reader = PyPDF2.PdfReader(str(pdf_path))
        extracted_pages = [(page.extract_text() or "") for page in reader.pages]
        return "\n".join(extracted_pages).strip()
