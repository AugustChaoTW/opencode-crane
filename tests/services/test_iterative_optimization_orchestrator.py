"""Tests for IterativePaperOptimizationOrchestrator."""

from __future__ import annotations

from datetime import datetime

import pytest

from crane.services.iterative_optimization_orchestrator import (
    IterativePaperOptimizationOrchestrator,
    OptimizationRound,
    OptimizationSession,
    EvaluationModule,
    PlanningModule,
    RewriteModule,
    LearningModule,
)


@pytest.fixture
def orchestrator() -> IterativePaperOptimizationOrchestrator:
    """Create an orchestrator instance."""
    return IterativePaperOptimizationOrchestrator()


class TestOptimizationRound:
    """Test OptimizationRound dataclass."""

    def test_initialization(self) -> None:
        """Test round initialization."""
        round_result = OptimizationRound(
            round_number=1,
            timestamp=datetime.now(),
            initial_score=75.0,
            final_score=80.0,
            score_gain=5.0,
            gain_percentage=6.67,
            revisions_applied=["revision1", "revision2"],
        )

        assert round_result.round_number == 1
        assert round_result.score_gain == 5.0
        assert len(round_result.revisions_applied) == 2


class TestOptimizationSession:
    """Test OptimizationSession dataclass."""

    def test_initialization(self) -> None:
        """Test session initialization."""
        session = OptimizationSession(
            session_id="test_session",
            paper_path="test.tex",
            target_journal="IEEE TPAMI",
            created_at=datetime.now(),
        )

        assert session.session_id == "test_session"
        assert session.is_active is True
        assert len(session.rounds) == 0

    def test_add_round(self) -> None:
        """Test adding rounds to session."""
        session = OptimizationSession(
            session_id="test_session",
            paper_path="test.tex",
            target_journal="IEEE TPAMI",
            created_at=datetime.now(),
        )

        round_result = OptimizationRound(
            round_number=1,
            timestamp=datetime.now(),
            initial_score=75.0,
            final_score=80.0,
            score_gain=5.0,
            gain_percentage=6.67,
            revisions_applied=["revision1"],
        )

        session.add_round(round_result)
        assert len(session.rounds) == 1
        assert session.final_score == 80.0
        assert session.total_gain == 5.0

    def test_get_convergence_status_no_rounds(self) -> None:
        """Test convergence status with no rounds."""
        session = OptimizationSession(
            session_id="test_session",
            paper_path="test.tex",
            target_journal="IEEE TPAMI",
            created_at=datetime.now(),
        )

        status = session.get_convergence_status()
        assert status["converged"] is False

    def test_get_convergence_status_converged(self) -> None:
        """Test convergence status when converged."""
        session = OptimizationSession(
            session_id="test_session",
            paper_path="test.tex",
            target_journal="IEEE TPAMI",
            created_at=datetime.now(),
            convergence_threshold=1.0,
        )

        round_result = OptimizationRound(
            round_number=1,
            timestamp=datetime.now(),
            initial_score=75.0,
            final_score=75.5,
            score_gain=0.5,
            gain_percentage=0.67,
            revisions_applied=["revision1"],
            convergence_detected=True,
        )

        session.add_round(round_result)
        status = session.get_convergence_status()
        assert status["converged"] is True

    def test_get_trend(self) -> None:
        """Test getting score trend."""
        session = OptimizationSession(
            session_id="test_session",
            paper_path="test.tex",
            target_journal="IEEE TPAMI",
            created_at=datetime.now(),
        )

        for i in range(3):
            round_result = OptimizationRound(
                round_number=i + 1,
                timestamp=datetime.now(),
                initial_score=75.0 + i * 2,
                final_score=80.0 + i * 2,
                score_gain=5.0,
                gain_percentage=6.67,
                revisions_applied=["revision1"],
            )
            session.add_round(round_result)

        trend = session.get_trend()
        assert len(trend) == 3
        assert trend[0] == 80.0
        assert trend[1] == 82.0
        assert trend[2] == 84.0


