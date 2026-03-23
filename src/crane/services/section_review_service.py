"""Section-level paper review service."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from crane.services.latex_parser import PaperStructure, SectionLocation, parse_latex_sections


class ReviewType(Enum):
    LOGIC = "logic"
    DATA = "data"
    FRAMING = "framing"
    COMPLETENESS = "completeness"
    WRITING = "writing"
    FIGURES = "figures"


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

    def review_paper(
        self,
        paper_path: str | Path,
        sections: list[str] | None = None,
        review_types: list[ReviewType] | None = None,
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

        total_issues = sum(len(r.issues) for r in section_reviews)
        all_issues = [i for r in section_reviews for i in r.issues]

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
            "recommendation": self._get_recommendation(total_issues, all_issues),
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
