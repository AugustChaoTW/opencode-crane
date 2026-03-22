"""Semantic Scholar provider for academic paper search."""

from __future__ import annotations

import os

import requests

from crane.providers.base import PaperProvider, UnifiedMetadata

SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1"


class SemanticScholarProvider(PaperProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")

    @property
    def name(self) -> str:
        return "semantic_scholar"

    def search(self, query: str, max_results: int = 10) -> list[UnifiedMetadata]:
        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,authors,year,abstract,externalIds,url,citationCount,references",
        }
        data = self._request("GET", "/paper/search", params=params)
        papers = data.get("data", [])
        return [self._parse_paper(paper) for paper in papers]

    def get_by_id(self, paper_id: str) -> UnifiedMetadata | None:
        try:
            data = self._request(
                "GET",
                f"/paper/{paper_id}",
                params={
                    "fields": "title,authors,year,abstract,externalIds,url,citationCount,references"
                },
            )
            return self._parse_paper(data)
        except Exception:
            return None

    def get_by_doi(self, doi: str) -> UnifiedMetadata | None:
        return self.get_by_id(f"DOI:{doi}")

    def get_recommendations(self, paper_id: str, limit: int = 10) -> list[UnifiedMetadata]:
        try:
            data = self._request(
                "POST",
                "/recommendations/v1/papers/forpaper",
                json={"positivePaperIds": [paper_id], "limit": limit},
            )
            papers = data.get("recommendedPapers", [])
            return [self._parse_paper(paper) for paper in papers]
        except Exception:
            return []

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{SEMANTIC_SCHOLAR_API_URL}{path}"
        headers = kwargs.pop("headers", {})
        if self.api_key:
            headers["x-api-key"] = self.api_key

        response = requests.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()

    def _parse_paper(self, paper: dict) -> UnifiedMetadata:
        source_id = paper.get("paperId", "")
        title = paper.get("title", "") or ""
        abstract = paper.get("abstract", "") or ""
        year = paper.get("year", 0) or 0
        citations = paper.get("citationCount", 0) or 0
        url = paper.get("url", "") or f"https://www.semanticscholar.org/paper/{source_id}"

        external_ids = paper.get("externalIds", {}) or {}
        doi = external_ids.get("DOI", "") or ""

        authors = []
        for author in paper.get("authors", []) or []:
            if author.get("name"):
                authors.append(author["name"])

        references = []
        for ref in paper.get("references", [])[:10] or []:
            if ref and ref.get("paperId"):
                references.append(ref["paperId"])

        pdf_url = ""
        open_access = paper.get("openAccessPdf")
        if open_access and isinstance(open_access, dict):
            pdf_url = open_access.get("url", "") or ""

        return UnifiedMetadata(
            title=title,
            authors=authors,
            year=year,
            doi=doi,
            abstract=abstract,
            source=self.name,
            source_id=source_id,
            url=url,
            pdf_url=pdf_url,
            citations=citations,
            references=references,
        )
