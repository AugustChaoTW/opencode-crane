# pyright: reportMissingImports=false

from __future__ import annotations

from pathlib import Path

import pytest

from crane.models.writing_style_models import (
    ReadabilityMetrics,
    StyleGuide,
    StyleMetrics,
    VocabularyMetrics,
)
from crane.services.style_guide_builder import (
    StyleGuideBuilder,
    _count_syllables,
    _sentences,
    _words,
)


@pytest.fixture
def builder() -> StyleGuideBuilder:
    return StyleGuideBuilder()


SAMPLE_ACADEMIC_TEXT = (
    "We propose a novel framework for detecting anomalies in network traffic. "
    "The proposed method leverages deep learning techniques to identify patterns. "
    "Our results demonstrate significant improvement over existing baselines. "
    "Table 1 shows the comparison of accuracy across different datasets. "
    "The experiments were conducted on three publicly available benchmarks. "
    "We find that the proposed approach achieves state-of-the-art performance. "
    "Future work will explore additional applications in cybersecurity."
)

PASSIVE_TEXT = (
    "The experiment was conducted by the research team. "
    "Data was collected from multiple sources. "
    "The results were analysed using statistical methods. "
    "It was determined that the approach is effective."
)


class TestCountSyllables:
    def test_monosyllabic(self) -> None:
        assert _count_syllables("the") == 1
        assert _count_syllables("cat") == 1

    def test_multisyllabic(self) -> None:
        assert _count_syllables("computer") >= 2
        assert _count_syllables("university") >= 3

    def test_empty_and_short(self) -> None:
        assert _count_syllables("a") == 1
        assert _count_syllables("") == 1

    def test_silent_e(self) -> None:
        result = _count_syllables("make")
        assert result == 1


class TestSentences:
    def test_basic_splitting(self) -> None:
        text = "First sentence. Second sentence. Third one!"
        sents = _sentences(text)
        assert len(sents) == 3

    def test_empty_text(self) -> None:
        assert _sentences("") == []

    def test_no_terminal_punctuation(self) -> None:
        assert _sentences("no period here") == []


class TestWords:
    def test_basic_tokenisation(self) -> None:
        tokens = _words("Hello World 123")
        assert tokens == ["hello", "world"]

    def test_empty_text(self) -> None:
        assert _words("") == []


class TestCalculateStyleMetrics:
    def test_returns_all_sub_metrics(self, builder: StyleGuideBuilder) -> None:
        metrics = builder.calculate_style_metrics(SAMPLE_ACADEMIC_TEXT)
        assert isinstance(metrics, StyleMetrics)
        assert isinstance(metrics.readability, ReadabilityMetrics)
        assert isinstance(metrics.vocabulary, VocabularyMetrics)
        assert metrics.timestamp

    def test_readability_values_in_range(self, builder: StyleGuideBuilder) -> None:
        metrics = builder.calculate_style_metrics(SAMPLE_ACADEMIC_TEXT)
        assert 0.0 <= metrics.readability.flesch_kincaid_grade <= 20.0
        assert metrics.readability.smog_index >= 0.0
        assert metrics.readability.avg_sentence_length > 0
        assert metrics.readability.avg_word_length > 0.0

    def test_vocabulary_metrics(self, builder: StyleGuideBuilder) -> None:
        metrics = builder.calculate_style_metrics(SAMPLE_ACADEMIC_TEXT)
        assert 0.0 < metrics.vocabulary.type_token_ratio <= 1.0
        assert metrics.vocabulary.unique_word_count > 0

    def test_grammar_detects_passive(self, builder: StyleGuideBuilder) -> None:
        metrics = builder.calculate_style_metrics(PASSIVE_TEXT)
        assert metrics.grammar.passive_voice_ratio > 0.0

    def test_argumentation_detects_claims(self, builder: StyleGuideBuilder) -> None:
        metrics = builder.calculate_style_metrics(SAMPLE_ACADEMIC_TEXT)
        assert metrics.argumentation.claim_count > 0

    def test_argumentation_detects_evidence(self, builder: StyleGuideBuilder) -> None:
        metrics = builder.calculate_style_metrics(SAMPLE_ACADEMIC_TEXT)
        assert metrics.argumentation.evidence_count > 0

    def test_empty_text(self, builder: StyleGuideBuilder) -> None:
        metrics = builder.calculate_style_metrics("")
        assert metrics.readability.avg_sentence_length == 0


