"""Q1 Journal Paper Evaluation Service.

Evaluates papers against Q1 journal standards based on common
review criteria from top venues (IEEE TPAMI, NeurIPS, ICML, etc.).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from crane.services.latex_parser import PaperStructure, parse_latex_sections


class EvaluationCategory(Enum):
    WRITING_QUALITY = "writing_quality"
    METHODOLOGY = "methodology"
    NOVELTY = "novelty"
    EVALUATION = "evaluation"
    PRESENTATION = "presentation"
    LIMITATIONS = "limitations"
    REPRODUCIBILITY = "reproducibility"


class Q1Score(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    WEAK = "weak"
    CRITICAL = "critical"


@dataclass
class EvaluationCriterion:
    category: EvaluationCategory
    name: str
    description: str
    weight: float
    score: Q1Score
    evidence: list[str]
    suggestions: list[str]


@dataclass
class Q1Evaluation:
    paper_path: str
    overall_score: float
    readiness: str
    criteria: list[EvaluationCriterion]
    summary: dict[str, Any]


class Q1EvaluationService:
    """Service for evaluating papers against Q1 journal standards."""

    Q1_CRITERIA = {
        EvaluationCategory.WRITING_QUALITY: [
            {
                "name": "Academic Tone",
                "description": "Paper uses formal academic language throughout",
                "weight": 0.15,
                "checks": [
                    (r"\b(awesome|cool|nice|great|amazing)\b", "Informal adjectives detected"),
                    (r"\b(I think|I believe|in my opinion)\b", "Personal opinion language"),
                    (r"\b(a lot of|tons of|loads of)\b", "Informal quantifiers"),
                ],
            },
            {
                "name": "Clarity and Precision",
                "description": "Sentences are clear, unambiguous, and precise",
                "weight": 0.10,
                "checks": [
                    (r"\b(thing|things|stuff)\b", "Vague references"),
                    (r"\b(basically|literally|actually)\b", "Filler words"),
                ],
            },
            {
                "name": "Logical Flow",
                "description": "Arguments flow logically with clear transitions",
                "weight": 0.10,
                "checks": [
                    (r"(?<!\. )(And|But|So)\s+[A-Z]", "Weak transitions"),
                ],
            },
        ],
        EvaluationCategory.METHODOLOGY: [
            {
                "name": "Research Design",
                "description": "Clear research questions and methodology",
                "weight": 0.15,
                "checks": [
                    (
                        r"\\section\{.*[Mm]ethod.*\}|\\section\{.*[Aa]pproach.*\}",
                        "Methodology section present",
                    ),
                ],
            },
            {
                "name": "Technical Rigor",
                "description": "Mathematical formulations and algorithms are correct",
                "weight": 0.10,
                "checks": [
                    (r"\\begin\{equation\}|\\begin\{align\}", "Mathematical formulations present"),
                ],
            },
        ],
        EvaluationCategory.NOVELTY: [
            {
                "name": "Contribution Statement",
                "description": "Clear statement of contributions in introduction",
                "weight": 0.10,
                "checks": [
                    (r"[Cc]ontribution|[Oo]ur [Cc]ontribution", "Contribution statement present"),
                ],
            },
            {
                "name": "Comparison with Prior Work",
                "description": "Clear differentiation from existing methods",
                "weight": 0.05,
                "checks": [
                    (
                        r"[Cc]ompared to|[Uu]nlike|[Dd]iffer from|[Ii]n contrast",
                        "Comparison language present",
                    ),
                ],
            },
        ],
        EvaluationCategory.EVALUATION: [
            {
                "name": "Baseline Comparisons",
                "description": "Comparison with relevant baselines",
                "weight": 0.10,
                "checks": [
                    (
                        r"[Bb]aseline|[Ss]tate-of-the-art|SOTA|[Cc]ompared with",
                        "Baseline comparison present",
                    ),
                ],
            },
            {
                "name": "Statistical Significance",
                "description": "Results include statistical analysis",
                "weight": 0.05,
                "checks": [
                    (
                        r"p\s*[<>=]\s*0\.\d+|confidence interval|standard deviation",
                        "Statistical analysis present",
                    ),
                ],
            },
        ],
        EvaluationCategory.PRESENTATION: [
            {
                "name": "Figure Quality",
                "description": "Figures are clear, labeled, and informative",
                "weight": 0.05,
                "checks": [
                    (r"\\begin\{figure\}", "Figures present"),
                ],
            },
            {
                "name": "Table Clarity",
                "description": "Tables are well-formatted with clear headers",
                "weight": 0.05,
                "checks": [
                    (r"\\begin\{table\}", "Tables present"),
                ],
            },
        ],
        EvaluationCategory.LIMITATIONS: [
            {
                "name": "Limitations Discussed",
                "description": "Paper acknowledges limitations",
                "weight": 0.05,
                "checks": [
                    (
                        r"[Ll]imitation|[Cc]onstraint|[Ss]hortcoming|[Dd]rawback",
                        "Limitations discussed",
                    ),
                ],
            },
            {
                "name": "Future Work",
                "description": "Clear future research directions",
                "weight": 0.05,
                "checks": [
                    (
                        r"[Ff]uture [Ww]ork|[Ff]uture [Dd]irection|[Nn]ext [Ss]tep",
                        "Future work discussed",
                    ),
                ],
            },
        ],
        EvaluationCategory.REPRODUCIBILITY: [
            {
                "name": "Code Availability",
                "description": "Code is available or will be released",
                "weight": 0.05,
                "checks": [
                    (
                        r"[Cc]ode.*[aA]vailable|[Gg]ithub|[Rr]epository|[Oo]pen.?source",
                        "Code availability mentioned",
                    ),
                ],
            },
            {
                "name": "Implementation Details",
                "description": "Sufficient implementation details for reproduction",
                "weight": 0.05,
                "checks": [
                    (
                        r"[Hh]yperparameter|[Ii]mplementation [Dd]etail|[Tt]raining [Ss]etup",
                        "Implementation details present",
                    ),
                ],
            },
        ],
    }

    def evaluate(self, paper_path: str | Path) -> Q1Evaluation:
        """Evaluate paper against Q1 standards."""
        structure = parse_latex_sections(paper_path)
        full_text = structure.raw_text

        criteria = []
        for category, checks in self.Q1_CRITERIA.items():
            for check in checks:
                criterion = self._evaluate_criterion(category, check, full_text)
                criteria.append(criterion)

        overall_score = self._calculate_overall_score(criteria)
        readiness = self._determine_readiness(overall_score, criteria)

        summary = {
            "total_criteria": len(criteria),
            "by_score": {
                "excellent": sum(1 for c in criteria if c.score == Q1Score.EXCELLENT),
                "good": sum(1 for c in criteria if c.score == Q1Score.GOOD),
                "acceptable": sum(1 for c in criteria if c.score == Q1Score.ACCEPTABLE),
                "weak": sum(1 for c in criteria if c.score == Q1Score.WEAK),
                "critical": sum(1 for c in criteria if c.score == Q1Score.CRITICAL),
            },
            "by_category": {
                cat.value: {
                    "score": self._category_score(criteria, cat),
                    "issues": sum(
                        1
                        for c in criteria
                        if c.category == cat and c.score in [Q1Score.WEAK, Q1Score.CRITICAL]
                    ),
                }
                for cat in EvaluationCategory
            },
        }

        return Q1Evaluation(
            paper_path=str(paper_path),
            overall_score=overall_score,
            readiness=readiness,
            criteria=criteria,
            summary=summary,
        )

    def _evaluate_criterion(
        self,
        category: EvaluationCategory,
        check_config: dict,
        text: str,
    ) -> EvaluationCriterion:
        pattern = re.compile(check_config["checks"][0][0], re.IGNORECASE | re.DOTALL)
        matches = list(pattern.finditer(text))

        evidence = []
        for match in matches[:3]:
            evidence.append(match.group(0)[:100])

        if len(matches) > 0:
            score = Q1Score.GOOD
            suggestions = []
        else:
            score = Q1Score.WEAK
            suggestions = [check_config["checks"][0][1]]

        return EvaluationCriterion(
            category=category,
            name=check_config["name"],
            description=check_config["description"],
            weight=check_config["weight"],
            score=score,
            evidence=evidence,
            suggestions=suggestions,
        )

    def _calculate_overall_score(self, criteria: list[EvaluationCriterion]) -> float:
        score_map = {
            Q1Score.EXCELLENT: 1.0,
            Q1Score.GOOD: 0.8,
            Q1Score.ACCEPTABLE: 0.6,
            Q1Score.WEAK: 0.4,
            Q1Score.CRITICAL: 0.2,
        }

        total_weight = sum(c.weight for c in criteria)
        weighted_sum = sum(c.weight * score_map[c.score] for c in criteria)

        return round(weighted_sum / total_weight, 2) if total_weight > 0 else 0.0

    def _determine_readiness(
        self, overall_score: float, criteria: list[EvaluationCriterion]
    ) -> str:
        critical_count = sum(1 for c in criteria if c.score == Q1Score.CRITICAL)
        weak_count = sum(1 for c in criteria if c.score == Q1Score.WEAK)

        if critical_count > 0:
            return "NOT READY: Critical issues must be addressed"
        elif weak_count > 3:
            return "NEEDS WORK: Multiple weak areas require improvement"
        elif overall_score >= 0.8:
            return "READY: Meets Q1 standards"
        elif overall_score >= 0.6:
            return "NEARLY READY: Minor improvements needed"
        else:
            return "NEEDS WORK: Significant improvements required"

    def _category_score(
        self, criteria: list[EvaluationCriterion], category: EvaluationCategory
    ) -> float:
        score_map = {
            Q1Score.EXCELLENT: 1.0,
            Q1Score.GOOD: 0.8,
            Q1Score.ACCEPTABLE: 0.6,
            Q1Score.WEAK: 0.4,
            Q1Score.CRITICAL: 0.2,
        }

        category_criteria = [c for c in criteria if c.category == category]
        if not category_criteria:
            return 0.0

        return round(sum(score_map[c.score] for c in category_criteria) / len(category_criteria), 2)

    def to_dict(self, evaluation: Q1Evaluation) -> dict[str, Any]:
        """Convert Q1Evaluation to dictionary."""
        return {
            "paper_path": evaluation.paper_path,
            "overall_score": evaluation.overall_score,
            "readiness": evaluation.readiness,
            "criteria": [
                {
                    "category": c.category.value,
                    "name": c.name,
                    "description": c.description,
                    "weight": c.weight,
                    "score": c.score.value,
                    "evidence": c.evidence,
                    "suggestions": c.suggestions,
                }
                for c in evaluation.criteria
            ],
            "summary": evaluation.summary,
        }
