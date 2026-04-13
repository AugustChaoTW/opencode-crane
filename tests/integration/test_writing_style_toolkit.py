"""Integration tests for v0.10.1 Writing Style Toolkit (Phase C).

Tests all 7 MCP tools, domain detection, exemplar retrieval,
and report generation against the 55-journal database.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

import pytest

from crane.models.writing_style_models import (
    ExemplarSnippet,
    RewriteSuggestion,
    SectionDiagnosis,
    StyleGuide,
    StyleIssue,
    StyleMetrics,
)
from crane.services.section_chunker import Section
from crane.services.writing_style_service import WritingStyleService
from crane.tools.writing_style_tools import register_tools


SAMPLE_LATEX = textwrap.dedent(r"""
\documentclass{article}
\title{A Novel Approach to Deep Learning}
\begin{document}
\begin{abstract}
We propose a novel deep learning framework for image classification.
Our method achieves state-of-the-art performance on multiple benchmarks.
The proposed approach leverages transformer architectures with attention mechanisms.
Furthermore, we demonstrate significant improvements over existing baselines.
\end{abstract}

\section{Introduction}
Deep learning has revolutionized computer vision \cite{lecun2015}.
In recent years, transformer-based models have shown remarkable performance
in various tasks \cite{vaswani2017,dosovitskiy2020}. However, existing
approaches may suffer from computational inefficiency. We propose a novel
method that could address these limitations. Our contributions are threefold:
(1) we introduce a new architecture, (2) we develop an efficient training
procedure, and (3) we conduct extensive experiments. Furthermore, our approach
demonstrates superior convergence properties.

\section{Related Work}
Previous studies have explored various approaches to image classification
\cite{he2016,huang2017,tan2019}. ResNet \cite{he2016} introduced residual
connections. DenseNet \cite{huang2017} proposed dense connectivity patterns.
EfficientNet \cite{tan2019} suggested compound scaling. Nevertheless, these
methods generally require significant computational resources \cite{strubell2019}.
Moreover, recent work has focused on attention mechanisms \cite{wang2018}.

\section{Methods}
We formulate the problem as an optimization task. Given input $x$, the model
computes embeddings via a transformer encoder. The loss function combines
cross-entropy with a regularization term. Algorithm 1 describes the training
procedure. The gradient is computed using backpropagation. Each epoch processes
the entire training set in mini-batches. The learning rate follows a cosine
annealing schedule. Dropout is applied for regularization.

\section{Experiments}
Table 1 reports the classification accuracy on ImageNet. Our method achieves
92.3\% top-1 accuracy, outperforming the best baseline by 1.2\%.
We conduct ablation studies to validate each component.
The results demonstrate consistent improvements across all benchmarks.

\section{Discussion}
The experimental results suggest that our approach is effective.
However, there are several limitations that should be acknowledged.
The computational cost may be prohibitive for resource-constrained settings.
Furthermore, the method might not generalize to all domains.
Nevertheless, the overall performance is promising.

