# pyright: reportMissingImports=false
"""Tests for WritingStyleService (v0.10.1 Phase B)."""

from __future__ import annotations

from pathlib import Path

import yaml

from crane.models.writing_style_models import (
    ExemplarSnippet,
    RewriteSuggestion,
    SectionDiagnosis,
    StyleGuide,
    StyleIssue,
    StyleMetrics,
)
from crane.services.section_chunker import Section
from crane.services.style_guide_builder import StyleGuideBuilder
from crane.services.writing_style_service import (
    WritingStyleService,
    _classify_severity,
    _extract_example_span,
    _flatten_metrics,
    _recommend_fix,
    _safe_filename,
)


def _minimal_journal(
    name: str = "Test Journal",
    abbreviation: str = "TJ",
    publisher: str = "IEEE",
) -> dict:
    return {
        "name": name,
        "abbreviation": abbreviation,
        "publisher": publisher,
        "quartile": "Q1",
        "impact_factor": 10.0,
        "scope_keywords": ["machine learning", "deep learning"],
        "preferred_paper_types": ["empirical"],
        "preferred_method_families": ["deep learning"],
        "preferred_evidence_patterns": ["benchmark_heavy"],
        "typical_word_count": [6000, 10000],
        "review_timeline_months": [3, 6],
        "acceptance_rate": 0.2,
        "apc_usd": 0,
        "open_access": False,
        "open_access_type": "subscription",
        "waiver_available": False,
        "desk_reject_signals": [],
        "citation_venues": ["NeurIPS", "ICML"],
    }


def _write_profiles(tmp_path: Path, journals: list[dict]) -> Path:
    path = tmp_path / "profiles.yaml"
    path.write_text(
        yaml.safe_dump({"journals": journals}, sort_keys=False),
        encoding="utf-8",
    )
    return path


def _make_section(
    name: str = "Introduction",
    canonical_name: str = "Introduction",
    content: str = "",
) -> Section:
    return Section(
        name=name,
        canonical_name=canonical_name,
        level=1,
        content=content,
        character_count=len(content),
        word_count=len(content.split()) if content else 0,
    )


SAMPLE_INTRO_TEXT = (
    "In recent years, deep learning has attracted significant attention "
    "due to its remarkable performance in various tasks. However, existing "
    "approaches suffer from limited scalability and poor generalisation "
    "to unseen domains. To address these challenges, we propose a novel "
    "framework that leverages attention mechanisms for improved feature "
    "extraction. Our approach differs from prior work in three key aspects. "
    "First, we introduce a hierarchical attention module that captures "
    "multi-scale dependencies. Second, we develop an efficient training "
    "procedure that reduces computational overhead. Third, we conduct "
    "extensive experiments on five benchmark datasets demonstrating "
    "state-of-the-art performance."
)

SAMPLE_METHODS_TEXT = (
    "The proposed method is formulated as follows. Given a training set "
    "of labelled examples, the objective is to learn a mapping function "
    "that minimises the expected loss. The model architecture consists "
    "of an encoder and a decoder connected by a bottleneck layer. "
    "The encoder was designed to extract hierarchical features from the "
    "input data. The decoder was implemented to reconstruct the output "
    "from the latent representation. The loss function was computed using "
    "cross-entropy between the predicted and ground-truth labels. "
    "Optimisation was performed using stochastic gradient descent with "
    "momentum. The learning rate was initialised at zero point zero one "
    "and was decayed by a factor of ten every thirty epochs."
)


