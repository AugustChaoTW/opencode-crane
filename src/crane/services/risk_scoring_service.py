"""Risk Scoring Service - Four-dimensional risk assessment and acceptance prediction."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class RiskLevel(Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class DimensionScore:
    dimension: str
    score: float
    weight: float
    interpretation: str


@dataclass
class RiskAssessment:
    desk_reject_risk: DimensionScore
    reviewer_expectations: DimensionScore
    writing_quality: DimensionScore
    ethics_compliance: DimensionScore
    final_score: float
    acceptance_probability: float
    risk_level: RiskLevel
    recommendation: str


class RiskScoringService:
    """Service for four-dimensional risk assessment and prediction."""

    DIMENSION_WEIGHTS = {
        "desk_reject_risk": 0.25,
        "reviewer_expectations": 0.25,
        "writing_quality": 0.20,
        "ethics_compliance": 0.30,
    }

    ACCEPTANCE_PROBABILITY_MAPPING = {
        (90, 100): (0.95, "Extremely high - expect accept"),
        (80, 89): (0.85, "High - likely accept or minor revision"),
        (70, 79): (0.65, "Moderate - expect minor or major revision"),
        (60, 69): (0.35, "Low - expect major revision or reject"),
        (0, 59): (0.05, "Very low - likely reject"),
    }

    def __init__(self):
        self.assessments: list[RiskAssessment] = []

    def calculate_four_dimensional_score(
        self,
        desk_reject_score: float,
        reviewer_expectations_score: float,
        writing_quality_score: float,
        ethics_compliance_score: float,
    ) -> RiskAssessment:
        """Calculate four-dimensional risk assessment."""

        desk_reject = DimensionScore(
            dimension="Desk Reject Risk",
            score=desk_reject_score,
            weight=self.DIMENSION_WEIGHTS["desk_reject_risk"],
            interpretation=self._interpret_desk_reject(desk_reject_score),
        )

        reviewer_expectations = DimensionScore(
            dimension="Reviewer Expectations",
            score=reviewer_expectations_score,
            weight=self.DIMENSION_WEIGHTS["reviewer_expectations"],
            interpretation=self._interpret_reviewer_expectations(reviewer_expectations_score),
        )

        writing_quality = DimensionScore(
            dimension="Writing Quality",
            score=writing_quality_score,
            weight=self.DIMENSION_WEIGHTS["writing_quality"],
            interpretation=self._interpret_writing_quality(writing_quality_score),
        )

        ethics_compliance = DimensionScore(
            dimension="Ethics Compliance",
            score=ethics_compliance_score,
            weight=self.DIMENSION_WEIGHTS["ethics_compliance"],
            interpretation=self._interpret_ethics_compliance(ethics_compliance_score),
        )

        final_score = (
            desk_reject_score * desk_reject.weight
            + reviewer_expectations_score * reviewer_expectations.weight
            + writing_quality_score * writing_quality.weight
            + ethics_compliance_score * ethics_compliance.weight
        )

        acceptance_prob, prob_interpretation = self._predict_acceptance_probability(final_score)

        risk_level = self._determine_risk_level(final_score)
        recommendation = self._generate_recommendation(
            final_score, risk_level, ethics_compliance_score
        )

        assessment = RiskAssessment(
            desk_reject_risk=desk_reject,
            reviewer_expectations=reviewer_expectations,
            writing_quality=writing_quality,
            ethics_compliance=ethics_compliance,
            final_score=round(final_score, 1),
            acceptance_probability=round(acceptance_prob, 2),
            risk_level=risk_level,
            recommendation=recommendation,
        )

        self.assessments.append(assessment)
        return assessment

    def _interpret_desk_reject(self, score: float) -> str:
        """Interpret desk reject risk score."""
        if score >= 90:
            return "✅ Extremely low risk - scope matches well, novelty clear"
        elif score >= 75:
            return "✅ Low risk - good scope match, reasonable novelty clarity"
        elif score >= 60:
            return "⚠️ Moderate risk - scope or novelty may need clarification"
        elif score >= 45:
            return "❌ High risk - scope or novelty concerns"
        else:
            return "❌ Very high risk - strong mismatch with journal scope"

    def _interpret_reviewer_expectations(self, score: float) -> str:
        """Interpret reviewer expectations score."""
        if score >= 90:
            return "✅ Exceeds expectations - outstanding methodology and experiments"
        elif score >= 80:
            return "✅ Meets expectations - solid methodology, complete experiments"
        elif score >= 70:
            return "✅ Mostly meets - adequate methodology, some experimental gaps"
        elif score >= 60:
            return "⚠️ Below expectations - methodology or experiments need strengthening"
        else:
            return "❌ Significantly below expectations"

    def _interpret_writing_quality(self, score: float) -> str:
        """Interpret writing quality score."""
        if score >= 90:
            return "✅ Excellent - professional writing, clear presentation"
        elif score >= 80:
            return "✅ Good - clear writing, well-organized"
        elif score >= 70:
            return "✅ Acceptable - mostly clear, minor improvements needed"
        elif score >= 60:
            return "⚠️ Fair - writing quality issues detected"
        else:
            return "❌ Poor - significant writing or presentation problems"

    def _interpret_ethics_compliance(self, score: float) -> str:
        """Interpret ethics compliance score."""
        if score >= 95:
            return "✅ Complete - all required statements and approvals present"
        elif score >= 80:
            return "✅ Good - all major requirements met"
        elif score >= 60:
            return "⚠️ Acceptable - some minor statements missing"
        elif score >= 40:
            return "❌ At risk - significant compliance issues"
        else:
            return "🔴 Critical - major ethics violations"

    def _predict_acceptance_probability(self, final_score: float) -> tuple[float, str]:
        """Predict acceptance probability from final score."""
        for (min_score, max_score), (
            prob,
            interpretation,
        ) in self.ACCEPTANCE_PROBABILITY_MAPPING.items():
            if min_score <= final_score <= max_score:
                return prob, interpretation
        return 0.0, "Score out of range"

    def _determine_risk_level(self, final_score: float) -> RiskLevel:
        """Determine overall risk level from final score."""
        if final_score >= 90:
            return RiskLevel.VERY_LOW
        elif final_score >= 80:
            return RiskLevel.LOW
        elif final_score >= 70:
            return RiskLevel.MODERATE
        elif final_score >= 60:
            return RiskLevel.HIGH
        else:
            return RiskLevel.VERY_HIGH

    def _generate_recommendation(
        self, final_score: float, risk_level: RiskLevel, ethics_score: float
    ) -> str:
        """Generate submission recommendation."""
        if ethics_score < 60:
            return "🔴 CRITICAL: Fix ethics compliance issues before submission"

        if risk_level == RiskLevel.VERY_LOW:
            return "✅ READY TO SUBMIT - Confidence: Very High"
        elif risk_level == RiskLevel.LOW:
            return "✅ READY TO SUBMIT - Confidence: High (expect minor revision)"
        elif risk_level == RiskLevel.MODERATE:
            return "⚠️ CAN SUBMIT - But recommend fixing major items first"
        elif risk_level == RiskLevel.HIGH:
            return "❌ NOT RECOMMENDED - High risk of rejection (fix major items)"
        else:
            return "❌ STRONGLY NOT RECOMMENDED - Consider changing journal"

    def get_assessment_summary(self, assessment: RiskAssessment) -> dict[str, Any]:
        """Get summary of assessment."""
        return {
            "final_score": assessment.final_score,
            "acceptance_probability": f"{assessment.acceptance_probability * 100:.0f}%",
            "risk_level": assessment.risk_level.value,
            "recommendation": assessment.recommendation,
            "dimensions": {
                "desk_reject_risk": {
                    "score": assessment.desk_reject_risk.score,
                    "interpretation": assessment.desk_reject_risk.interpretation,
                },
                "reviewer_expectations": {
                    "score": assessment.reviewer_expectations.score,
                    "interpretation": assessment.reviewer_expectations.interpretation,
                },
                "writing_quality": {
                    "score": assessment.writing_quality.score,
                    "interpretation": assessment.writing_quality.interpretation,
                },
                "ethics_compliance": {
                    "score": assessment.ethics_compliance.score,
                    "interpretation": assessment.ethics_compliance.interpretation,
                },
            },
        }

    def compare_assessments(
        self, assessment1: RiskAssessment, assessment2: RiskAssessment
    ) -> dict[str, Any]:
        """Compare two risk assessments."""
        return {
            "assessment_1_score": assessment1.final_score,
            "assessment_2_score": assessment2.final_score,
            "difference": round(assessment2.final_score - assessment1.final_score, 1),
            "assessment_1_probability": assessment1.acceptance_probability,
            "assessment_2_probability": assessment2.acceptance_probability,
            "recommendation": (
                "Assessment 2 is better"
                if assessment2.final_score > assessment1.final_score
                else "Assessment 1 is better"
            ),
        }
