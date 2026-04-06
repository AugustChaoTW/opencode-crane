"""Submission Workflow Service - Orchestrates the complete journal submission workflow."""

from __future__ import annotations

from typing import Any

from crane.services.chapter_coach_service import ChapterCoachService
from crane.services.cover_letter_service import CoverLetterService
from crane.services.journal_submission_service import JournalSubmissionService
from crane.services.questionnaire_engine import QuestionnaireEngine
from crane.services.review_inspector_service import ReviewInspectorService
from crane.services.risk_scoring_service import RiskScoringService


class SubmissionWorkflowService:
    """Orchestrates the complete paper submission workflow with three roles."""

    def __init__(self, project_dir: str | None = None):
        self.submission_service = JournalSubmissionService(project_dir)
        self.questionnaire_engine = QuestionnaireEngine()
        self.coach_service = ChapterCoachService(project_dir)
        self.review_service = ReviewInspectorService(project_dir)
        self.risk_service = RiskScoringService()
        self.cover_letter_service = CoverLetterService()
        self.config = self.submission_service.load_config()

    def journal_setup(
        self,
        field: str,
        journals: list[str],
        page_limit: int = 16,
        timeline: str = "normal",
        acceptance_target: float = 0.75,
    ) -> dict[str, Any]:
        """Initialize journal submission project (Step 1)."""
        result = self.submission_service.initialize_submission_project(
            field=field,
            journals=journals,
            page_limit=page_limit,
            timeline=timeline,
            acceptance_target=acceptance_target,
        )
        return {
            "status": "success",
            "message": "Journal setup complete",
            "config": result,
        }

    def coach_chapter(self, chapter: str, content: str | None = None) -> dict[str, Any]:
        """Provide coaching feedback on a chapter (Step 2 - ongoing)."""
        feedback = self.coach_service.coach_chapter(chapter, content)
        return {
            "status": "success",
            "chapter": chapter,
            "feedback": feedback,
        }

    def full_review(self, paper_content: str | None = None) -> dict[str, Any]:
        """Perform comprehensive pre-submission review (Step 3)."""
        report = self.review_service.review_full(paper_content)
        summary = self.review_service.get_defect_summary()

        return {
            "status": "success",
            "report": report.to_dict(),
            "recommendation": report.recommendation,
            "summary": summary,
        }

    def assess_risk(
        self,
        desk_reject_score: float = 75.0,
        reviewer_expectations_score: float = 75.0,
        writing_quality_score: float = 75.0,
        ethics_compliance_score: float = 90.0,
    ) -> dict[str, Any]:
        """Assess submission risk and predict acceptance probability (Step 4)."""
        assessment = self.risk_service.calculate_four_dimensional_score(
            desk_reject_score=desk_reject_score,
            reviewer_expectations_score=reviewer_expectations_score,
            writing_quality_score=writing_quality_score,
            ethics_compliance_score=ethics_compliance_score,
        )

        summary = self.risk_service.get_assessment_summary(assessment)

        return {
            "status": "success",
            "assessment": summary,
            "final_score": assessment.final_score,
            "acceptance_probability": f"{assessment.acceptance_probability * 100:.0f}%",
            "recommendation": assessment.recommendation,
        }

    def generate_cover_letter(
        self,
        journal_name: str,
        paper_highlights: list[str] | None = None,
        paper_title: str = "",
        authors: list[str] | None = None,
    ) -> dict[str, Any]:
        """Generate journal-specific cover letter (Step 5)."""
        return self.cover_letter_service.generate_cover_letter(
            journal_name=journal_name,
            paper_title=paper_title,
            paper_highlights=paper_highlights,
            authors=authors,
        )

    def journal_workflow_auto(
        self,
        field: str,
        journals: list[str],
        paper_content: str | None = None,
        auto_scores: bool = True,
    ) -> dict[str, Any]:
        """Complete one-click workflow (Step 6 - automated)."""

        step1_result = self.journal_setup(field, journals)

        step2_feedback = None
        if paper_content:
            for chapter in [
                "abstract",
                "introduction",
                "methods",
                "results",
                "discussion",
                "conclusion",
            ]:
                step2_feedback = self.coach_chapter(chapter)

        step3_review = self.full_review(paper_content)

        step4_risk = self.assess_risk()

        step5_letter = self.generate_cover_letter(journals[0])

        workflow_summary = {
            "status": "complete",
            "steps": {
                "1_setup": step1_result,
                "2_coaching": step2_feedback or "Skipped (no paper content)",
                "3_full_review": step3_review,
                "4_risk_assessment": step4_risk,
                "5_cover_letter": step5_letter,
            },
            "recommendation": step4_risk.get("recommendation", ""),
            "next_actions": [
                "Fix any CRITICAL defects reported in step 3",
                "Consider the risk assessment in step 4",
                "Customize the cover letter from step 5",
                "Submit to journal",
            ],
        }

        return workflow_summary

    def get_workflow_status(self) -> dict[str, Any]:
        """Get current workflow status."""
        config = self.submission_service.load_config()

        if not config:
            return {"status": "not_initialized", "message": "No submission project found"}

        return {
            "status": "initialized",
            "field": config.field,
            "journals": config.target_journals,
            "timeline": config.timeline,
            "next_step": "Run 'crane coach --chapter [chapter]' to start diagnosis",
        }
