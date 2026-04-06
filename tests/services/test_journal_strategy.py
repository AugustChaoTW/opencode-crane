"""Tests for journal strategy service."""

from __future__ import annotations

import importlib


def _load():
    return importlib.import_module("crane.services.journal_strategy_service")


class TestPaperAttributes:
    def test_detect_application_system(self, tmp_path):
        svc = _load()
        service = svc.JournalRecommendationService()

        tex_file = tmp_path / "test.tex"
        tex_file.write_text(r"""
\title{Production System}
\section{Introduction}
Our production system achieves 1000 QPS with 0.52ms P99 latency.
""")
        attrs = service.analyze_paper_attributes(tex_file)

        assert attrs.paper_type == svc.PaperType.APPLICATION_SYSTEM

    def test_detect_theoretical_diagnostic(self, tmp_path):
        svc = _load()
        service = svc.JournalRecommendationService()

        tex_file = tmp_path / "test.tex"
        tex_file.write_text(r"""
\title{Theoretical Framework}
\section{Introduction}
We prove a theorem about well-posedness and Hadamard conditions.
""")
        attrs = service.analyze_paper_attributes(tex_file)

        assert attrs.paper_type == svc.PaperType.THEORETICAL_DIAGNOSTIC

    def test_detect_survey_review(self, tmp_path):
        svc = _load()
        service = svc.JournalRecommendationService()

        tex_file = tmp_path / "test.tex"
        tex_file.write_text(r"""
\title{Comprehensive Survey}
\section{Introduction}
This survey provides a comprehensive taxonomy of methods.
""")
        attrs = service.analyze_paper_attributes(tex_file)

        assert attrs.paper_type == svc.PaperType.SURVEY_REVIEW

    def test_detect_survey_from_abstract(self, tmp_path):
        svc = _load()
        service = svc.JournalRecommendationService()

        tex_file = tmp_path / "test.tex"
        tex_file.write_text(r"""
\title{Recent Advances in Deep Learning}
\begin{abstract}
This paper provides a comprehensive survey of deep learning methods
from 2015 to 2025. We review the literature and provide a taxonomy.
\end{abstract}
""")
        attrs = service.analyze_paper_attributes(tex_file)

        assert attrs.paper_type == svc.PaperType.SURVEY_REVIEW

    def test_empirical_with_related_work_not_survey(self, tmp_path):
        """Papers with 'related work' sections should NOT be classified as survey."""
        svc = _load()
        service = svc.JournalRecommendationService()

        tex_file = tmp_path / "test.tex"
        tex_file.write_text(r"""
\title{A Novel Approach for Sentiment Analysis}
\begin{abstract}
We propose a new method for sentiment analysis using transformer models.
Our approach achieves state-of-the-art results on three benchmarks.
\end{abstract}
\section{Introduction}
We review related work in sentiment analysis and propose improvements.
\section{Related Work}
A comprehensive review of existing methods shows gaps in current approaches.
\section{Method}
Our model uses attention mechanisms with 12 layers.
\section{Experiments}
We evaluate on SST-2, IMDB, and Yelp datasets with 85.3\% accuracy.
Our ablation study confirms each component's contribution.
\section{Results}
Table 1 shows baselines and our method. F1 score improved by 3.2\%.
""")
        attrs = service.analyze_paper_attributes(tex_file)

        assert attrs.paper_type != svc.PaperType.SURVEY_REVIEW
        assert attrs.paper_type == svc.PaperType.EMPIRICAL_STUDY

    def test_system_paper_not_survey(self, tmp_path):
        """System papers with 'review' in text should still be APPLICATION_SYSTEM."""
        svc = _load()
        service = svc.JournalRecommendationService()

        tex_file = tmp_path / "test.tex"
        tex_file.write_text(r"""
\title{Distributed Training System for Large Models}
\begin{abstract}
We present a distributed training system achieving 10000 QPS
with 0.3ms P99 latency across 64 GPUs.
\end{abstract}
\section{Introduction}
We review the current landscape of distributed training frameworks.
\section{System Architecture}
Our microservice architecture uses Kubernetes deployment.
The engineering challenges include latency optimization and throughput scaling.
\section{Evaluation}
Production deployment handles 1M requests per hour.
""")
        attrs = service.analyze_paper_attributes(tex_file)

        assert attrs.paper_type != svc.PaperType.SURVEY_REVIEW
        assert attrs.paper_type == svc.PaperType.APPLICATION_SYSTEM

    def test_theoretical_not_survey(self, tmp_path):
        """Theoretical papers should not be misclassified as survey."""
        svc = _load()
        service = svc.JournalRecommendationService()

        tex_file = tmp_path / "test.tex"
        tex_file.write_text(r"""
\title{Convergence Bounds for Non-Convex Optimization}
\begin{abstract}
We prove a theorem about convergence rates under Hadamard conditions.
Our proof establishes well-posedness for the gradient flow.
\end{abstract}
\section{Related Work}
We review existing theoretical results in optimization.
\section{Theorem}
Theorem 1: Under assumptions A1-A3, the algorithm converges.
Proof: By induction on the iteration count...
Lemma 2: The gradient norm is bounded.
""")
        attrs = service.analyze_paper_attributes(tex_file)

        assert attrs.paper_type != svc.PaperType.SURVEY_REVIEW
        assert attrs.paper_type == svc.PaperType.THEORETICAL_DIAGNOSTIC

    def test_detect_survey_from_title_pattern(self, tmp_path):
        """Title patterns like 'This paper is a survey' should trigger survey."""
        svc = _load()
        service = svc.JournalRecommendationService()

        tex_file = tmp_path / "test.tex"
        tex_file.write_text(r"""
\title{A Survey of Reinforcement Learning Methods}
\begin{abstract}
This paper is a survey of reinforcement learning methods.
\end{abstract}
""")
        attrs = service.analyze_paper_attributes(tex_file)

        assert attrs.paper_type == svc.PaperType.SURVEY_REVIEW

    def test_detect_survey_systematic_review(self, tmp_path):
        """'Systematic review' in title should trigger survey."""
        svc = _load()
        service = svc.JournalRecommendationService()

        tex_file = tmp_path / "test.tex"
        tex_file.write_text(r"""
\title{A Systematic Review of Federated Learning}
\begin{abstract}
We conduct a systematic review of federated learning approaches.
\end{abstract}
""")
        attrs = service.analyze_paper_attributes(tex_file)

        assert attrs.paper_type == svc.PaperType.SURVEY_REVIEW


