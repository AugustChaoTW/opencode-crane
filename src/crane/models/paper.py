"""
Paper data model for CRANE.

Redesigned from gscientist/references/paper.py:
- Removed SQLite serialization (to_dict/from_dict for DB)
- Added YAML serialization (to_yaml/from_yaml)
- Added BibTeX generation (to_bibtex)
- Added ai_annotations dataclass
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class AiAnnotations:
    """AI-generated annotations for a paper."""

    summary: str = ""
    key_contributions: list[str] = field(default_factory=list)
    methodology: str = ""
    relevance_notes: str = ""
    tags: list[str] = field(default_factory=list)
    related_issues: list[int] = field(default_factory=list)
    added_date: Optional[str] = None


@dataclass
class Paper:
    """Academic paper metadata."""

    key: str
    title: str
    authors: list[str]
    year: int

    # Identifiers and links
    doi: str = ""
    url: str = ""
    pdf_url: str = ""
    pdf_path: str = ""

    # Content
    abstract: str = ""
    venue: str = ""
    source: str = "manual"
    paper_type: str = "unknown"
    categories: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)

    # Optional bibliographic fields
    publication: str = ""
    publisher: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""

    # AI annotations
    ai_annotations: Optional[AiAnnotations] = None

    # Embedded BibTeX
    bibtex: str = ""

    def __post_init__(self):
        if not self.key:
            raise ValueError("key cannot be empty")
        if not self.title:
            raise ValueError("title cannot be empty")

    def to_yaml_dict(self) -> dict:
        """Serialize to a dict suitable for YAML output."""
        raise NotImplementedError

    @classmethod
    def from_yaml_dict(cls, data: dict) -> "Paper":
        """Create a Paper from a YAML-loaded dict."""
        raise NotImplementedError

    def to_bibtex(self) -> str:
        """Generate a BibTeX entry string."""
        raise NotImplementedError

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Paper):
            return NotImplemented
        return self.key == other.key

    def __hash__(self) -> int:
        return hash(self.key)

    def __str__(self) -> str:
        authors_str = ", ".join(self.authors) if self.authors else "No authors"
        return f"{authors_str} ({self.year}). {self.title}. [{self.key}]"
