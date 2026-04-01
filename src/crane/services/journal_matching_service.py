from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from crane.models.paper_profile import EvidencePattern, JournalFit, PaperProfile, PaperType


class JournalMatchingService:
    """Profile-based journal matching using weighted fit scoring."""

    REQUIRED_FIELDS = {
        "name",
        "abbreviation",
        "publisher",
        "quartile",
        "impact_factor",
        "scope_keywords",
        "preferred_paper_types",
        "preferred_method_families",
        "preferred_evidence_patterns",
        "typical_word_count",
        "review_timeline_months",
        "acceptance_rate",
        "apc_usd",
        "open_access",
        "desk_reject_signals",
        "citation_venues",
    }

    def __init__(self, profiles_path: str | Path | None = None):
        """Load journal profiles from YAML and validate schema."""
        root = Path(__file__).resolve().parents[3]
        self.profiles_path = (
            Path(profiles_path)
            if profiles_path is not None
            else root / "data" / "journals" / "q1_journal_profiles.yaml"
        )
        self.journals = self._load_profiles(self.profiles_path)

    def _load_profiles(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            raise FileNotFoundError(f"Journal profiles file not found: {path}")

        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or "journals" not in raw:
            raise ValueError("Journal profiles YAML must be a mapping with a 'journals' key")

        journals = raw.get("journals", [])
        if not isinstance(journals, list):
            raise ValueError("'journals' must be a list")

        validated: list[dict[str, Any]] = []
        for idx, journal in enumerate(journals):
            if not isinstance(journal, dict):
                raise ValueError(f"Journal entry at index {idx} must be a mapping")

            missing = self.REQUIRED_FIELDS.difference(journal.keys())
            if missing:
                raise ValueError(
                    f"Journal '{journal.get('name', idx)}' missing required fields: {sorted(missing)}"
                )

            if not isinstance(journal["scope_keywords"], list):
                raise ValueError("scope_keywords must be a list")
            if not isinstance(journal["preferred_paper_types"], list):
                raise ValueError("preferred_paper_types must be a list")
            if not isinstance(journal["preferred_evidence_patterns"], list):
                raise ValueError("preferred_evidence_patterns must be a list")
            if not isinstance(journal["citation_venues"], list):
                raise ValueError("citation_venues must be a list")

            twc = journal["typical_word_count"]
            if not isinstance(twc, list) or len(twc) != 2:
                raise ValueError("typical_word_count must be [min, max]")

            validated.append(journal)
        return validated

    def match(self, profile: PaperProfile) -> list[JournalFit]:
        """Match paper profile against all journals and sort by overall_fit."""
        fits: list[JournalFit] = []

        for journal in self.journals:
            scope_fit = self.calculate_scope_fit(profile, journal)
            contribution_style_fit = self.calculate_contribution_style_fit(profile, journal)
            evaluation_style_fit = self.calculate_evaluation_style_fit(profile, journal)
            citation_fit = self.calculate_citation_neighborhood_fit(profile, journal)
            operational_fit = self.calculate_operational_fit(profile, journal)
            desk_risk, risk_factors = self.assess_desk_reject_risk(profile, journal)

            fit = JournalFit(
                journal_name=str(journal["name"]),
                scope_fit=scope_fit,
                contribution_style_fit=contribution_style_fit,
                evaluation_style_fit=evaluation_style_fit,
                citation_neighborhood_fit=citation_fit,
                operational_fit=operational_fit,
                desk_reject_risk=desk_risk,
                risk_factors=risk_factors,
            )
            fit.calculate_overall()
            fits.append(fit)

        fits.sort(key=lambda item: (-item.overall_fit, item.desk_reject_risk, item.journal_name))

        labels = ["target", "backup", "safe"]
        for idx, fit in enumerate(fits):
            fit.recommendation = labels[idx] if idx < len(labels) else "consider"

        return fits

    def recommend_top3(self, profile: PaperProfile) -> dict[str, JournalFit | None]:
        """Return target/backup/safe recommendations."""
        fits = self.match(profile)
        return {
            "target": fits[0] if len(fits) > 0 else None,
            "backup": fits[1] if len(fits) > 1 else None,
            "safe": fits[2] if len(fits) > 2 else None,
        }

    def calculate_scope_fit(self, profile: PaperProfile, journal: dict[str, Any]) -> float:
        """Jaccard similarity between paper domain+keywords and journal scope keywords."""
        paper_terms = {kw.strip().lower() for kw in profile.keywords if kw.strip()}
        if profile.problem_domain.strip():
            paper_terms.add(profile.problem_domain.strip().lower())

        journal_terms = {
            kw.strip().lower() for kw in journal.get("scope_keywords", []) if kw.strip()
        }
        if not paper_terms or not journal_terms:
            return 0.0

        intersection = len(paper_terms & journal_terms)
        union = len(paper_terms | journal_terms)
        return intersection / union if union else 0.0

    def calculate_contribution_style_fit(
        self, profile: PaperProfile, journal: dict[str, Any]
    ) -> float:
        """Check whether paper type aligns with journal preferred paper types."""
        preferred = {str(pt).strip().lower() for pt in journal.get("preferred_paper_types", [])}
        paper_type = profile.paper_type.value.lower()

        if paper_type in preferred:
            return 1.0
        if paper_type == PaperType.UNKNOWN.value:
            return 0.0

        partial_map = {
            PaperType.THEORETICAL.value: {"empirical", "survey"},
            PaperType.EMPIRICAL.value: {"theoretical", "system", "application"},
            PaperType.SYSTEM.value: {"empirical", "application"},
            PaperType.SURVEY.value: {"theoretical", "empirical"},
        }
        if preferred & partial_map.get(paper_type, set()):
            return 0.5
        return 0.0

    def calculate_evaluation_style_fit(
        self, profile: PaperProfile, journal: dict[str, Any]
    ) -> float:
        """Check whether evidence style aligns with journal preference."""
        preferred = {
            str(pattern).strip().lower()
            for pattern in journal.get("preferred_evidence_patterns", [])
        }
        evidence = profile.evidence_pattern.value.lower()

        if evidence in preferred:
            return 1.0
        if evidence == EvidencePattern.MIXED.value and preferred:
            return 0.5
        if evidence != EvidencePattern.UNKNOWN.value and "mixed" in preferred:
            return 0.5
        return 0.0

    def calculate_citation_neighborhood_fit(
        self, profile: PaperProfile, journal: dict[str, Any]
    ) -> float:
        """Compute venue overlap as |paper ∩ journal| / |journal|."""
        paper_venues = {
            venue.strip().lower() for venue in profile.citation_neighborhood if venue.strip()
        }
        journal_venues = {
            venue.strip().lower() for venue in journal.get("citation_venues", []) if venue
        }

        if not journal_venues:
            return 0.0
        if not paper_venues:
            return 0.0

        return len(paper_venues & journal_venues) / len(journal_venues)

    def calculate_operational_fit(self, profile: PaperProfile, journal: dict[str, Any]) -> float:
        """Word-count fit with linear decay outside journal's typical range."""
        word_count = max(profile.word_count, 0)
        word_range = journal.get("typical_word_count", [0, 0])
        if not isinstance(word_range, list) or len(word_range) != 2:
            return 0.0

        min_wc = int(word_range[0])
        max_wc = int(word_range[1])
        if min_wc <= 0 or max_wc <= 0 or min_wc > max_wc:
            return 0.0

        if min_wc <= word_count <= max_wc:
            return 1.0

        if word_count < min_wc:
            return max(0.0, 1.0 - ((min_wc - word_count) / min_wc))

        return max(0.0, 1.0 - ((word_count - max_wc) / max_wc))

    def assess_desk_reject_risk(
        self, profile: PaperProfile, journal: dict[str, Any]
    ) -> tuple[float, list[str]]:
        """Assess desk-reject risk and return (risk, triggered_factors)."""
        factors: list[str] = []
        signals = [str(s).strip().lower() for s in journal.get("desk_reject_signals", [])]

        for signal in signals:
            if "no experiments" in signal:
                if profile.evidence_pattern in {
                    EvidencePattern.THEOREM_HEAVY,
                    EvidencePattern.UNKNOWN,
                }:
                    factors.append(signal)
            elif "incremental" in signal or "weak novelty" in signal or "limited novelty" in signal:
                if profile.novelty_shape.value == "incremental":
                    factors.append(signal)
            elif "poor baselines" in signal or "insufficient comparison" in signal:
                if profile.evidence_pattern not in {
                    EvidencePattern.BENCHMARK_HEAVY,
                    EvidencePattern.MIXED,
                }:
                    factors.append(signal)
            elif "insufficient" in signal and "validation" in signal:
                if profile.num_references < 20:
                    factors.append(signal)
            elif "scalability" in signal:
                if profile.validation_scale.lower() not in {"large", "large-scale", "web-scale"}:
                    factors.append(signal)
            elif "relevance" in signal and not profile.problem_domain.strip():
                factors.append(signal)

        unique_factors = sorted(set(factors))
        risk = len(unique_factors) / len(signals) if signals else 0.0
        return risk, unique_factors
