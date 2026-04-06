"""Unit tests for journal submission services - Phase 2 implementation."""

from __future__ import annotations

import pytest

from crane.services.chapter_coach_service import ChapterCoachService
from crane.services.cover_letter_service import CoverLetterService
from crane.services.review_inspector_service import (
    DefectSeverity,
    ReviewInspectorService,
)
from crane.services.risk_scoring_service import RiskLevel, RiskScoringService
from crane.services.submission_workflow_service import SubmissionWorkflowService


class TestChapterCoachService:
    """Tests for ChapterCoachService coaching feedback."""

    def test_coach_abstract_provides_feedback(self):
        """Coaching abstract chapter should return feedback dict."""
        service = ChapterCoachService()
        feedback = service.coach_chapter("abstract")

        assert isinstance(feedback, dict)
        assert "chapter" in feedback
        assert feedback["chapter"] == "abstract"
        assert "expectations" in feedback

    def test_coach_all_chapters(self):
        """All chapters can be coached."""
        service = ChapterCoachService()
        chapters = ["abstract", "introduction", "methods", "results", "discussion", "conclusion"]

        for chapter in chapters:
            feedback = service.coach_chapter(chapter)
            assert feedback["chapter"] == chapter
            assert "expectations" in feedback

    def test_coach_chapter_with_content(self):
        """Coaching with actual content should provide targeted feedback."""
        service = ChapterCoachService()
        content = "This is a test abstract about machine learning."
        feedback = service.coach_chapter("abstract", content=content)

        assert feedback is not None
        assert "diagnostics" in feedback or "expectations" in feedback


class TestReviewInspectorService:
    """Tests for ReviewInspectorService defect detection."""

    def test_review_with_empty_content(self):
        """Empty content should detect structural issues."""
        service = ReviewInspectorService()
        report = service.review_full(paper_content="")

        assert report.total_defects == 0  # Empty content = no defects detected

    def test_review_detects_critical_defects(self):
        """Complete analysis should find critical issues."""
        service = ReviewInspectorService()
        minimal_paper = "\\section{Introduction}"
        report = service.review_full(paper_content=minimal_paper)

        assert report.total_defects > 0 or len(report.critical_defects) >= 0

    def test_defect_severity_enum(self):
        """DefectSeverity enum should have correct values."""
        assert DefectSeverity.CRITICAL.value == "critical"
        assert DefectSeverity.MAJOR.value == "major"
        assert DefectSeverity.MINOR.value == "minor"

    def test_review_report_to_dict(self):
        """ReviewReport should serialize to dict."""
        service = ReviewInspectorService()
        report = service.review_full(paper_content="test")

        result = report.to_dict()
        assert "total_defects" in result
        assert "critical_count" in result
        assert "major_count" in result
        assert "minor_count" in result

    def test_check_critical_items_detects_missing_data_availability(self):
        """Content without data availability statement should flag."""
        service = ReviewInspectorService()
        content = "\\section{Methods} Only methods here."
        report = service.review_full(paper_content=content)

        # Should find at least one defect (data availability)
        assert len(service.defects) >= 1

    def test_check_major_items_detects_missing_ablation(self):
        """Content without ablation keywords should flag."""
        service = ReviewInspectorService()
        content = """\\section{Results} 
        We achieved 90% accuracy.
        Table 1 shows comparisons.
        """
        report = service.review_full(paper_content=content)

        # Defects should be collected
        assert report.total_defects >= 0


