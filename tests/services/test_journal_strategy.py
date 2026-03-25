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