class TestEvaluationModule:
    """Test EvaluationModule."""

    def test_initialization(self) -> None:
        """Test module initialization."""
        from crane.services.paper_profile_service import PaperProfileService

        service = PaperProfileService()
        module = EvaluationModule(service)
        assert module.profile_service is not None

    def test_evaluate(self) -> None:
        """Test paper evaluation."""
        from crane.services.paper_profile_service import PaperProfileService

        service = PaperProfileService()
        module = EvaluationModule(service)

        result = module.evaluate("test.tex")
        assert "score" in result
        assert "profile" in result
        assert "timestamp" in result
        assert 0.0 <= result["score"] <= 100.0


class TestPlanningModule:
    """Test PlanningModule."""

    def test_initialization(self) -> None:
        """Test module initialization."""
        from crane.services.revision_planning_service import RevisionPlanningService

        service = RevisionPlanningService()
        module = PlanningModule(service)
        assert module.revision_service is not None

    def test_plan_revisions(self) -> None:
        """Test revision planning."""
        from crane.services.revision_planning_service import RevisionPlanningService

        service = RevisionPlanningService()
        module = PlanningModule(service)

        result = module.plan_revisions("test.tex", 75.0)
        assert "revision_items" in result
        assert "estimated_improvement" in result
        assert "estimated_effort_hours" in result


class TestRewriteModule:
    """Test RewriteModule."""

    def test_initialization(self) -> None:
        """Test module initialization."""
        from crane.services.interactive_rewrite_service import InteractiveRewriteService

        service = InteractiveRewriteService()
        module = RewriteModule(service)
        assert module.rewrite_service is not None

    def test_execute_rewrites(self) -> None:
        """Test rewrite execution."""
        from crane.services.interactive_rewrite_service import InteractiveRewriteService

        service = InteractiveRewriteService()
        module = RewriteModule(service)

        revision_items = [
            {"title": "revision1", "description": "test"},
            {"title": "revision2", "description": "test"},
        ]

        result = module.execute_rewrites("test.tex", revision_items)
        assert "session_id" in result
        assert "applied_revisions" in result
        assert "revision_count" in result


class TestLearningModule:
    """Test LearningModule."""

    def test_initialization(self) -> None:
        """Test module initialization."""
        module = LearningModule()
        assert len(module.round_history) == 0
        assert len(module.effectiveness_scores) == 0

    def test_record_round(self) -> None:
        """Test recording rounds."""
        module = LearningModule()
        round_result = OptimizationRound(
            round_number=1,
            timestamp=datetime.now(),
            initial_score=75.0,
            final_score=80.0,
            score_gain=5.0,
            gain_percentage=6.67,
            revisions_applied=["revision1"],
        )

        module.record_round(round_result)
        assert len(module.round_history) == 1

    def test_learn_effectiveness(self) -> None:
        """Test learning effectiveness."""
        module = LearningModule()
        module.learn_effectiveness("revision1", 5.0)
        module.learn_effectiveness("revision1", 6.0)

        assert "revision1" in module.effectiveness_scores
        assert module.effectiveness_scores["revision1"] > 0.0

    def test_get_most_effective_revisions(self) -> None:
        """Test getting most effective revisions."""
        module = LearningModule()
        module.learn_effectiveness("revision1", 5.0)
        module.learn_effectiveness("revision2", 3.0)
        module.learn_effectiveness("revision3", 7.0)

        most_effective = module.get_most_effective_revisions(top_k=2)
        assert len(most_effective) <= 2
        assert most_effective[0][0] == "revision3"

    def test_predict_convergence_round(self) -> None:
        """Test convergence prediction."""
        module = LearningModule()
        for i in range(5):
            round_result = OptimizationRound(
                round_number=i + 1,
                timestamp=datetime.now(),
                initial_score=75.0,
                final_score=75.0 + (5 - i) * 0.1,
                score_gain=(5 - i) * 0.1,
                gain_percentage=(5 - i) * 0.1,
                revisions_applied=["revision1"],
            )
            module.record_round(round_result)

        prediction = module.predict_convergence_round()
        assert prediction is None or isinstance(prediction, int)


