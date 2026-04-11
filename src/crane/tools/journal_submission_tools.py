"""Journal submission workflow MCP tools - Orchestrate paper review, coaching, and risk assessment."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from crane.services.questionnaire_engine import QuestionnaireEngine
from crane.services.submission_workflow_service import SubmissionWorkflowService
from crane.workspace import resolve_workspace


def register_tools(mcp):
    """Register journal submission workflow tools with the MCP server."""

    def _resolve_paper_path(paper_path: str, project_dir: str | None) -> str:
        """Resolve paper path to absolute path."""
        path = Path(paper_path)
        if path.is_absolute():
            return str(path)

        workspace = resolve_workspace(project_dir)
        return str(Path(workspace.project_root) / path)

    @mcp.tool()
    def crane_journal_setup(
        field: str,
        journals: list[str],
        page_limit: int = 16,
        timeline: str = "normal",
        acceptance_target: float = 0.75,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """
        Initialize journal submission project.

        Sets up journal targets, page limits, timeline, and acceptance goals.
        This is Step 1 of the 6-step journal submission workflow.

        Args:
            field: Research field (e.g., "Machine Learning", "Computer Vision")
            journals: List of target journal names (e.g., ["IEEE TPAMI", "IJCV"])
            page_limit: Maximum page limit (default 16)
            timeline: Submission timeline ("aggressive", "normal", "relaxed")
            acceptance_target: Target acceptance probability (0.0-1.0)
            project_dir: Project root directory (optional, auto-detected)

        Returns:
            Dict with setup status, configuration, and next steps.
        """
        workflow = SubmissionWorkflowService(project_dir=project_dir)
        return workflow.journal_setup(
            field=field,
            journals=journals,
            page_limit=page_limit,
            timeline=timeline,
            acceptance_target=acceptance_target,
        )

    @mcp.tool()
    def crane_coach_chapter(
        chapter: str,
        content: str | None = None,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """
        Provide coaching feedback on a paper chapter.

        The Coach role provides interactive guidance on each chapter
        (Abstract, Introduction, Methods, Results, Discussion, Conclusion).
        This is Step 2 of the 6-step journal submission workflow.

        Args:
            chapter: Chapter name ("abstract", "introduction", "methods", "results", "discussion", "conclusion")
            content: Chapter content (optional - if not provided, reads from file)
            project_dir: Project root directory (optional, auto-detected)

        Returns:
            Dict with coaching feedback, suggestions, and expected standard.
        """
        workflow = SubmissionWorkflowService(project_dir=project_dir)
        return workflow.coach_chapter(chapter=chapter, content=content)

    @mcp.tool()
    def crane_review_full(
        paper_content: str | None = None,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """
        Perform comprehensive pre-submission review.

        The Inspector role analyzes the entire paper for defects:
        - CRITICAL: Must be fixed (structure, ethics, reproducibility, data availability)
        - MAJOR: Should be fixed (ablation, limitations, SOTA comparison)
        - MINOR: Nice to fix (formatting, grammar, figure clarity)

        This is Step 3 of the 6-step journal submission workflow.

        Args:
            paper_content: Full paper content in LaTeX format (optional)
            project_dir: Project root directory (optional, auto-detected)

        Returns:
            Dict with defect report, recommendations, and estimated fix times.
        """
        workflow = SubmissionWorkflowService(project_dir=project_dir)
        return workflow.full_review(paper_content=paper_content)

    @mcp.tool()
    def crane_assess_risk(
        desk_reject_score: float = 75.0,
        reviewer_expectations_score: float = 75.0,
        writing_quality_score: float = 75.0,
        ethics_compliance_score: float = 90.0,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """
        Assess submission risk and predict acceptance probability.

        The Risk Assessor evaluates 4 dimensions:
        1. Desk Reject Risk (25% weight): Scope match, novelty clarity
        2. Reviewer Expectations (25% weight): Methodology, completeness of experiments
        3. Writing Quality (20% weight): Clarity, organization, presentation
        4. Ethics Compliance (30% weight): Statements, approvals, reproducibility

        Final score = weighted average of 4 dimensions
        Acceptance probability derived from final score

        This is Step 4 of the 6-step journal submission workflow.

        Args:
            desk_reject_score: Desk reject risk score (0-100)
            reviewer_expectations_score: Reviewer expectations score (0-100)
            writing_quality_score: Writing quality score (0-100)
            ethics_compliance_score: Ethics compliance score (0-100)
            project_dir: Project root directory (optional, auto-detected)

        Returns:
            Dict with risk assessment, acceptance probability, and recommendation.
        """
        workflow = SubmissionWorkflowService(project_dir=project_dir)
        return workflow.assess_risk(
            desk_reject_score=desk_reject_score,
            reviewer_expectations_score=reviewer_expectations_score,
            writing_quality_score=writing_quality_score,
            ethics_compliance_score=ethics_compliance_score,
        )

    @mcp.tool()
    def crane_generate_cover_letter(
        journal_name: str,
        paper_highlights: list[str] | None = None,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate personalized cover letter for submission.

        Creates a template cover letter with key contributions highlighted.
        Users should customize with journal-specific details.

        This is Step 5 of the 6-step journal submission workflow.

        Args:
            journal_name: Target journal name (e.g., "IEEE TPAMI")
            paper_highlights: List of key contributions (optional)
            project_dir: Project root directory (optional, auto-detected)

        Returns:
            Dict with cover letter template and customization guidance.
        """
        workflow = SubmissionWorkflowService(project_dir=project_dir)
        return workflow.generate_cover_letter(
            journal_name=journal_name,
            paper_highlights=paper_highlights,
        )

    @mcp.tool()
    def crane_journal_workflow_auto(
        field: str,
        journals: list[str],
        paper_content: str | None = None,
        auto_scores: bool = True,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute complete one-click journal submission workflow.

        Orchestrates all 6 steps automatically:
        1. Setup (journal targets, timeline, acceptance goal)
        2. Coaching (feedback on each chapter)
        3. Full Review (defect detection)
        4. Risk Assessment (4-dimensional scoring)
        5. Cover Letter (personalized template)
        6. Workflow Summary (action items and recommendations)

        This is Step 6 of the 6-step journal submission workflow.

        Args:
            field: Research field (e.g., "Machine Learning")
            journals: List of target journals
            paper_content: Full paper content (optional)
            auto_scores: Whether to use default risk scores (default True)
            project_dir: Project root directory (optional, auto-detected)

        Returns:
            Dict with complete workflow results, next actions, and recommendations.
        """
        workflow = SubmissionWorkflowService(project_dir=project_dir)
        return workflow.journal_workflow_auto(
            field=field,
            journals=journals,
            paper_content=paper_content,
            auto_scores=auto_scores,
        )

    @mcp.tool()
    def crane_get_journal_workflow_status(
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """
        Get current journal submission workflow status.

        Shows project initialization status, target journals, timeline,
        and next recommended step.

        Args:
            project_dir: Project root directory (optional, auto-detected)

        Returns:
            Dict with workflow status and next steps.
        """
        workflow = SubmissionWorkflowService(project_dir=project_dir)
        return workflow.get_workflow_status()

    @mcp.tool()
    def crane_journal_questionnaire(
        field: str = "",
        previous_responses: dict[str, Any] | None = None,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """
        Run interactive questionnaire for journal selection.

        10 core questions guide the user through journal selection:
        - Research field and subfield
        - Contribution type (novel method, system, empirical study, etc.)
        - Experimental scope (small-scale, medium, large-scale)
        - Novelty level (incremental, moderate, high breakthrough)
        - Publication urgency (immediately, within 6 months, flexible)

        Based on responses, suggests target journals and acceptance targets.

        Args:
            field: Research field (optional - if not provided, will ask)
            previous_responses: Prior answers for context (optional)
            project_dir: Project root directory (optional, auto-detected)

        Returns:
            Dict with next question, current responses, and recommended journals.
        """
        engine = QuestionnaireEngine()
        result = engine.get_next_question(
            field=field,
            previous_responses=previous_responses or {},
        )
        return {
            "status": "success" if result else "complete",
            "question": result.get("question") if result else None,
            "question_id": result.get("id") if result else None,
            "options": result.get("options") if result else None,
            "recommendations": engine.recommend_journals(
                field=field,
                previous_responses=previous_responses or {},
            ),
        }
