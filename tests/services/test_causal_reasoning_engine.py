"""Tests for CausalReasoningEngine."""

from __future__ import annotations

import pytest

from crane.services.causal_reasoning_engine import (
    CausalReasoningEngine,
    CausalReasoningResult,
    WorldModelReasoningModule,
    ResearchPositioningAnalyzer,
    StrategyDecisionModule,
    FirstPrinciplesDeconstructModule,
    ExperimentalDesignCausalityModule,
    JournalDecisionPredictorModule,
    PaperRevisionPrioritizationModule,
    IterativeOptimizationCoordinatorModule,
)


class TestCausalReasoningResult:
    """Test CausalReasoningResult dataclass."""

    def test_initialization(self) -> None:
        """Test result initialization."""
        result = CausalReasoningResult(
            module_name="TestModule",
            reasoning_type="test_reasoning",
            conclusion="Test conclusion",
            confidence=0.85,
            supporting_evidence=["Evidence 1", "Evidence 2"],
            next_actions=["Action 1", "Action 2"],
        )

        assert result.module_name == "TestModule"
        assert result.confidence == 0.85
        assert len(result.supporting_evidence) == 2
        assert len(result.next_actions) == 2


class TestWorldModelReasoningModule:
    """Test WorldModelReasoningModule."""

    def test_initialization(self) -> None:
        """Test module initialization."""
        from crane.services.submission_simulation_service import SubmissionSimulationService

        service = SubmissionSimulationService()
        module = WorldModelReasoningModule(service)
        assert module.simulation_service is not None

    def test_reason_about_submission(self) -> None:
        """Test submission reasoning."""
        from crane.services.submission_simulation_service import SubmissionSimulationService

        service = SubmissionSimulationService()
        module = WorldModelReasoningModule(service)

        result = module.reason_about_submission(
            paper_path="test.tex",
            target_journal="IEEE TPAMI",
        )

        assert isinstance(result, CausalReasoningResult)
        assert result.module_name == "WorldModelReasoning"
        assert 0.0 <= result.confidence <= 1.0


class TestResearchPositioningAnalyzer:
    """Test ResearchPositioningAnalyzer."""

    def test_initialization(self) -> None:
        """Test analyzer initialization."""
        from crane.services.research_positioning_service import ResearchPositioningService

        service = ResearchPositioningService()
        analyzer = ResearchPositioningAnalyzer(service)
        assert analyzer.positioning_service is not None

    def test_analyze_positioning(self) -> None:
        """Test positioning analysis."""
        from crane.services.research_positioning_service import ResearchPositioningService

        service = ResearchPositioningService()
        analyzer = ResearchPositioningAnalyzer(service)

        result = analyzer.analyze_positioning(paper_path="test.tex", domain="AI/ML")

        assert isinstance(result, CausalReasoningResult)
        assert result.module_name == "ResearchPositioningAnalyzer"
        assert len(result.supporting_evidence) > 0


class TestStrategyDecisionModule:
    """Test StrategyDecisionModule."""

    def test_initialization(self) -> None:
        """Test module initialization."""
        from crane.services.ideation_service import IdeationService

        service = IdeationService()
        module = StrategyDecisionModule(service)
        assert module.ideation_service is not None

    def test_decide_strategy(self) -> None:
        """Test strategy decision."""
        from crane.services.ideation_service import IdeationService

        service = IdeationService()
        module = StrategyDecisionModule(service)

        context = {"paper_type": "empirical", "domain": "AI/ML"}
        result = module.decide_strategy(context)

        assert isinstance(result, CausalReasoningResult)
        assert result.module_name == "StrategyDecisionModule"
        assert result.reasoning_type == "strategic_decision"