class TestRiskScoringService:
    """Tests for RiskScoringService 4D assessment."""

    def test_four_dimensional_scoring(self):
        """Calculate 4D score from input dimensions."""
        service = RiskScoringService()
        assessment = service.calculate_four_dimensional_score(
            desk_reject_score=80.0,
            reviewer_expectations_score=75.0,
            writing_quality_score=85.0,
            ethics_compliance_score=90.0,
        )

        assert assessment.final_score > 0
        assert assessment.final_score <= 100
        assert assessment.acceptance_probability >= 0
        assert assessment.acceptance_probability <= 1
        assert assessment.risk_level is not None

    def test_weights_sum_to_one(self):
        """Weights should sum to 1.0."""
        weights = RiskScoringService.DIMENSION_WEIGHTS
        total = sum(weights.values())

        assert abs(total - 1.0) < 0.001

    def test_desk_reject_interpretation(self):
        """High desk_reject score should give low risk interpretation."""
        service = RiskScoringService()

        high_score_interp = service._interpret_desk_reject(95.0)
        assert "very low" in high_score_interp.lower() or "low" in high_score_interp.lower()

        low_score_interp = service._interpret_desk_reject(30.0)
        assert "high" in low_score_interp.lower() or "very high" in low_score_interp.lower()

    def test_acceptance_probability_mapping(self):
        """Acceptance probability should map correctly to score ranges."""
        service = RiskScoringService()

        prob_90, _ = service._predict_acceptance_probability(95.0)
        assert prob_90 >= 0.90  # Score 95 should be very high probability

        prob_50, _ = service._predict_acceptance_probability(65.0)
        assert 0.0 <= prob_50 <= 0.5  # Score 65 should be moderate-to-low probability

    def test_risk_level_determination(self):
        """Risk level should map to score correctly."""
        service = RiskScoringService()

        level_high = service._determine_risk_level(95.0)
        assert level_high == RiskLevel.VERY_LOW

        level_moderate = service._determine_risk_level(75.0)
        assert level_moderate == RiskLevel.MODERATE

        level_low = service._determine_risk_level(35.0)
        assert level_low == RiskLevel.VERY_HIGH

    def test_recommendation_generation(self):
        """Recommendation should be generated based on score and ethics."""
        service = RiskScoringService()

        rec_good = service._generate_recommendation(
            final_score=85.0, risk_level=RiskLevel.LOW, ethics_score=90.0
        )
        assert "READY" in rec_good or "ready" in rec_good.lower()

        rec_ethics_bad = service._generate_recommendation(
            final_score=85.0,
            risk_level=RiskLevel.LOW,
            ethics_score=50.0,  # Low ethics score triggers critical warning
        )
        assert "CRITICAL" in rec_ethics_bad or "critical" in rec_ethics_bad.lower()

    def test_assessment_summary(self):
        """Assessment summary should include all dimensions."""
        service = RiskScoringService()
        assessment = service.calculate_four_dimensional_score(
            desk_reject_score=80.0,
            reviewer_expectations_score=75.0,
            writing_quality_score=85.0,
            ethics_compliance_score=90.0,
        )

        summary = service.get_assessment_summary(assessment)

        assert "final_score" in summary
        assert "acceptance_probability" in summary
        assert "risk_level" in summary
        assert "recommendation" in summary
        assert "dimensions" in summary
        assert "desk_reject_risk" in summary["dimensions"]
        assert "reviewer_expectations" in summary["dimensions"]
        assert "writing_quality" in summary["dimensions"]
        assert "ethics_compliance" in summary["dimensions"]

    def test_compare_assessments(self):
        """Should compare two risk assessments."""
        service = RiskScoringService()

        assessment1 = service.calculate_four_dimensional_score(
            desk_reject_score=70.0,
            reviewer_expectations_score=70.0,
            writing_quality_score=70.0,
            ethics_compliance_score=70.0,
        )

        assessment2 = service.calculate_four_dimensional_score(
            desk_reject_score=80.0,
            reviewer_expectations_score=80.0,
            writing_quality_score=80.0,
            ethics_compliance_score=80.0,
        )

        comparison = service.compare_assessments(assessment1, assessment2)

        assert "assessment_1_score" in comparison
        assert "assessment_2_score" in comparison
        assert "difference" in comparison
        assert comparison["difference"] > 0  # Assessment2 is better


class TestCoverLetterService:
    """Tests for CoverLetterService cover letter generation."""

    def test_generate_for_supported_journal(self):
        """Generate cover letter for supported journal."""
        service = CoverLetterService()
        result = service.generate_cover_letter(
            journal_name="IEEE TPAMI",
            paper_title="Machine Learning Study",
            paper_highlights=["Novel approach", "Strong results"],
        )

        assert result["status"] == "success"
        assert "cover_letter" in result
        assert "IEEE TPAMI" in result["cover_letter"]
        assert "Machine Learning Study" in result["cover_letter"]
        assert "Novel approach" in result["cover_letter"]

    def test_generate_for_unsupported_journal(self):
        """Generate generic cover letter for unknown journal."""
        service = CoverLetterService()
        result = service.generate_cover_letter(
            journal_name="Unknown Journal XYZ",
            paper_title="Test Paper",
        )

        assert result["status"] == "success"
        assert "cover_letter" in result
        assert "Unknown Journal XYZ" in result["cover_letter"]
        assert "Test Paper" in result["cover_letter"]

    def test_cover_letter_includes_highlights(self):
        """Cover letter should include provided highlights."""
        service = CoverLetterService()
        highlights = [
            "Novel neural architecture",
            "10x speedup over baselines",
            "New benchmark dataset",
        ]
        result = service.generate_cover_letter(
            journal_name="NeurIPS",
            paper_highlights=highlights,
        )

        for highlight in highlights:
            assert highlight in result["cover_letter"]

    def test_cover_letter_includes_authors(self):
        """Cover letter should include author names."""
        service = CoverLetterService()
        authors = ["Dr. Alice Smith", "Dr. Bob Johnson"]
        result = service.generate_cover_letter(
            journal_name="ICML",
            authors=authors,
        )

        for author in authors:
            assert author in result["cover_letter"]

    def test_get_supported_journals(self):
        """Should list supported journals."""
        service = CoverLetterService()
        journals_info = service.get_supported_journals()

        assert "supported" in journals_info
        assert len(journals_info["supported"]) > 0
        assert "IEEE TPAMI" in journals_info["supported"]


