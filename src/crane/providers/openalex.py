"""OpenAlex provider for academic paper search."""

from __future__ import annotations

import requests

from crane.providers.base import PaperProvider, UnifiedMetadata

OPENALEX_API_URL = "https://api.openalex.org/works"
OPENALEX_EMAIL = "opencode-crane@example.com"


class OpenAlexProvider(PaperProvider):
    @property
    def name(self) -> str:
        return "openalex"

    def search(self, query: str, max_results: int = 10) -> list[UnifiedMetadata]:
        params = {
            "search": query,
            "per_page": max_results,
            "mailto": OPENALEX_EMAIL,
        }
        data = self._fetch_works(params)
        return [self._parse_work(work) for work in data]

    def get_by_id(self, paper_id: str) -> UnifiedMetadata | None:
        if paper_id.startswith("W"):
            url = f"{OPENALEX_API_URL}/{paper_id}"
        else:
            url = f"{OPENALEX_API_URL}/W{paper_id}"

        try:
            response = requests.get(url, params={"mailto": OPENALEX_EMAIL})
            response.raise_for_status()
            return self._parse_work(response.json())
        except Exception:
            return None

    def get_by_doi(self, doi: str) -> UnifiedMetadata | None:
        url = f"{OPENALEX_API_URL}/doi:{doi}"
        try:
            response = requests.get(url, params={"mailto": OPENALEX_EMAIL})
            response.raise_for_status()
            return self._parse_work(response.json())
        except Exception:
            return None

    def _fetch_works(self, params: dict) -> list[dict]:
        response = requests.get(OPENALEX_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])

    def _parse_work(self, work: dict) -> UnifiedMetadata:
        source_id = work.get("id", "").replace("https://openalex.org/", "")
        title = work.get("title", "") or ""
        doi = work.get("doi", "") or ""
        if doi.startswith("https://doi.org/"):
            doi = doi.replace("https://doi.org/", "")

        authors = []
        for authorship in work.get("authorships", []):
            author = authorship.get("author", {})
            if author.get("display_name"):
                authors.append(author["display_name"])

        year = work.get("publication_year", 0) or 0
        abstract = self._reconstruct_abstract(work.get("abstract_inverted_index"))
        citations = work.get("cited_by_count", 0) or 0

        references = []
        for ref in work.get("referenced_works", [])[:10]:
            ref_id = ref.replace("https://openalex.org/", "")
            references.append(ref_id)

        pdf_url = ""
        for location in work.get("open_access", {}).get("oa_url", "") or []:
            if location and (location.endswith(".pdf") or "pdf" in location.lower()):
                pdf_url = location
                break

        return UnifiedMetadata(
            title=title,
            authors=authors,
            year=year,
            doi=doi,
            abstract=abstract,
            source=self.name,
            source_id=source_id,
            url=f"https://openalex.org/{source_id}",
            pdf_url=pdf_url,
            citations=citations,
            references=references,
        )

    def _reconstruct_abstract(self, inverted_index: dict | None) -> str:
        if not inverted_index:
            return ""

        words = []
        for word, positions in inverted_index.items():
            for pos in positions:
                words.append((pos, word))

        words.sort()
        return " ".join(word for _, word in words)
