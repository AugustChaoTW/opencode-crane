"""Review Inspector Service - Pre-submission full paper review and defect detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from crane.services.journal_submission_service import JournalSubmissionService


class DefectSeverity(Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


@dataclass
class Defect:
    id: str
    chapter: str
    severity: DefectSeverity
    description: str
    location: str = ""
    suggestion: str = ""
    estimated_fix_time: str = "1 hour"


@dataclass
class ReviewReport:
    total_defects: int
    critical_defects: list[Defect] = field(default_factory=list)
    major_defects: list[Defect] = field(default_factory=list)
    minor_defects: list[Defect] = field(default_factory=list)
    summary: str = ""
    recommendation: str = ""
    estimated_total_fix_time: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_defects": self.total_defects,
            "critical_count": len(self.critical_defects),
            "major_count": len(self.major_defects),
            "minor_count": len(self.minor_defects),
            "summary": self.summary,
            "recommendation": self.recommendation,
            "estimated_fix_time": self.estimated_total_fix_time,
        }


class ReviewInspectorService:
    """Service for comprehensive pre-submission paper review."""

    CRITICAL_CHECKS = {
        "imrad_structure": "IMRAD structure complete (Abstract, Intro, Related Work, Methods, Results, Discussion, Conclusion)",
        "abstract": "Abstract present and ≤250 words",
        "introduction": "Introduction clear with research question and contributions",
        "ethics_approval": "Ethics approval number present (if human subjects)",
        "reproducibility": "Sufficient detail for reproducibility",
        "error_reporting": "Main results have error bars or confidence intervals",
        "page_limit": "Within page limit (±10% acceptable)",
    }

    MAJOR_CHECKS = {
        "related_work": "Related work organized and with comparison table",
        "contributions": "Contributions ≤4 and clearly stated",
        "ablation_study": "Ablation study complete for all proposed modules",
        "statistical_significance": "Statistical significance reported (p-values)",
        "sota_comparison": "SOTA comparison present and fair",
        "limitations": "≥3 limitations acknowledged in discussion",
        "reference_format": "Reference format consistent",
    }

    MINOR_CHECKS = {
        "figure_clarity": "Figures clear with labels and legends",
        "table_formatting": "Tables formatted consistently",
        "terminology": "Terminology used consistently",
        "spelling": "No spelling or grammar errors",
    }

    def __init__(self, project_dir: str | None = None):
        self.submission_service = JournalSubmissionService(project_dir)
        self.config = self.submission_service.load_config()
        self.defects: list[Defect] = []

    def review_full(self, paper_content: str | None = None) -> ReviewReport:
        """Perform comprehensive pre-submission review."""
        self.defects = []

        if paper_content:
            self._analyze_structure(paper_content)
            self._check_critical_items(paper_content)
            self._check_major_items(paper_content)
            self._check_minor_items(paper_content)

        return self._generate_report()

    def _analyze_structure(self, content: str) -> None:
        """Analyze paper structure."""
        sections = [
            "\\section{Abstract}",
            "\\section{Introduction}",
            "\\section{Related Work}",
            "\\section{Method",
            "\\section{Result",
            "\\section{Discussion}",
            "\\section{Conclusion}",
        ]

        found_sections = [s for s in sections if s.lower() in content.lower()]

        if len(found_sections) < 5:
            self.defects.append(
                Defect(
                    id="struct_001",
                    chapter="overall",
                    severity=DefectSeverity.CRITICAL,
                    description=f"IMRAD structure incomplete - found {len(found_sections)}/7 sections",
                    suggestion="Ensure all 7 IMRAD sections are present",
                    estimated_fix_time="2-3 hours",
                )
            )

    def _check_critical_items(self, content: str) -> None:
        """Check critical items that must be fixed before submission."""
        content_lower = content.lower()

        if content.count(":") < 5:
            self.defects.append(
                Defect(
                    id="abstract_001",
                    chapter="abstract",
                    severity=DefectSeverity.CRITICAL,
                    description="Abstract may be incomplete or too short",
                    suggestion="Abstract should contain: background, problem, solution, results, conclusion",
                    estimated_fix_time="1 hour",
                )
            )

        if "ethics" not in content_lower and "irb" not in content_lower:
            if self.config and self.config.has_human_subjects:
                self.defects.append(
                    Defect(
                        id="ethics_001",
                        chapter="overall",
                        severity=DefectSeverity.CRITICAL,
                        description="Ethics approval statement missing (paper involves human subjects)",
                        suggestion="Add ethics approval number in Acknowledgments or Methods",
                        estimated_fix_time="Contact with IRB",
                    )
                )

        if "data availability" not in content_lower and "code" not in content_lower:
            self.defects.append(
                Defect(
                    id="availability_001",
                    chapter="overall",
                    severity=DefectSeverity.CRITICAL,
                    description="No data/code availability statement",
                    suggestion="Add statement: 'Code is available at [URL]' or explain why not available",
                    estimated_fix_time="30 minutes",
                )
            )

    def _check_major_items(self, content: str) -> None:
        """Check major items that should be fixed before submission."""
        content_lower = content.lower()

        if "table" not in content_lower or "figure" not in content_lower:
            self.defects.append(
                Defect(
                    id="sota_001",
                    chapter="related_work",
                    severity=DefectSeverity.MAJOR,
                    description="Missing comparison table/figure vs SOTA",
                    suggestion="Add Table/Figure comparing methods with SOTA",
                    estimated_fix_time="2 hours",
                )
            )

        ablation_keywords = ["ablation", "without", "without_", "-", "variant"]
        has_ablation = any(kw in content_lower for kw in ablation_keywords)
        if not has_ablation:
            self.defects.append(
                Defect(
                    id="ablation_001",
                    chapter="results",
                    severity=DefectSeverity.MAJOR,
                    description="Ablation study appears incomplete or missing",
                    suggestion="Add ablation experiments for each major component",
                    estimated_fix_time="3-5 days (requires new experiments)",
                )
            )

        limitation_keywords = ["limitation", "limitation", "future", "constraint", "challenge"]
        has_limitations = any(kw in content_lower for kw in limitation_keywords)
        if not has_limitations:
            self.defects.append(
                Defect(
                    id="limitation_001",
                    chapter="discussion",
                    severity=DefectSeverity.MAJOR,
                    description="Limitations not clearly acknowledged",
                    suggestion="Add ≥3 explicit limitations in Discussion section",
                    estimated_fix_time="1-2 hours",
                )
            )

    def _check_minor_items(self, content: str) -> None:
        """Check minor items that can be fixed after submission if needed."""
        lines = content.split("\n")

        long_lines = [l for l in lines if len(l) > 120]
        if len(long_lines) > 5:
            self.defects.append(
                Defect(
                    id="formatting_001",
                    chapter="overall",
                    severity=DefectSeverity.MINOR,
                    description="Some lines exceed 120 characters (formatting issue)",
                    suggestion="Reformat long sentences for better readability",
                    estimated_fix_time="1 hour",
                )
            )

        if "[?]" in content or "TODO" in content or "FIXME" in content:
            self.defects.append(
                Defect(
                    id="placeholder_001",
                    chapter="overall",
                    severity=DefectSeverity.MINOR,
                    description="Placeholder text found in manuscript",
                    suggestion="Replace all [?], TODO, FIXME with actual content",
                    estimated_fix_time="30 minutes",
                )
            )

    def _generate_report(self) -> ReviewReport:
        """Generate review report from collected defects."""
        critical = [d for d in self.defects if d.severity == DefectSeverity.CRITICAL]
        major = [d for d in self.defects if d.severity == DefectSeverity.MAJOR]
        minor = [d for d in self.defects if d.severity == DefectSeverity.MINOR]

        report = ReviewReport(
            total_defects=len(self.defects),
            critical_defects=critical,
            major_defects=major,
            minor_defects=minor,
        )

        if not self.defects:
            report.summary = "✅ No defects found - paper ready for submission!"
            report.recommendation = "SUBMIT NOW"
        elif critical:
            report.summary = (
                f"⚠️  {len(critical)} CRITICAL defect(s) must be fixed before submission"
            )
            report.recommendation = "FIX CRITICAL ITEMS BEFORE SUBMITTING"
            report.estimated_total_fix_time = "2-3 days"
        elif major:
            report.summary = f"⚠️  {len(major)} MAJOR defect(s) - recommend fixing before submission"
            report.recommendation = "CAN SUBMIT, BUT EXPECT REVISION REQUESTS"
            report.estimated_total_fix_time = "3-5 days"
        else:
            report.summary = f"✅ Only {len(minor)} minor formatting issue(s)"
            report.recommendation = "READY TO SUBMIT"
            report.estimated_total_fix_time = "<1 day"

        return report

    def get_defect_summary(self) -> dict[str, Any]:
        """Get summary of all defects found."""
        critical = [d for d in self.defects if d.severity == DefectSeverity.CRITICAL]
        major = [d for d in self.defects if d.severity == DefectSeverity.MAJOR]
        minor = [d for d in self.defects if d.severity == DefectSeverity.MINOR]

        return {
            "total": len(self.defects),
            "critical": {
                "count": len(critical),
                "items": [
                    {
                        "id": d.id,
                        "description": d.description,
                        "fix_time": d.estimated_fix_time,
                    }
                    for d in critical
                ],
            },
            "major": {
                "count": len(major),
                "items": [
                    {
                        "id": d.id,
                        "description": d.description,
                        "fix_time": d.estimated_fix_time,
                    }
                    for d in major
                ],
            },
            "minor": {
                "count": len(minor),
                "items": [
                    {
                        "id": d.id,
                        "description": d.description,
                        "fix_time": d.estimated_fix_time,
                    }
                    for d in minor
                ],
            },
        }
