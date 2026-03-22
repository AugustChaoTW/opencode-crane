from __future__ import annotations

from typing import Any, cast

import feedparser  # pyright: ignore[reportMissingImports]
import requests

from crane.providers.base import PaperProvider, UnifiedMetadata

ARXIV_API_URL = "http://export.arxiv.org/api/query"


class ArxivProvider(PaperProvider):
    @property
    def name(self) -> str:
        return "arxiv"

    def search(self, query: str, max_results: int = 10) -> list[UnifiedMetadata]:
        params = {
            "search_query": query,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        entries = self._fetch_entries(params)
        return [self._parse_entry(entry) for entry in entries]

    def get_by_id(self, paper_id: str) -> UnifiedMetadata | None:
        entries = self._fetch_entries({"id_list": paper_id})
        if not entries:
            return None
        return self._parse_entry(entries[0])

    def get_by_doi(self, doi: str) -> UnifiedMetadata | None:
        if doi.startswith("arxiv:"):
            return self.get_by_id(doi.removeprefix("arxiv:"))

        entries = self._fetch_entries({"search_query": f'doi:"{doi}"', "max_results": 1})
        if not entries:
            return None
        return self._parse_entry(entries[0])

    def _fetch_entries(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        response = requests.get(ARXIV_API_URL, params=params)
        response.raise_for_status()

        feed = feedparser.parse(response.content)
        return cast(list[dict[str, Any]], feed.get("entries", []))

    def _parse_entry(self, entry: dict[str, Any]) -> UnifiedMetadata:
        source_id = str(entry.get("id", "")).split("/")[-1]
        links = cast(list[dict[str, Any]], entry.get("links", []))
        authors = cast(list[dict[str, Any]], entry.get("authors", []))
        published = str(entry.get("published", ""))
        year = self._parse_year(published)
        pdf_url = next(
            (str(link.get("href", "")) for link in links if link.get("type") == "application/pdf"),
            "",
        )

        return UnifiedMetadata(
            title=str(entry.get("title", "")).replace("\n", " ").strip(),
            authors=[str(author.get("name", "")) for author in authors],
            year=year,
            doi=str(entry.get("doi") or entry.get("arxiv_doi") or f"arxiv:{source_id}"),
            abstract=str(entry.get("summary", "")).replace("\n", " ").strip(),
            source=self.name,
            source_id=source_id,
            url=str(entry.get("id", "")),
            pdf_url=pdf_url,
            citations=0,
            references=[],
        )

    def _parse_year(self, published: str) -> int:
        year_text = published.split("-", maxsplit=1)[0]
        if year_text.isdigit():
            return int(year_text)
        return 0