class TestFirstPrinciplesDeconstructModule:
    """Test FirstPrinciplesDeconstructModule."""

    def test_initialization(self) -> None:
        """Test module initialization."""
        from crane.services.first_principles_service import FirstPrinciplesService

        service = FirstPrinciplesService()
        module = FirstPrinciplesDeconstructModule(service)
        assert module.first_principles_service is not None

    def test_deconstruct_wisdom(self) -> None:
        """Test wisdom deconstruction."""
        from crane.services.first_principles_service import FirstPrinciplesService

        service = FirstPrinciplesService()
        module = FirstPrinciplesDeconstructModule(service)

        result = module.deconstruct_wisdom(domain="AI/ML")

        assert isinstance(result, CausalReasoningResult)
        assert result.module_name == "FirstPrinciplesDeconstructModule"
        assert result.reasoning_type == "first_principles_analysis"


class TestExperimentalDesignCausalityModule:
    """Test ExperimentalDesignCausalityModule."""

    def test_initialization(self) -> None:
        """Test module initialization."""
        from crane.services.evidence_evaluation_service import EvidenceEvaluationService

        service = EvidenceEvaluationService()
        module = ExperimentalDesignCausalityModule(service)
        assert module.evidence_service is not None

    def test_analyze_experimental_causality(self) -> None:
        """Test experimental causality analysis."""
        from crane.services.evidence_evaluation_service import EvidenceEvaluationService

        service = EvidenceEvaluationService()
        module = ExperimentalDesignCausalityModule(service)

        result = module.analyze_experimental_causality(paper_path="test.tex")

        assert isinstance(result, CausalReasoningResult)
        assert result.module_name == "ExperimentalDesignCausalityModule"
        assert result.reasoning_type == "experimental_causality"


class TestJournalDecisionPredictorModule:
    """Test JournalDecisionPredictorModule."""

    def test_initialization(self) -> None:
        """Test module initialization."""
        from crane.services.review_simulation_service import ReviewSimulationService

        service = ReviewSimulationService()
        module = JournalDecisionPredictorModule(service)
        assert module.review_service is not None

    def test_predict_journal_decision(self) -> None:
        """Test journal decision prediction."""
        from crane.services.review_simulation_service import ReviewSimulationService

        service = ReviewSimulationService()
        module = JournalDecisionPredictorModule(service)

        result = module.predict_journal_decision(
            paper_path="test.tex",
            journal_name="IEEE TPAMI",
        )

        assert isinstance(result, CausalReasoningResult)
        assert result.module_name == "JournalDecisionPredictorModule"
        assert result.reasoning_type == "journal_decision_prediction"


class TestPaperRevisionPrioritizationModule:
    """Test PaperRevisionPrioritizationModule."""

    def test_initialization(self) -> None:
        """Test module initialization."""
        from crane.services.revision_planning_service import RevisionPlanningService

        service = RevisionPlanningService()
        module = PaperRevisionPrioritizationModule(service)
        assert module.revision_service is not None

    def test_prioritize_revisions(self) -> None:
        """Test revision prioritization."""
        from crane.services.revision_planning_service import RevisionPlanningService

        service = RevisionPlanningService()
        module = PaperRevisionPrioritizationModule(service)

        result = module.prioritize_revisions(paper_path="test.tex")

        assert isinstance(result, CausalReasoningResult)
        assert result.module_name == "PaperRevisionPrioritizationModule"
        assert result.reasoning_type == "revision_prioritization"


class TestIterativeOptimizationCoordinatorModule:
    """Test IterativeOptimizationCoordinatorModule."""

    def test_initialization(self) -> None:
        """Test module initialization."""
        from crane.services.trust_calibration_service import TrustCalibrationService

        service = TrustCalibrationService()
        module = IterativeOptimizationCoordinatorModule(service)
        assert module.trust_service is not None

    def test_coordinate_optimization(self) -> None:
        """Test optimization coordination."""
        from crane.services.trust_calibration_service import TrustCalibrationService

        service = TrustCalibrationService()
        module = IterativeOptimizationCoordinatorModule(service)

        result = module.coordinate_optimization(
            task_description="Test task",
            ai_output={"result": "test"},
        )

        assert isinstance(result, CausalReasoningResult)
        assert result.module_name == "IterativeOptimizationCoordinatorModule"
        assert result.reasoning_type == "optimization_coordination"


