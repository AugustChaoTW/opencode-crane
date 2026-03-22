from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class UnifiedMetadata:
    title: str
    authors: list[str]
    year: int
    doi: str
    abstract: str
    source: str
    source_id: str
    url: str
    pdf_url: str
    citations: int
    references: list[str]


class PaperProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> list[UnifiedMetadata]:
        pass

    @abstractmethod
    def get_by_id(self, paper_id: str) -> UnifiedMetadata | None:
        pass

    @abstractmethod
    def get_by_doi(self, doi: str) -> UnifiedMetadata | None:
        pass
