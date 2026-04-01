from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from crane.models.paper_profile import DimensionScore, PaperProfile


@dataclass
class CriticismPattern:
    name: str
    description: str
    severity: str
    dimension: str
    trigger_signals: list[str]
    example_critique: str


@dataclass
class PredictedCriticism:
    pattern: CriticismPattern
    likelihood: float
    matched_signals: list[str]
    suggested_fix: str


@dataclass
class ReviewPrediction:
    criticisms: list[PredictedCriticism]
    overall_sentiment: str
    predicted_decision: str
    confidence: float


class ReviewSimulationService:
    _DEFAULT_PATTERN_FILE = Path(__file__).resolve().parents[3] / "data" / "review_patterns.yaml"
    _GATE_DIMENSIONS = {"methodology", "novelty", "evaluation"}
    _GATE_THRESHOLD = 60.0

    def __init__(self, patterns_path: str | Path | None = None):
        self.patterns_path = (
            Path(patterns_path) if patterns_path is not None else self._DEFAULT_PATTERN_FILE
        )
        self.patterns = self._load_patterns(self.patterns_path)

    def predict_criticisms(
        self,
        dimension_scores: list[DimensionScore],
        profile: PaperProfile,
    ) -> ReviewPrediction:
        score_map = {item.dimension.lower(): item.score for item in dimension_scores}
        gates_failed = any(
            score_map.get(dimension, 100.0) < self._GATE_THRESHOLD
            for dimension in self._GATE_DIMENSIONS
        )
        profile_text = self._profile_text(profile)

        criticisms: list[PredictedCriticism] = []
        for pattern in self.patterns:
            pattern_score = score_map.get(pattern.dimension.lower())
            matched_signals = [
                signal for signal in pattern.trigger_signals if signal.lower() in profile_text
            ]
            likelihood = self._likelihood(pattern, pattern_score, matched_signals)
            if likelihood >= 0.35:
                criticisms.append(
                    PredictedCriticism(
                        pattern=pattern,
                        likelihood=likelihood,
                        matched_signals=matched_signals,
                        suggested_fix=self._suggested_fix(pattern.name),
                    )
                )

        criticisms.sort(key=lambda item: item.likelihood, reverse=True)
        major_high = [
            item
            for item in criticisms
            if item.pattern.severity == "major" and item.likelihood >= 0.55
        ]
        major_high_dimensions = {item.pattern.dimension for item in major_high}

        if gates_failed:
            decision = "reject"
        elif not major_high:
            decision = "accept"
        elif 1 <= len(major_high_dimensions) <= 2:
            decision = "minor_revisions"
        else:
            decision = "major_revisions"

        if decision == "reject" or len(major_high_dimensions) >= 3:
            sentiment = "harsh"
        elif major_high:
            sentiment = "balanced"
        else:
            sentiment = "encouraging"

        confidence = self._prediction_confidence(criticisms, dimension_scores)
        return ReviewPrediction(
            criticisms=criticisms,
            overall_sentiment=sentiment,
            predicted_decision=decision,
            confidence=confidence,
        )

    def generate_mock_review(
        self,
        prediction: ReviewPrediction,
    ) -> str:
        lines = [
            "Summary",
            f"- Sentiment: {prediction.overall_sentiment}",
            f"- Predicted decision: {prediction.predicted_decision}",
            f"- Confidence: {prediction.confidence:.2f}",
            "",
            "Major Points",
        ]

        high_items = [item for item in prediction.criticisms if item.likelihood >= 0.55]
        if not high_items:
            lines.append("- The paper is generally solid with no dominant reviewer concerns.")
        else:
            for item in high_items:
                lines.append(f"- [{item.pattern.severity}] {item.pattern.example_critique}")
                lines.append(f"  Suggested fix: {item.suggested_fix}")

        lines.extend(["", "Minor Notes"])
        medium_items = [item for item in prediction.criticisms if 0.35 <= item.likelihood < 0.55]
        if not medium_items:
            lines.append("- No additional minor notes.")
        else:
            for item in medium_items[:5]:
                lines.append(f"- {item.pattern.description}")

        return "\n".join(lines)

    def _load_patterns(self, path: Path) -> list[CriticismPattern]:
        if not path.exists():
            return []

        with path.open(encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        if not isinstance(payload, dict):
            return []

        raw_patterns = payload.get("patterns", [])
        if not isinstance(raw_patterns, list):
            return []

        patterns: list[CriticismPattern] = []
        for item in raw_patterns:
            if not isinstance(item, dict):
                continue
            trigger_signals = item.get("trigger_signals", [])
            if not isinstance(trigger_signals, list):
                continue
            if not all(isinstance(signal, str) for signal in trigger_signals):
                continue
            patterns.append(
                CriticismPattern(
                    name=str(item.get("name", "")),
                    description=str(item.get("description", "")),
                    severity=str(item.get("severity", "minor")),
                    dimension=str(item.get("dimension", "")),
                    trigger_signals=[
                        signal for signal in trigger_signals if isinstance(signal, str)
                    ],
                    example_critique=str(item.get("example_critique", "")),
                )
            )
        return patterns

    def _profile_text(self, profile: PaperProfile) -> str:
        chunks = [
            profile.problem_domain,
            profile.method_family,
            profile.validation_scale,
            profile.novelty_shape.value,
            profile.evidence_pattern.value,
            " ".join(profile.keywords),
            "code available" if profile.has_code else "code unavailable",
            "appendix" if profile.has_appendix else "no appendix",
        ]
        return " ".join(chunk.lower() for chunk in chunks if chunk)

    def _likelihood(
        self,
        pattern: CriticismPattern,
        score: float | None,
        matched_signals: list[str],
    ) -> float:
        dimension_component = 0.3
        if score is not None:
            if score < 70.0:
                dimension_component = min(0.8, 0.45 + (70.0 - score) / 100.0)
            else:
                dimension_component = max(0.05, 0.2 - (score - 70.0) / 200.0)

        signal_component = 0.0
        if pattern.trigger_signals:
            signal_component = (len(matched_signals) / len(pattern.trigger_signals)) * 0.4

        severity_component = 0.12 if pattern.severity == "major" else 0.04
        likelihood = dimension_component + signal_component + severity_component
        return round(min(1.0, max(0.0, likelihood)), 3)

    def _prediction_confidence(
        self,
        criticisms: list[PredictedCriticism],
        dimension_scores: list[DimensionScore],
    ) -> float:
        if not dimension_scores:
            return 0.2
        avg_score_confidence = sum(item.confidence for item in dimension_scores) / len(
            dimension_scores
        )
        if not criticisms:
            return round(min(1.0, max(0.0, avg_score_confidence * 0.8 + 0.1)), 3)
        avg_likelihood = sum(item.likelihood for item in criticisms) / len(criticisms)
        return round(min(1.0, max(0.0, avg_score_confidence * 0.6 + avg_likelihood * 0.4)), 3)

    def _suggested_fix(self, pattern_name: str) -> str:
        fixes = {
            "novelty_concerns": "Strengthen novelty positioning against closest prior work with explicit comparison.",
            "weak_baselines": "Add recent and competitive baseline methods with reproducible settings.",
            "methodology_unclear": "Expand method section with clear algorithmic steps and implementation details.",
            "insufficient_experiments": "Broaden evaluation with more datasets, ablations, and stress tests.",
            "reproducibility_concerns": "Release code or provide full hyperparameters, seeds, and environment details.",
            "overclaiming": "Tone down claims and align conclusions with observed evidence.",
            "poor_writing_quality": "Revise structure and language for clarity, precision, and readability.",
            "missing_limitations": "Add a dedicated limitations/threats-to-validity subsection.",
            "statistical_rigor": "Include confidence intervals, variance analysis, and significance testing.",
            "presentation_issues": "Improve figure/table readability and ensure captions are self-contained.",
        }
        return fixes.get(
            pattern_name, "Address the issue with targeted evidence and clearer reporting."
        )
