"""Dynamic journal matching with trend tracking and real-time ranking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from crane.models.paper_profile import JournalFit, PaperProfile
from crane.services.journal_matching_service import JournalMatchingService


@dataclass
class TrendMetric:
    """Single metric trend data."""

    metric_name: str
    values: list[float] = field(default_factory=list)
    timestamps: list[datetime] = field(default_factory=list)
    trend_direction: str = "stable"  # "up", "down", "stable"

    def add_value(self, value: float, timestamp: datetime | None = None) -> None:
        """Add a new metric value."""
        ts = timestamp or datetime.now()
        self.values.append(value)
        self.timestamps.append(ts)
        self._update_trend()

    def _update_trend(self) -> None:
        """Update trend direction based on recent values."""
        if len(self.values) < 2:
            self.trend_direction = "stable"
            return

        recent = self.values[-3:] if len(self.values) >= 3 else self.values
        if len(recent) >= 2:
            if recent[-1] > recent[0]:
                self.trend_direction = "up"
            elif recent[-1] < recent[0]:
                self.trend_direction = "down"
            else:
                self.trend_direction = "stable"

    def get_trend_score(self) -> float:
        """Return trend score: 1.0 (up), 0.5 (stable), 0.0 (down)."""
        if self.trend_direction == "up":
            return 1.0
        elif self.trend_direction == "down":
            return 0.0
        else:
            return 0.5


@dataclass
class JournalTrendProfile:
    """Trend data for a single journal."""

    journal_name: str
    impact_factor_trend: TrendMetric = field(default_factory=lambda: TrendMetric("impact_factor"))
    acceptance_rate_trend: TrendMetric = field(
        default_factory=lambda: TrendMetric("acceptance_rate")
    )
    citation_velocity_trend: TrendMetric = field(
        default_factory=lambda: TrendMetric("citation_velocity")
    )
    review_speed_trend: TrendMetric = field(default_factory=lambda: TrendMetric("review_speed"))
    last_updated: datetime = field(default_factory=datetime.now)

    def get_overall_trend_score(self) -> float:
        """Weighted average of all trend scores."""
        scores = [
            self.impact_factor_trend.get_trend_score() * 0.4,
            self.acceptance_rate_trend.get_trend_score() * 0.3,
            self.citation_velocity_trend.get_trend_score() * 0.2,
            self.review_speed_trend.get_trend_score() * 0.1,
        ]
        return sum(scores)


class TrendTrackingModule:
    """Track journal metrics trends over time."""

    def __init__(self):
        """Initialize trend tracking."""
        self.journal_trends: dict[str, JournalTrendProfile] = {}

    def track_metric(
        self, journal_name: str, metric_name: str, value: float, timestamp: datetime | None = None
    ) -> None:
        """Track a metric value for a journal."""
        if journal_name not in self.journal_trends:
            self.journal_trends[journal_name] = JournalTrendProfile(journal_name)

        profile = self.journal_trends[journal_name]
        ts = timestamp or datetime.now()

        if metric_name == "impact_factor":
            profile.impact_factor_trend.add_value(value, ts)
        elif metric_name == "acceptance_rate":
            profile.acceptance_rate_trend.add_value(value, ts)
        elif metric_name == "citation_velocity":
            profile.citation_velocity_trend.add_value(value, ts)
        elif metric_name == "review_speed":
            profile.review_speed_trend.add_value(value, ts)

        profile.last_updated = ts

    def get_trend_profile(self, journal_name: str) -> JournalTrendProfile | None:
        """Get trend profile for a journal."""
        return self.journal_trends.get(journal_name)

    def get_trending_journals(self, top_k: int = 5) -> list[tuple[str, float]]:
        """Get journals with strongest upward trends."""
        trends = [
            (name, profile.get_overall_trend_score())
            for name, profile in self.journal_trends.items()
        ]
        trends.sort(key=lambda x: x[1], reverse=True)
        return trends[:top_k]


class RealTimeRankingEngine:
    """5-dimensional dynamic ranking of journals."""

    DIMENSIONS = [
        "scope_fit",
        "contribution_fit",
        "evaluation_fit",
        "trend_score",
        "cost_efficiency",
    ]

    def __init__(self, trend_module: TrendTrackingModule):
        """Initialize ranking engine."""
        self.trend_module = trend_module
        self.weights = {
            "scope_fit": 0.25,
            "contribution_fit": 0.25,
            "evaluation_fit": 0.25,
            "trend_score": 0.15,
            "cost_efficiency": 0.10,
        }

    def compute_dimension_scores(
        self, journal_fit: JournalFit, trend_profile: JournalTrendProfile | None = None
    ) -> dict[str, float]:
        """Compute 5-dimensional scores for a journal."""
        scores = {
            "scope_fit": journal_fit.scope_fit,
            "contribution_fit": journal_fit.contribution_style_fit,
            "evaluation_fit": journal_fit.evaluation_style_fit,
            "trend_score": trend_profile.get_overall_trend_score() * 100 if trend_profile else 50.0,
            "cost_efficiency": 100.0 - min(journal_fit.cost_assessment.apc_usd / 100, 100.0)
            if journal_fit.cost_assessment
            else 50.0,
        }
        return scores

    def compute_dynamic_rank(
        self, journal_fit: JournalFit, trend_profile: JournalTrendProfile | None = None
    ) -> float:
        """Compute weighted dynamic rank (0-100)."""
        scores = self.compute_dimension_scores(journal_fit, trend_profile)
        weighted_score = sum(scores[dim] * self.weights[dim] for dim in self.DIMENSIONS)
        return min(100.0, max(0.0, weighted_score))

    def rank_journals(
        self, journal_fits: list[JournalFit]
    ) -> list[tuple[JournalFit, float, dict[str, float]]]:
        """Rank journals by dynamic score."""
        ranked = []
        for fit in journal_fits:
            trend = self.trend_module.get_trend_profile(fit.journal_name)
            score = self.compute_dynamic_rank(fit, trend)
            dimensions = self.compute_dimension_scores(fit, trend)
            ranked.append((fit, score, dimensions))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked


class IntelligentRecommendationEngine:
    """Personalized journal recommendations based on history and trends."""

    def __init__(self, ranking_engine: RealTimeRankingEngine):
        """Initialize recommendation engine."""
        self.ranking_engine = ranking_engine
        self.user_history: dict[str, list[str]] = {}  # user_id -> [journal_names]
        self.user_preferences: dict[str, dict[str, float]] = {}  # user_id -> {dimension: weight}

    def record_user_choice(self, user_id: str, journal_name: str) -> None:
        """Record user's journal choice."""
        if user_id not in self.user_history:
            self.user_history[user_id] = []
        self.user_history[user_id].append(journal_name)

    def learn_user_preferences(self, user_id: str, dimension_scores: dict[str, float]) -> None:
        """Learn user preferences from their choices."""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}

        for dim, score in dimension_scores.items():
            if dim not in self.user_preferences[user_id]:
                self.user_preferences[user_id][dim] = 0.0
            # Exponential moving average
            self.user_preferences[user_id][dim] = (
                0.7 * self.user_preferences[user_id][dim] + 0.3 * score
            )

    def get_personalized_recommendations(
        self, user_id: str, journal_fits: list[JournalFit], top_k: int = 5
    ) -> list[tuple[JournalFit, float, str]]:
        """Get personalized recommendations for a user."""
        ranked = self.ranking_engine.rank_journals(journal_fits)

        # Apply user preference boost
        if user_id in self.user_preferences:
            prefs = self.user_preferences[user_id]
            boosted = []
            for fit, score, dims in ranked:
                boost = sum(dims.get(dim, 0) * (prefs.get(dim, 0) / 100) for dim in prefs)
                boosted_score = score + boost * 5  # 5% max boost
                boosted.append((fit, boosted_score, dims))
            ranked = sorted(boosted, key=lambda x: x[1], reverse=True)

        # Generate recommendations with rationale
        recommendations = []
        for i, (fit, score, dims) in enumerate(ranked[:top_k]):
            if i == 0:
                rationale = "Best overall fit based on your profile and journal trends"
            elif i == 1:
                rationale = "Strong backup option with complementary strengths"
            else:
                rationale = f"Solid fit with {dims.get('trend_score', 0):.0f}/100 trend momentum"

            recommendations.append((fit, score, rationale))

        return recommendations