class TestJournalFiltering:
    def test_filter_by_scope(self):
        svc = _load()
        service = svc.JournalRecommendationService()

        attrs = svc.PaperAttributes(
            paper_type=svc.PaperType.APPLICATION_SYSTEM,
            research_focus="Sentiment Analysis",
            core_contribution="Repair Pipeline",
            main_metrics=["QPS", "latency"],
            validation_scale="18M samples",
            suitable_journal_types=["ACM_ESWA", "IEEE_TAC"],
        )

        journals = service.filter_journals_by_scope(attrs)

        assert len(journals) > 0
        assert any(j.scope_fit > 0 for j in journals)

    def test_priority_score_calculation(self):
        svc = _load()
        service = svc.JournalRecommendationService()

        journals = [
            svc.JournalInfo(
                name="Test",
                abbreviation="TEST",
                impact_factor=10.0,
                acceptance_rate=0.25,
                review_timeline_months=(3, 5),
                scope="test",
                scope_fit=0.8,
                apc=0.0,
                desk_rejection_rate=0.1,
                tier=svc.JournalTier.TIER_1,
            )
        ]

        scored = service.calculate_priority_scores(journals)

        assert scored[0].priority_score > 0


class TestSubmissionStrategy:
    def test_create_strategy(self, tmp_path):
        svc = _load()
        service = svc.JournalRecommendationService()

        attrs = svc.PaperAttributes(
            paper_type=svc.PaperType.APPLICATION_SYSTEM,
            research_focus="Sentiment Analysis",
            core_contribution="Repair Pipeline",
            main_metrics=["QPS", "latency"],
            validation_scale="18M samples",
            suitable_journal_types=["ACM_ESWA", "IEEE_TAC", "IEEE_TAI"],
        )

        strategy = service.create_submission_strategy(attrs)

        assert len(strategy.target_journals) > 0
        assert len(strategy.checklist) > 0

    def test_framing_suggestions(self):
        svc = _load()
        service = svc.JournalRecommendationService()

        attrs = svc.PaperAttributes(
            paper_type=svc.PaperType.APPLICATION_SYSTEM,
            research_focus="Sentiment Analysis",
            core_contribution="Repair Pipeline",
            main_metrics=["QPS", "latency"],
            validation_scale="18M samples",
            suitable_journal_types=["IEEE_TNNLS"],
        )

        strategy = service.create_submission_strategy(attrs)

        assert len(strategy.framing_suggestions) > 0


