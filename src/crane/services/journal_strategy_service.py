"""Journal recommendation workflow service.

Implements comprehensive journal selection based on paper attributes,
scope filtering, impact analysis, and submission strategy.

Journals are loaded dynamically from ``q1_journal_profiles.yaml`` via
:class:`~crane.services.journal_matching_service.JournalMatchingService`,
eliminating the need for a hardcoded journal database.
"""

from __future__ import annotations

import re
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
    """Service for comprehensive journal recommendation workflow.

    Loads all Q1 journal profiles from YAML via
    :class:`~crane.services.journal_matching_service.JournalMatchingService`
    instead of using a hardcoded journal database.
    """

    _PAPER_TYPE_TO_PREFERRED: dict[PaperType, set[str]] = {
        PaperType.APPLICATION_SYSTEM: {"application", "system"},
        PaperType.THEORETICAL_DIAGNOSTIC: {"theoretical"},
        PaperType.EMPIRICAL_STUDY: {"empirical"},
        PaperType.SURVEY_REVIEW: {"survey"},
    }

    PAPER_TYPE_KEYWORDS: dict[PaperType, dict[str, list[str]]] = {
        PaperType.APPLICATION_SYSTEM: {
            "keywords": ["application", "system", "engineering", "reliability"],
            "metrics": ["QPS", "latency", "accuracy", "success_rate"],
        },
        PaperType.THEORETICAL_DIAGNOSTIC: {
            "keywords": ["theory", "diagnostic", "framework", "analysis"],
            "metrics": ["CKA", "effective_rank", "linear_probe"],
        },
        PaperType.EMPIRICAL_STUDY: {
            "keywords": ["empirical", "experiment", "benchmark", "evaluation"],
            "metrics": ["accuracy", "F1", "precision", "recall"],
        },
        PaperType.SURVEY_REVIEW: {
            "keywords": ["survey", "review", "taxonomy", "comparison"],
            "metrics": ["coverage", "depth", "organization"],
        },
    }

    def __init__(self, profiles_path: str | Path | None = None):
        from crane.services.journal_matching_service import JournalMatchingService

        self._matching_service = JournalMatchingService(profiles_path)
        self._journals: dict[str, JournalInfo] = {}
        self._profiles_by_key: dict[str, dict[str, Any]] = {}
        self._build_journal_db()

    def _build_journal_db(self) -> None:
        for profile in self._matching_service.journals:
            key = self._make_key(profile["abbreviation"])
            self._journals[key] = self._profile_to_journal_info(profile)
            self._profiles_by_key[key] = profile

    @staticmethod
    def _make_key(abbreviation: str) -> str:
        return abbreviation.replace(" ", "_").upper()

    @staticmethod
    def _profile_to_journal_info(profile: dict[str, Any]) -> JournalInfo:
        """Convert a single YAML journal profile to a :class:`JournalInfo`."""
        impact = float(profile.get("impact_factor", 0))
        if impact >= 10:
            tier = JournalTier.TIER_1
        elif impact >= 7:
            tier = JournalTier.TIER_2
        else:
            tier = JournalTier.TIER_3

        signals = profile.get("desk_reject_signals", [])
        desk_rate = round(min(0.05 * len(signals), 0.25), 2)

        review = profile.get("review_timeline_months", [3, 6])

        return JournalInfo(
            name=str(profile["name"]),
            abbreviation=str(profile["abbreviation"]),
            impact_factor=impact,
            acceptance_rate=float(profile.get("acceptance_rate", 0.2)),
            review_timeline_months=(int(review[0]), int(review[1])),
            scope=", ".join(str(kw) for kw in profile.get("scope_keywords", [])),
            scope_fit=0.0,
            apc=float(profile.get("apc_usd", 0)),
            desk_rejection_rate=desk_rate,
            tier=tier,
        )

    def _suitable_keys_for_type(self, paper_type: PaperType) -> list[str]:
        """Return journal keys whose YAML preferred types overlap *paper_type*."""
        preferred = self._PAPER_TYPE_TO_PREFERRED.get(paper_type, set())
        keys: list[str] = []
        for key, profile in self._profiles_by_key.items():
            yaml_types = {str(t).lower() for t in profile.get("preferred_paper_types", [])}
            if preferred & yaml_types:
                keys.append(key)
        return keys

    def analyze_paper_attributes(self, paper_path: str | Path) -> PaperAttributes:
        """Analyze paper to determine its attributes."""
        path = Path(paper_path)
        content = path.read_text(encoding="utf-8") if path.exists() else ""

        paper_type = self._detect_paper_type(content)
        keywords_info = self.PAPER_TYPE_KEYWORDS.get(paper_type, {})

        return PaperAttributes(
            paper_type=paper_type,
            research_focus=self._extract_research_focus(content),
            core_contribution=self._extract_core_contribution(content),
            main_metrics=keywords_info.get("metrics", []),
            validation_scale=self._extract_validation_scale(content),
            suitable_journal_types=self._suitable_keys_for_type(paper_type),
        )

    def filter_journals_by_scope(self, paper_attrs: PaperAttributes) -> list[JournalInfo]:
        """Filter journals based on paper scope.

        When *suitable_journal_types* is provided and at least one key
        resolves to a loaded journal, those journals are returned (backward
        compatible).  Otherwise, journals are selected by matching the
        paper type against each journal's YAML ``preferred_paper_types``.
        """
        # Try explicit keys first (backward compatibility)
        explicit_keys = {k for k in paper_attrs.suitable_journal_types if k in self._journals}

        if explicit_keys:
            matched_keys = explicit_keys
        else:
            # Fall back to paper-type matching
            matched_keys = set(self._suitable_keys_for_type(paper_attrs.paper_type))

        journals: list[JournalInfo] = []
        for key in matched_keys:
            journal = self._journals.get(key)
            if journal is not None:
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

    # ------------------------------------------------------------------
    # Paper-type detection helpers
    # ------------------------------------------------------------------

    # Patterns that strongly indicate a SURVEY paper (title/abstract level)
    _SURVEY_TITLE_PATTERNS = [
        r"survey\s+of",
        r"comprehensive\s+(review|survey|overview)",
        r"systematic\s+review",
        r"literature\s+review",
        r"taxonomy\s+of",
        r"state\s+of\s+the\s+art\s+in",
        r"recent\s+advances\s+in\s+\w+\s*(survey|review)?",
        r"this\s+(paper|article|work)\s+(is|presents|provides)\s+(a\s+)?(survey|review|overview)",
        r"we\s+(survey|review)\s+(the\s+)?(literature|existing|methods|approaches)",
    ]

    # Patterns that indicate an EMPIRICAL or APPLICATION paper even when
    # "review" appears (these should NOT trigger SURVEY_REVIEW)
    _NOT_SURVEY_PATTERNS = [
        r"we\s+review\s+(related\s+)?work",
        r"review\s+of\s+(related|previous|existing)\s+work",
        r"related\s+work",
        r"literature\s+review\s+section",
        r"section\s+\d+\s*[:.]?\s+(related\s+work|background|literature\s+review)",
    ]

    def _detect_paper_type(self, content: str) -> PaperType:
        """Detect paper type using context-aware pattern matching.

        Strategy:
        1. Check for strong survey signals in title/abstract first
        2. If "review" appears, verify it's not just a related-work section
        3. Use weighted scoring across the full document
        4. Fall back to EMPIRICAL_STUDY when uncertain
        """
        content_lower = content.lower()

        # --- Step 1: Extract title and abstract for higher-weight analysis ---
        title = self._extract_title(content)
        abstract = self._extract_abstract(content)
        title_lower = title.lower()
        abstract_lower = abstract.lower() if abstract else ""

        # --- Step 2: Check for strong survey signals in title/abstract ---
        survey_in_title = any(re.search(p, title_lower) for p in self._SURVEY_TITLE_PATTERNS)
        survey_in_abstract = any(re.search(p, abstract_lower) for p in self._SURVEY_TITLE_PATTERNS)

        # If title strongly indicates survey → immediate classification
        if survey_in_title:
            return PaperType.SURVEY_REVIEW

        # --- Step 3: Check for "not survey" patterns ---
        has_not_survey = any(re.search(p, content_lower) for p in self._NOT_SURVEY_PATTERNS)

        # --- Step 4: Weighted scoring for survey ---
        survey_score = 0.0

        # Title matches (high weight)
        if survey_in_abstract:
            survey_score += 3.0

        # Full-text survey keywords (lower weight, context-checked)
        survey_keywords = ["survey", "taxonomy"]
        for kw in survey_keywords:
            # Count occurrences but cap at 5 to avoid runaway scoring
            count = min(len(re.findall(rf"\b{kw}\b", content_lower)), 5)
            survey_score += count * 0.5

        # "review" keyword — only count if NOT in a not-survey context
        if not has_not_survey:
            review_count = min(len(re.findall(r"\breview\b", content_lower)), 5)
            survey_score += review_count * 0.3
        else:
            # "review" appears but in related-work context → small penalty
            survey_score -= 1.0

        # Positive signals for OTHER paper types reduce survey confidence
        # Theoretical signals
        theoretical_signals = len(
            re.findall(
                r"\b(theorem|proof|lemma|well-posed|hadamard|convergence\s+bound)\b",
                content_lower,
            )
        )
        if theoretical_signals >= 2:
            survey_score -= 3.0

        # Empirical/experimental signals
        empirical_signals = len(
            re.findall(
                r"\b(experiment|dataset|benchmark|ablation|baseline|accuracy|f1|auc)\b",
                content_lower,
            )
        )
        if empirical_signals >= 3:
            survey_score -= 2.0

        # System/engineering signals
        system_signals = len(
            re.findall(
                r"\b(system|architecture|deployment|latency|throughput|qps|microservice)\b",
                content_lower,
            )
        )
        if system_signals >= 2:
            survey_score -= 2.0

        # Threshold: need strong evidence to classify as survey
        if survey_score >= 3.0:
            return PaperType.SURVEY_REVIEW

        # --- Step 5: Check other paper types ---
        if theoretical_signals >= 2 or any(
            w in content_lower for w in ["theorem", "proof", "well-posed", "hadamard"]
        ):
            return PaperType.THEORETICAL_DIAGNOSTIC

        if system_signals >= 2 or any(
            w in content_lower for w in ["system", "production", "qps", "latency", "engineering"]
        ):
            return PaperType.APPLICATION_SYSTEM

        # Default: empirical study (most common paper type)
        return PaperType.EMPIRICAL_STUDY

    @staticmethod
    def _extract_title(content: str) -> str:
        """Extract paper title from LaTeX content."""
        # Try \title{...} pattern
        match = re.search(r"\\title\{([^}]*)\}", content)
        if match:
            return match.group(1).strip()
        # Fallback: first non-empty line that looks like a title
        lines = content.strip().split("\n")
        for line in lines[:10]:
            stripped = line.strip()
            if stripped and not stripped.startswith(("%", "\\", "{", "}")):
                return stripped
        return ""

    @staticmethod
    def _extract_abstract(content: str) -> str:
        """Extract abstract text from LaTeX content."""
        match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

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
        keywords_info = self.PAPER_TYPE_KEYWORDS.get(paper_attrs.paper_type, {})
        keywords = keywords_info.get("keywords", [])

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
