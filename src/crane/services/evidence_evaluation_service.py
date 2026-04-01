from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from crane.models.paper_profile import (
    DimensionScore,
    EvidenceLedger,
    EvidencePattern,
    NoveltyShape,
    PaperProfile,
    RevisionEffort,
    RevisionItem,
    RevisionPlan,
    RevisionPriority,
)
from crane.services.latex_parser import get_all_sections_flat, parse_latex_sections
from crane.services.paper_profile_service import PaperProfileService


@dataclass
class EvidenceEvaluation:
    paper_path: str
    profile: PaperProfile
    evidence: EvidenceLedger
    dimension_scores: list[DimensionScore]
    overall_score: float
    gates_passed: bool
    readiness: str
    revision_plan: RevisionPlan


class EvidenceEvaluationService:
    DIMENSION_WEIGHTS = {
        "writing_quality": 0.12,
        "methodology": 0.18,
        "novelty": 0.18,
        "evaluation": 0.20,
        "presentation": 0.08,
        "limitations": 0.10,
        "reproducibility": 0.14,
    }

    GATE_DIMENSIONS = {"methodology", "novelty", "evaluation"}
    GATE_THRESHOLD = 60.0

    def __init__(self, mode: str = "hybrid"):
        if mode not in {"heuristic", "hybrid"}:
            raise ValueError("mode must be 'heuristic' or 'hybrid'")
        self.mode = mode
        self._profile_service = PaperProfileService()
        self._section_names: set[str] = set()
        self._raw_text: str = ""

    def evaluate(self, paper_path: str | Path) -> EvidenceEvaluation:
        if self.mode == "heuristic":
            return self._evaluate_heuristic(paper_path)
        return self._evaluate_hybrid(paper_path)

    def _evaluate_hybrid(self, paper_path: str | Path) -> EvidenceEvaluation:
        self._prepare_context(paper_path)
        profile = self._profile_service.extract_profile(paper_path)
        evidence = self._profile_service.extract_evidence(paper_path)

        scores = []
        for dim_name in self.DIMENSION_WEIGHTS:
            score = self._score_dimension(dim_name, profile, evidence)
            scores.append(score)

        overall = sum(s.score * self.DIMENSION_WEIGHTS[s.dimension] for s in scores)
        gates_passed = self._check_gates(scores)
        readiness = self._determine_readiness(overall, gates_passed, scores)
        revision_plan = self._generate_revision_plan(scores)

        return EvidenceEvaluation(
            paper_path=str(paper_path),
            profile=profile,
            evidence=evidence,
            dimension_scores=scores,
            overall_score=round(overall, 2),
            gates_passed=gates_passed,
            readiness=readiness,
            revision_plan=revision_plan,
        )

    def _score_dimension(
        self,
        dimension: str,
        profile: PaperProfile,
        evidence: EvidenceLedger,
    ) -> DimensionScore:
        if dimension == "writing_quality":
            return self._score_writing_quality(profile, evidence)
        if dimension == "methodology":
            return self._score_methodology(profile, evidence)
        if dimension == "novelty":
            return self._score_novelty(profile, evidence)
        if dimension == "evaluation":
            return self._score_evaluation(profile, evidence)
        if dimension == "presentation":
            return self._score_presentation(profile, evidence)
        if dimension == "limitations":
            return self._score_limitations(profile, evidence)
        if dimension == "reproducibility":
            return self._score_reproducibility(profile, evidence)
        raise ValueError(f"unsupported dimension: {dimension}")

    def _check_gates(self, scores: list[DimensionScore]) -> bool:
        for score in scores:
            if score.dimension in self.GATE_DIMENSIONS and score.score < self.GATE_THRESHOLD:
                return False
        return True

    def _determine_readiness(
        self,
        overall: float,
        gates: bool,
        scores: list[DimensionScore],
    ) -> str:
        _ = scores
        if not gates:
            return "not_ready"
        if overall >= 80:
            return "ready"
        if overall >= 60:
            return "ready_with_revisions"
        return "not_ready"

    def _generate_revision_plan(self, scores: list[DimensionScore]) -> RevisionPlan:
        items: list[RevisionItem] = []
        for score in scores:
            if score.score < 80:
                priority = (
                    RevisionPriority.IMMEDIATE
                    if score.score < self.GATE_THRESHOLD
                    else RevisionPriority.MEDIUM_TERM
                )
                effort = (
                    RevisionEffort.HIGH
                    if score.score < 40
                    else (RevisionEffort.MEDIUM if score.score < 80 else RevisionEffort.LOW)
                )
                for suggestion in score.suggestions[:2]:
                    items.append(
                        RevisionItem(
                            dimension=score.dimension,
                            suggestion=suggestion,
                            priority=priority,
                            effort=effort,
                            expected_impact=min(20.0, max(1.0, (80.0 - score.score) * 0.5)),
                        )
                    )

        current_score = sum(s.score * self.DIMENSION_WEIGHTS[s.dimension] for s in scores)
        projected_gain = sum(item.expected_impact * 0.15 for item in items[:5])
        plan = RevisionPlan(
            items=items,
            current_score=round(current_score, 2),
            projected_score=min(100.0, round(current_score + projected_gain, 2)),
        )
        plan.sort_by_impact()
        return plan

    def _evaluate_heuristic(self, paper_path: str | Path) -> EvidenceEvaluation:
        from crane.services.q1_evaluation_service import Q1EvaluationService

        self._prepare_context(paper_path)
        profile = self._profile_service.extract_profile(paper_path)
        evidence = self._profile_service.extract_evidence(paper_path)

        old_service = Q1EvaluationService()
        old_result = old_service.evaluate(paper_path)

        score_map = {
            "excellent": 95.0,
            "good": 80.0,
            "acceptable": 60.0,
            "weak": 40.0,
            "critical": 20.0,
        }
        grouped: dict[str, list[float]] = {name: [] for name in self.DIMENSION_WEIGHTS}
        reasons: dict[str, list[str]] = {name: [] for name in self.DIMENSION_WEIGHTS}
        suggestions: dict[str, list[str]] = {name: [] for name in self.DIMENSION_WEIGHTS}

        for criterion in old_result.criteria:
            key = criterion.category.value
            numeric = score_map.get(criterion.score.value, 40.0)
            grouped[key].append(numeric)
            reasons[key].append(f"legacy:{criterion.name.lower().replace(' ', '_')}")
            suggestions[key].extend(criterion.suggestions)

        dimension_scores: list[DimensionScore] = []
        for dimension in self.DIMENSION_WEIGHTS:
            values = grouped.get(dimension, [])
            score = round(sum(values) / len(values), 2) if values else 40.0
            confidence = 0.55 if values else 0.35
            dimension_scores.append(
                DimensionScore(
                    dimension=dimension,
                    score=score,
                    confidence=confidence,
                    reason_codes=sorted(set(reasons.get(dimension, []))),
                    evidence_spans=[],
                    missing_evidence=[] if values else ["legacy-no-signals"],
                    suggestions=sorted(set(suggestions.get(dimension, [])))
                    or [f"Strengthen {dimension.replace('_', ' ')} evidence."],
                )
            )

        overall = old_result.overall_score * 100.0
        gates_passed = self._check_gates(dimension_scores)
        readiness = self._determine_readiness(overall, gates_passed, dimension_scores)
        revision_plan = self._generate_revision_plan(dimension_scores)

        return EvidenceEvaluation(
            paper_path=str(paper_path),
            profile=profile,
            evidence=evidence,
            dimension_scores=dimension_scores,
            overall_score=round(overall, 2),
            gates_passed=gates_passed,
            readiness=readiness,
            revision_plan=revision_plan,
        )

    def _prepare_context(self, paper_path: str | Path) -> None:
        structure = parse_latex_sections(paper_path)
        self._raw_text = structure.raw_text.lower()
        self._section_names = {section.name.lower() for section in get_all_sections_flat(structure)}

    def _score_writing_quality(
        self,
        profile: PaperProfile,
        evidence: EvidenceLedger,
    ) -> DimensionScore:
        score = 0.0
        reason_codes: list[str] = []
        missing_evidence: list[str] = []
        suggestions: list[str] = []

        if 5000 <= profile.word_count <= 10000:
            score += 30
            reason_codes.append("wc-ideal")
        elif 3000 <= profile.word_count <= 12000:
            score += 18
            reason_codes.append("wc-acceptable")
        else:
            missing_evidence.append("target_word_count_5k_to_10k")
            suggestions.append("Adjust manuscript length to ~5k-10k words for Q1 readability.")

        informal_hits = self._regex_hits(r"\b(awesome|cool|nice|amazing|stuff|thing|basically)\b")
        if informal_hits == 0:
            score += 25
            reason_codes.append("tone-academic")
        else:
            missing_evidence.append("informal_language_present")
            suggestions.append("Replace informal terms with precise academic wording.")
            score += max(0.0, 10 - 3 * informal_hits)

        if profile.num_references >= 20:
            score += 15
            reason_codes.append("citation-density-sufficient")
        else:
            missing_evidence.append("limited_citation_support")
            suggestions.append("Increase citation support for key claims.")

        observed = evidence.observed_count
        if observed >= 5:
            score += 20
            reason_codes.append("claims-supported")
        elif observed >= 2:
            score += 12
            reason_codes.append("claims-partially-supported")
        else:
            missing_evidence.append("few_explicit_claims")
            suggestions.append(
                "Make major claims explicit and support them with concrete evidence."
            )

        if evidence.missing_count == 0:
            score += 10
            reason_codes.append("no-global-missing-signal")
        else:
            missing_evidence.append("missing_evidence_markers")
            suggestions.append("Address missing evidence noted in evaluation/results sections.")

        final_score = min(100.0, score)
        confidence = self._confidence_from_evidence(evidence, base=0.45)
        return DimensionScore(
            dimension="writing_quality",
            score=final_score,
            confidence=confidence,
            reason_codes=reason_codes,
            evidence_spans=self._evidence_spans(evidence, ("show", "analysis", "results")),
            missing_evidence=missing_evidence,
            suggestions=self._uniq(suggestions)
            or ["Tighten prose and improve precision in argument flow."],
        )

    def _score_methodology(self, profile: PaperProfile, evidence: EvidenceLedger) -> DimensionScore:
        score = 0.0
        reason_codes: list[str] = []
        missing_evidence: list[str] = []
        suggestions: list[str] = []

        has_method_section = self._has_section(("method", "approach", "methodology"))
        has_equations = profile.num_equations > 0
        has_algorithm = bool(self._regex_hits(r"\b(algorithm|pseudocode|procedure)\b"))
        has_method_family = bool(profile.method_family)
        has_problem_definition = bool(
            self._regex_hits(
                r"\b(we define|problem statement|minimize|objective|optimization problem)\b"
            )
        )
        has_assumptions_or_threats = bool(
            self._regex_hits(r"\b(assumption|threats? to validity|limitations?)\b")
        )
        has_tech_depth = profile.num_equations > 3
        method_claims = self._evidence_spans(
            evidence,
            ("method", "approach", "algorithm", "we propose", "we introduce"),
        )
        method_clearly_described = len(method_claims) > 0

        checks = [
            (
                has_method_section,
                20.0,
                "method-section",
                "Add a dedicated method/approach section.",
            ),
            (
                has_equations,
                15.0,
                "equations",
                "Include formal equations where core method is defined.",
            ),
            (
                has_algorithm,
                15.0,
                "algorithm",
                "Provide algorithm/pseudocode for the core procedure.",
            ),
            (has_method_family, 10.0, "method-family", "Clarify method family and positioning."),
            (
                has_problem_definition,
                10.0,
                "problem-definition",
                "Add explicit problem definition and optimization objective.",
            ),
            (
                has_assumptions_or_threats,
                10.0,
                "assumption-analysis",
                "Discuss assumptions and threats to validity.",
            ),
            (
                has_tech_depth,
                10.0,
                "technical-depth",
                "Increase technical depth with deeper formal derivations.",
            ),
            (
                method_clearly_described,
                10.0,
                "method-clarity",
                "Describe method pipeline step-by-step with implementation details.",
            ),
        ]

        for passed, points, code, remediation in checks:
            if passed:
                score += points
                reason_codes.append(code)
            else:
                missing_evidence.append(code)
                suggestions.append(remediation)

        final_score = min(100.0, score)
        confidence = self._confidence_from_evidence(evidence, base=0.55)
        return DimensionScore(
            dimension="methodology",
            score=final_score,
            confidence=confidence,
            reason_codes=reason_codes,
            evidence_spans=method_claims[:5],
            missing_evidence=missing_evidence,
            suggestions=self._uniq(suggestions),
        )

    def _score_novelty(self, profile: PaperProfile, evidence: EvidenceLedger) -> DimensionScore:
        score = 0.0
        reason_codes: list[str] = []
        missing_evidence: list[str] = []
        suggestions: list[str] = []

        novelty_claims = self._evidence_spans(
            evidence,
            ("we propose", "we introduce", "contribution", "novel", "our method"),
        )
        if novelty_claims:
            score += 25
            reason_codes.append("contribution-claims")
        else:
            missing_evidence.append("contribution-claims")
            suggestions.append("State explicit contributions with measurable novelty.")

        if self._regex_hits(r"\b(compared to|unlike|differ from|in contrast|prior work)\b"):
            score += 20
            reason_codes.append("prior-work-delta")
        else:
            missing_evidence.append("prior-work-delta")
            suggestions.append("Add direct comparison language against closest prior work.")

        if profile.novelty_shape != NoveltyShape.UNKNOWN:
            score += 20
            reason_codes.append(f"novelty-shape:{profile.novelty_shape.value}")
        else:
            missing_evidence.append("novelty-shape-unknown")
            suggestions.append("Clarify whether novelty is method, application, or analysis.")

        if profile.num_references >= 20:
            score += 10
            reason_codes.append("literature-grounded")
        else:
            missing_evidence.append("thin-related-work")

        if profile.citation_neighborhood:
            score += 10
            reason_codes.append("venue-context")
        else:
            missing_evidence.append("venue-context")

        if profile.evidence_pattern in {EvidencePattern.BENCHMARK_HEAVY, EvidencePattern.MIXED}:
            score += 10
            reason_codes.append("empirical-support-pattern")
        else:
            missing_evidence.append("empirical-support-pattern")

        if profile.problem_domain:
            score += 5
            reason_codes.append("domain-specificity")

        final_score = min(100.0, score)
        confidence = self._confidence_from_evidence(evidence, base=0.5)
        return DimensionScore(
            dimension="novelty",
            score=final_score,
            confidence=confidence,
            reason_codes=reason_codes,
            evidence_spans=novelty_claims[:5],
            missing_evidence=missing_evidence,
            suggestions=self._uniq(suggestions)
            or ["Strengthen novelty claims with sharper differentiation from prior work."],
        )

    def _score_evaluation(self, profile: PaperProfile, evidence: EvidenceLedger) -> DimensionScore:
        score = 0.0
        reason_codes: list[str] = []
        missing_evidence: list[str] = []
        suggestions: list[str] = []

        has_benchmark_mentions = bool(
            self._regex_hits(r"\b(benchmark|dataset|baseline|sota|leaderboard)\b")
        )
        has_stats = bool(
            self._regex_hits(
                r"\b(p\s*[<>=]\s*0\.\d+|confidence interval|std\.?|standard deviation)\b"
            )
        )
        has_eval_section = self._has_section(("experiment", "evaluation", "results"))
        observed_eval_claims = self._evidence_spans(evidence, ("results", "benchmark", "baseline"))

        if has_eval_section:
            score += 15
            reason_codes.append("eval-section")
        else:
            missing_evidence.append("eval-section")
            suggestions.append("Add a dedicated evaluation/experiments section.")

        if has_benchmark_mentions:
            score += 20
            reason_codes.append("benchmark-mentions")
        else:
            missing_evidence.append("benchmark-mentions")
            suggestions.append("Report benchmark/dataset details and baseline choices.")

        if profile.num_tables >= 2:
            score += 15
            reason_codes.append("tables-rich")
        elif profile.num_tables == 1:
            score += 8
            reason_codes.append("tables-minimal")
        else:
            missing_evidence.append("result-tables")
            suggestions.append("Add result tables with baselines and ablations.")

        if has_stats:
            score += 15
            reason_codes.append("statistical-analysis")
        else:
            missing_evidence.append("statistical-analysis")
            suggestions.append("Include significance tests or confidence intervals.")

        if profile.validation_scale == "large":
            score += 15
            reason_codes.append("validation-large")
        elif profile.validation_scale == "medium":
            score += 10
            reason_codes.append("validation-medium")
        elif profile.validation_scale == "small":
            score += 5
            reason_codes.append("validation-small")
        else:
            missing_evidence.append("validation-scale")

        if profile.evidence_pattern in {EvidencePattern.BENCHMARK_HEAVY, EvidencePattern.MIXED}:
            score += 10
            reason_codes.append("evaluation-pattern")

        if len(observed_eval_claims) >= 2:
            score += 10
            reason_codes.append("multiple-eval-claims")
        elif len(observed_eval_claims) == 1:
            score += 5
            reason_codes.append("single-eval-claim")
        else:
            missing_evidence.append("explicit-eval-claims")

        final_score = min(100.0, score)
        confidence = self._confidence_from_evidence(evidence, base=0.55)
        return DimensionScore(
            dimension="evaluation",
            score=final_score,
            confidence=confidence,
            reason_codes=reason_codes,
            evidence_spans=observed_eval_claims[:5],
            missing_evidence=missing_evidence,
            suggestions=self._uniq(suggestions)
            or ["Strengthen empirical evaluation breadth and statistical rigor."],
        )

    def _score_presentation(
        self, profile: PaperProfile, evidence: EvidenceLedger
    ) -> DimensionScore:
        score = 0.0
        reason_codes: list[str] = []
        missing_evidence: list[str] = []
        suggestions: list[str] = []

        if profile.num_figures >= 3:
            score += 35
            reason_codes.append("figures-rich")
        elif profile.num_figures >= 1:
            score += 20
            reason_codes.append("figures-present")
        else:
            missing_evidence.append("figures")
            suggestions.append("Add clear figures to communicate pipeline and key findings.")

        if profile.num_tables >= 3:
            score += 35
            reason_codes.append("tables-rich")
        elif profile.num_tables >= 1:
            score += 20
            reason_codes.append("tables-present")
        else:
            missing_evidence.append("tables")
            suggestions.append("Add summary tables for quantitative results.")

        if profile.has_appendix:
            score += 20
            reason_codes.append("appendix-present")
        else:
            missing_evidence.append("appendix")
            suggestions.append(
                "Provide appendix for extra figures/tables and implementation artifacts."
            )

        if profile.word_count >= 3000:
            score += 10
            reason_codes.append("length-supports-structure")

        final_score = min(100.0, score)
        confidence = self._confidence_from_evidence(evidence, base=0.4)
        return DimensionScore(
            dimension="presentation",
            score=final_score,
            confidence=confidence,
            reason_codes=reason_codes,
            evidence_spans=[],
            missing_evidence=missing_evidence,
            suggestions=self._uniq(suggestions)
            or ["Improve figure/table density and readability."],
        )

    def _score_limitations(self, profile: PaperProfile, evidence: EvidenceLedger) -> DimensionScore:
        _ = profile
        score = 0.0
        reason_codes: list[str] = []
        missing_evidence: list[str] = []
        suggestions: list[str] = []

        limitation_spans = self._evidence_spans(
            evidence,
            ("limitation", "shortcoming", "constraint", "drawback", "threat"),
        )
        has_limitation_text = bool(
            self._regex_hits(
                r"\b(limitation|shortcoming|constraint|drawback|threats? to validity)\b"
            )
        )
        has_future_work = bool(
            self._regex_hits(r"\b(future work|future direction|next step|we plan to)\b")
        )

        if has_limitation_text:
            score += 45
            reason_codes.append("limitations-discussed")
        else:
            missing_evidence.append("limitations-discussed")
            suggestions.append("Add explicit limitations/threats-to-validity discussion.")

        if has_future_work:
            score += 25
            reason_codes.append("future-work")
        else:
            missing_evidence.append("future-work")
            suggestions.append("Add a future-work paragraph tied to current limitations.")

        if limitation_spans:
            score += 20
            reason_codes.append("limitation-spans")
        else:
            missing_evidence.append("limitation-spans")

        if evidence.missing_count == 0:
            score += 10
            reason_codes.append("low-missing-evidence")

        final_score = min(100.0, score)
        confidence = self._confidence_from_evidence(evidence, base=0.5)
        return DimensionScore(
            dimension="limitations",
            score=final_score,
            confidence=confidence,
            reason_codes=reason_codes,
            evidence_spans=limitation_spans[:5],
            missing_evidence=missing_evidence,
            suggestions=self._uniq(suggestions)
            or ["Include honest discussion of failure cases and external validity threats."],
        )

    def _score_reproducibility(
        self, profile: PaperProfile, evidence: EvidenceLedger
    ) -> DimensionScore:
        score = 0.0
        reason_codes: list[str] = []
        missing_evidence: list[str] = []
        suggestions: list[str] = []

        if profile.has_code:
            score += 30
            reason_codes.append("code-available")
        else:
            missing_evidence.append("code-available")
            suggestions.append("Release code or a reproducibility package.")

        repro_points = profile.reproducibility_maturity * 40.0
        score += repro_points
        if repro_points >= 30:
            reason_codes.append("repro-maturity-high")
        elif repro_points >= 15:
            reason_codes.append("repro-maturity-medium")
        else:
            missing_evidence.append("repro-maturity-low")
            suggestions.append("Add hyperparameters, seeds, data splits, and hardware details.")

        if self._regex_hits(
            r"\b(hyperparameter|training setup|implementation details|random seed)\b"
        ):
            score += 20
            reason_codes.append("impl-details")
        else:
            missing_evidence.append("impl-details")

        if profile.has_appendix:
            score += 10
            reason_codes.append("appendix-support")

        final_score = min(100.0, score)
        confidence = self._confidence_from_evidence(evidence, base=0.45)
        return DimensionScore(
            dimension="reproducibility",
            score=final_score,
            confidence=confidence,
            reason_codes=reason_codes,
            evidence_spans=self._evidence_spans(
                evidence,
                ("code", "implementation", "training", "hyperparameter", "seed"),
            ),
            missing_evidence=missing_evidence,
            suggestions=self._uniq(suggestions)
            or ["Document reproducibility assets and implementation settings."],
        )

    def _has_section(self, keywords: tuple[str, ...]) -> bool:
        for name in self._section_names:
            if any(keyword in name for keyword in keywords):
                return True
        return False

    def _regex_hits(self, pattern: str) -> int:
        return len(re.findall(pattern, self._raw_text, flags=re.IGNORECASE))

    def _evidence_spans(
        self,
        evidence: EvidenceLedger,
        keywords: tuple[str, ...],
        limit: int = 5,
    ) -> list[str]:
        matches: list[str] = []
        lowered = tuple(keyword.lower() for keyword in keywords)
        for item in evidence.items:
            span = item.span.strip()
            section = item.section.lower()
            claim = item.claim.lower()
            if any(keyword in span.lower() for keyword in lowered) or any(
                keyword in section or keyword in claim for keyword in lowered
            ):
                matches.append(span)
            if len(matches) >= limit:
                break
        return matches

    def _confidence_from_evidence(self, evidence: EvidenceLedger, base: float) -> float:
        observed_bonus = min(0.35, evidence.observed_count * 0.05)
        missing_penalty = min(0.20, evidence.missing_count * 0.04)
        confidence = base + observed_bonus - missing_penalty
        return max(0.1, min(1.0, round(confidence, 3)))

    def _uniq(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        output: list[str] = []
        for value in values:
            if value and value not in seen:
                seen.add(value)
                output.append(value)
        return output
