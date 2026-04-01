# pyright: reportMissingImports=false

from __future__ import annotations

from pathlib import Path

import pytest

from crane.services.latex_parser import (
    _build_hierarchy,
    get_all_sections_flat,
    get_section_text,
    parse_latex_sections,
)


def _write_tex(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_parse_latex_sections_file_not_found() -> None:
    with pytest.raises(FileNotFoundError, match="LaTeX file not found"):
        parse_latex_sections("/tmp/does-not-exist-12345.tex")


def test_parse_latex_sections_extracts_title_abstract_sections(tmp_path: Path) -> None:
    tex = r"""
\title{Great Paper}
\begin{abstract}
This is the abstract.
\end{abstract}
\section{Intro}
Intro text.
\subsection{Background}
Background text.
\section{Method}
Method text.
\appendix
\section{Extra}
Appendix text.
"""
    path = _write_tex(tmp_path / "paper.tex", tex)

    result = parse_latex_sections(path)

    assert result.title == "Great Paper"
    assert result.abstract == "This is the abstract."
    assert len(result.sections) == 2
    assert result.sections[0].name == "Intro"
    assert len(result.sections[0].subsections) == 1
    assert result.sections[0].subsections[0].name == "Background"
    assert len(result.appendices) == 1
    assert result.appendices[0].name == "Extra"


@pytest.mark.parametrize(
    ("content", "title", "abstract"),
    [
        (r"\section{A}\nBody", "", ""),
        (r"\title{Only Title}\n\section{A}\nBody", "Only Title", ""),
        (
            r"\begin{abstract}Only abstract\end{abstract}\n\section{A}\nBody",
            "",
            "Only abstract",
        ),
    ],
)
def test_parse_latex_missing_optional_parts(
    tmp_path: Path, content: str, title: str, abstract: str
) -> None:
    path = _write_tex(tmp_path / "opt.tex", content)
    result = parse_latex_sections(path)
    assert result.title == title
    assert result.abstract == abstract


def test_build_hierarchy_empty_returns_empty() -> None:
    assert _build_hierarchy([]) == []


def test_build_hierarchy_nests_subsections(tmp_path: Path) -> None:
    tex = r"""
\section{S1}
aaa
\subsection{S1.1}
bbb
\subsubsection{S1.1.1}
ccc
\section{S2}
ddd
"""
    result = parse_latex_sections(_write_tex(tmp_path / "nested.tex", tex))
    roots = result.sections

    assert [s.name for s in roots] == ["S1", "S2"]
    assert roots[0].subsections[0].name == "S1.1"
    assert roots[0].subsections[0].subsections[0].name == "S1.1.1"


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("intro", "Intro body."),
        ("INTRO", "Intro body."),
        ("related", "Related body."),
        ("missing", ""),
    ],
)
def test_get_section_text_case_insensitive(tmp_path: Path, query: str, expected: str) -> None:
    tex = r"""
\section{Intro}
Intro body.
\subsection{Related}
Related body.
"""
    structure = parse_latex_sections(_write_tex(tmp_path / "query.tex", tex))
    assert get_section_text(structure, query).strip() == expected


def test_get_all_sections_flat_contains_sections_and_appendices(tmp_path: Path) -> None:
    tex = r"""
\section{A}
A text
\subsection{A1}
A1 text
\appendix
\section{B}
B text
"""
    structure = parse_latex_sections(_write_tex(tmp_path / "flat.tex", tex))
    names = [section.name for section in get_all_sections_flat(structure)]
    assert names == ["A", "A1", "B"]


@pytest.mark.parametrize(
    "section_cmd",
    [
        "section",
        "subsection",
        "subsubsection",
    ],
)
def test_parse_supports_all_section_levels(tmp_path: Path, section_cmd: str) -> None:
    tex = f"\\{section_cmd}{{Name}}\nBody"
    structure = parse_latex_sections(_write_tex(tmp_path / f"{section_cmd}.tex", tex))
    flat = get_all_sections_flat(structure)
    assert len(flat) == 1
    assert flat[0].name == "Name"
