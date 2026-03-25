"""Journal recommendation workflow service.

Implements comprehensive journal selection based on paper attributes,
scope filtering, impact analysis, and submission strategy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class PaperType(Enum):
    APPLICATION_SYSTEM = "application_system"
    THEORETICAL_DIAGNOSTIC = "theoretical_diagnostic"
    EMPIRICAL_STUDY = "empirical_study"
    SURVEY_REVIEW = "survey_review"


class JournalTier(Enum):
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"


@dataclass
class PaperAttributes:
    paper_type: PaperType
    research_focus: str
    core_contribution: str
    main_metrics: list[str]
    validation_scale: str
    suitable_journal_types: list[str]


@dataclass
class JournalInfo:
    name: str
    abbreviation: str
    impact_factor: float
    acceptance_rate: float
    review_timeline_months: tuple[int, int]
    scope: str
    scope_fit: float
    apc: float
    desk_rejection_rate: float
    tier: JournalTier
    priority_score: float = 0.0


@dataclass
class SubmissionStrategy:
    paper_type: PaperType
    target_journals: list[JournalInfo]
    backup_journals: list[JournalInfo]
    safe_journals: list[JournalInfo]
    framing_suggestions: dict[str, str]
    checklist: list[str]


class JournalRecommendationService:
    """Service for comprehensive journal recommendation workflow."""

    JOURNAL_DATABASE = {
        "IEEE_TNNLS": JournalInfo(
            name="IEEE Transactions on Neural Networks and Learning Systems",
            abbreviation="TNNLS",
            impact_factor=13.8,
            acceptance_rate=0.25,
            review_timeline_months=(3, 5),
            scope="Neural networks, representation learning, deep learning",
            scope_fit=0.0,
            apc=0.0,
            desk_rejection_rate=0.15,
            tier=JournalTier.TIER_1,
        ),
        "IEEE_TKDE": JournalInfo(
            name="IEEE Transactions on Knowledge and Data Engineering",
            abbreviation="TKDE",
            impact_factor=8.78,
            acceptance_rate=0.35,
            review_timeline_months=(2, 4),
            scope="Knowledge engineering, data management, AI applications",
            scope_fit=0.0,
            apc=0.0,
            desk_rejection_rate=0.20,
            tier=JournalTier.TIER_1,
        ),
        "ACM_ESWA": JournalInfo(
            name="Expert Systems with Applications",
            abbreviation="ESWA",
            impact_factor=7.5,
            acceptance_rate=0.40,
            review_timeline_months=(3, 4),
            scope="Expert systems, applications, decision support",
            scope_fit=0.0,
            apc=0.0,
            desk_rejection_rate=0.10,
            tier=JournalTier.TIER_2,
        ),
        "IEEE_TAC": JournalInfo(
            name="IEEE Transactions on Affective Computing",
            abbreviation="TAC",
            impact_factor=9.2,
            acceptance_rate=0.30,
            review_timeline_months=(4, 6),
            scope="Affective computing, emotion recognition, HCI",
            scope_fit=0.0,
            apc=0.0,
            desk_rejection_rate=0.12,
            tier=JournalTier.TIER_1,
        ),
        "IEEE_TKDD": JournalInfo(
            name="IEEE Transactions on Knowledge Discovery from Data",
            abbreviation="TKDD",
            impact_factor=7.2,
            acceptance_rate=0.35,
            review_timeline_months=(3, 5),
            scope="Data mining, knowledge discovery, pattern recognition",
            scope_fit=0.0,
            apc=0.0,
            desk_rejection_rate=0.15,
            tier=JournalTier.TIER_2,
        ),
        "IEEE_TAI": JournalInfo(
            name="IEEE Transactions on Artificial Intelligence",
            abbreviation="TAI",
            impact_factor=6.5,
            acceptance_rate=0.40,
            review_timeline_months=(3, 4),
            scope="AI systems, applications, theory",
            scope_fit=0.0,
            apc=0.0,
            desk_rejection_rate=0.10,
            tier=JournalTier.TIER_3,
        ),
    }

    PAPER_TYPE_MAPPING = {
        PaperType.APPLICATION_SYSTEM: {
            "suitable_journals": ["ACM_ESWA", "IEEE_TAC", "IEEE_TAI"],
            "keywords": ["application", "system", "engineering", "reliability"],
            "metrics": ["QPS", "latency", "accuracy", "success_rate"],
        },
        PaperType.THEORETICAL_DIAGNOSTIC: {
            "suitable_journals": ["IEEE_TNNLS", "IEEE_TKDE"],
            "keywords": ["theory", "diagnostic", "framework", "analysis"],
            "metrics": ["CKA", "effective_rank", "linear_probe"],
        },
        PaperType.EMPIRICAL_STUDY: {
            "suitable_journals": ["IEEE_TNNLS", "IEEE_TKDD", "ACM_ESWA"],
            "keywords": ["empirical", "experiment", "benchmark", "evaluation"],
            "metrics": ["accuracy", "F1", "precision", "recall"],
        },
        PaperType.SURVEY_REVIEW: {
            "suitable_journals": ["IEEE_TKDE", "ACM_ESWA", "IEEE_TAI"],
            "keywords": ["survey", "review", "taxonomy", "comparison"],
            "metrics": ["coverage", "depth", "organization"],
        },
    }

    def analyze_paper_attributes(self, paper_path: str | Path) -> PaperAttributes:
        """Analyze paper to determine its attributes."""
        path = Path(paper_path)
        content = path.read_text(encoding="utf-8") if path.exists() else ""

        paper_type = self._detect_paper_type(content)
        mapping = self.PAPER_TYPE_MAPPING.get(paper_type, {})

        return PaperAttributes(
            paper_type=paper_type,
            research_focus=self._extract_research_focus(content),
            core_contribution=self._extract_core_contribution(content),
            main_metrics=mapping.get("metrics", []),
            validation_scale=self._extract_validation_scale(content),
            suitable_journal_types=mapping.get("suitable_journals", []),
        )

    def filter_journals_by_scope(self, paper_attrs: PaperAttributes) -> list[JournalInfo]:
        """Filter journals based on paper scope."""
        suitable_keys = paper_attrs.suitable_journal_types
        journals = []

        for key, journal in self.JOURNAL_DATABASE.items():
            if key in suitable_keys:
                journal_copy = JournalInfo(**vars(journal))
                journal_copy.scope_fit = self._calculate_scope_fit(paper_attrs, journal)
                journals.append(journal_copy)

        return sorted(journals, key=lambda j: j.scope_fit, reverse=True)

    def calculate_priority_scores(self, journals: list[JournalInfo]) -> list[JournalInfo]:
        """Calculate priority scores for journals."""
        for journal in journals:
            if_score = min(journal.impact_factor / 15.0, 1.0) * 0.3
            ar_score = (1.0 - journal.acceptance_rate) * 0.3
            speed_score = (1.0 - (journal.review_timeline_months[0] / 6.0)) * 0.2
            scope_score = journal.scope_fit * 0.2

            journal.priority_score = round(if_score + ar_score + speed_score + scope_score, 2)

        return sorted(journals, key=lambda j: j.priority_score, reverse=True)

    def create_submission_strategy(self, paper_attrs: PaperAttributes) -> SubmissionStrategy:
        """Create submission strategy based on paper attributes."""
        filtered_journals = self.filter_journals_by_scope(paper_attrs)
        scored_journals = self.calculate_priority_scores(filtered_journals)

        target = [j for j in scored_journals if j.tier == JournalTier.TIER_1][:1]
        backup = [j for j in scored_journals if j.tier == JournalTier.TIER_2][:1]
        safe = [j for j in scored_journals if j.tier == JournalTier.TIER_3][:1]

        framing = self._generate_framing_suggestions(paper_attrs, target[0] if target else None)
        checklist = self._generate_submission_checklist(paper_attrs)

        return SubmissionStrategy(
            paper_type=paper_attrs.paper_type,
            target_journals=target,
            backup_journals=backup,
            safe_journals=safe,
            framing_suggestions=framing,
            checklist=checklist,
        )

    def _detect_paper_type(self, content: str) -> PaperType:
        content_lower = content.lower()

        if any(
            w in content_lower for w in ["survey", "review", "taxonomy", "comprehensive overview"]
        ):
            return PaperType.SURVEY_REVIEW
        elif any(
            w in content_lower
            for w in ["theorem", "proof", "well-posed", "hadamard", "theoretical"]
        ):
            return PaperType.THEORETICAL_DIAGNOSTIC
        elif any(
            w in content_lower for w in ["system", "production", "qps", "latency", "engineering"]
        ):
            return PaperType.APPLICATION_SYSTEM
        else:
            return PaperType.EMPIRICAL_STUDY

    def _extract_research_focus(self, content: str) -> str:
        content_lower = content.lower()
        if "sentiment" in content_lower or "affect" in content_lower:
            return "Affective Computing / Sentiment Analysis"
        elif "neural network" in content_lower or "representation" in content_lower:
            return "Neural Network Representation Learning"
        elif "knowledge" in content_lower or "expert" in content_lower:
            return "Knowledge Engineering"
        else:
            return "Machine Learning / AI"

    def _extract_core_contribution(self, content: str) -> str:
        if "repair" in content.lower() and "pipeline" in content.lower():
            return "Deterministic Repair Pipeline"
        elif "diagnostic" in content.lower() or "framework" in content.lower():
            return "Diagnostic Framework"
        else:
            return "Novel Method / Algorithm"

    def _extract_validation_scale(self, content: str) -> str:
        if "18.2m" in content.lower() or "18 million" in content.lower():
            return "Large-scale (18M+ samples)"
        elif "18m" in content.lower():
            return "Medium-scale (18M samples)"
        else:
            return "Standard validation"

    def _calculate_scope_fit(self, paper_attrs: PaperAttributes, journal: JournalInfo) -> float:
        mapping = self.PAPER_TYPE_MAPPING.get(paper_attrs.paper_type, {})
        keywords = mapping.get("keywords", [])

        scope_lower = journal.scope.lower()
        matches = sum(1 for kw in keywords if kw in scope_lower)
        return min(matches / len(keywords) if keywords else 0.0, 1.0)

    def _generate_framing_suggestions(
        self, paper_attrs: PaperAttributes, target_journal: JournalInfo | None
    ) -> dict[str, str]:
        if not target_journal:
            return {}

        suggestions = {}

        if paper_attrs.paper_type == PaperType.APPLICATION_SYSTEM:
            if "TNNLS" in target_journal.abbreviation:
                suggestions["title"] = (
                    "Emphasize 'neural network representation' over 'expert system'"
                )
                suggestions["abstract"] = (
                    "Focus on representation analysis, not system implementation"
                )
                suggestions["metrics"] = "Emphasize CKA stability, de-emphasize QPS/latency"
            elif "ESWA" in target_journal.abbreviation:
                suggestions["title"] = "Keep 'expert system' framing"
                suggestions["abstract"] = "Emphasize practical applications and reliability"
                suggestions["metrics"] = "Highlight QPS, latency, success rate"

        elif paper_attrs.paper_type == PaperType.THEORETICAL_DIAGNOSTIC:
            if "TNNLS" in target_journal.abbreviation:
                suggestions["title"] = "Use 'task complexity framework' instead of 'well-posed'"
                suggestions["abstract"] = "Focus on practical representation analysis"
                suggestions["metrics"] = "Emphasize CKA cross-layer stability"

        return suggestions

    def _generate_submission_checklist(self, paper_attrs: PaperAttributes) -> list[str]:
        return [
            "□ Paper formatted with journal template",
            "□ No compilation errors (0 errors, 0 undefined citations)",
            "□ Cover letter written with journal-specific framing",
            "□ Novelty statement clear",
            "□ Conflict of interest declared",
            "□ Supplementary materials prepared",
            "□ Code/data availability statement",
            "□ 5 keywords selected",
            "□ Subject areas selected in submission system",
        ]

    def to_dict(self, strategy: SubmissionStrategy) -> dict[str, Any]:
        """Convert SubmissionStrategy to dictionary."""

        def journal_to_dict(j: JournalInfo) -> dict:
            return {
                "name": j.name,
                "abbreviation": j.abbreviation,
                "impact_factor": j.impact_factor,
                "acceptance_rate": round(j.acceptance_rate * 100, 1),
                "review_timeline": (
                    f"{j.review_timeline_months[0]}-{j.review_timeline_months[1]} months"
                ),
                "scope": j.scope,
                "scope_fit": round(j.scope_fit * 100, 1),
                "apc": j.apc,
                "desk_rejection_rate": round(j.desk_rejection_rate * 100, 1),
                "tier": j.tier.value,
                "priority_score": j.priority_score,
            }

        return {
            "paper_type": strategy.paper_type.value,
            "target_journals": [journal_to_dict(j) for j in strategy.target_journals],
            "backup_journals": [journal_to_dict(j) for j in strategy.backup_journals],
            "safe_journals": [journal_to_dict(j) for j in strategy.safe_journals],
            "framing_suggestions": strategy.framing_suggestions,
            "checklist": strategy.checklist,
        }