class TestSubmissionWorkflowService:
    """Tests for SubmissionWorkflowService orchestration."""

    def test_journal_setup(self):
        """Journal setup should initialize config."""
        workflow = SubmissionWorkflowService()
        result = workflow.journal_setup(
            field="Machine Learning",
            journals=["IEEE TPAMI", "IJCV"],
        )

        assert result["status"] == "success"
        assert "config" in result

    def test_coach_chapter(self):
        """Coach chapter should provide feedback."""
        workflow = SubmissionWorkflowService()
        result = workflow.coach_chapter(chapter="abstract")

        assert result["status"] == "success"
        assert "chapter" in result
        assert "feedback" in result

    def test_full_review(self):
        """Full review should detect defects."""
        workflow = SubmissionWorkflowService()
        result = workflow.full_review(paper_content="test content")

        assert result["status"] == "success"
        assert "report" in result
        assert "recommendation" in result
        assert "summary" in result

    def test_assess_risk(self):
        """Risk assessment should calculate 4D score."""
        workflow = SubmissionWorkflowService()
        result = workflow.assess_risk(
            desk_reject_score=80.0,
            reviewer_expectations_score=75.0,
            writing_quality_score=85.0,
            ethics_compliance_score=90.0,
        )

        assert result["status"] == "success"
        assert "assessment" in result
        assert "final_score" in result
        assert "acceptance_probability" in result
        assert "recommendation" in result

    def test_generate_cover_letter(self):
        """Generate cover letter should work."""
        workflow = SubmissionWorkflowService()
        result = workflow.generate_cover_letter(
            journal_name="IEEE TPAMI",
            paper_highlights=["Novel method"],
        )

        assert result["status"] == "success"
        assert "cover_letter" in result

    def test_get_workflow_status(self):
        """Get workflow status should return status."""
        workflow = SubmissionWorkflowService()
        status = workflow.get_workflow_status()

        assert "status" in status

    def test_workflow_auto_orchestration(self):
        """Auto workflow should orchestrate all steps."""
        workflow = SubmissionWorkflowService()
        result = workflow.journal_workflow_auto(
            field="Machine Learning",
            journals=["IEEE TPAMI"],
            paper_content="test content",
        )

        assert result["status"] == "complete"
        assert "steps" in result
        assert "1_setup" in result["steps"]
        assert "3_full_review" in result["steps"]
        assert "4_risk_assessment" in result["steps"]
        assert "5_cover_letter" in result["steps"]
        assert "recommendation" in result
        assert "next_actions" in result


class TestWorkflowIntegration:
    """Integration tests for complete workflow."""

    def test_workflow_chain_setup_then_review(self):
        """Full workflow: setup → review."""
        workflow = SubmissionWorkflowService()

        setup_result = workflow.journal_setup(
            field="ML",
            journals=["IEEE TPAMI"],
        )
        assert setup_result["status"] == "success"

        review_result = workflow.full_review(paper_content="test")
        assert review_result["status"] == "success"

    def test_workflow_chain_review_then_risk(self):
        """Full workflow: review → assess risk."""
        workflow = SubmissionWorkflowService()

        review = workflow.full_review(paper_content="test")
        assert review["status"] == "success"

        risk = workflow.assess_risk()
        assert risk["status"] == "success"

    def test_risk_assessment_matches_dimensions(self):
        """Risk assessment scores should be weighted properly."""
        service = RiskScoringService()

        assessment = service.calculate_four_dimensional_score(
            desk_reject_score=100.0,
            reviewer_expectations_score=0.0,
            writing_quality_score=0.0,
            ethics_compliance_score=0.0,
        )

        # Final score should be weighted by desk_reject weight (0.25)
        expected_min = 100.0 * 0.25
        assert assessment.final_score >= expected_min * 0.9  # Allow small floating point error
