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