class TestWritingStyleServiceInit:
    def test_init_with_known_journal(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        assert svc.journal_name == "Test Journal"
        assert isinstance(svc.style_guide, StyleGuide)
        assert svc.style_guide.journal_name == "Test Journal"

    def test_init_with_abbreviation(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="TJ",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        assert svc.journal_name == "TJ"
        assert isinstance(svc.style_guide, StyleGuide)

    def test_init_with_unknown_journal(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Unknown Journal XYZ",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        assert svc.style_guide.sample_size == 0
        assert svc.style_guide.confidence_score == 0.0

    def test_init_with_explicit_domain(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            domain="cybersecurity",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        assert svc.domain == "cybersecurity"

    def test_init_missing_profiles_uses_defaults(self, tmp_path: Path) -> None:
        svc = WritingStyleService(
            journal_name="Nonexistent",
            profiles_path=tmp_path / "missing.yaml",
            cache_dir=tmp_path / "cache",
        )
        assert isinstance(svc.style_guide, StyleGuide)
        assert svc.style_guide.sample_size == 0


class TestDomainDetection:
    def test_domain_defaults_to_computer_science(self, tmp_path: Path) -> None:
        journal = _minimal_journal()
        journal["scope_keywords"] = ["general topic"]
        profiles = _write_profiles(tmp_path, [journal])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        assert isinstance(svc.domain, str)
        assert len(svc.domain) > 0

    def test_explicit_domain_overrides_detection(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            domain="iot",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        assert svc.domain == "iot"


def _minimal_journal_with(**overrides: object) -> dict:
    base = _minimal_journal()
    base.update(overrides)
    return base


class TestDiagnoseSection:
    def test_diagnose_returns_section_diagnosis(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        section = _make_section(content=SAMPLE_INTRO_TEXT)
        diag = svc.diagnose_section(section)

        assert isinstance(diag, SectionDiagnosis)
        assert diag.section_name == "Introduction"
        assert isinstance(diag.current_metrics, StyleMetrics)
        assert isinstance(diag.target_metrics, StyleMetrics)
        assert isinstance(diag.deviation_score, float)
        assert 0.0 <= diag.deviation_score <= 100.0

    def test_diagnose_identifies_issues(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        section = _make_section(
            name="Methods",
            canonical_name="Methods",
            content=SAMPLE_METHODS_TEXT,
        )
        diag = svc.diagnose_section(section)

        assert isinstance(diag.issues, list)
        for issue in diag.issues:
            assert isinstance(issue, StyleIssue)
            assert issue.severity in ("critical", "major", "minor")
            assert issue.category in (
                "readability",
                "vocabulary",
                "grammar",
                "argumentation",
            )

    def test_diagnose_generates_suggestions(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        section = _make_section(content=SAMPLE_METHODS_TEXT)
        diag = svc.diagnose_section(section)

        assert isinstance(diag.suggestions, list)
        for sug in diag.suggestions:
            assert isinstance(sug, RewriteSuggestion)
            assert 0.0 <= sug.confidence <= 1.0

    def test_diagnose_empty_section(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        section = _make_section(content="Hello world.")
        diag = svc.diagnose_section(section)
        assert isinstance(diag, SectionDiagnosis)

    def test_issues_sorted_by_severity(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        section = _make_section(content=SAMPLE_METHODS_TEXT)
        diag = svc.diagnose_section(section)

        severity_order = {"critical": 0, "major": 1, "minor": 2}
        for i in range(len(diag.issues) - 1):
            current_order = severity_order.get(diag.issues[i].severity, 3)
            next_order = severity_order.get(diag.issues[i + 1].severity, 3)
            assert current_order <= next_order


class TestDiagnoseFullPaper:
    def test_diagnose_full_paper(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )

        tex_file = tmp_path / "paper.tex"
        tex_file.write_text(
            r"""\documentclass{article}
\title{Test Paper}
\begin{document}
\begin{abstract}
This paper presents a novel approach to deep learning.
We demonstrate improved performance on benchmark datasets.
\end{abstract}
\section{Introduction}
"""
            + SAMPLE_INTRO_TEXT
            + r"""
\section{Methods}
"""
            + SAMPLE_METHODS_TEXT
            + r"""
\section{Conclusion}
We have presented a novel framework for deep learning.
The results demonstrate significant improvements over baselines.
\end{document}
""",
            encoding="utf-8",
        )

        diagnoses = svc.diagnose_full_paper(str(tex_file))

        assert isinstance(diagnoses, dict)
        assert len(diagnoses) >= 2
        for name, diag in diagnoses.items():
            assert isinstance(name, str)
            assert isinstance(diag, SectionDiagnosis)

    def test_diagnose_full_paper_file_not_found(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )

        try:
            svc.diagnose_full_paper(str(tmp_path / "nonexistent.tex"))
            assert False, "Expected FileNotFoundError"
        except FileNotFoundError:
            pass


class TestSuggestRewrites:
    def test_suggest_rewrites_rule_style(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        section = _make_section(content=SAMPLE_METHODS_TEXT)
        diag = svc.diagnose_section(section)
        suggestions = svc.suggest_rewrites(diag, style="rule")

        assert isinstance(suggestions, list)
        for sug in suggestions:
            assert isinstance(sug, RewriteSuggestion)

    def test_suggest_rewrites_hybrid_style(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        section = _make_section(content=SAMPLE_METHODS_TEXT)
        diag = svc.diagnose_section(section)
        suggestions = svc.suggest_rewrites(diag, style="hybrid")

        assert isinstance(suggestions, list)

    def test_suggest_rewrites_max_count(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        section = _make_section(content=SAMPLE_METHODS_TEXT)
        diag = svc.diagnose_section(section)
        suggestions = svc.suggest_rewrites(diag, max_suggestions=2)

        assert len(suggestions) <= 2

    def test_suggest_rewrites_sorted_by_confidence(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        section = _make_section(content=SAMPLE_METHODS_TEXT)
        diag = svc.diagnose_section(section)
        suggestions = svc.suggest_rewrites(diag)

        for i in range(len(suggestions) - 1):
            assert suggestions[i].confidence >= suggestions[i + 1].confidence


class TestGetExemplars:
    def test_get_exemplars_empty_guide(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        exemplars = svc.get_exemplars("Introduction")
        assert isinstance(exemplars, list)

    def test_get_exemplars_with_cached_guide(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)
        guide_data = {
            "journal_name": "Test Journal",
            "domain": "computer_science",
            "metrics": {
                "flesch_kincaid_grade": 12.0,
                "smog_index": 14.0,
                "avg_sentence_length": 22,
                "avg_word_length": 5.0,
                "type_token_ratio": 0.55,
                "technical_term_density": 0.08,
                "passive_voice_ratio": 0.15,
                "nominalization_ratio": 0.06,
            },
            "section_targets": {},
            "exemplars": [
                {
                    "text": "We propose a novel method.",
                    "section": "Introduction",
                    "source_paper": "paper1",
                    "metrics": {
                        "flesch_kincaid_grade": 10.0,
                        "smog_index": 12.0,
                        "avg_sentence_length": 20,
                        "avg_word_length": 4.8,
                        "type_token_ratio": 0.6,
                        "technical_term_density": 0.05,
                        "passive_voice_ratio": 0.1,
                        "nominalization_ratio": 0.04,
                    },
                },
                {
                    "text": "The results demonstrate improvement.",
                    "section": "Results",
                    "source_paper": "paper2",
                    "metrics": {},
                },
            ],
            "sample_size": 2,
            "confidence_score": 0.8,
            "created_at": "2025-01-01T00:00:00",
        }
        cache_path = cache_dir / "test_journal.yaml"
        cache_path.write_text(yaml.safe_dump(guide_data, sort_keys=False), encoding="utf-8")

        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=cache_dir,
        )

        intro_exemplars = svc.get_exemplars("Introduction")
        assert len(intro_exemplars) == 1
        assert isinstance(intro_exemplars[0], ExemplarSnippet)
        assert intro_exemplars[0].section == "Introduction"

    def test_get_exemplars_fallback(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)
        guide_data = {
            "journal_name": "Test Journal",
            "domain": "computer_science",
            "metrics": {},
            "section_targets": {},
            "exemplars": [
                {
                    "text": "Example text.",
                    "section": "Methods",
                    "source_paper": "p1",
                    "metrics": {},
                },
            ],
            "sample_size": 1,
            "confidence_score": 0.5,
            "created_at": "2025-01-01T00:00:00",
        }
        cache_path = cache_dir / "test_journal.yaml"
        cache_path.write_text(yaml.safe_dump(guide_data, sort_keys=False), encoding="utf-8")

        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=cache_dir,
        )

        exemplars = svc.get_exemplars("Nonexistent Section")
        assert len(exemplars) >= 1


class TestStyleGuideCaching:
    def test_cache_created_on_first_build(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=cache_dir,
        )
        assert isinstance(svc.style_guide, StyleGuide)

    def test_cache_loaded_on_second_init(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)

        guide_data = {
            "journal_name": "Cached Journal",
            "domain": "cached_domain",
            "metrics": {
                "flesch_kincaid_grade": 99.0,
                "smog_index": 99.0,
                "avg_sentence_length": 99,
                "avg_word_length": 99.0,
                "type_token_ratio": 0.99,
                "technical_term_density": 0.99,
                "passive_voice_ratio": 0.99,
                "nominalization_ratio": 0.99,
            },
            "section_targets": {},
            "exemplars": [],
            "sample_size": 42,
            "confidence_score": 0.95,
            "created_at": "2025-01-01T00:00:00",
        }
        cache_path = cache_dir / "test_journal.yaml"
        cache_path.write_text(yaml.safe_dump(guide_data, sort_keys=False), encoding="utf-8")

        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=cache_dir,
        )

        assert svc.style_guide.journal_name == "Cached Journal"
        assert svc.style_guide.sample_size == 42
        assert svc.style_guide.confidence_score == 0.95


class TestCompareJournals:
    def test_compare_with_self(self, tmp_path: Path) -> None:
        profiles = _write_profiles(
            tmp_path,
            [
                _minimal_journal(name="J1", abbreviation="J1"),
                _minimal_journal(name="J2", abbreviation="J2", publisher="ACM"),
            ],
        )
        svc = WritingStyleService(
            journal_name="J1",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        result = svc.compare_journals([])
        assert "J1" in result
        assert isinstance(result["J1"], dict)

    def test_compare_with_other_journal(self, tmp_path: Path) -> None:
        profiles = _write_profiles(
            tmp_path,
            [
                _minimal_journal(name="J1", abbreviation="J1"),
                _minimal_journal(name="J2", abbreviation="J2", publisher="ACM"),
            ],
        )
        svc = WritingStyleService(
            journal_name="J1",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        result = svc.compare_journals(["J2"])
        assert "J1" in result
        assert "J2" in result

    def test_compare_includes_unknown_journal_with_defaults(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal(name="J1", abbreviation="J1")])
        svc = WritingStyleService(
            journal_name="J1",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        result = svc.compare_journals(["NonexistentJournal"])
        assert "J1" in result
        assert "NonexistentJournal" in result
        assert isinstance(result["NonexistentJournal"], dict)


class TestGetStyleGuide:
    def test_returns_style_guide(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        guide = svc.get_style_guide()
        assert isinstance(guide, StyleGuide)
        assert guide.journal_name == "Test Journal"


class TestCrossSectionPatterns:
    def test_cross_section_passive_voice_detection(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )

        passive_text = (
            "The model was trained on the dataset. "
            "The results were evaluated using standard metrics. "
            "The features were extracted from the input. "
            "The parameters were optimised using gradient descent. "
            "The experiments were conducted on multiple benchmarks."
        )

        tex_file = tmp_path / "paper.tex"
        tex_file.write_text(
            r"""\documentclass{article}
\title{Test}
\begin{document}
\section{Introduction}
"""
            + passive_text
            + r"""
\section{Methods}
"""
            + passive_text
            + r"""
\section{Results}
"""
            + passive_text
            + r"""
\end{document}
""",
            encoding="utf-8",
        )

        diagnoses = svc.diagnose_full_paper(str(tex_file))
        assert len(diagnoses) >= 2


class TestHelperFunctions:
    def test_classify_severity_critical(self) -> None:
        assert _classify_severity(0.5) == "critical"

    def test_classify_severity_major(self) -> None:
        assert _classify_severity(0.25) == "major"

    def test_classify_severity_minor(self) -> None:
        assert _classify_severity(0.12) == "minor"

    def test_classify_severity_boundary(self) -> None:
        assert _classify_severity(0.40) == "critical"
        assert _classify_severity(0.20) == "major"
        assert _classify_severity(0.10) == "minor"

    def test_flatten_metrics(self) -> None:
        metrics = StyleMetrics()
        flat = _flatten_metrics(metrics)
        assert isinstance(flat, dict)
        assert "flesch_kincaid_grade" in flat
        assert "passive_voice_ratio" in flat
        assert len(flat) == 8

    def test_safe_filename(self) -> None:
        assert _safe_filename("IEEE TPAMI") == "ieee_tpami"
        assert _safe_filename("ACM Computing Surveys") == "acm_computing_surveys"
        assert _safe_filename("Test/Journal:Name") == "testjournalname"

    def test_extract_example_span_passive(self) -> None:
        text = "The model was trained on the dataset."
        span = _extract_example_span("passive_voice_ratio", text)
        assert "was trained" in span

    def test_extract_example_span_nominalization(self) -> None:
        text = "The utilization of resources was significant."
        span = _extract_example_span("nominalization_ratio", text)
        assert "utilization" in span

    def test_extract_example_span_unknown_metric(self) -> None:
        span = _extract_example_span("unknown_metric", "Some text here.")
        assert span == ""

    def test_recommend_fix_passive_high(self) -> None:
        fix = _recommend_fix("passive_voice_ratio", "high", 0.5, 0.2)
        assert "active voice" in fix.lower()

    def test_recommend_fix_sentence_length_high(self) -> None:
        fix = _recommend_fix("avg_sentence_length", "high", 35.0, 22.0)
        assert "shorter" in fix.lower() or "break" in fix.lower()

    def test_recommend_fix_unknown_metric(self) -> None:
        fix = _recommend_fix("unknown_metric", "high", 1.0, 0.5)
        assert "0.50" in fix


class TestDefaultStyleGuide:
    def test_default_guide_has_section_targets(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Unknown Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        guide = svc.get_style_guide()
        assert len(guide.section_targets) > 0
        assert "Introduction" in guide.section_targets
        assert "Methods" in guide.section_targets
        assert "Conclusion" in guide.section_targets

    def test_default_guide_metrics_are_averages(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Unknown Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        guide = svc.get_style_guide()
        flat = _flatten_metrics(guide.metrics)
        assert flat["flesch_kincaid_grade"] > 0.0
        assert flat["avg_sentence_length"] > 0.0


class TestDomainWeighting:
    def test_ai_ml_domain_weights_applied(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            domain="ai_ml",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        assert svc._domain_weights.get("technical_term_density") == 1.3
        assert svc._domain_weights.get("passive_voice_ratio") == 0.8

    def test_cybersecurity_domain_weights(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            domain="cybersecurity",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        assert svc._domain_weights.get("technical_term_density") == 1.4

    def test_unknown_domain_no_weights(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            domain="unknown_domain",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        assert svc._domain_weights == {}


class TestIntegrationWithPhaseA:
    def test_section_chunker_integration(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        assert isinstance(svc.section_chunker, object)

    def test_style_guide_builder_integration(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        assert isinstance(svc.style_guide_builder, StyleGuideBuilder)

    def test_full_pipeline_section_to_diagnosis(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )

        sections = svc.section_chunker.chunk_text("Introduction\n" + SAMPLE_INTRO_TEXT)
        assert len(sections) >= 1

        for sec in sections:
            if sec.content.strip():
                diag = svc.diagnose_section(sec)
                assert isinstance(diag, SectionDiagnosis)
                break

    def test_style_guide_builder_metrics_calculation(self, tmp_path: Path) -> None:
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        svc = WritingStyleService(
            journal_name="Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        metrics = svc.style_guide_builder.calculate_style_metrics(SAMPLE_INTRO_TEXT)
        assert isinstance(metrics, StyleMetrics)
        assert metrics.readability.avg_sentence_length > 0
        assert metrics.vocabulary.type_token_ratio > 0.0