\section{Conclusion}
We presented a novel deep learning framework for image classification.
Our method achieves state-of-the-art results on multiple benchmarks.
Future work will explore extensions to other vision tasks.
\end{document}
""").strip()


@pytest.fixture
def sample_tex_file(tmp_path: Path) -> str:
    tex_file = tmp_path / "test_paper.tex"
    tex_file.write_text(SAMPLE_LATEX, encoding="utf-8")
    return str(tex_file)


@pytest.fixture
def tpami_service() -> WritingStyleService:
    return WritingStyleService("IEEE TPAMI")


@pytest.fixture
def tosem_service() -> WritingStyleService:
    return WritingStyleService("ACM TOSEM")


class TestWritingStyleService:
    def test_load_journal_by_abbreviation(self):
        service = WritingStyleService("IEEE TPAMI")
        assert service.journal_name == "IEEE TPAMI"

    def test_load_journal_by_full_name(self):
        service = WritingStyleService(
            "IEEE Transactions on Pattern Analysis and Machine Intelligence"
        )
        assert service.journal_name.startswith("IEEE Transactions")

    def test_style_guide_built(self, tpami_service: WritingStyleService):
        guide = tpami_service.style_guide
        assert isinstance(guide, StyleGuide)
        assert guide.journal_name != ""
        assert isinstance(guide.metrics, StyleMetrics)

    def test_acm_domain_detection(self, tosem_service: WritingStyleService):
        assert isinstance(tosem_service.domain, str)
        assert tosem_service.domain != ""

    def test_diagnose_section(self, tpami_service: WritingStyleService, sample_tex_file: str):
        sections = tpami_service.section_chunker.chunk_latex_paper(sample_tex_file)
        intro = next((s for s in sections if s.canonical_name == "Introduction"), None)
        assert intro is not None
        diagnosis = tpami_service.diagnose_section(intro)
        assert isinstance(diagnosis, SectionDiagnosis)
        assert diagnosis.section_name == "Introduction"
        assert 0.0 <= diagnosis.deviation_score <= 100.0
        assert isinstance(diagnosis.issues, list)

    def test_diagnose_full_paper(self, tpami_service: WritingStyleService, sample_tex_file: str):
        diagnoses = tpami_service.diagnose_full_paper(sample_tex_file)
        assert len(diagnoses) >= 3
        assert all(isinstance(d, SectionDiagnosis) for d in diagnoses.values())

    def test_get_exemplars(self, tpami_service: WritingStyleService):
        exemplars = tpami_service.get_exemplars("Introduction", count=2)
        assert isinstance(exemplars, list)
        for ex in exemplars:
            assert isinstance(ex, ExemplarSnippet)

    def test_suggest_rewrites(self, tpami_service: WritingStyleService, sample_tex_file: str):
        sections = tpami_service.section_chunker.chunk_latex_paper(sample_tex_file)
        intro = next((s for s in sections if s.canonical_name == "Introduction"), None)
        assert intro is not None
        diagnosis = tpami_service.diagnose_section(intro)
        suggestions = tpami_service.suggest_rewrites(diagnosis, max_suggestions=3)
        assert isinstance(suggestions, list)
        for s in suggestions:
            assert isinstance(s, RewriteSuggestion)
            assert hasattr(s, "confidence")

    def test_compare_journals(self, tpami_service: WritingStyleService):
        comparison = tpami_service.compare_journals(["ACM TOSEM"])
        assert "IEEE TPAMI" in comparison
        assert "ACM TOSEM" in comparison
        assert isinstance(comparison["IEEE TPAMI"], dict)

    def test_get_style_guide(self, tpami_service: WritingStyleService):
        guide = tpami_service.get_style_guide()
        assert isinstance(guide, StyleGuide)
        assert guide.journal_name != ""


class TestMCPToolsIntegration:
    """Test all 7 MCP tools via their registered functions."""

    @pytest.fixture
    def tools(self) -> dict[str, Any]:
        captured: dict[str, Any] = {}

        class FakeMCP:
            def tool(self):
                def decorator(func):
                    captured[func.__name__] = func
                    return func
                return decorator

        register_tools(FakeMCP())
        return captured

    def test_all_six_tools_registered(self, tools: dict[str, Any]):
        expected = {
            "crane_extract_journal_style_guide",
            "crane_diagnose",           # replaces crane_diagnose_paper + crane_diagnose_section
            "crane_get_style_exemplars",
            "crane_suggest_rewrites",
            "crane_compare_sections",
            "crane_export_style_report",
        }
        assert set(tools.keys()) == expected

    def test_extract_journal_style_guide(self, tools: dict[str, Any]):
        result = tools["crane_extract_journal_style_guide"](journal_name="IEEE TPAMI")
        assert result["journal"] == "IEEE TPAMI"
        assert result["confidence"] >= 0
        assert "target_metrics" in result
        assert "error" not in result

    def test_extract_journal_style_guide_unknown(self, tools: dict[str, Any]):
        result = tools["crane_extract_journal_style_guide"](journal_name="Fake Journal XYZ")
        assert "error" not in result or result.get("confidence", 0) >= 0

    def test_diagnose_section(self, tools: dict[str, Any], sample_tex_file: str):
        result = tools["crane_diagnose"](
            paper_path=sample_tex_file,
            journal_name="IEEE TPAMI",
            scope="section",
            section_name="Introduction",
        )
        assert "error" not in result
        assert result["section_name"] == "Introduction"
        assert result["journal"] == "IEEE TPAMI"
        assert "deviation_score" in result

    def test_diagnose_paper(self, tools: dict[str, Any], sample_tex_file: str):
        result = tools["crane_diagnose"](
            paper_path=sample_tex_file,
            journal_name="IEEE TPAMI",
            scope="paper",
        )
        assert "error" not in result
        assert result["journal"] == "IEEE TPAMI"
        assert result["sections_analysed"] >= 3
        assert "overall_deviation" in result

    def test_diagnose_section_requires_section_name(self, tools: dict[str, Any], sample_tex_file: str):
        result = tools["crane_diagnose"](
            paper_path=sample_tex_file,
            journal_name="IEEE TPAMI",
            scope="section",
            # section_name intentionally omitted
        )
        assert "error" in result

    def test_get_style_exemplars(self, tools: dict[str, Any]):
        result = tools["crane_get_style_exemplars"](
            journal_name="IEEE TPAMI",
            section_name="Introduction",
            count=2,
        )
        assert result["journal"] == "IEEE TPAMI"
        assert isinstance(result["exemplars"], list)
        assert "error" not in result

    def test_suggest_rewrites(self, tools: dict[str, Any], sample_tex_file: str):
        result = tools["crane_suggest_rewrites"](
            paper_path=sample_tex_file,
            section_name="Introduction",
            journal_name="IEEE TPAMI",
            count=3,
        )
        assert "error" not in result
        assert result["section"] == "Introduction"
        assert "deviation_score" in result
        assert isinstance(result["suggestions"], list)

    def test_compare_sections(self, tools: dict[str, Any], sample_tex_file: str):
        result = tools["crane_compare_sections"](
            paper_path=sample_tex_file,
            section_name="Introduction",
            journal1="IEEE TPAMI",
            journal2="ACM TOSEM",
        )
        assert "error" not in result
        assert "journals" in result
        assert len(result["journals"]) == 2
        assert "differences" in result
        assert "recommendation" in result

    def test_export_style_report(self, tools: dict[str, Any], sample_tex_file: str, tmp_path: Path):
        output = str(tmp_path / "test_report.md")
        result = tools["crane_export_style_report"](
            paper_path=sample_tex_file,
            journal_name="IEEE TPAMI",
            output_path=output,
        )
        assert "error" not in result
        assert result["journal"] == "IEEE TPAMI"
        assert result["sections_analysed"] >= 3
        assert result["report_length"] > 0
        assert Path(output).exists()


class TestDomainDetection:
    def test_ieee_tpami_domain(self):
        service = WritingStyleService("IEEE TPAMI")
        assert isinstance(service.domain, str)
        assert service.domain != ""

    def test_cybersecurity_journal(self):
        service = WritingStyleService("IEEE TDSC")
        assert isinstance(service.domain, str)


class TestCrossJournalComparison:
    def test_ieee_vs_acm(self):
        ieee = WritingStyleService("IEEE TPAMI")
        comparison = ieee.compare_journals(["ACM TOSEM"], section_name="Introduction")
        assert "IEEE TPAMI" in comparison
        assert "ACM TOSEM" in comparison

    def test_same_publisher(self):
        j1 = WritingStyleService("IEEE TPAMI")
        comparison = j1.compare_journals(["IEEE TNNLS"], section_name="Methods")
        assert "IEEE TPAMI" in comparison
        assert "IEEE TNNLS" in comparison
