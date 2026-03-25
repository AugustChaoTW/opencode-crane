"""Crossref provider for academic paper DOI resolution."""

from __future__ import annotations

import requests

from crane.providers.base import PaperProvider, UnifiedMetadata

CROSSREF_API_URL = "https://api.crossref.org/works"
CROSSREF_EMAIL = "opencode-crane@example.com"


class CrossrefProvider(PaperProvider):
    @property
    def name(self) -> str:
        return "crossref"

    def search(self, query: str, max_results: int = 10) -> list[UnifiedMetadata]:
        params = {
            "query": query,
            "rows": max_results,
            "mailto": CROSSREF_EMAIL,
        }
        response = requests.get(CROSSREF_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        items = data.get("message", {}).get("items", [])
        return [self._parse_work(item) for item in items]

    def get_by_id(self, paper_id: str) -> UnifiedMetadata | None:
        if paper_id.startswith("10."):
            return self.get_by_doi(paper_id)
        return None

    def get_by_doi(self, doi: str) -> UnifiedMetadata | None:
        url = f"{CROSSREF_API_URL}/{doi}"
        try:
            response = requests.get(url, params={"mailto": CROSSREF_EMAIL})
            response.raise_for_status()
            data = response.json()
            return self._parse_work(data.get("message", {}))
        except Exception:
            return None

    def _parse_work(self, work: dict) -> UnifiedMetadata:
        doi = work.get("DOI", "")
        title_list = work.get("title", [])
        title = title_list[0] if title_list else ""

        authors = []
        for author in work.get("author", []):
            name = f"{author.get('given', '')} {author.get('family', '')}".strip()
            if name:
                authors.append(name)

        year = 0
        date_parts = work.get("published-print", {}).get("date-parts", [[]])
        if date_parts and date_parts[0]:
            year = date_parts[0][0]
        if not year:
            date_parts = work.get("published-online", {}).get("date-parts", [[]])
            if date_parts and date_parts[0]:
                year = date_parts[0][0]
        if not year:
            date_parts = work.get("created", {}).get("date-parts", [[]])
            if date_parts and date_parts[0]:
                year = date_parts[0][0]

        abstract = work.get("abstract", "") or ""
        abstract = abstract.replace("<jats:p>", "").replace("</jats:p>", "")
        abstract = abstract.replace("<jats:italic>", "").replace("</jats:italic>", "")

        container = work.get("container-title", [])
        _venue = container[0] if container else ""

        citations = work.get("is-referenced-by-count", 0) or 0

        references = []
        for ref in work.get("reference", [])[:10]:
            if ref.get("DOI"):
                references.append(ref["DOI"])

        url_str = ""
        links = work.get("link", [])
        for link in links:
            if link.get("content-type") == "application/pdf":
                url_str = link.get("URL", "")
                break

        return UnifiedMetadata(
            title=title,
            authors=authors,
            year=year,
            doi=doi,
            abstract=abstract,
            source=self.name,
            source_id=doi,
            url=f"https://doi.org/{doi}" if doi else "",
            pdf_url=url_str,
            citations=citations,
            references=references,
        )
