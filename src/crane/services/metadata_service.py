"""Metadata normalization and deduplication service."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from crane.providers.base import UnifiedMetadata


@dataclass
class NormalizedMetadata:
    """Standardized metadata format with provenance tracking."""

    title: str
    authors: list[str]
    year: int
    doi: str
    abstract: str
    sources: list[str] = field(default_factory=list)
    source_ids: dict[str, str] = field(default_factory=dict)
    urls: dict[str, str] = field(default_factory=dict)
    pdf_urls: list[str] = field(default_factory=list)
    citations: dict[str, int] = field(default_factory=dict)
    references: list[str] = field(default_factory=list)

    @property
    def primary_source(self) -> str:
        if not self.sources:
            return ""
        priority = ["semantic_scholar", "openalex", "arxiv"]
        for source in priority:
            if source in self.sources:
                return source
        return self.sources[0]

    @property
    def max_citations(self) -> int:
        if not self.citations:
            return 0
        return max(self.citations.values())


class MetadataNormalizer:
    """Normalize and deduplicate metadata from multiple sources."""

    TITLE_SIMILARITY_THRESHOLD = 0.85
    AUTHOR_SIMILARITY_THRESHOLD = 0.8

    def normalize(self, metadata_list: list[UnifiedMetadata]) -> list[NormalizedMetadata]:
        """Normalize a list of metadata from different sources."""
        if not metadata_list:
            return []

        normalized = [self._to_normalized(m) for m in metadata_list]
        return self._deduplicate(normalized)

    def _to_normalized(self, metadata: UnifiedMetadata) -> NormalizedMetadata:
        """Convert UnifiedMetadata to NormalizedMetadata."""
        return NormalizedMetadata(
            title=self._normalize_title(metadata.title),
            authors=[self._normalize_author(a) for a in metadata.authors],
            year=metadata.year,
            doi=self._normalize_doi(metadata.doi),
            abstract=metadata.abstract,
            sources=[metadata.source],
            source_ids={metadata.source: metadata.source_id},
            urls={metadata.source: metadata.url},
            pdf_urls=[metadata.pdf_url] if metadata.pdf_url else [],
            citations={metadata.source: metadata.citations},
            references=metadata.references,
        )

    def _deduplicate(self, items: list[NormalizedMetadata]) -> list[NormalizedMetadata]:
        """Deduplicate normalized metadata by DOI and title similarity."""
        if not items:
            return []

        groups: list[list[NormalizedMetadata]] = []

        for item in items:
            matched_group = None

            for group in groups:
                if self._is_duplicate(item, group[0]):
                    matched_group = group
                    break

            if matched_group:
                matched_group.append(item)
            else:
                groups.append([item])

        return [self._merge_group(group) for group in groups]

    def _is_duplicate(self, a: NormalizedMetadata, b: NormalizedMetadata) -> bool:
        """Check if two metadata items are duplicates."""
        if a.doi and b.doi and a.doi == b.doi:
            return True

        if a.title and b.title:
            similarity = self._title_similarity(a.title, b.title)
            if similarity >= self.TITLE_SIMILARITY_THRESHOLD:
                if a.year and b.year and a.year != b.year:
                    return False
                return True

        return False

    def _merge_group(self, group: list[NormalizedMetadata]) -> NormalizedMetadata:
        """Merge a group of duplicate metadata into a single normalized item."""
        if len(group) == 1:
            return group[0]

        base = group[0]
        for item in group[1:]:
            base.sources.extend(item.sources)
            base.source_ids.update(item.source_ids)
            base.urls.update(item.urls)
            base.pdf_urls.extend(item.pdf_urls)
            base.citations.update(item.citations)

            if not base.abstract and item.abstract:
                base.abstract = item.abstract

            if not base.doi and item.doi:
                base.doi = item.doi

            existing_authors = set(a.lower() for a in base.authors)
            for author in item.authors:
                if author.lower() not in existing_authors:
                    base.authors.append(author)
                    existing_authors.add(author.lower())

            base.references = list(set(base.references + item.references))

        base.sources = list(set(base.sources))
        base.pdf_urls = list(set(base.pdf_urls))

        return base

    def _normalize_title(self, title: str) -> str:
        title = title.strip()
        title = re.sub(r"\s+", " ", title)
        return title

    def _normalize_author(self, author: str) -> str:
        return author.strip()

    def _normalize_doi(self, doi: str) -> str:
        if not doi:
            return ""
        doi = doi.strip()
        doi = re.sub(r"^https?://doi\.org/", "", doi)
        doi = re.sub(r"^doi:", "", doi, flags=re.IGNORECASE)
        return doi

    def _title_similarity(self, a: str, b: str) -> float:
        a_normalized = re.sub(r"[^\w\s]", "", a.lower())
        b_normalized = re.sub(r"[^\w\s]", "", b.lower())
        return SequenceMatcher(None, a_normalized, b_normalized).ratio()