class TestYAMLDrivenJournalDatabase:
    def test_all_yaml_journals_loaded(self):
        svc = _load()
        service = svc.JournalRecommendationService()

        assert len(service._journals) >= 18

    def test_no_hardcoded_journal_database_attribute(self):
        svc = _load()
        assert not hasattr(svc.JournalRecommendationService, "JOURNAL_DATABASE")

    def test_known_journals_present(self):
        svc = _load()
        service = svc.JournalRecommendationService()

        expected_abbrs = {
            "IEEE TPAMI",
            "IEEE TNNLS",
            "IEEE TSE",
            "IEEE TKDE",
            "ACM CSUR",
            "ACM TOCS",
            "ACM TOSEM",
            "Nat Mach Intell",
            "AIJ",
            "ESWA",
            "INS",
            "KBS",
            "NN",
            "PR",
            "CVIU",
            "JMLR",
            "MLJ",
            "IJCV",
        }
        loaded_abbrs = {j.abbreviation for j in service._journals.values()}

        assert expected_abbrs.issubset(loaded_abbrs)

    def test_journal_info_fields_populated(self):
        svc = _load()
        service = svc.JournalRecommendationService()

        for key, journal in service._journals.items():
            assert journal.name, f"{key} missing name"
            assert journal.abbreviation, f"{key} missing abbreviation"
            assert journal.impact_factor > 0, f"{key} has zero impact factor"
            assert journal.acceptance_rate > 0, f"{key} has zero acceptance rate"
            assert journal.review_timeline_months[0] > 0, f"{key} invalid timeline"
            assert journal.scope, f"{key} missing scope"
            assert journal.tier in (
                svc.JournalTier.TIER_1,
                svc.JournalTier.TIER_2,
                svc.JournalTier.TIER_3,
            )


class TestTierAssignment:
    def test_high_impact_is_tier1(self):
        svc = _load()
        service = svc.JournalRecommendationService()

        tpami = service._journals.get("IEEE_TPAMI")
        assert tpami is not None
        assert tpami.impact_factor >= 10
        assert tpami.tier == svc.JournalTier.TIER_1

    def test_medium_impact_is_tier2(self):
        svc = _load()
        service = svc.JournalRecommendationService()

        eswa = service._journals.get("ESWA")
        assert eswa is not None
        assert 7 <= eswa.impact_factor < 10
        assert eswa.tier == svc.JournalTier.TIER_2

    def test_low_impact_is_tier3(self):
        svc = _load()
        service = svc.JournalRecommendationService()

        tocs = service._journals.get("ACM_TOCS")
        assert tocs is not None
        assert tocs.impact_factor < 7
        assert tocs.tier == svc.JournalTier.TIER_3

    def test_top_journals_by_impact_factor_ranked(self):
        svc = _load()
        service = svc.JournalRecommendationService()

        tier1 = [j for j in service._journals.values() if j.tier == svc.JournalTier.TIER_1]
        assert len(tier1) >= 5
        sorted_by_if = sorted(tier1, key=lambda j: -j.impact_factor)
        assert sorted_by_if[0].impact_factor > sorted_by_if[-1].impact_factor


class TestAllPaperTypesGetJournals:
    def test_application_system_gets_journals(self):
        svc = _load()
        service = svc.JournalRecommendationService()

        keys = service._suitable_keys_for_type(svc.PaperType.APPLICATION_SYSTEM)
        assert len(keys) >= 3
        abbrs = {service._journals[k].abbreviation for k in keys}
        assert "ESWA" in abbrs

    def test_theoretical_gets_journals(self):
        svc = _load()
        service = svc.JournalRecommendationService()

        keys = service._suitable_keys_for_type(svc.PaperType.THEORETICAL_DIAGNOSTIC)
        assert len(keys) >= 3
        abbrs = {service._journals[k].abbreviation for k in keys}
        assert "IEEE TNNLS" in abbrs

    def test_empirical_gets_journals(self):
        svc = _load()
        service = svc.JournalRecommendationService()

        keys = service._suitable_keys_for_type(svc.PaperType.EMPIRICAL_STUDY)
        assert len(keys) >= 10

    def test_survey_gets_journals(self):
        svc = _load()
        service = svc.JournalRecommendationService()

        keys = service._suitable_keys_for_type(svc.PaperType.SURVEY_REVIEW)
        assert len(keys) >= 1
        abbrs = {service._journals[k].abbreviation for k in keys}
        assert "ACM CSUR" in abbrs