class TestCausalReasoningEngine:
    """Test CausalReasoningEngine."""

    def test_initialization(self) -> None:
        """Test engine initialization."""
        engine = CausalReasoningEngine()
        assert engine.submission_module is not None
        assert engine.positioning_module is not None
        assert engine.strategy_module is not None
        assert engine.first_principles_module is not None
        assert engine.experimental_module is not None
        assert engine.journal_module is not None
        assert engine.revision_module is not None
        assert engine.optimization_module is not None

    def test_reason_about_submission(self) -> None:
        """Test submission reasoning."""
        engine = CausalReasoningEngine()
        result = engine.reason_about_submission(
            paper_path="test.tex",
            target_journal="IEEE TPAMI",
        )

        assert isinstance(result, CausalReasoningResult)
        assert result.module_name == "WorldModelReasoning"

    def test_analyze_research_positioning(self) -> None:
        """Test research positioning analysis."""
        engine = CausalReasoningEngine()
        result = engine.analyze_research_positioning(
            paper_path="test.tex",
            domain="AI/ML",
        )

        assert isinstance(result, CausalReasoningResult)
        assert result.module_name == "ResearchPositioningAnalyzer"

    def test_decide_research_strategy(self) -> None:
        """Test research strategy decision."""
        engine = CausalReasoningEngine()
        context = {"paper_type": "empirical", "domain": "AI/ML"}
        result = engine.decide_research_strategy(context)

        assert isinstance(result, CausalReasoningResult)
        assert result.module_name == "StrategyDecisionModule"

    def test_deconstruct_domain_wisdom(self) -> None:
        """Test domain wisdom deconstruction."""
        engine = CausalReasoningEngine()
        result = engine.deconstruct_domain_wisdom(domain="AI/ML")

        assert isinstance(result, CausalReasoningResult)
        assert result.module_name == "FirstPrinciplesDeconstructModule"

    def test_analyze_experimental_design(self) -> None:
        """Test experimental design analysis."""
        engine = CausalReasoningEngine()
        result = engine.analyze_experimental_design(paper_path="test.tex")

        assert isinstance(result, CausalReasoningResult)
        assert result.module_name == "ExperimentalDesignCausalityModule"

    def test_predict_journal_decision(self) -> None:
        """Test journal decision prediction."""
        engine = CausalReasoningEngine()
        result = engine.predict_journal_decision(
            paper_path="test.tex",
            journal_name="IEEE TPAMI",
        )

        assert isinstance(result, CausalReasoningResult)
        assert result.module_name == "JournalDecisionPredictorModule"

    def test_prioritize_revisions(self) -> None:
        """Test revision prioritization."""
        engine = CausalReasoningEngine()
        result = engine.prioritize_revisions(paper_path="test.tex")

        assert isinstance(result, CausalReasoningResult)
        assert result.module_name == "PaperRevisionPrioritizationModule"

    def test_coordinate_optimization(self) -> None:
        """Test optimization coordination."""
        engine = CausalReasoningEngine()
        result = engine.coordinate_optimization(
            task_description="Test task",
            ai_output={"result": "test"},
        )

        assert isinstance(result, CausalReasoningResult)
        assert result.module_name == "IterativeOptimizationCoordinatorModule"

    def test_run_full_analysis(self) -> None:
        """Test full analysis."""
        engine = CausalReasoningEngine()
        results = engine.run_full_analysis(
            paper_path="test.tex",
            target_journal="IEEE TPAMI",
            domain="AI/ML",
        )

        assert "submission_outcome" in results
        assert "research_positioning" in results
        assert "experimental_design" in results
        assert "journal_decision" in results
        assert "revision_priorities" in results
        assert all(isinstance(r, CausalReasoningResult) for r in results.values())
