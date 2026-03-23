"""Tests for section review service."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def _load_parser():
    return importlib.import_module("crane.services.latex_parser")


def _load_review():
    return importlib.import_module("crane.services.section_review_service")


class TestLatexParser:
    def test_parse_sections(self, tmp_path):
        parser = _load_parser()
        tex_file = tmp_path / "test.tex"
        tex_file.write_text(r"""
\title{Test Paper}
\begin{abstract}
This is a test abstract.
\end{abstract}
\section{Introduction}
Introduction content.
\section{Methodology}
Methodology content.
\subsection{Component A}
Component A content.
""")
        structure = parser.parse_latex_sections(tex_file)

        assert structure.title == "Test Paper"
        assert "test abstract" in structure.abstract.lower()
        assert len(structure.sections) == 2
        assert structure.sections[0].name == "Introduction"
        assert structure.sections[1].name == "Methodology"
        assert len(structure.sections[1].subsections) == 1

    def test_parse_appendices(self, tmp_path):
        parser = _load_parser()
        tex_file = tmp_path / "test.tex"
        tex_file.write_text(r"""
\section{Main}
Main content.
\appendix
\section{Appendix A}
Appendix content.
""")
        structure = parser.parse_latex_sections(tex_file)

        assert len(structure.sections) == 1
        assert len(structure.appendices) == 1
        assert structure.appendices[0].name == "Appendix A"


class TestSectionReviewService:
    def test_review_section_detects_issues(self):
        review = _load_review()
        parser = _load_parser()
        service = review.SectionReviewService()

        section = parser.SectionLocation(
            name="Test",
            level=1,
            start_line=1,
            end_line=10,
            content="It is worth noting that this is a novel approach. Furthermore, we achieve significant improvement.",
        )

        result = service.review_section(section, [review.ReviewType.WRITING])

        assert len(result.issues) > 0
        assert result.score < 1.0

    def test_review_paper_returns_summary(self, tmp_path):
        review = _load_review()
        tex_file = tmp_path / "test.tex"
        tex_file.write_text(r"""
\title{Test}
\section{Introduction}
We propose a novel neuro-symbolic expert system.
\section{Experiments}
We achieve 62.5% improvement.
""")
        service = review.SectionReviewService()
        result = service.review_paper(tex_file)

        assert result.summary["total_issues"] >= 0
        assert "overall_score" in result.summary
        assert "recommendation" in result.summary


class TestSectionReviewTools:
    def test_registered(self):
        from crane.server import mcp

        tools = mcp._tool_manager._tools if hasattr(mcp, "_tool_manager") else {}
        assert "review_paper_sections" in tools
        assert "parse_paper_structure" in tools
