"""Judge Reliability Service - LLM Judge Reliability Diagnostics.

Based on ICLR 2026 paper: "Diagnosing LLM Judge Reliability: 
Conformal Prediction Sets and Transitivity Violations" (Gupta & Kumar, 2026)

Key features:
1. Transitivity Violation Detection - detect directed 3-cycles
2. Conformal Prediction Sets - prediction sets with guaranteed coverage
3. Per-document Reliability Scores - reliability based on set width
4. Cross-judge Agreement Analysis - inter-judge consistency
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class TransitivityResult:
    """Result of transitivity violation detection."""
    violation_rate: float  # Aggregate violation rate
    docs_with_violations: float  # Fraction of docs with >=1 violation
    max_violation_rate: float  # Maximum per-document rate
    has_cycles: bool  # Whether any cycles detected


@dataclass
class ConformalResult:
    """Result of conformal prediction analysis."""
    prediction_set: list[int]  # Set of possible scores
    set_width: int  # Size of prediction set (1-5)
    coverage_guarantee: float  # Theoretical coverage (1-alpha)
    reliability_score: float  # Derived reliability (1-10)


@dataclass
class ReliabilityReport:
    """Combined reliability report for a document."""
    transitivity: TransitivityResult | None
    conformal: ConformalResult | None
    cross_judge_agreement: float | None
    overall_reliability: float  # 1-10 scale
    difficulty_class: str  # easy/medium/hard


class JudgeReliabilityService:
    """Service for evaluating LLM judge reliability."""

    # Criteria that should be most reliable (from paper)
    RELIABLE_CRITERIA = {"relevance", "coherence"}
    # Criteria that are less reliable
    UNRELIABLE_CRITERIA = {"fluency", "consistency"}

    def __init__(self, alpha: float = 0.10):
        """Initialize with significance level alpha."""
        self.alpha = alpha
        # Calibration data from prior evaluations
        self._calibration_scores: dict[str, list[int]] = defaultdict(list)

    def check_transitivity(
        self, pairwise_preferences: list[tuple[str, str, str]]
    ) -> TransitivityResult:
        """Check for transitivity violations (directed 3-cycles).

        Args:
            pairwise_preferences: List of (item_a, item_b, winner) tuples
                where winner is "A" if A>B, "B" if B>A, "tie" if equal

        Returns:
            TransitivityResult with violation metrics
        """
        # Build tournament graph
        edges: set[tuple[str, str]] = set()
        for a, b, winner in pairwise_preferences:
            if winner == "A":
                edges.add((a, b))
            elif winner == "B":
                edges.add((b, a))
            # ties don't form edges

        # Count directed 3-cycles (A>B, B>C, C>A)
        items = set()
        for a, b in edges:
            items.add(a)
            items.add(b)

        total_triples = 0
        cycles = 0
        items_list = list(items)

        for i in range(len(items_list)):
            for j in range(len(items_list)):
                if i == j:
                    continue
                for k in range(len(items_list)):
                    if i == k or j == k:
                        continue
                    a, b, c = items_list[i], items_list[j], items_list[k]
                    total_triples += 1
                    if (a, b) in edges and (b, c) in edges and (c, a) in edges:
                        cycles += 1

        violation_rate = cycles / total_triples if total_triples > 0 else 0.0
        docs_with_violations = 1.0 if cycles > 0 else 0.0

        return TransitivityResult(
            violation_rate=violation_rate,
            docs_with_violations=docs_with_violations,
            max_violation_rate=violation_rate,  # Simplified
            has_cycles=cycles > 0,
        )

    def generate_conformal_set(
        self, score: int, calibration_scores: list[int]
    ) -> ConformalResult:
        """Generate conformal prediction set for a score.

        Args:
            score: The judge's score (1-5)
            calibration_scores: List of calibration scores from prior evaluations

        Returns:
            ConformalResult with prediction set and reliability
        """
        if not calibration_scores:
            # No calibration data - return full uncertainty
            return ConformalResult(
                prediction_set=[1, 2, 3, 4, 5],
                set_width=5,
                coverage_guarantee=1.0 - self.alpha,
                reliability_score=1.0,  # Low reliability
            )

        # Calculate quantile for conformal prediction
        n = len(calibration_scores)
        q_level = int((1 - self.alpha) * (n + 1))
        sorted_scores = sorted(calibration_scores + [score])
        rank = sorted_scores.index(score) + 1

        # Simple conformal approach: use residuals
        residuals = [abs(s - score) for s in calibration_scores]
        residuals_sorted = sorted(residuals)
        threshold = residuals_sorted[min(q_level - 1, len(residuals) - 1)] if residuals else 0

        # Generate prediction set
        prediction_set = [
            s for s in range(1, 6) if abs(s - score) <= threshold
        ]
        if not prediction_set:
            prediction_set = [score]  # At least include the original

        set_width = len(prediction_set)
        coverage = 1.0 - self.alpha

        # Reliability: narrower set = higher reliability
        # Width 1 = score 10, width 5 = score 1
        reliability = max(1.0, 10.0 - (set_width - 1) * 2.0)

        return ConformalResult(
            prediction_set=prediction_set,
            set_width=set_width,
            coverage_guarantee=coverage,
            reliability_score=reliability,
        )

    def analyze_reliability(
        self,
        scores: dict[str, int],
        criterion: str = "general",
    ) -> ReliabilityReport:
        """Analyze reliability of evaluation scores.

        Args:
            scores: Dict of criterion -> score (1-5)
            criterion: The evaluation criterion being analyzed

        Returns:
            ReliabilityReport with overall reliability score
        """
        # Check transitivity (simplified - in practice would need pairwise)
        transitivity = None

        # Generate conformal sets for each criterion
        conformal_results = {}
        for crit, score in scores.items():
            cal_scores = self._calibration_scores.get(crit, [])
            result = self.generate_conformal_set(score, cal_scores)
            conformal_results[crit] = result

        # Calculate average reliability
        if conformal_results:
            avg_reliability = np.mean(
                [r.reliability_score for r in conformal_results.values()]
            )
        else:
            avg_reliability = 5.0  # Neutral

        # Determine difficulty class
        if avg_reliability >= 7.0:
            difficulty = "easy"
        elif avg_reliability >= 4.0:
            difficulty = "medium"
        else:
            difficulty = "hard"

        # Check criterion-specific reliability
        if criterion in self.RELIABLE_CRITERIA:
            # Boost reliability for reliable criteria
            avg_reliability = min(10.0, avg_reliability * 1.2)
        elif criterion in self.UNRELIABLE_CRITERIA:
            # Reduce reliability for unreliable criteria
            avg_reliability = max(1.0, avg_reliability * 0.8)

        # Cross-judge agreement (placeholder - would need multiple judges)
        cross_judge = None

        return ReliabilityReport(
            transitivity=transitivity,
            conformal=conformal_results.get(criterion),
            cross_judge_agreement=cross_judge,
            overall_reliability=avg_reliability,
            difficulty_class=difficulty,
        )

    def add_calibration_score(self, criterion: str, score: int) -> None:
        """Add a calibration score for future reliability estimation."""
        self._calibration_scores[criterion].append(score)
        # Keep only recent calibration data
        if len(self._calibration_scores[criterion]) > 100:
            self._calibration_scores[criterion] = (
                self._calibration_scores[criterion][-100:]
            )

    def get_trust_signal(self, reliability: float) -> str:
        """Get human-readable trust signal.

        Args:
            reliability: Reliability score (1-10)

        Returns:
            Trust signal string
        """
        if reliability >= 8.0:
            return "HIGH - Trust this evaluation"
        elif reliability >= 5.0:
            return "MEDIUM - Consider verification"
        else:
            return "LOW - Requires human review"