class TestIterativePaperOptimizationOrchestrator:
    """Test IterativePaperOptimizationOrchestrator."""

    def test_initialization(self, orchestrator: IterativePaperOptimizationOrchestrator) -> None:
        """Test orchestrator initialization."""
        assert orchestrator.evaluation_module is not None
        assert orchestrator.planning_module is not None
        assert orchestrator.rewrite_module is not None
        assert orchestrator.learning_module is not None
        assert len(orchestrator.sessions) == 0

    def test_start_optimization(self, orchestrator: IterativePaperOptimizationOrchestrator) -> None:
        """Test starting optimization."""
        session_id = orchestrator.start_optimization(
            paper_path="test.tex",
            target_journal="IEEE TPAMI",
        )

        assert session_id in orchestrator.sessions
        session = orchestrator.sessions[session_id]
        assert session.is_active is True
        assert len(session.rounds) == 0

    def test_run_optimization_round(
        self, orchestrator: IterativePaperOptimizationOrchestrator
    ) -> None:
        """Test running optimization round."""
        session_id = orchestrator.start_optimization(
            paper_path="test.tex",
            target_journal="IEEE TPAMI",
        )

        round_result = orchestrator.run_optimization_round(session_id)
        assert round_result is not None
        assert round_result.round_number == 1
        assert round_result.initial_score > 0
        assert round_result.final_score > 0

    def test_run_full_optimization(
        self, orchestrator: IterativePaperOptimizationOrchestrator
    ) -> None:
        """Test running full optimization."""
        result = orchestrator.run_full_optimization(
            paper_path="test.tex",
            target_journal="IEEE TPAMI",
            max_rounds=3,
        )

        assert "session_id" in result
        assert "rounds_completed" in result
        assert "final_score" in result
        assert "convergence_status" in result
        assert "score_trend" in result

    def test_get_session_status(self, orchestrator: IterativePaperOptimizationOrchestrator) -> None:
        """Test getting session status."""
        session_id = orchestrator.start_optimization(
            paper_path="test.tex",
            target_journal="IEEE TPAMI",
        )

        status = orchestrator.get_session_status(session_id)
        assert status is not None
        assert status["session_id"] == session_id
        assert status["is_active"] is True

    def test_get_round_details(self, orchestrator: IterativePaperOptimizationOrchestrator) -> None:
        """Test getting round details."""
        session_id = orchestrator.start_optimization(
            paper_path="test.tex",
            target_journal="IEEE TPAMI",
        )

        orchestrator.run_optimization_round(session_id)
        details = orchestrator.get_round_details(session_id, 1)

        assert details is not None
        assert details["round_number"] == 1
        assert "initial_score" in details
        assert "final_score" in details

    def test_list_sessions(self, orchestrator: IterativePaperOptimizationOrchestrator) -> None:
        """Test listing sessions."""
        orchestrator.start_optimization(
            paper_path="test1.tex",
            target_journal="IEEE TPAMI",
        )
        orchestrator.start_optimization(
            paper_path="test2.tex",
            target_journal="JMLR",
        )

        sessions = orchestrator.list_sessions()
        assert len(sessions) == 2

    def test_get_learning_insights(
        self, orchestrator: IterativePaperOptimizationOrchestrator
    ) -> None:
        """Test getting learning insights."""
        session_id = orchestrator.start_optimization(
            paper_path="test.tex",
            target_journal="IEEE TPAMI",
        )

        orchestrator.run_optimization_round(session_id)
        insights = orchestrator.get_learning_insights()

        assert "total_rounds" in insights
        assert "most_effective_revisions" in insights
        assert "average_gain_per_round" in insights
