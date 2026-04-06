# pyright: reportMissingImports=false
"""Section-aware paper chunking for writing style analysis.

Extracts logical sections (Introduction, Methods, Results, etc.) from
LaTeX and PDF papers, producing :class:`Section` objects suitable for
per-section style metric computation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path

from crane.services.latex_parser import (
    SectionLocation,
    parse_latex_sections,
)

PyPDF2: object | None
try:
    PyPDF2 = import_module("PyPDF2")
except ModuleNotFoundError:  # pragma: no cover
    PyPDF2 = None

CANONICAL_SECTIONS: list[str] = [
    "Abstract",
    "Introduction",
    "Related Work",
    "Background",
    "Methods",
    "Methodology",
    "Experiments",
    "Results",
    "Discussion",
    "Conclusion",
    "Limitations",
    "Acknowledgements",
    "References",
]

_SECTION_ALIASES: dict[str, str] = {
    "literature review": "Related Work",
    "related works": "Related Work",
    "prior work": "Related Work",
    "method": "Methods",
    "methodology": "Methods",
    "proposed method": "Methods",
    "approach": "Methods",
    "experimental setup": "Experiments",
    "evaluation": "Experiments",
    "experimental results": "Results",
    "findings": "Results",
    "conclusions": "Conclusion",
    "concluding remarks": "Conclusion",
    "limitation": "Limitations",
    "threats to validity": "Limitations",
    "acknowledgement": "Acknowledgements",
    "acknowledgment": "Acknowledgements",
}

# Regex for detecting section-like headings in plain text (PDF fallback)
_PDF_HEADING_RE = re.compile(
    r"^(?:\d+\.?\s+)?"  # optional numbering: "1. " or "1 "
    r"([A-Z][A-Za-z\s&:,-]+)"  # heading text starting with uppercase
    r"\s*$",
    re.MULTILINE,
)


@dataclass
class Section:
    """A logical section extracted from an academic paper.

    Attributes:
        name: Display name (e.g. ``"Introduction"``).
        canonical_name: Normalised name from :data:`CANONICAL_SECTIONS`
            or the original name if no alias matches.
        level: Nesting depth (1=section, 2=subsection, 3=subsubsection).
        content: Raw text body of the section.
        page_range: ``(start_page, end_page)`` when available (PDF only).
        character_count: ``len(content)``.
        word_count: Number of whitespace-separated tokens.
        subsections: Child sections (populated for LaTeX sources).
    """

    name: str = ""
    canonical_name: str = ""
    level: int = 1
    content: str = ""
    page_range: tuple[int, int] = (0, 0)
    character_count: int = 0
    word_count: int = 0
    subsections: list[Section] = field(default_factory=list)


def _canonicalise(name: str) -> str:
    """Map a section heading to a canonical name."""
    lower = name.strip().lower()
    if lower in _SECTION_ALIASES:
        return _SECTION_ALIASES[lower]
    for canon in CANONICAL_SECTIONS:
        if canon.lower() == lower:
            return canon
    return name.strip()


def _section_from_location(loc: SectionLocation, source_paper: str = "") -> Section:
    """Convert an existing ``SectionLocation`` into a ``Section``."""
    content = loc.content or ""
    return Section(
        name=loc.name,
        canonical_name=_canonicalise(loc.name),
        level=loc.level,
        content=content,
        page_range=(0, 0),
        character_count=len(content),
        word_count=len(content.split()) if content else 0,
        subsections=[_section_from_location(sub, source_paper) for sub in (loc.subsections or [])],
    )


class SectionChunker:
    """Extract logical sections from LaTeX or PDF papers.

    Leverages :func:`crane.services.latex_parser.parse_latex_sections`
    for LaTeX files and falls back to heuristic heading detection for
    raw PDF text.
    """

    def chunk_latex_paper(self, paper_path: str | Path) -> list[Section]:
        """Parse a LaTeX file and return a list of :class:`Section` objects.

        Args:
            paper_path: Path to the ``.tex`` source file.

        Returns:
            Ordered list of top-level sections (with nested subsections).

        Raises:
            FileNotFoundError: If *paper_path* does not exist.
        """
        structure = parse_latex_sections(paper_path)
        sections: list[Section] = []

        if structure.abstract:
            sections.append(
                Section(
                    name="Abstract",
                    canonical_name="Abstract",
                    level=0,
                    content=structure.abstract,
                    character_count=len(structure.abstract),
                    word_count=len(structure.abstract.split()),
                )
            )

        for loc in structure.sections:
            sections.append(_section_from_location(loc))

        for loc in structure.appendices:
            sec = _section_from_location(loc)
            sec.canonical_name = f"Appendix: {sec.canonical_name}"
            sections.append(sec)

        return sections

    def chunk_pdf_paper(self, pdf_path: str | Path) -> list[Section]:
        """Extract sections from a PDF using heuristic heading detection.

        This is a best-effort fallback when LaTeX source is unavailable.
        It reads the full text via *PyPDF2* and splits on lines that
        look like section headings.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            List of detected sections (flat, no nesting).

        Raises:
            FileNotFoundError: If *pdf_path* does not exist.
            RuntimeError: If *PyPDF2* is not installed.
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        if PyPDF2 is None:
            raise RuntimeError("PyPDF2 is required for PDF section chunking")

        full_text, page_texts = self._extract_pdf_text(path)
        if not full_text.strip():
            return []

        return self._split_by_headings(full_text, page_texts)

    def chunk_text(self, text: str) -> list[Section]:
        """Split raw text into sections using heading heuristics.

        Useful when text has already been extracted externally.

        Args:
            text: Plain-text content of a paper.

        Returns:
            List of detected sections.
        """
        if not text.strip():
            return []
        return self._split_by_headings(text, [])

    @staticmethod
    def _extract_pdf_text(path: Path) -> tuple[str, list[tuple[int, str]]]:
        """Read all pages from *path* and return ``(full_text, [(page, text)])``.

        Requires *PyPDF2* to be available at runtime.
        """
        reader = PyPDF2.PdfReader(str(path))  # type: ignore[union-attr]
        page_texts: list[tuple[int, str]] = []
        parts: list[str] = []
        for idx, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            page_texts.append((idx, page_text))
            parts.append(page_text)
        return "\n".join(parts), page_texts

    @staticmethod
    def _find_page_for_offset(offset: int, page_texts: list[tuple[int, str]]) -> int:
        """Return the 1-based page number that contains *offset*."""
        cursor = 0
        for page_num, text in page_texts:
            end = cursor + len(text) + 1
            if offset < end:
                return page_num
            cursor = end
        return page_texts[-1][0] if page_texts else 0

    def _split_by_headings(self, text: str, page_texts: list[tuple[int, str]]) -> list[Section]:
        """Split *text* on heuristic heading patterns."""
        heading_positions: list[tuple[int, str]] = []
        for match in _PDF_HEADING_RE.finditer(text):
            candidate = match.group(1).strip()
            if len(candidate.split()) > 6:
                continue
            if _canonicalise(candidate) != candidate or candidate[0].isupper():
                heading_positions.append((match.start(), candidate))

        if not heading_positions:
            return [
                Section(
                    name="Body",
                    canonical_name="Body",
                    level=1,
                    content=text,
                    character_count=len(text),
                    word_count=len(text.split()),
                )
            ]

        sections: list[Section] = []

        pre = text[: heading_positions[0][0]].strip()
        if pre:
            sections.append(
                Section(
                    name="Preamble",
                    canonical_name="Preamble",
                    level=0,
                    content=pre,
                    character_count=len(pre),
                    word_count=len(pre.split()),
                )
            )

        for i, (pos, heading) in enumerate(heading_positions):
            end = heading_positions[i + 1][0] if i + 1 < len(heading_positions) else len(text)
            body = text[pos + len(heading) : end].strip()
            start_page = self._find_page_for_offset(pos, page_texts) if page_texts else 0
            end_page = self._find_page_for_offset(end - 1, page_texts) if page_texts else 0
            sections.append(
                Section(
                    name=heading,
                    canonical_name=_canonicalise(heading),
                    level=1,
                    content=body,
                    page_range=(start_page, end_page),
                    character_count=len(body),
                    word_count=len(body.split()) if body else 0,
                )
            )

        return sections
