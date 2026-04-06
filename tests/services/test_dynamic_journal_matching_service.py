"""Tests for DynamicJournalMatchingService."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from crane.models.paper_profile import PaperProfile, PaperType, EvidencePattern
from crane.services.dynamic_journal_matching_service import (
    DynamicJournalMatchingService,
    TrendTrackingModule,
    RealTimeRankingEngine,
    IntelligentRecommendationEngine,
    TrendMetric,
    JournalTrendProfile,
)


@pytest.fixture
def sample_paper_profile() -> PaperProfile:
    """Create a sample paper profile."""
    return PaperProfile(
        paper_type=PaperType.EMPIRICAL,
        method_family="deep learning",
        evidence_pattern=EvidencePattern.BENCHMARK_HEAVY,
        validation_scale="large-scale",
    )


@pytest.fixture
def trend_module() -> TrendTrackingModule:
    """Create a trend tracking module."""
    return TrendTrackingModule()


@pytest.fixture
def ranking_engine(trend_module: TrendTrackingModule) -> RealTimeRankingEngine:
    """Create a ranking engine."""
    return RealTimeRankingEngine(trend_module)


class TestTrendMetric:
    """Test TrendMetric class."""

    def test_add_value(self) -> None:
        """Test adding values to trend metric."""
        metric = TrendMetric("impact_factor")
        metric.add_value(5.0)
        metric.add_value(5.5)
        metric.add_value(6.0)

        assert len(metric.values) == 3
        assert metric.values == [5.0, 5.5, 6.0]

    def test_trend_direction_up(self) -> None:
        """Test upward trend detection."""
        metric = TrendMetric("impact_factor")
        metric.add_value(5.0)
        metric.add_value(5.5)
        metric.add_value(6.0)

        assert metric.trend_direction == "up"

    def test_trend_direction_down(self) -> None:
        """Test downward trend detection."""
        metric = TrendMetric("impact_factor")
        metric.add_value(6.0)
        metric.add_value(5.5)
        metric.add_value(5.0)

        assert metric.trend_direction == "down"

    def test_trend_direction_stable(self) -> None:
        """Test stable trend detection."""
        metric = TrendMetric("impact_factor")
        metric.add_value(5.0)
        metric.add_value(5.0)
        metric.add_value(5.0)

        assert metric.trend_direction == "stable"

    def test_get_trend_score(self) -> None:
        """Test trend score calculation."""
        metric = TrendMetric("impact_factor")
        metric.add_value(5.0)
        metric.add_value(5.5)
        metric.add_value(6.0)

        assert metric.get_trend_score() == 1.0

        metric2 = TrendMetric("impact_factor")
        metric2.add_value(6.0)
        metric2.add_value(5.5)
        metric2.add_value(5.0)

        assert metric2.get_trend_score() == 0.0


class TestJournalTrendProfile:
    """Test JournalTrendProfile class."""

    def test_initialization(self) -> None:
        """Test profile initialization."""
        profile = JournalTrendProfile("IEEE TPAMI")
        assert profile.journal_name == "IEEE TPAMI"
        assert profile.impact_factor_trend.metric_name == "impact_factor"

    def test_get_overall_trend_score(self) -> None:
        """Test overall trend score calculation."""
        profile = JournalTrendProfile("IEEE TPAMI")
        profile.impact_factor_trend.add_value(5.0)
        profile.impact_factor_trend.add_value(5.5)
        profile.impact_factor_trend.add_value(6.0)

        score = profile.get_overall_trend_score()
        assert 0.0 <= score <= 1.0


class TestTrendTrackingModule:
    """Test TrendTrackingModule class."""

    def test_track_metric(self, trend_module: TrendTrackingModule) -> None:
        """Test metric tracking."""
        trend_module.track_metric("IEEE TPAMI", "impact_factor", 5.0)
        trend_module.track_metric("IEEE TPAMI", "impact_factor", 5.5)

        profile = trend_module.get_trend_profile("IEEE TPAMI")
        assert profile is not None
        assert len(profile.impact_factor_trend.values) == 2

    def test_track_multiple_metrics(self, trend_module: TrendTrackingModule) -> None:
        """Test tracking multiple metrics."""
        trend_module.track_metric("IEEE TPAMI", "impact_factor", 5.0)
        trend_module.track_metric("IEEE TPAMI", "acceptance_rate", 0.15)
        trend_module.track_metric("IEEE TPAMI", "citation_velocity", 2.5)

        profile = trend_module.get_trend_profile("IEEE TPAMI")
        assert profile is not None
        assert len(profile.impact_factor_trend.values) == 1
        assert len(profile.acceptance_rate_trend.values) == 1
        assert len(profile.citation_velocity_trend.values) == 1

    def test_get_trending_journals(self, trend_module: TrendTrackingModule) -> None:
        """Test getting trending journals."""
        trend_module.track_metric("IEEE TPAMI", "impact_factor", 5.0)
        trend_module.track_metric("IEEE TPAMI", "impact_factor", 6.0)

        trend_module.track_metric("JMLR", "impact_factor", 3.0)
        trend_module.track_metric("JMLR", "impact_factor", 2.5)

        trending = trend_module.get_trending_journals(top_k=2)
        assert len(trending) <= 2
        assert trending[0][0] == "IEEE TPAMI"


class TestRealTimeRankingEngine:
    """Test RealTimeRankingEngine class."""

    def test_initialization(self, ranking_engine: RealTimeRankingEngine) -> None:
        """Test engine initialization."""
        assert len(ranking_engine.DIMENSIONS) == 5
        assert sum(ranking_engine.weights.values()) == pytest.approx(1.0)

    def test_compute_dimension_scores(
        self, ranking_engine: RealTimeRankingEngine, sample_paper_profile: PaperProfile
    ) -> None:
        """Test dimension score computation."""
        from crane.services.journal_matching_service import JournalMatchingService

        service = JournalMatchingService()
        fits = service.match(sample_paper_profile)

        if fits:
            scores = ranking_engine.compute_dimension_scores(fits[0])
            assert "scope_fit" in scores
            assert "contribution_fit" in scores
            assert "evaluation_fit" in scores
            assert "trend_score" in scores
            assert "cost_efficiency" in scores

    def test_compute_dynamic_rank(
        self, ranking_engine: RealTimeRankingEngine, sample_paper_profile: PaperProfile
    ) -> None:
        """Test dynamic rank computation."""
        from crane.services.journal_matching_service import JournalMatchingService

        service = JournalMatchingService()
        fits = service.match(sample_paper_profile)

        if fits:
            rank = ranking_engine.compute_dynamic_rank(fits[0])
            assert 0.0 <= rank <= 100.0


class TestIntelligentRecommendationEngine:
    """Test IntelligentRecommendationEngine class."""

    def test_record_user_choice(self, ranking_engine: RealTimeRankingEngine) -> None:
        """Test recording user choices."""
        engine = IntelligentRecommendationEngine(ranking_engine)
        engine.record_user_choice("user1", "IEEE TPAMI")
        engine.record_user_choice("user1", "JMLR")

        assert "user1" in engine.user_history
        assert len(engine.user_history["user1"]) == 2

    def test_learn_user_preferences(self, ranking_engine: RealTimeRankingEngine) -> None:
        """Test learning user preferences."""
        engine = IntelligentRecommendationEngine(ranking_engine)
        scores = {"scope_fit": 85.0, "contribution_fit": 90.0}
        engine.learn_user_preferences("user1", scores)

        assert "user1" in engine.user_preferences
        assert "scope_fit" in engine.user_preferences["user1"]

    def test_get_personalized_recommendations(
        self, ranking_engine: RealTimeRankingEngine, sample_paper_profile: PaperProfile
    ) -> None:
        """Test getting personalized recommendations."""
        from crane.services.journal_matching_service import JournalMatchingService

        service = JournalMatchingService()
        fits = service.match(sample_paper_profile)

        engine = IntelligentRecommendationEngine(ranking_engine)
        engine.record_user_choice("user1", "IEEE TPAMI")

        if fits:
            recs = engine.get_personalized_recommendations("user1", fits, top_k=3)
            assert len(recs) <= 3
            assert all(len(rec) == 3 for rec in recs)


class TestDynamicJournalMatchingService:
    """Test DynamicJournalMatchingService class."""

    def test_initialization(self) -> None:
        """Test service initialization."""
        service = DynamicJournalMatchingService()
        assert service.base_service is not None
        assert service.trend_module is not None
        assert service.ranking_engine is not None
        assert service.recommendation_engine is not None

    def test_match_with_trends(self, sample_paper_profile: PaperProfile) -> None:
        """Test matching with trends."""
        service = DynamicJournalMatchingService()
        result = service.match_with_trends(sample_paper_profile)

        assert "ranked_journals" in result
        assert "personalized_recommendations" in result
        assert "trending_journals" in result
        assert len(result["ranked_journals"]) > 0

    def test_match_with_user_id(self, sample_paper_profile: PaperProfile) -> None:
        """Test matching with user personalization."""
        service = DynamicJournalMatchingService()
        service.record_user_submission("user1", "IEEE TPAMI")

        result = service.match_with_trends(sample_paper_profile, user_id="user1")
        assert len(result["personalized_recommendations"]) > 0

    def test_update_journal_metrics(self) -> None:
        """Test updating journal metrics."""
        service = DynamicJournalMatchingService()
        metrics = {"impact_factor": 5.5, "acceptance_rate": 0.15}
        service.update_journal_metrics("IEEE TPAMI", metrics)

        trend = service.get_trend_analysis("IEEE TPAMI")
        assert trend is not None
        assert trend["journal_name"] == "IEEE TPAMI"

    def test_record_user_submission(self) -> None:
        """Test recording user submission."""
        service = DynamicJournalMatchingService()
        service.record_user_submission("user1", "IEEE TPAMI")

        assert "user1" in service.recommendation_engine.user_history

    def test_get_trend_analysis(self) -> None:
        """Test getting trend analysis."""
        service = DynamicJournalMatchingService()
        service.update_journal_metrics("IEEE TPAMI", {"impact_factor": 5.0})
        service.update_journal_metrics("IEEE TPAMI", {"impact_factor": 5.5})

        analysis = service.get_trend_analysis("IEEE TPAMI")
        assert analysis is not None
        assert "impact_factor_trend" in analysis
        assert "overall_trend_score" in analysis

    def test_nonexistent_journal_trend(self) -> None:
        """Test getting trend for nonexistent journal."""
        service = DynamicJournalMatchingService()
        analysis = service.get_trend_analysis("NonexistentJournal")
        assert analysis is None