class TestBuildFromPapers:
    def test_single_latex_paper(self, builder: StyleGuideBuilder, tmp_path: Path) -> None:
        tex = r"""
\title{Test Paper}
\begin{abstract}
This abstract describes a novel contribution to the field.
\end{abstract}
\section{Introduction}
We propose a new approach for addressing the research gap.
The problem has been studied extensively in prior work.
Our results show that the proposed method outperforms baselines.
Table 1 shows the comparison of accuracy.
\section{Methods}
The method uses a transformer architecture with attention mechanisms.
Data was collected from publicly available benchmarks.
We evaluate performance using standard metrics.
\section{Results}
Our approach achieves state-of-the-art performance on three datasets.
Table 2 presents the detailed results.
\section{Conclusion}
We presented a novel framework for the task.
Future work will explore additional applications.
"""
        path = tmp_path / "paper.tex"
        path.write_text(tex, encoding="utf-8")

        guide = builder.build_from_papers(
            journal_name="Test Journal",
            paper_paths=[str(path)],
            domain="computer_science",
        )

        assert isinstance(guide, StyleGuide)
        assert guide.journal_name == "Test Journal"
        assert guide.domain == "computer_science"
        assert guide.sample_size == 1
        assert 0.0 < guide.confidence_score <= 1.0
        assert guide.created_at
        assert len(guide.section_targets) > 0
        assert "Introduction" in guide.section_targets or any(
            "Intro" in k for k in guide.section_targets
        )

    def test_multiple_papers(self, builder: StyleGuideBuilder, tmp_path: Path) -> None:
        for i in range(3):
            tex = rf"""
\section{{Introduction}}
Paper {i} introduces a novel method for solving problem X.
We demonstrate improvement over prior work.
\section{{Methods}}
The approach uses technique {i} with advanced processing.
"""
            (tmp_path / f"paper{i}.tex").write_text(tex, encoding="utf-8")

        paths = [str(tmp_path / f"paper{i}.tex") for i in range(3)]
        guide = builder.build_from_papers("Multi Journal", paths)

        assert guide.sample_size == 3
        assert guide.confidence_score > builder._confidence_from_sample_size(1)

    def test_empty_paper_list(self, builder: StyleGuideBuilder) -> None:
        guide = builder.build_from_papers("Empty", [])
        assert guide.sample_size == 0
        assert guide.confidence_score == 0.0

    def test_section_targets_contain_expected_keys(
        self, builder: StyleGuideBuilder, tmp_path: Path
    ) -> None:
        tex = r"""
\section{Introduction}
We propose a framework for the analysis of complex systems.
\section{Methods}
The methodology involves statistical sampling and evaluation.
"""
        path = tmp_path / "t.tex"
        path.write_text(tex, encoding="utf-8")

        guide = builder.build_from_papers("J", [str(path)])
        for _sec_name, targets in guide.section_targets.items():
            assert "flesch_kincaid_grade" in targets
            assert "type_token_ratio" in targets
            assert "passive_voice_ratio" in targets


class TestConfidence:
    def test_zero_papers(self, builder: StyleGuideBuilder) -> None:
        assert builder._confidence_from_sample_size(0) == 0.0

    def test_one_paper(self, builder: StyleGuideBuilder) -> None:
        c = builder._confidence_from_sample_size(1)
        assert 0.0 < c < 1.0

    def test_many_papers_caps(self, builder: StyleGuideBuilder) -> None:
        assert builder._confidence_from_sample_size(100) == 0.95

    def test_monotonically_increasing(self, builder: StyleGuideBuilder) -> None:
        values = [builder._confidence_from_sample_size(n) for n in range(1, 31)]
        for a, b in zip(values, values[1:]):
            assert b >= a


class TestAggregateMetrics:
    def test_single_metric(self, builder: StyleGuideBuilder) -> None:
        m = StyleMetrics(
            readability=ReadabilityMetrics(flesch_kincaid_grade=10.0),
        )
        result = builder._aggregate_metrics([m])
        assert result.readability.flesch_kincaid_grade == 10.0

    def test_averages_correctly(self, builder: StyleGuideBuilder) -> None:
        m1 = StyleMetrics(
            readability=ReadabilityMetrics(flesch_kincaid_grade=10.0),
        )
        m2 = StyleMetrics(
            readability=ReadabilityMetrics(flesch_kincaid_grade=20.0),
        )
        result = builder._aggregate_metrics([m1, m2])
        assert result.readability.flesch_kincaid_grade == 15.0

    def test_empty_list(self, builder: StyleGuideBuilder) -> None:
        result = builder._aggregate_metrics([])
        assert isinstance(result, StyleMetrics)


class TestExcerpt:
    def test_short_text_unchanged(self) -> None:
        text = "Short text."
        assert StyleGuideBuilder._excerpt(text, max_words=10) == text

    def test_long_text_truncated(self) -> None:
        text = " ".join(["word"] * 200)
        result = StyleGuideBuilder._excerpt(text, max_words=50)
        assert result.endswith("...")
        assert len(result.split()) <= 52
