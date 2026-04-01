"""
Paper data model for CRANE.

Redesigned from gscientist/references/paper.py:
- Removed SQLite serialization (to_dict/from_dict for DB)
- Added YAML serialization (to_yaml/from_yaml)
- Added BibTeX generation (to_bibtex)
- Added ai_annotations dataclass
"""

from dataclasses import dataclass, field
from enum import Enum


class AnnotationTag(str, Enum):
    TRANSFORMER = "transformer"
    NLP = "nlp"
    LLM = "llm"
    FOUNDATIONAL = "foundational"
    ARCHITECTURE = "architecture"
    THEORY = "theory"
    EMPIRICAL = "empirical"
    METHOD = "method"
    SOFTWARE = "software"
    DATASET = "dataset"


ALLOWED_ANNOTATION_TAGS = {tag.value for tag in AnnotationTag}


class ContributionType(str, Enum):
    THEORY = "theory"
    EMPIRICAL = "empirical"
    METHOD = "method"
    SOFTWARE = "software"
    DATASET = "dataset"


@dataclass
class AiAnnotations:
    """AI-generated annotations for a paper."""

    summary: str = ""
    key_contributions: list[str] = field(default_factory=list)
    contribution_types: list[str] = field(default_factory=list)
    methodology: str = ""
    relevance_notes: str = ""
    tags: list[str] = field(default_factory=list)
    related_issues: list[int] = field(default_factory=list)
    added_date: str | None = None


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
    ai_annotations: AiAnnotations | None = None

    # Citation relationships
    cited_by: list[str] = field(default_factory=list)
    cites: list[str] = field(default_factory=list)

    # Embedded BibTeX
    bibtex: str = ""

    def __post_init__(self):
        if not self.key:
            raise ValueError("key cannot be empty")
        if not self.title:
            raise ValueError("title cannot be empty")

    def to_yaml_dict(self) -> dict:
        """Serialize to a dict suitable for YAML output."""
        data = {
            "key": self.key,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "doi": self.doi,
            "url": self.url,
            "pdf_url": self.pdf_url,
            "pdf_path": self.pdf_path,
            "abstract": self.abstract,
            "venue": self.venue,
            "source": self.source,
            "paper_type": self.paper_type,
            "categories": self.categories,
            "keywords": self.keywords,
            "publication": self.publication,
            "publisher": self.publisher,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
            "cited_by": self.cited_by,
            "cites": self.cites,
            "bibtex": self.bibtex,
        }

        if self.ai_annotations is not None:
            data["ai_annotations"] = {
                "summary": self.ai_annotations.summary,
                "key_contributions": self.ai_annotations.key_contributions,
                "contribution_types": self.ai_annotations.contribution_types,
                "methodology": self.ai_annotations.methodology,
                "relevance_notes": self.ai_annotations.relevance_notes,
                "tags": self.ai_annotations.tags,
                "related_issues": self.ai_annotations.related_issues,
                "added_date": self.ai_annotations.added_date,
            }

        return data

    @classmethod
    def from_yaml_dict(cls, data: dict) -> "Paper":
        """Create a Paper from a YAML-loaded dict."""
        raw_annotations = data.get("ai_annotations")
        ai_annotations = None
        if isinstance(raw_annotations, AiAnnotations):
            ai_annotations = raw_annotations
        elif isinstance(raw_annotations, dict):
            ai_annotations = AiAnnotations(**raw_annotations)

        return cls(
            key=data["key"],
            title=data["title"],
            authors=data["authors"],
            year=data["year"],
            doi=data.get("doi", ""),
            url=data.get("url", ""),
            pdf_url=data.get("pdf_url", ""),
            pdf_path=data.get("pdf_path", ""),
            abstract=data.get("abstract", ""),
            venue=data.get("venue", ""),
            source=data.get("source", "manual"),
            paper_type=data.get("paper_type", "unknown"),
            categories=data.get("categories", []),
            keywords=data.get("keywords", []),
            publication=data.get("publication", ""),
            publisher=data.get("publisher", ""),
            volume=data.get("volume", ""),
            issue=data.get("issue", ""),
            ai_annotations=ai_annotations,
            cited_by=data.get("cited_by", []),
            cites=data.get("cites", []),
            bibtex=data.get("bibtex", ""),
        )

    def to_bibtex(self) -> str:
        """Generate a BibTeX entry string."""
        paper_type_map = {
            "conference": "inproceedings",
            "journal": "article",
        }
        entry_type = paper_type_map.get(self.paper_type, "misc")

        lines = [f"@{entry_type}{{{self.key},"]
        lines.append(f"  title={{{self.title}}},")
        lines.append(f"  author={{{' and '.join(self.authors)}}},")

        if entry_type == "inproceedings":
            lines.append(f"  booktitle={{{self.venue}}},")
        elif entry_type == "article":
            lines.append(f"  journal={{{self.venue}}},")

        lines.append(f"  year={{{self.year}}}")

        if self.doi:
            lines[-1] = f"{lines[-1]},"
            lines.append(f"  doi={{{self.doi}}}")

        lines.append("}")
        return "\n".join(lines)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Paper):
            return NotImplemented
        return self.key == other.key

    def __hash__(self) -> int:
        return hash(self.key)

    def __str__(self) -> str:
        authors_str = ", ".join(self.authors) if self.authors else "No authors"
        return f"{authors_str} ({self.year}). {self.title}. [{self.key}]"
