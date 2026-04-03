"""Section-level paper review service."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from crane.models.paper import Paper
from crane.services.latex_parser import SectionLocation, parse_latex_sections


class ReviewType(Enum):
    LOGIC = "logic"
    DATA = "data"
    FRAMING = "framing"
    COMPLETENESS = "completeness"
    WRITING = "writing"
    FIGURES = "figures"
    SCHOLARLY_VOICE = "scholarly_voice"
    BASELINE_COMPLETENESS = "baseline_completeness"
    EVALUATION_RIGOR = "evaluation_rigor"
    SCOPE_LIMITATION = "scope_limitation"
    METHODOLOGY = "methodology"
    LENGTH = "length"


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ReviewIssue:
    id: str
    type: ReviewType
    severity: Severity
    location: str
    original: str
    issue: str
    suggestion: str
    status: str = "pending"


@dataclass
class SectionReview:
    name: str
    start_line: int
    end_line: int
    issues: list[ReviewIssue]
    protected_zones: list[dict[str, Any]]
    score: float
    issues_count: dict[str, int]


@dataclass
class PaperReview:
    paper_path: str
    reviewed_at: str
    sections: list[SectionReview]
    summary: dict[str, Any]


class SectionReviewService:
    """Service for section-level paper review."""

    def __init__(self):
        self.review_patterns = self._build_review_patterns()

    def _build_review_patterns(self) -> dict[ReviewType, list[dict]]:
        return {
            ReviewType.LOGIC: [
                {
                    "pattern": re.compile(
                        r"if\s+['\"][^'\"]+['\"]|or\s+['\"][^'\"]+['\"]", re.IGNORECASE
                    ),
                    "issue": "Potential Python logic error: string comparison with 'or'",
                    "suggestion": "Use any() or explicit comparison",
                    "severity": Severity.CRITICAL,
                },
            ],
            ReviewType.DATA: [
                {
                    "pattern": re.compile(r"\d+\.?\d*\s*%"),
                    "check": "percentage_consistency",
                    "severity": Severity.HIGH,
                },
                {
                    "pattern": re.compile(r"\$\d+[\d,.]*/\w+"),
                    "check": "cost_consistency",
                    "severity": Severity.HIGH,
                },
                {
                    "pattern": re.compile(r"\d+\.?\d*\s*ms"),
                    "check": "latency_consistency",
                    "severity": Severity.HIGH,
                },
            ],
            ReviewType.FRAMING: [
                {
                    "pattern": re.compile(r"novel\s+\w+", re.IGNORECASE),
                    "issue": "Possible overclaiming with 'novel'",
                    "suggestion": "Ensure claim is supported by comparison",
                    "severity": Severity.MEDIUM,
                },
                {
                    "pattern": re.compile(r"first\s+to|state-of-the-art|sota", re.IGNORECASE),
                    "issue": "Strong claim requiring citation",
                    "suggestion": "Add citation or weaken claim",
                    "severity": Severity.HIGH,
                },
                {
                    "pattern": re.compile(r"expert\s+system|neuro-symbolic", re.IGNORECASE),
                    "issue": "Technical term requiring precise definition",
                    "suggestion": "Define term or use more precise language",
                    "severity": Severity.HIGH,
                },
                {
                    "pattern": re.compile(
                        r"\b(deterministic repair|post-processing pipeline|repair layer)\b",
                        re.IGNORECASE,
                    ),
                    "check": "appropriate_framing",
                    "severity": Severity.LOW,
                },
                {
                    "pattern": re.compile(
                        r"\b(breakthrough|revolutionary|groundbreaking|unprecedented)\b",
                        re.IGNORECASE,
                    ),
                    "issue": "Overclaiming detected",
                    "suggestion": "Use more measured language (e.g., 'effective', 'competitive')",
                    "severity": Severity.HIGH,
                },
            ],
            ReviewType.COMPLETENESS: [
                {
                    "pattern": re.compile(r"baseline|comparison|compare", re.IGNORECASE),
                    "check": "baseline_mentioned",
                    "severity": Severity.HIGH,
                },
                {
                    "pattern": re.compile(
                        r"limitation|future\s+work|beyond\s+scope", re.IGNORECASE
                    ),
                    "check": "limitations_discussed",
                    "severity": Severity.MEDIUM,
                },
            ],
            ReviewType.WRITING: [
                {
                    "pattern": re.compile(
                        r"It\s+is\s+worth\s+noting|It\s+should\s+be\s+emphasized|As\s+can\s+be\s+seen",
                        re.IGNORECASE,
                    ),
                    "issue": "AI writing pattern: filler phrase",
                    "suggestion": "Remove filler, state directly",
                    "severity": Severity.LOW,
                },
                {
                    "pattern": re.compile(r"Furthermore,|Moreover,|Additionally,", re.IGNORECASE),
                    "check": "transition_variety",
                    "severity": Severity.LOW,
                },
                {
                    "pattern": re.compile(
                        r"significant\s+improvement|substantial\s+gain", re.IGNORECASE
                    ),
                    "issue": "Vague quantifier",
                    "suggestion": "Replace with specific percentage or metric",
                    "severity": Severity.MEDIUM,
                },
            ],
            ReviewType.FIGURES: [
                {
                    "pattern": re.compile(r"\\begin\{figure\}.*?\\end\{figure\}", re.DOTALL),
                    "check": "figure_completeness",
                    "severity": Severity.MEDIUM,
                },
            ],
            ReviewType.SCHOLARLY_VOICE: [
                {
                    "pattern": re.compile(
                        r"\b(awesome|cool|nice|great|amazing|fantastic|incredible|super|wonderful)\b",
                        re.IGNORECASE,
                    ),
                    "issue": "Informal/colloquial language inappropriate for academic writing",
                    "suggestion": (
                        "Replace with precise academic terms "
                        "(e.g., 'significant', 'substantial', 'effective')"
                    ),
                    "severity": Severity.MEDIUM,
                },
                {
                    "pattern": re.compile(
                        (
                            r"\b(stuff|things|basically|literally|actually|really|very|"
                            r"pretty much|kind of|sort of)\b"
                        ),
                        re.IGNORECASE,
                    ),
                    "issue": "Vague or informal language",
                    "suggestion": "Use specific technical terms instead of vague descriptors",
                    "severity": Severity.MEDIUM,
                },
                {
                    "pattern": re.compile(
                        r"\b(I think|I believe|in my opinion|I feel|we think|we believe)\b",
                        re.IGNORECASE,
                    ),
                    "issue": "Personal opinion language inappropriate for academic writing",
                    "suggestion": "Remove personal pronouns and state findings objectively",
                    "severity": Severity.HIGH,
                },
                {
                    "pattern": re.compile(
                        r"\b(a lot of|lots of|tons of|loads of|bunch of)\b", re.IGNORECASE
                    ),
                    "issue": "Informal quantification",
                    "suggestion": (
                        "Use precise quantifiers "
                        "(e.g., 'numerous', 'several', 'multiple', specific numbers)"
                    ),
                    "severity": Severity.MEDIUM,
                },
                {
                    "pattern": re.compile(
                        r"\b(gets?|got|gotten|gotta|gonna|wanna|kinda)\b", re.IGNORECASE
                    ),
                    "issue": "Informal verb forms",
                    "suggestion": (
                        "Use formal equivalents (e.g., 'obtains', 'obtained', 'must', 'going to')"
                    ),
                    "severity": Severity.MEDIUM,
                },
                {
                    "pattern": re.compile(
                        r"\b(big|huge|tiny|small|fast|slow)\b(?!\s+(?:scale|data|model|number|amount))",
                        re.IGNORECASE,
                    ),
                    "issue": "Informal adjective (consider context)",
                    "suggestion": (
                        "Use precise technical terms "
                        "(e.g., 'large-scale', 'high-speed', 'computationally efficient')"
                    ),
                    "severity": Severity.LOW,
                },
                {
                    "pattern": re.compile(r"(?<!\. )\b(And|But|So|Or)\b\s+[A-Z]", re.IGNORECASE),
                    "issue": "Sentence starting with conjunction (common in informal writing)",
                    "suggestion": (
                        "Restructure sentence or use formal transition "
                        "(e.g., 'Furthermore', 'However', 'Consequently')"
                    ),
                    "severity": Severity.LOW,
                },
                {
                    "pattern": re.compile(r"\b(show|shows|showed)\s+(that|how)\b", re.IGNORECASE),
                    "check": "demonstrate_precision",
                    "severity": Severity.LOW,
                },
                {
                    "pattern": re.compile(
                        r"\b(thing|things|stuff|issue|problem)\s+(is|are|was|were)\b",
                        re.IGNORECASE,
                    ),
                    "issue": "Vague subject reference",
                    "suggestion": (
                        "Specify what you're referring to "
                        "(e.g., 'The challenge is', 'The limitation is')"
                    ),
                    "severity": Severity.MEDIUM,
                },
                {
                    "pattern": re.compile(
                        r"\b(like|such as)\s+\w+,\s*\w+,\s*(and|or)\s+\w+", re.IGNORECASE
                    ),
                    "check": "list_completeness",
                    "severity": Severity.LOW,
                },
            ],
            ReviewType.BASELINE_COMPLETENESS: [
                {
                    "pattern": re.compile(
                        r"\b(PICARD|Outlines|Guidance|Constrained Decoding|grammar-constrained)\b",
                        re.IGNORECASE,
                    ),
                    "issue": "Missing constrained decoding baseline comparison",
                    "suggestion": "Add comparison with PICARD, Outlines, or Guidance",
                    "severity": Severity.HIGH,
                },
                {
                    "pattern": re.compile(
                        r"\b(Model Retry|naive|strawman|without repair)\b", re.IGNORECASE
                    ),
                    "issue": "Possible strawman baseline detected",
                    "suggestion": "Ensure baseline is meaningful, not a strawman",
                    "severity": Severity.HIGH,
                },
                {
                    "pattern": re.compile(
                        r"\b(state-of-the-art|SOTA|current best)\b", re.IGNORECASE
                    ),
                    "issue": "SOTA comparison required",
                    "suggestion": "Add comparison with current state-of-the-art methods",
                    "severity": Severity.HIGH,
                },
            ],
            ReviewType.EVALUATION_RIGOR: [
                {
                    "pattern": re.compile(
                        r"\b(parse success|structural success|format compliance)\b", re.IGNORECASE
                    ),
                    "issue": "Structural metric only, missing semantic evaluation",
                    "suggestion": "Add semantic accuracy evaluation alongside structural metrics",
                    "severity": Severity.HIGH,
                },
                {
                    "pattern": re.compile(
                        r"\b(semantic reversal|semantic accuracy|semantic correctness)\b",
                        re.IGNORECASE,
                    ),
                    "check": "semantic_evaluation_present",
                    "severity": Severity.MEDIUM,
                },
                {
                    "pattern": re.compile(
                        r"\b(failure rate|failure analysis|edge cases|0\.02\%)\b", re.IGNORECASE
                    ),
                    "check": "failure_analysis_present",
                    "severity": Severity.MEDIUM,
                },
                {
                    "pattern": re.compile(
                        (
                            r"\b(p-value|confidence interval|statistical significance|"
                            r"standard deviation)\b"
                        ),
                        re.IGNORECASE,
                    ),
                    "check": "statistical_analysis_present",
                    "severity": Severity.MEDIUM,
                },
            ],
            ReviewType.SCOPE_LIMITATION: [
                {
                    "pattern": re.compile(
                        (
                            r"\b(production-ready|production-grade|fully online|"
                            r"real-world deployment)\b"
                        ),
                        re.IGNORECASE,
                    ),
                    "issue": "Strong scope claim requiring validation",
                    "suggestion": (
                        "Clarify: controlled experimental evaluation, not production deployment"
                    ),
                    "severity": Severity.HIGH,
                },
                {
                    "pattern": re.compile(
                        r"\b(all tasks|any domain|universal|general-purpose)\b", re.IGNORECASE
                    ),
                    "issue": "Overgeneralization detected",
                    "suggestion": "Specify limitations or mark as future work",
                    "severity": Severity.HIGH,
                },
                {
                    "pattern": re.compile(
                        (
                            r"\b(generalize to|applicable to|transfer to)\s+"
                            r"(NER|QA|summarization|translation)\b"
                        ),
                        re.IGNORECASE,
                    ),
                    "issue": "Generalization claim without validation",
                    "suggestion": "Add validation or mark as hypothesized",
                    "severity": Severity.HIGH,
                },
                {
                    "pattern": re.compile(
                        r"\b(beyond the scope|out of scope|future work|limitation)\b", re.IGNORECASE
                    ),
                    "check": "limitations_discussed",
                    "severity": Severity.LOW,
                },
            ],
            ReviewType.METHODOLOGY: [
                {
                    "pattern": re.compile(
                        r"\b(hyperparameter|parameter sensitivity|threshold selection)\b",
                        re.IGNORECASE,
                    ),
                    "check": "parameter_discussion_present",
                    "severity": Severity.MEDIUM,
                },
                {
                    "pattern": re.compile(
                        r"\b(implementation detail|training setup|experimental setup)\b",
                        re.IGNORECASE,
                    ),
                    "check": "implementation_details_present",
                    "severity": Severity.MEDIUM,
                },
                {
                    "pattern": re.compile(
                        r"\b(code available|github|repository|open source|reproducibility)\b",
                        re.IGNORECASE,
                    ),
                    "check": "code_availability_mentioned",
                    "severity": Severity.LOW,
                },
            ],
            ReviewType.LENGTH: [
                {
                    "pattern": re.compile(r"\d+\s*pages", re.IGNORECASE),
                    "check": "page_count_mentioned",
                    "severity": Severity.LOW,
                },
                {
                    "pattern": re.compile(
                        r"\b(repeated|redundant|duplicate|unnecessary)\b", re.IGNORECASE
                    ),
                    "issue": "Possible redundancy detected",
                    "suggestion": "Remove redundant content",
                    "severity": Severity.MEDIUM,
                },
            ],
        }

    def review_section(
        self,
        section: SectionLocation,
        review_types: list[ReviewType],
        full_text: str = "",
    ) -> SectionReview:
        """Review a single section."""
        issues = []
        issue_counter = 0

        for review_type in review_types:
            patterns = self.review_patterns.get(review_type, [])

            for pattern_config in patterns:
                pattern = pattern_config["pattern"]

                for match in pattern.finditer(section.content):
                    issue_counter += 1
                    issue_id = f"{section.name.lower().replace(' ', '_')}_{issue_counter:03d}"

                    issue = ReviewIssue(
                        id=issue_id,
                        type=review_type,
                        severity=pattern_config.get("severity", Severity.MEDIUM),
                        location=f"Section {section.name}",
                        original=match.group(0)[:100],
                        issue=pattern_config.get("issue", f"{review_type.value} pattern detected"),
                        suggestion=pattern_config.get("suggestion", "Review this section"),
                    )
                    issues.append(issue)

        issues_count = {
            "critical": sum(1 for i in issues if i.severity == Severity.CRITICAL),
            "high": sum(1 for i in issues if i.severity == Severity.HIGH),
            "medium": sum(1 for i in issues if i.severity == Severity.MEDIUM),
            "low": sum(1 for i in issues if i.severity == Severity.LOW),
        }

        total_issues = len(issues)
        score = max(0.0, 1.0 - (total_issues * 0.05) - (issues_count["critical"] * 0.2))

        return SectionReview(
            name=section.name,
            start_line=section.start_line,
            end_line=section.end_line,
            issues=issues,
            protected_zones=[],
            score=round(score, 2),
            issues_count=issues_count,
        )

    def analyze_black_swans(
        self,
        issues: list[dict[str, Any]],
        paper_context: dict[str, Any] | None = None,
    ) -> list[dict[str, str]]:
        """Generate three low-probability, high-impact invalidation scenarios."""
        context = paper_context or {}
        domain = str(context.get("domain") or "the target domain")
        paper_type = str(context.get("paper_type") or "empirical study")
        key_claims = context.get("key_claims") or []
        primary_claim = key_claims[0] if key_claims else "your core contribution"

        issue_types = {str(issue.get("type", "")).lower() for issue in issues}
        has_baseline_risk = bool(
            {"framing", "baseline_completeness", "scope_limitation"} & issue_types
        )
        has_data_risk = bool({"data", "evaluation_rigor"} & issue_types)
        has_repro_risk = bool({"methodology", "completeness", "length"} & issue_types)

        scenario_1 = {
            "scenario": (
                f"A stronger method is published in {domain} before review, making "
                f"comparisons behind {primary_claim} appear obsolete."
            ),
            "probability": "low",
            "impact": "critical" if has_baseline_risk else "high",
            "mitigation": (
                "Add a camera-ready fallback benchmark plan, include stronger and "
                "newer baselines, and frame contribution as a robust trade-off "
                "(quality/latency/cost) rather than pure SOTA."
            ),
        }
        scenario_2 = {
            "scenario": (
                f"A latent annotation or split-leakage flaw is discovered in a key {domain} "
                "dataset, invalidating headline improvements."
            ),
            "probability": "very-low" if has_data_risk else "low",
            "impact": "critical",
            "mitigation": (
                "Pre-register alternate datasets, run contamination checks, and report "
                "sensitivity analyses showing whether conclusions hold after relabeling "
                "or dataset replacement."
            ),
        }
        scenario_3 = {
            "scenario": (
                f"Under independent reproduction, the {paper_type} pipeline shows unstable "
                "behavior outside tuned conditions, collapsing practical gains."
            ),
            "probability": "low" if has_repro_risk else "very-low",
            "impact": "high",
            "mitigation": (
                "Ship deterministic settings, ablations over sensitive parameters, and "
                "multi-seed confidence intervals to prove robustness under distribution shift."
            ),
        }

        return [scenario_1, scenario_2, scenario_3]

    def simulate_competitor_response(
        self,
        issues: list[dict[str, Any]],
        paper_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Simulate how a capable competitor would exploit identified weaknesses."""
        context = paper_context or {}
        domain = str(context.get("domain") or "this domain")

        exploitable_weaknesses: list[str] = []
        counter_measures: list[str] = []

        for issue in issues:
            severity = str(issue.get("severity", "")).lower()
            issue_type = str(issue.get("type", "")).lower()
            issue_text = str(issue.get("issue", "")).strip()

            if severity in {"critical", "high"} and issue_text:
                exploitable_weaknesses.append(issue_text)

            if issue_type in {"baseline_completeness", "framing", "evaluation_rigor"}:
                counter_measures.append(
                    "Expand baseline suite and include the newest strong competitor methods."
                )
            if issue_type in {"data", "methodology"}:
                counter_measures.append(
                    "Add robustness checks (multi-seed, alternate splits, and error analysis)."
                )
            if issue_type in {"scope_limitation", "completeness"}:
                counter_measures.append(
                    "Narrow claims and explicitly delimit where the method should not be used."
                )

        if not exploitable_weaknesses:
            exploitable_weaknesses = [
                "Comparative advantage may be challenged by stronger baseline framing.",
                "Evidence depth may be attacked if failure modes are under-reported.",
            ]

        if not counter_measures:
            counter_measures = [
                "Preempt reviewer concerns with stronger ablations and stress tests.",
                "Convert broad claims into scoped, evidence-backed statements.",
            ]

        competitor_strategy = (
            f"A smart competitor in {domain} would replicate your setup on stronger baselines, "
            "highlight failure cases where gains disappear, and reposition your contribution as "
            "incremental unless your evidence and scope boundaries are tightened."
        )

        return {
            "competitor_strategy": competitor_strategy,
            "exploitable_weaknesses": list(dict.fromkeys(exploitable_weaknesses))[:6],
            "counter_measures": list(dict.fromkeys(counter_measures))[:6],
        }

    def check_survivor_bias(
        self,
        issues: list[dict[str, Any]],
        paper_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Detect likely survivor-bias patterns from issue and context signals."""
        _ = paper_context or {}

        evidence: list[str] = []
        issue_text_blob = " ".join(
            f"{issue.get('issue', '')} {issue.get('suggestion', '')}" for issue in issues
        ).lower()
        issue_types = {str(issue.get("type", "")).lower() for issue in issues}

        if "overclaim" in issue_text_blob or "state-of-the-art" in issue_text_blob:
            evidence.append(
                "Strong success framing appears without sufficient conservative framing."
            )
        if "strawman" in issue_text_blob or "missing" in issue_text_blob:
            evidence.append(
                "Baseline design may emphasize wins while underrepresenting hard comparisons."
            )
        if "failure" not in issue_text_blob and "evaluation_rigor" in issue_types:
            evidence.append(
                "Failure-mode reporting appears limited relative to performance claims."
            )
        if "limitations" not in issue_text_blob and "completeness" in issue_types:
            evidence.append("Limitations discussion appears weak, raising survivorship concern.")

        has_survivor_bias = len(evidence) >= 2
        recommendation = (
            "Add explicit negative results, failed variants, and boundary conditions. "
            "Report where the method underperforms and compare against difficult baselines "
            "to avoid survivorship bias."
            if has_survivor_bias
            else "Current draft shows no strong survivor-bias signal; preserve this by retaining "
            "failure analyses and explicit limitations."
        )

        return {
            "has_survivor_bias": has_survivor_bias,
            "evidence": evidence,
            "recommendation": recommendation,
        }

    def generate_strengthened_version(
        self,
        issues: list[dict[str, Any]],
        black_swans: list[dict[str, str]],
        competitor_analysis: dict[str, Any],
    ) -> str:
        """Generate a markdown strengthened version from adversarial findings."""
        top_issues = [
            str(issue.get("issue", "")).strip()
            for issue in issues
            if str(issue.get("severity", "")).lower() in {"critical", "high"}
        ]
        top_issues = [issue for issue in top_issues if issue]

        weakness_points = [
            f"- {item}"
            for item in competitor_analysis.get("exploitable_weaknesses", [])[:4]
            if item
        ]
        counter_points = [
            f"- {item}" for item in competitor_analysis.get("counter_measures", [])[:4] if item
        ]
        swan_points = [
            f"- **{swan.get('scenario', 'Unknown scenario')}** → {swan.get('mitigation', '')}"
            for swan in black_swans[:3]
        ]
        priority_points = [f"- {issue}" for issue in top_issues[:4]]

        if not priority_points:
            priority_points = ["- No critical/high issues detected; focus on robustness hardening."]
        if not weakness_points:
            weakness_points = ["- No explicit exploitable weaknesses identified."]
        if not counter_points:
            counter_points = ["- Add stronger evidence depth and scoped claims."]

        return "\n".join(
            [
                "## Strengthened Version (Adversarially Hardened)",
                "",
                "### 1) Priority Weaknesses to Fix First",
                *priority_points,
                "",
                "### 2) Competitor Attack Surface",
                *weakness_points,
                "",
                "### 3) Counter-Measures to Preempt Criticism",
                *counter_points,
                "",
                "### 4) Black Swan Preparedness",
                *swan_points,
                "",
                "### 5) Revised Positioning",
                (
                    "Reframe contributions as robust and scoped rather than universally superior. "
                    "Back every strong claim with stronger baselines, failure analyses, and "
                    "reproducibility evidence so the paper remains credible under adversarial review."
                ),
            ]
        )

    def _build_paper_context(
        self, paper: Paper | None, issues: list[ReviewIssue]
    ) -> dict[str, Any]:
        """Build heuristic paper context for adversarial analysis."""
        default_context: dict[str, Any] = {
            "domain": "AI/ML",
            "paper_type": "empirical study",
            "key_claims": [],
        }
        if not paper:
            return default_context

        context = dict(default_context)
        if paper.ai_annotations:
            tags = paper.ai_annotations.tags or []
            context["domain"] = tags[0] if tags else default_context["domain"]
            context["paper_type"] = (
                "theoretical/diagnostic"
                if "theoretical" in {tag.lower() for tag in tags}
                else default_context["paper_type"]
            )
            context["key_claims"] = paper.ai_annotations.key_contributions or []

        if not context["key_claims"]:
            high_issues = [
                i.issue for i in issues if i.severity in {Severity.CRITICAL, Severity.HIGH}
            ]
            context["key_claims"] = high_issues[:2]

        return context

    def _issues_to_dict(self, issues: list[ReviewIssue]) -> list[dict[str, Any]]:
        """Convert ReviewIssue models to dictionary payloads."""
        return [
            {
                "id": issue.id,
                "type": issue.type.value,
                "severity": issue.severity.value,
                "location": issue.location,
                "original": issue.original,
                "issue": issue.issue,
                "suggestion": issue.suggestion,
                "status": issue.status,
            }
            for issue in issues
        ]

    def review_paper(
        self,
        paper_path: str | Path,
        sections: list[str] | None = None,
        review_types: list[ReviewType] | None = None,
        paper: Paper | None = None,
    ) -> PaperReview:
        """Review entire paper or specific sections."""
        structure = parse_latex_sections(paper_path)

        if review_types is None:
            review_types = list(ReviewType)

        section_reviews = []

        for section in structure.sections:
            if sections and section.name not in sections:
                continue

            review = self.review_section(section, review_types, structure.raw_text)
            section_reviews.append(review)

            for subsection in section.subsections:
                if sections and subsection.name not in sections:
                    continue
                sub_review = self.review_section(subsection, review_types, structure.raw_text)
                section_reviews.append(sub_review)

        annotation_context_used = False
        if paper and paper.ai_annotations:
            annotation_text_parts = [
                paper.ai_annotations.summary,
                paper.ai_annotations.methodology,
                paper.ai_annotations.relevance_notes,
                " ".join(paper.ai_annotations.key_contributions),
                " ".join(paper.ai_annotations.tags),
            ]
            annotation_text = "\n".join(part for part in annotation_text_parts if part)
            if annotation_text:
                annotation_context_used = True
                ai_section = SectionLocation(
                    name="AI Annotations",
                    level=1,
                    start_line=0,
                    end_line=0,
                    content=annotation_text,
                    subsections=[],
                )
                section_reviews.append(
                    self.review_section(ai_section, review_types, structure.raw_text)
                )

        total_issues = sum(len(r.issues) for r in section_reviews)
        all_issues = [i for r in section_reviews for i in r.issues]
        issue_dicts = self._issues_to_dict(all_issues)
        paper_context = self._build_paper_context(paper, all_issues)
        black_swans = self.analyze_black_swans(issue_dicts, paper_context)
        competitor_analysis = self.simulate_competitor_response(issue_dicts, paper_context)
        survivor_bias = self.check_survivor_bias(issue_dicts, paper_context)
        strengthened_version = self.generate_strengthened_version(
            issue_dicts,
            black_swans,
            competitor_analysis,
        )

        summary = {
            "total_issues": total_issues,
            "by_severity": {
                "critical": sum(1 for i in all_issues if i.severity == Severity.CRITICAL),
                "high": sum(1 for i in all_issues if i.severity == Severity.HIGH),
                "medium": sum(1 for i in all_issues if i.severity == Severity.MEDIUM),
                "low": sum(1 for i in all_issues if i.severity == Severity.LOW),
            },
            "by_type": {rt.value: sum(1 for i in all_issues if i.type == rt) for rt in ReviewType},
            "overall_score": round(
                sum(r.score for r in section_reviews) / max(len(section_reviews), 1), 2
            ),
            "annotation_context_used": annotation_context_used,
            "recommendation": self._get_recommendation(total_issues, all_issues),
            "adversarial_analysis": {
                "black_swans": black_swans,
                "competitor_response": competitor_analysis,
                "survivor_bias": survivor_bias,
                "strengthened_version": strengthened_version,
            },
        }

        return PaperReview(
            paper_path=str(paper_path),
            reviewed_at=datetime.now().isoformat(),
            sections=section_reviews,
            summary=summary,
        )

    def _get_recommendation(self, total_issues: int, issues: list[ReviewIssue]) -> str:
        critical = sum(1 for i in issues if i.severity == Severity.CRITICAL)
        high = sum(1 for i in issues if i.severity == Severity.HIGH)

        if critical > 0:
            return "CRITICAL: Must fix critical issues before submission"
        elif high > 3:
            return "HIGH: Significant revision needed before submission"
        elif total_issues > 10:
            return "MEDIUM: Moderate revision recommended"
        else:
            return "LOW: Minor polishing recommended"

    def to_dict(self, review: PaperReview) -> dict[str, Any]:
        """Convert PaperReview to dictionary."""
        return {
            "paper_path": review.paper_path,
            "reviewed_at": review.reviewed_at,
            "sections": [
                {
                    "name": s.name,
                    "location": {"start_line": s.start_line, "end_line": s.end_line},
                    "issues": [
                        {
                            "id": i.id,
                            "type": i.type.value,
                            "severity": i.severity.value,
                            "location": i.location,
                            "original": i.original,
                            "issue": i.issue,
                            "suggestion": i.suggestion,
                            "status": i.status,
                        }
                        for i in s.issues
                    ],
                    "protected_zones": s.protected_zones,
                    "score": s.score,
                    "issues_count": s.issues_count,
                }
                for s in review.sections
            ],
            "summary": review.summary,
        }