class TestAnalyzeAttributesDynamic:
    def test_empirical_paper_gets_dynamic_keys(self, tmp_path):
        svc = _load()
        service = svc.JournalRecommendationService()

        tex = tmp_path / "paper.tex"
        tex.write_text(
            r"\title{Benchmark Study}"
            "\n"
            r"\section{Experiments}"
            "\n"
            "We evaluate on multiple datasets with accuracy and F1 baselines.",
        )

        attrs = service.analyze_paper_attributes(tex)

        assert attrs.paper_type == svc.PaperType.EMPIRICAL_STUDY
        for key in attrs.suitable_journal_types:
            assert key in service._journals, f"key {key} not in loaded journals"

    def test_strategy_from_analyzed_paper(self, tmp_path):
        svc = _load()
        service = svc.JournalRecommendationService()

        tex = tmp_path / "paper.tex"
        tex.write_text(
            r"\title{Production System}"
            "\n"
            r"\section{Introduction}"
            "\n"
            "Our system achieves 5000 QPS with sub-millisecond latency.",
        )

        attrs = service.analyze_paper_attributes(tex)
        strategy = service.create_submission_strategy(attrs)

        assert strategy.paper_type == svc.PaperType.APPLICATION_SYSTEM
        all_recommended = (
            strategy.target_journals + strategy.backup_journals + strategy.safe_journals
        )
        assert len(all_recommended) >= 1


class TestBackwardCompatibility:
    def test_existing_key_ieee_tnnls_still_resolves(self):
        svc = _load()
        service = svc.JournalRecommendationService()

        attrs = svc.PaperAttributes(
            paper_type=svc.PaperType.THEORETICAL_DIAGNOSTIC,
            research_focus="Representation Learning",
            core_contribution="Diagnostic Framework",
            main_metrics=["CKA"],
            validation_scale="Standard",
            suitable_journal_types=["IEEE_TNNLS"],
        )

        journals = service.filter_journals_by_scope(attrs)
        assert len(journals) == 1
        assert "TNNLS" in journals[0].abbreviation

    def test_existing_key_ieee_tkde_still_resolves(self):
        svc = _load()
        service = svc.JournalRecommendationService()

        attrs = svc.PaperAttributes(
            paper_type=svc.PaperType.EMPIRICAL_STUDY,
            research_focus="Data Mining",
            core_contribution="Novel Method",
            main_metrics=["accuracy"],
            validation_scale="Standard",
            suitable_journal_types=["IEEE_TKDE"],
        )

        journals = service.filter_journals_by_scope(attrs)
        assert len(journals) == 1
        assert "TKDE" in journals[0].abbreviation

    def test_unknown_legacy_keys_fall_back_to_type_matching(self):
        svc = _load()
        service = svc.JournalRecommendationService()

        attrs = svc.PaperAttributes(
            paper_type=svc.PaperType.APPLICATION_SYSTEM,
            research_focus="Test",
            core_contribution="Test",
            main_metrics=[],
            validation_scale="Standard",
            suitable_journal_types=["NONEXISTENT_KEY"],
        )

        journals = service.filter_journals_by_scope(attrs)
        assert len(journals) > 0

    def test_public_method_signatures_unchanged(self):
        svc = _load()
        import inspect

        service_cls = svc.JournalRecommendationService
        assert hasattr(service_cls, "analyze_paper_attributes")
        assert hasattr(service_cls, "filter_journals_by_scope")
        assert hasattr(service_cls, "calculate_priority_scores")
        assert hasattr(service_cls, "create_submission_strategy")
        assert hasattr(service_cls, "to_dict")

        sig = inspect.signature(service_cls.filter_journals_by_scope)
        assert "paper_attrs" in sig.parameters
