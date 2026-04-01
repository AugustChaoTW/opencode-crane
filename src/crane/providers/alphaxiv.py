from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests

from crane.providers.base import PaperProvider, UnifiedMetadata

ALPHAXIV_API_BASE = "https://api.alphaxiv.org"
ALPHAXIV_MAX_RETRIES = 3
ALPHAXIV_RETRY_DELAY = 2.0


@dataclass
class AlphaXivOverview:
    """Structured AI-generated paper overview from alphaXiv."""

    arxiv_id: str
    version_id: str
    title: str
    abstract: str
    overview: str
    summary: str
    citations_bibtex: str
    language: str = "en"
    source: str = "alphaxiv"

    def __post_init__(self) -> None:
        if not self.arxiv_id:
            raise ValueError("arxiv_id cannot be empty")

    def to_markdown(self) -> str:
        """Convert to clean markdown for downstream processing."""
        parts: list[str] = []
        parts.append(f"# {self.title}")
        parts.append("")
        parts.append("## Abstract")
        parts.append(self.abstract)
        parts.append("")
        if self.overview:
            parts.append("## Overview")
            parts.append(self.overview)
            parts.append("")
        if self.summary:
            parts.append("## Summary")
            parts.append(self.summary)
        return "\n".join(parts)


class AlphaXivProvider(PaperProvider):
    """Fetch structured paper summaries from alphaXiv API.

    API endpoints:
      GET /papers/v3/{arxiv_id} → metadata + versionId
      GET /papers/v3/{versionId}/overview/{lang} → structured overview
    """

    def __init__(self, auth_token: str | None = None):
        self._auth_token = auth_token
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})
        if auth_token:
            self._session.headers.update({"Authorization": f"Bearer {auth_token}"})

    @property
    def name(self) -> str:
        return "alphaxiv"

    def get_overview(self, arxiv_id: str, language: str = "en") -> AlphaXivOverview | None:
        """Fetch AI-generated structured overview for an arXiv paper.

        Returns None if paper not found or no overview available.
        Handles rate limiting with exponential backoff.
        """
        paper_data = self._resolve_paper(arxiv_id)
        if not paper_data:
            return None

        version_id = str(paper_data.get("versionId", ""))
        if not version_id:
            return None

        overview_data = self._fetch_overview(version_id, language)
        if not overview_data or not overview_data.get("overview"):
            return None

        return AlphaXivOverview(
            arxiv_id=arxiv_id,
            version_id=version_id,
            title=str(overview_data.get("title", paper_data.get("title", ""))),
            abstract=str(overview_data.get("abstract", paper_data.get("abstract", ""))),
            overview=str(overview_data.get("overview", "")),
            summary=str(overview_data.get("summary", "")),
            citations_bibtex=str(overview_data.get("citationBibtex", "")),
            language=language,
        )

    def _resolve_paper(self, arxiv_id: str) -> dict[str, Any] | None:
        """GET /papers/v3/{arxiv_id} → paper metadata."""
        url = f"{ALPHAXIV_API_BASE}/papers/v3/{arxiv_id}"
        return self._request_with_retry(url)

    def _fetch_overview(self, version_id: str, language: str) -> dict[str, Any] | None:
        """GET /papers/v3/{versionId}/overview/{language}."""
        url = f"{ALPHAXIV_API_BASE}/papers/v3/{version_id}/overview/{language}"
        return self._request_with_retry(url)

    def _request_with_retry(self, url: str) -> dict[str, Any] | None:
        """Make GET request with retry on 429/5xx."""
        for attempt in range(ALPHAXIV_MAX_RETRIES):
            try:
                response = self._session.get(url, timeout=30)
                if response.status_code == 200:
                    payload = response.json()
                    if isinstance(payload, dict):
                        return payload
                    return None
                if response.status_code == 404:
                    return None
                if response.status_code == 429:
                    delay = ALPHAXIV_RETRY_DELAY * (2**attempt)
                    time.sleep(delay)
                    continue
                if response.status_code >= 500:
                    time.sleep(ALPHAXIV_RETRY_DELAY)
                    continue
                return None
            except requests.RequestException:
                if attempt < ALPHAXIV_MAX_RETRIES - 1:
                    time.sleep(ALPHAXIV_RETRY_DELAY)
                    continue
                return None
        return None

    def search(self, query: str, max_results: int = 10) -> list[UnifiedMetadata]:
        return []

    def get_by_id(self, paper_id: str) -> UnifiedMetadata | None:
        paper_data = self._resolve_paper(paper_id)
        if not paper_data:
            return None

        published = str(paper_data.get("publishedDate", ""))
        year = 0
        if len(published) >= 4 and published[:4].isdigit():
            year = int(published[:4])

        authors_raw = paper_data.get("authors", [])
        authors: list[str] = []
        if isinstance(authors_raw, list):
            for item in authors_raw:
                if isinstance(item, str):
                    authors.append(item)
                elif isinstance(item, dict):
                    authors.append(str(item.get("name", "")))

        return UnifiedMetadata(
            title=str(paper_data.get("title", "")),
            authors=[author for author in authors if author],
            year=year,
            doi="",
            abstract=str(paper_data.get("abstract", "")),
            source="alphaxiv",
            source_id=paper_id,
            url=f"https://alphaxiv.org/abs/{paper_id}",
            pdf_url=f"https://arxiv.org/pdf/{paper_id}.pdf",
            citations=0,
            references=[],
        )

    def get_by_doi(self, doi: str) -> UnifiedMetadata | None:
        return None
