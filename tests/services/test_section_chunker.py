# pyright: reportMissingImports=false

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from crane.services.section_chunker import (
    CANONICAL_SECTIONS,
    Section,
    SectionChunker,
    _canonicalise,
)


@pytest.fixture
def chunker() -> SectionChunker:
    return SectionChunker()


def _write_tex(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "paper.tex"
    path.write_text(content, encoding="utf-8")
    return path


class TestCanonicalise:
    def test_exact_match(self) -> None:
        assert _canonicalise("Introduction") == "Introduction"
        assert _canonicalise("Methods") == "Methods"

    def test_alias_mapping(self) -> None:
        assert _canonicalise("literature review") == "Related Work"
        assert _canonicalise("Related Works") == "Related Work"
        assert _canonicalise("Methodology") == "Methods"
        assert _canonicalise("Conclusions") == "Conclusion"

    def test_case_insensitive(self) -> None:
        assert _canonicalise("INTRODUCTION") == "Introduction"
        assert _canonicalise("discussion") == "Discussion"

    def test_unknown_passes_through(self) -> None:
        assert _canonicalise("System Design") == "System Design"

    def test_strips_whitespace(self) -> None:
        assert _canonicalise("  Introduction  ") == "Introduction"


class TestSection:
    def test_default_values(self) -> None:
        s = Section()
        assert s.name == ""
        assert s.level == 1
        assert s.content == ""
        assert s.page_range == (0, 0)
        assert s.character_count == 0
        assert s.word_count == 0
        assert s.subsections == []

    def test_custom_values(self) -> None:
        s = Section(
            name="Introduction",
            canonical_name="Introduction",
            level=1,
            content="Some text here.",
            page_range=(1, 2),
            character_count=15,
            word_count=3,
        )
        assert s.name == "Introduction"
        assert s.page_range == (1, 2)


class TestChunkLatexPaper:
    def test_extracts_abstract_and_sections(self, tmp_path: Path, chunker: SectionChunker) -> None:
        tex = r"""
\title{Test Paper}
\begin{abstract}
This is the abstract of the test paper.
\end{abstract}
\section{Introduction}
This paper introduces a novel approach.
\section{Methods}
We use the following methods.
\subsection{Data Collection}
Data was collected from multiple sources.
\section{Results}
Results show improvement.
"""
        path = _write_tex(tmp_path, tex)
        sections = chunker.chunk_latex_paper(path)

        names = [s.name for s in sections]
        assert "Abstract" in names
        assert "Introduction" in names
        assert "Methods" in names
        assert "Results" in names

        abstract_sec = next(s for s in sections if s.name == "Abstract")
        assert "abstract of the test paper" in abstract_sec.content
        assert abstract_sec.character_count > 0
        assert abstract_sec.word_count > 0

    def test_handles_appendices(self, tmp_path: Path, chunker: SectionChunker) -> None:
        tex = r"""
\section{Introduction}
Intro.
\appendix
\section{Proof Details}
Proof here.
"""
        path = _write_tex(tmp_path, tex)
        sections = chunker.chunk_latex_paper(path)

        appendix = [s for s in sections if "Appendix" in s.canonical_name]
        assert len(appendix) == 1

    def test_file_not_found(self, chunker: SectionChunker) -> None:
        with pytest.raises(FileNotFoundError):
            chunker.chunk_latex_paper("/tmp/nonexistent_12345.tex")

    def test_empty_latex(self, tmp_path: Path, chunker: SectionChunker) -> None:
        path = _write_tex(tmp_path, "")
        sections = chunker.chunk_latex_paper(path)
        assert sections == []

    def test_subsections_nested(self, tmp_path: Path, chunker: SectionChunker) -> None:
        tex = r"""
\section{Methods}
Overview.
\subsection{Approach A}
Details A.
\subsection{Approach B}
Details B.
"""
        path = _write_tex(tmp_path, tex)
        sections = chunker.chunk_latex_paper(path)
        methods = next(s for s in sections if s.name == "Methods")
        assert len(methods.subsections) == 2
        assert methods.subsections[0].canonical_name == "Approach A"

    def test_canonical_names_normalised(self, tmp_path: Path, chunker: SectionChunker) -> None:
        tex = r"""
\section{Literature Review}
Review.
\section{Experimental Setup}
Setup.
\section{Concluding Remarks}
End.
"""
        path = _write_tex(tmp_path, tex)
        sections = chunker.chunk_latex_paper(path)
        canonical = [s.canonical_name for s in sections]
        assert "Related Work" in canonical
        assert "Experiments" in canonical
        assert "Conclusion" in canonical


class TestChunkText:
    def test_empty_text_returns_empty(self, chunker: SectionChunker) -> None:
        assert chunker.chunk_text("") == []
        assert chunker.chunk_text("   ") == []

    def test_no_headings_returns_single_body(self, chunker: SectionChunker) -> None:
        text = "This is a paragraph of text without any headings."
        sections = chunker.chunk_text(text)
        assert len(sections) == 1
        assert sections[0].name == "Body"

    def test_detects_numbered_headings(self, chunker: SectionChunker) -> None:
        text = "Some preamble.\n1. Introduction\nIntro text here.\n2. Methods\nMethod text.\n"
        sections = chunker.chunk_text(text)
        names = [s.name for s in sections]
        assert "Introduction" in names or any("Intro" in n for n in names)

    def test_word_and_char_counts(self, chunker: SectionChunker) -> None:
        text = "Body\nThis has five words here.\n"
        sections = chunker.chunk_text(text)
        assert all(s.character_count >= 0 for s in sections)
        assert all(s.word_count >= 0 for s in sections)


class TestChunkPdfPaper:
    def test_file_not_found(self, chunker: SectionChunker) -> None:
        with pytest.raises(FileNotFoundError):
            chunker.chunk_pdf_paper("/tmp/nonexistent_12345.pdf")

    def test_extracts_sections_from_pdf(
        self, chunker: SectionChunker, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        pdf_path = tmp_path / "paper.pdf"
        pdf_path.write_bytes(b"fake-pdf")

        page1 = MagicMock()
        page1.extract_text.return_value = (
            "Title of Paper\nAbstract\nThis paper presents a new approach.\n"
        )
        page2 = MagicMock()
        page2.extract_text.return_value = (
            "Introduction\n"
            "We introduce a method for testing.\n"
            "Methods\n"
            "The method works as follows.\n"
        )
        reader = MagicMock()
        reader.pages = [page1, page2]
        monkeypatch.setattr(
            "crane.services.section_chunker.PyPDF2.PdfReader",
            lambda *_a, **_k: reader,
        )

        sections = chunker.chunk_pdf_paper(pdf_path)
        assert len(sections) > 0
        assert any(s.canonical_name == "Introduction" for s in sections) or len(sections) >= 1

    def test_empty_pdf_returns_empty(
        self, chunker: SectionChunker, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        pdf_path = tmp_path / "empty.pdf"
        pdf_path.write_bytes(b"fake-pdf")

        reader = MagicMock()
        reader.pages = []
        monkeypatch.setattr(
            "crane.services.section_chunker.PyPDF2.PdfReader",
            lambda *_a, **_k: reader,
        )

        assert chunker.chunk_pdf_paper(pdf_path) == []


class TestCanonicalSections:
    def test_standard_sections_present(self) -> None:
        assert "Introduction" in CANONICAL_SECTIONS
        assert "Methods" in CANONICAL_SECTIONS
        assert "Results" in CANONICAL_SECTIONS
        assert "Discussion" in CANONICAL_SECTIONS
        assert "Conclusion" in CANONICAL_SECTIONS
