"""Submission outcome simulation service using heuristic world-model reasoning."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from crane.services.latex_parser import get_all_sections_flat, parse_latex_sections
from crane.workspace import resolve_workspace


class SubmissionSimulationService:
    """Simulate paper submission outcomes for target journals."""

    _DEFAULT_JOURNALS_PATH = Path("data") / "journals" / "q1_journal_profiles.yaml"

    _BASE_SCENARIOS: list[dict[str, Any]] = [
        {
            "name": "Direct Accept",
            "timeline": "6-8 weeks",
            "description": "Strong alignment and execution lead to acceptance without major change.",
            "second_order_effects": [
                "Earlier publication cycle may increase citation velocity.",
                "Reviewer enthusiasm can improve editorial framing of contribution.",
            ],
        },
        {
            "name": "Minor Revision",
            "timeline": "8-12 weeks",
            "description": "Core contribution is accepted, with requests for clarity and additional analysis.",
            "second_order_effects": [
                "Revision can strengthen reproducibility and improve long-term impact.",
                "Extra analyses may broaden audience confidence in claims.",
            ],
        },
        {
            "name": "Major Revision",
            "timeline": "3-6 months",
            "description": "Promise is recognized, but substantial methodological or evaluation updates are required.",
            "second_order_effects": [
                "Extended revision cycle may delay downstream project milestones.",
                "Addressing major comments often yields stronger final paper quality.",
            ],
        },
        {
            "name": "Reject & Resubmit",
            "timeline": "4-9 months",
            "description": "Current draft is not accepted, but a redesigned submission could be competitive.",
            "second_order_effects": [
                "Resubmission may require reframing novelty and experimentation plan.",
                "Strategic journal pivot can improve eventual acceptance probability.",
            ],
        },
        {
            "name": "Reject",
            "timeline": "4-10 weeks",
            "description": "Fit or evidence gaps are too large for revision within this venue cycle.",
            "second_order_effects": [
                "Team morale and publication timeline may be negatively affected.",
                "Early rejection can accelerate redirection to a better-fit venue.",
            ],
        },
        {
            "name": "Desk Reject",
            "timeline": "1-3 weeks",
            "description": "Editor screens out submission due to scope mismatch or structure gaps.",
            "second_order_effects": [
                "Fast decision preserves time for immediate resubmission elsewhere.",
                "Persistent desk-reject patterns can indicate framing mismatch.",
            ],
        },
        {
            "name": "Conditional Accept",
            "timeline": "6-10 weeks",
            "description": "Acceptance is contingent on a focused and fast revision response.",
            "second_order_effects": [
                "Focused revision can improve reviewer trust and citation potential.",
                "Failure to address required fixes risks downgrade to major revision.",
            ],
        },
    ]

    _COMMON_SECTION_PATTERNS = {
        "abstract": ["abstract"],
        "introduction": ["introduction", "intro"],
        "method": ["method", "approach", "methodology", "model"],
        "evaluation": ["evaluation", "experiments", "results", "experimental"],
        "related_work": ["related work", "background", "literature review"],
        "conclusion": ["conclusion", "concluding"],
        "limitations": ["limitation", "threat", "ethical", "constraints"],
    }

    def __init__(self, project_dir: str | None = None):
        """Resolve workspace and load journal profiles."""
        workspace = resolve_workspace(project_dir)
        self.project_root = Path(workspace.project_root)
        self.journals_path = self.project_root / self._DEFAULT_JOURNALS_PATH
        self.journals = self._load_journal_profiles(self.journals_path)

    def simulate_outcomes(
        self,
        paper_path: str,
        target_journal: str,
        revision_status: str = "current",
        num_scenarios: int = 5,
    ) -> dict[str, Any]:
        """
        Simulate submission outcomes using World Model reasoning.

        Returns:
            Structured simulation output including scenarios,
            world-model analysis, and recommendation.
        """
        resolved_paper_path = self._resolve_paper_path(paper_path)
        paper_profile = self._build_paper_profile(resolved_paper_path)
        journal = self._find_target_journal(target_journal)

        fit_score = self._score_journal_fit(paper_profile, journal)
        adjusted_acceptance = self._estimate_acceptance_probability(
            paper_profile=paper_profile,
            journal=journal,
            fit_score=fit_score,
            revision_status=revision_status,
        )

        scenarios = self._build_scenarios(
            adjusted_acceptance=adjusted_acceptance,
            fit_score=fit_score,
            paper_profile=paper_profile,
            requested=num_scenarios,
        )

        world_model = self._build_world_model_analysis(
            paper_profile=paper_profile,
            fit_score=fit_score,
            scenarios=scenarios,
            target_journal=journal.get("abbreviation") or journal.get("name") or target_journal,
        )

        best = scenarios[0]
        recommendation = (
            f"Most likely trajectory: {best['name']} ({best['probability']:.0%}). "
            f"Prioritize interventions on {', '.join(world_model['interventions'][:2])}."
        )

        return {
            "paper_profile": paper_profile,
            "target_journal": journal.get("abbreviation") or journal.get("name") or target_journal,
            "scenarios": scenarios,
            "world_model_analysis": world_model,
            "recommendation": recommendation,
        }

    def _resolve_paper_path(self, paper_path: str) -> Path:
        path = Path(paper_path)
        if path.is_absolute():
            resolved = path
        else:
            resolved = self.project_root / path

        if not resolved.exists():
            raise FileNotFoundError(f"Paper not found: {resolved}")
        return resolved

    def _load_journal_profiles(self, journals_path: Path) -> list[dict[str, Any]]:
        if not journals_path.exists():
            raise FileNotFoundError(f"Journal profiles file not found: {journals_path}")

        payload = yaml.safe_load(journals_path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError("Journal profiles YAML must be a mapping")

        journals = payload.get("journals", [])
        if not isinstance(journals, list):
            raise ValueError("Journal profiles must contain a 'journals' list")
        return [journal for journal in journals if isinstance(journal, dict)]

    def _find_target_journal(self, target_journal: str) -> dict[str, Any]:
        normalized_target = target_journal.strip().lower()
        if not normalized_target:
            return self.journals[0] if self.journals else {}

        for journal in self.journals:
            name = str(journal.get("name", "")).strip().lower()
            abbreviation = str(journal.get("abbreviation", "")).strip().lower()
            if normalized_target in {name, abbreviation}:
                return journal
            if normalized_target in name or normalized_target in abbreviation:
                return journal

        return {
            "name": target_journal,
            "abbreviation": target_journal,
            "scope_keywords": [],
            "preferred_paper_types": [],
            "acceptance_rate": 0.18,
            "review_timeline_months": [3, 6],
            "desk_reject_signals": [],
        }

    def _build_paper_profile(self, paper_path: Path) -> dict[str, Any]:
        structure = parse_latex_sections(paper_path)
        text = structure.raw_text
        sections = [section.name.lower() for section in get_all_sections_flat(structure)]

        section_presence: dict[str, bool] = {}
        for canonical, tokens in self._COMMON_SECTION_PATTERNS.items():
            if canonical == "abstract":
                section_presence[canonical] = bool(structure.abstract.strip())
                continue
            section_presence[canonical] = any(
                any(token in section_name for token in tokens) for section_name in sections
            )

        references = self._count_references(text)
        figures = len(re.findall(r"\\begin\{figure\*?\}", text, flags=re.IGNORECASE))
        tables = len(re.findall(r"\\begin\{table\*?\}", text, flags=re.IGNORECASE))
        word_count = len(re.findall(r"\b\w+\b", text))
        estimated_pages = max(1.0, round(word_count / 500, 1))

        tokens = self._extract_paper_keywords(text)

        return {
            "paper_path": str(paper_path),
            "title": structure.title,
            "word_count": word_count,
            "estimated_pages": estimated_pages,
            "section_count": len(structure.sections),
            "reference_count": references,
            "figure_count": figures,
            "table_count": tables,
            "keywords": tokens,
            "section_presence": section_presence,
        }

    def _extract_paper_keywords(self, text: str) -> list[str]:
        explicit = re.search(r"\\keywords\{([^}]*)\}", text, flags=re.IGNORECASE)
        if explicit:
            return [
                token.strip().lower() for token in explicit.group(1).split(",") if token.strip()
            ]

        fallback_candidates = [
            "machine learning",
            "deep learning",
            "transformer",
            "computer vision",
            "natural language processing",
            "optimization",
            "benchmark",
            "ablation",
            "robustness",
            "software engineering",
            "data mining",
            "knowledge representation",
        ]
        lowered = text.lower()
        return [candidate for candidate in fallback_candidates if candidate in lowered]

    def _count_references(self, text: str) -> int:
        bibitems = len(re.findall(r"\\bibitem\{", text))
        cite_keys = 0
        for cite_group in re.findall(r"\\cite\w*\{([^}]*)\}", text):
            cite_keys += len([key for key in cite_group.split(",") if key.strip()])
        return max(bibitems, cite_keys)

    def _score_journal_fit(self, paper_profile: dict[str, Any], journal: dict[str, Any]) -> float:
        paper_keywords = {keyword.lower() for keyword in paper_profile.get("keywords", [])}
        scope_keywords = {
            str(keyword).strip().lower() for keyword in journal.get("scope_keywords", []) if keyword
        }

        scope_fit = 0.0
        if paper_keywords and scope_keywords:
            scope_fit = len(paper_keywords & scope_keywords) / len(scope_keywords)

        section_presence = paper_profile.get("section_presence", {})
        evaluation_rigor = 1.0 if section_presence.get("evaluation", False) else 0.0
        if paper_profile.get("figure_count", 0) + paper_profile.get("table_count", 0) >= 3:
            evaluation_rigor = min(1.0, evaluation_rigor + 0.2)

        preferred_types = [
            str(item).lower().strip() for item in journal.get("preferred_paper_types", []) if item
        ]
        inferred_type = self._infer_paper_type(paper_profile)
        paper_type_fit = (
            1.0 if inferred_type in preferred_types else 0.4 if preferred_types else 0.6
        )

        weighted = (scope_fit * 0.45) + (paper_type_fit * 0.25) + (evaluation_rigor * 0.30)
        return round(max(0.0, min(1.0, weighted)), 3)

    def _infer_paper_type(self, paper_profile: dict[str, Any]) -> str:
        section_presence = paper_profile.get("section_presence", {})
        if section_presence.get("evaluation", False) and paper_profile.get("figure_count", 0) > 0:
            return "empirical"
        if section_presence.get("method", False) and section_presence.get("evaluation", False):
            return "system"
        if paper_profile.get("reference_count", 0) >= 80:
            return "survey"
        return "theoretical"

    def _estimate_acceptance_probability(
        self,
        paper_profile: dict[str, Any],
        journal: dict[str, Any],
        fit_score: float,
        revision_status: str,
    ) -> float:
        base_rate = float(journal.get("acceptance_rate", 0.18))
        adjustments = 0.0

        section_presence = paper_profile.get("section_presence", {})
        references = int(paper_profile.get("reference_count", 0))
        pages = float(paper_profile.get("estimated_pages", 0.0))

        if not section_presence.get("limitations", False):
            adjustments -= 0.10
        if not section_presence.get("related_work", False):
            adjustments -= 0.15
        if references < 20:
            adjustments -= 0.10
        elif references > 50:
            adjustments += 0.05
        if section_presence.get("evaluation", False):
            adjustments += 0.20
        else:
            adjustments -= 0.30
        if pages < 6.0:
            adjustments -= 0.15

        revision_map = {
            "current": 0.0,
            "post_revision": 0.05,
            "final": 0.08,
        }
        adjustments += revision_map.get(revision_status.lower(), 0.0)

        fit_adjustment = (fit_score - 0.5) * 0.25
        adjusted = base_rate + adjustments + fit_adjustment
        return round(max(0.02, min(0.92, adjusted)), 3)

    def _build_scenarios(
        self,
        adjusted_acceptance: float,
        fit_score: float,
        paper_profile: dict[str, Any],
        requested: int,
    ) -> list[dict[str, Any]]:
        requested_scenarios = max(3, min(7, requested))

        direct_accept = adjusted_acceptance * (0.10 + 0.55 * fit_score)
        minor_revision = adjusted_acceptance * (0.35 + 0.20 * fit_score)
        major_revision = max(0.0, adjusted_acceptance - direct_accept - minor_revision)

        rejection_branch = max(0.0, 1.0 - adjusted_acceptance)
        reject_resubmit = rejection_branch * (0.45 + 0.30 * fit_score)
        reject = max(0.0, rejection_branch - reject_resubmit)

        desk_reject = max(0.0, (1.0 - fit_score) * 0.05)
        conditional_accept = max(0.0, min(0.08, adjusted_acceptance * 0.12))

        raw = {
            "Direct Accept": direct_accept,
            "Minor Revision": minor_revision,
            "Major Revision": major_revision,
            "Reject & Resubmit": reject_resubmit,
            "Reject": reject,
            "Desk Reject": desk_reject,
            "Conditional Accept": conditional_accept,
        }

        selected_templates = self._BASE_SCENARIOS[:requested_scenarios]
        selected_names = [scenario["name"] for scenario in selected_templates]
        selected_probs = {name: raw.get(name, 0.0) for name in selected_names}
        normalized = self._normalize_probabilities(selected_probs)

        key_factors = self._derive_key_factors(paper_profile)
        scenarios: list[dict[str, Any]] = []
        for template in selected_templates:
            name = template["name"]
            scenarios.append(
                {
                    "name": name,
                    "probability": normalized.get(name, 0.0),
                    "timeline": template["timeline"],
                    "description": template["description"],
                    "key_factors": key_factors,
                    "second_order_effects": template["second_order_effects"],
                }
            )

        scenarios.sort(key=lambda item: item["probability"], reverse=True)
        return scenarios

    def _derive_key_factors(self, paper_profile: dict[str, Any]) -> list[str]:
        section_presence = paper_profile.get("section_presence", {})
        references = int(paper_profile.get("reference_count", 0))

        factors = [
            "Scope alignment between paper keywords and journal aims.",
            "Strength and completeness of empirical validation.",
            "Narrative credibility from related-work and limitations framing.",
        ]
        if not section_presence.get("related_work", False):
            factors.append("Missing related-work section may trigger novelty concerns.")
        if not section_presence.get("limitations", False):
            factors.append("Missing limitations section may elevate reviewer skepticism.")
        if references < 20:
            factors.append("Low reference density may suggest insufficient literature grounding.")
        return factors[:5]

    def _normalize_probabilities(self, probabilities: dict[str, float]) -> dict[str, float]:
        total = sum(max(0.0, probability) for probability in probabilities.values())
        if total <= 0:
            uniform = round(1.0 / len(probabilities), 3) if probabilities else 0.0
            return {name: uniform for name in probabilities}

        normalized = {
            name: max(0.0, probability) / total for name, probability in probabilities.items()
        }

        rounded = {name: round(prob, 3) for name, prob in normalized.items()}
        delta = round(1.0 - sum(rounded.values()), 3)
        if rounded:
            top_key = max(rounded, key=lambda name: rounded[name])
            rounded[top_key] = round(max(0.0, min(1.0, rounded[top_key] + delta)), 3)
        return rounded

    def _build_world_model_analysis(
        self,
        paper_profile: dict[str, Any],
        fit_score: float,
        scenarios: list[dict[str, Any]],
        target_journal: str,
    ) -> dict[str, Any]:
        section_presence = paper_profile.get("section_presence", {})

        causal_factors = [
            f"Scope-fit score ({fit_score:.2f}) between paper keywords and {target_journal} profile.",
            f"Evaluation evidence status: {'present' if section_presence.get('evaluation') else 'missing'}.",
            f"Literature grounding via reference count ({paper_profile.get('reference_count', 0)}).",
            f"Argument completeness from limitations section ({'present' if section_presence.get('limitations') else 'missing'}).",
        ]

        hidden_variables = [
            "Reviewer strictness variance across cycles.",
            "Competing submissions with similar claims in the same issue.",
            "Editor preference for methodological novelty versus application impact.",
            "Reviewer familiarity with the paper's subdomain.",
        ]

        interventions = [
            "Add/strengthen a dedicated limitations and threats-to-validity section.",
            "Expand related-work differentiation against strongest recent baselines.",
            "Increase experimental rigor with stronger ablations and error analysis.",
            "Tighten framing to match explicit journal scope language.",
        ]

        uncertainty_areas = [
            "Reviewer assignment quality and subject-matter fit.",
            "How novelty is perceived against unpublished or concurrent work.",
            "Variance in editorial tolerance for revision depth.",
        ]

        if not section_presence.get("evaluation", False):
            uncertainty_areas.append(
                "No evaluation section makes effect-size credibility hard to infer."
            )

        base_confidence = 0.45 + (fit_score * 0.35)
        structural_bonus = 0.05 if section_presence.get("evaluation", False) else -0.08
        structural_bonus += 0.04 if section_presence.get("related_work", False) else -0.05
        structural_bonus += 0.04 if section_presence.get("limitations", False) else -0.05
        confidence = round(max(0.1, min(0.95, base_confidence + structural_bonus)), 3)

        default_trajectory = scenarios[0]["name"] if scenarios else "Unknown"
        return {
            "causal_factors": causal_factors,
            "hidden_variables": hidden_variables,
            "default_trajectory": default_trajectory,
            "interventions": interventions,
            "uncertainty_areas": uncertainty_areas,
            "confidence_score": confidence,
        }