class DynamicJournalMatchingService:
    """Unified service for dynamic journal matching with trends and personalization."""

    def __init__(self, profiles_path: str | Path | None = None):
        """Initialize service with journal profiles."""
        self.base_service = JournalMatchingService(profiles_path)
        self.trend_module = TrendTrackingModule()
        self.ranking_engine = RealTimeRankingEngine(self.trend_module)
        self.recommendation_engine = IntelligentRecommendationEngine(self.ranking_engine)

    def match_with_trends(
        self, profile: PaperProfile, user_id: str | None = None, budget_usd: float | None = None
    ) -> dict[str, Any]:
        """Match paper to journals with trend analysis and personalization."""
        # Get base matches
        base_fits = self.base_service.match(profile, budget_usd)

        # Rank with trends
        ranked = self.ranking_engine.rank_journals(base_fits)

        # Get personalized recommendations if user_id provided
        recommendations = []
        if user_id:
            recommendations = self.recommendation_engine.get_personalized_recommendations(
                user_id, base_fits, top_k=5
            )

        # Get trending journals
        trending = self.trend_module.get_trending_journals(top_k=3)

        return {
            "ranked_journals": [
                {
                    "journal_name": fit.journal_name,
                    "overall_fit": fit.overall_fit,
                    "dynamic_rank": score,
                    "dimensions": dims,
                    "trend_direction": (
                        self.trend_module.get_trend_profile(
                            fit.journal_name
                        ).get_overall_trend_score()
                        if self.trend_module.get_trend_profile(fit.journal_name)
                        else 0.5
                    ),
                }
                for fit, score, dims in ranked[:10]
            ],
            "personalized_recommendations": [
                {
                    "journal_name": fit.journal_name,
                    "score": score,
                    "rationale": rationale,
                }
                for fit, score, rationale in recommendations
            ]
            if recommendations
            else [],
            "trending_journals": [
                {"journal_name": name, "trend_score": score} for name, score in trending
            ],
        }

    def update_journal_metrics(
        self, journal_name: str, metrics: dict[str, float], timestamp: datetime | None = None
    ) -> None:
        """Update journal metrics for trend tracking."""
        for metric_name, value in metrics.items():
            self.trend_module.track_metric(journal_name, metric_name, value, timestamp)

    def record_user_submission(self, user_id: str, journal_name: str) -> None:
        """Record user's submission choice."""
        self.recommendation_engine.record_user_choice(user_id, journal_name)

    def get_trend_analysis(self, journal_name: str) -> dict[str, Any] | None:
        """Get detailed trend analysis for a journal."""
        profile = self.trend_module.get_trend_profile(journal_name)
        if not profile:
            return None

        return {
            "journal_name": journal_name,
            "impact_factor_trend": {
                "direction": profile.impact_factor_trend.trend_direction,
                "values": profile.impact_factor_trend.values[-5:],
            },
            "acceptance_rate_trend": {
                "direction": profile.acceptance_rate_trend.trend_direction,
                "values": profile.acceptance_rate_trend.values[-5:],
            },
            "citation_velocity_trend": {
                "direction": profile.citation_velocity_trend.trend_direction,
                "values": profile.citation_velocity_trend.values[-5:],
            },
            "review_speed_trend": {
                "direction": profile.review_speed_trend.trend_direction,
                "values": profile.review_speed_trend.values[-5:],
            },
            "overall_trend_score": profile.get_overall_trend_score(),
            "last_updated": profile.last_updated.isoformat(),
        }
