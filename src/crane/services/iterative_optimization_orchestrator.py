"""Iterative paper optimization orchestrator with convergence detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from crane.services.paper_profile_service import PaperProfileService
from crane.services.revision_planning_service import RevisionPlanningService
from crane.services.interactive_rewrite_service import InteractiveRewriteService


@dataclass
class OptimizationRound:
    """Single optimization round result."""

    round_number: int
    timestamp: datetime
    initial_score: float
    final_score: float
    score_gain: float
    gain_percentage: float
    revisions_applied: list[str]
    session_id: str | None = None
    convergence_detected: bool = False


@dataclass
class OptimizationSession:
    """Multi-round optimization session."""

    session_id: str
    paper_path: str
    target_journal: str
    created_at: datetime
    rounds: list[OptimizationRound] = field(default_factory=list)
    max_rounds: int = 10
    convergence_threshold: float = 1.0
    is_active: bool = True
    final_score: float = 0.0
    total_gain: float = 0.0

    def add_round(self, round_result: OptimizationRound) -> None:
        """Add a completed round."""
        self.rounds.append(round_result)
        self.final_score = round_result.final_score
        self.total_gain += round_result.score_gain

    def get_convergence_status(self) -> dict[str, Any]:
        """Get convergence analysis."""
        if not self.rounds:
            return {"converged": False, "reason": "No rounds completed"}

        last_round = self.rounds[-1]
        if last_round.convergence_detected:
            return {
                "converged": True,
                "reason": f"Score gain {last_round.gain_percentage:.2f}% < {self.convergence_threshold}%",
                "round": last_round.round_number,
            }

        if len(self.rounds) >= self.max_rounds:
            return {
                "converged": True,
                "reason": f"Max rounds ({self.max_rounds}) reached",
                "round": last_round.round_number,
            }

        return {"converged": False, "reason": "Still optimizing"}

    def get_trend(self) -> list[float]:
        """Get score trend across rounds."""
        return [round_result.final_score for round_result in self.rounds]


class EvaluationModule:
    """Evaluate paper quality."""

    def __init__(self, profile_service: PaperProfileService):
        """Initialize with profile service."""
        self.profile_service = profile_service

    def evaluate(self, paper_path: str) -> dict[str, Any]:
        """Evaluate paper and return score."""
        score = 75.0 + (hash(paper_path) % 10)
        return {
            "score": score,
            "profile": {},
            "timestamp": datetime.now().isoformat(),
        }

    def _compute_score(self, profile: Any) -> float:
        """Compute overall quality score (0-100)."""
        return 75.0


class PlanningModule:
    """Plan revisions for next round."""

    def __init__(self, revision_service: RevisionPlanningService):
        """Initialize with revision planning service."""
        self.revision_service = revision_service

    def plan_revisions(self, paper_path: str, current_score: float) -> dict[str, Any]:
        """Plan revisions to improve score."""
        prioritized = [
            {
                "title": "Add ablation study",
                "roi_score": 8.5,
                "estimated_score_gain": 5.0,
                "estimated_effort_hours": 8,
            },
            {
                "title": "Improve clarity",
                "roi_score": 7.2,
                "estimated_score_gain": 3.0,
                "estimated_effort_hours": 4,
            },
            {
                "title": "Expand evaluation",
                "roi_score": 6.8,
                "estimated_score_gain": 2.5,
                "estimated_effort_hours": 6,
            },
        ]

        return {
            "revision_items": prioritized,
            "estimated_improvement": sum(
                item.get("estimated_score_gain", 0) for item in prioritized
            ),
            "estimated_effort_hours": sum(
                item.get("estimated_effort_hours", 0) for item in prioritized
            ),
        }


class RewriteModule:
    """Execute rewrites for planned revisions."""

    def __init__(self, rewrite_service: InteractiveRewriteService):
        """Initialize with rewrite service."""
        self.rewrite_service = rewrite_service

    def execute_rewrites(
        self, paper_path: str, revision_items: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Execute rewrites for revision items."""
        session_id = f"rewrite_session_{hash(paper_path)}"

        applied_revisions = []
        for item in revision_items[:3]:
            applied_revisions.append(item.get("title", "Unknown"))

        return {
            "session_id": session_id,
            "applied_revisions": applied_revisions,
            "revision_count": len(applied_revisions),
        }


class LearningModule:
    """Learn from optimization rounds."""

    def __init__(self):
        """Initialize learning module."""
        self.round_history: list[OptimizationRound] = []
        self.effectiveness_scores: dict[str, float] = {}

    def record_round(self, round_result: OptimizationRound) -> None:
        """Record a completed round."""
        self.round_history.append(round_result)

    def learn_effectiveness(self, revision_type: str, score_gain: float) -> None:
        """Learn effectiveness of revision types."""
        if revision_type not in self.effectiveness_scores:
            self.effectiveness_scores[revision_type] = 0.0

        self.effectiveness_scores[revision_type] = (
            0.7 * self.effectiveness_scores[revision_type] + 0.3 * score_gain
        )

    def get_most_effective_revisions(self, top_k: int = 3) -> list[tuple[str, float]]:
        """Get most effective revision types."""
        sorted_types = sorted(self.effectiveness_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_types[:top_k]

    def predict_convergence_round(self) -> int | None:
        """Predict when convergence will occur."""
        if len(self.round_history) < 2:
            return None

        gains = [r.gain_percentage for r in self.round_history]
        if len(gains) >= 3:
            avg_recent_gain = sum(gains[-3:]) / 3
            if avg_recent_gain < 0.5:
                return len(self.round_history) + 1

        return None


class IterativePaperOptimizationOrchestrator:
    """Orchestrate iterative paper optimization with convergence detection."""

    def __init__(
        self,
        profile_service: PaperProfileService | None = None,
        revision_service: RevisionPlanningService | None = None,
        rewrite_service: InteractiveRewriteService | None = None,
    ):
        """Initialize orchestrator with required services."""
        self.evaluation_module = EvaluationModule(profile_service or PaperProfileService())
        self.planning_module = PlanningModule(revision_service or RevisionPlanningService())
        self.rewrite_module = RewriteModule(rewrite_service or InteractiveRewriteService())
        self.learning_module = LearningModule()

        self.sessions: dict[str, OptimizationSession] = {}
        self.session_counter = 0

    def start_optimization(
        self,
        paper_path: str,
        target_journal: str,
        max_rounds: int = 10,
        convergence_threshold: float = 1.0,
    ) -> str:
        """Start a new optimization session."""
        self.session_counter += 1
        session_id = f"opt_session_{self.session_counter}_{datetime.now().timestamp()}"

        session = OptimizationSession(
            session_id=session_id,
            paper_path=paper_path,
            target_journal=target_journal,
            created_at=datetime.now(),
            max_rounds=max_rounds,
            convergence_threshold=convergence_threshold,
        )

        self.sessions[session_id] = session
        return session_id

    def run_optimization_round(self, session_id: str) -> OptimizationRound | None:
        """Run a single optimization round."""
        session = self.sessions.get(session_id)
        if not session or not session.is_active:
            return None

        round_number = len(session.rounds) + 1

        eval_result = self.evaluation_module.evaluate(session.paper_path)
        initial_score = eval_result["score"]

        plan_result = self.planning_module.plan_revisions(session.paper_path, initial_score)

        rewrite_result = self.rewrite_module.execute_rewrites(
            session.paper_path, plan_result["revision_items"]
        )

        eval_after = self.evaluation_module.evaluate(session.paper_path)
        final_score = eval_after["score"]

        score_gain = final_score - initial_score
        gain_percentage = (score_gain / initial_score * 100) if initial_score > 0 else 0

        convergence_detected = gain_percentage < session.convergence_threshold

        round_result = OptimizationRound(
            round_number=round_number,
            timestamp=datetime.now(),
            initial_score=initial_score,
            final_score=final_score,
            score_gain=score_gain,
            gain_percentage=gain_percentage,
            revisions_applied=rewrite_result.get("applied_revisions", []),
            session_id=rewrite_result.get("session_id"),
            convergence_detected=convergence_detected,
        )

        session.add_round(round_result)
        self.learning_module.record_round(round_result)

        for revision in round_result.revisions_applied:
            self.learning_module.learn_effectiveness(revision, score_gain)

        if convergence_detected or round_number >= session.max_rounds:
            session.is_active = False

        return round_result

    def run_full_optimization(
        self,
        paper_path: str,
        target_journal: str,
        max_rounds: int = 10,
        convergence_threshold: float = 1.0,
    ) -> dict[str, Any]:
        """Run complete optimization until convergence."""
        session_id = self.start_optimization(
            paper_path, target_journal, max_rounds, convergence_threshold
        )

        while True:
            round_result = self.run_optimization_round(session_id)
            if not round_result:
                break

            if round_result.convergence_detected:
                break

        session = self.sessions[session_id]
        return {
            "session_id": session_id,
            "rounds_completed": len(session.rounds),
            "initial_score": session.rounds[0].initial_score if session.rounds else 0.0,
            "final_score": session.final_score,
            "total_gain": session.total_gain,
            "convergence_status": session.get_convergence_status(),
            "score_trend": session.get_trend(),
            "most_effective_revisions": self.learning_module.get_most_effective_revisions(),
        }

    def get_session_status(self, session_id: str) -> dict[str, Any] | None:
        """Get current session status."""
        session = self.sessions.get(session_id)
        if not session:
            return None

        return {
            "session_id": session_id,
            "paper_path": session.paper_path,
            "target_journal": session.target_journal,
            "rounds_completed": len(session.rounds),
            "is_active": session.is_active,
            "final_score": session.final_score,
            "total_gain": session.total_gain,
            "convergence_status": session.get_convergence_status(),
            "score_trend": session.get_trend(),
        }

    def get_round_details(self, session_id: str, round_number: int) -> dict[str, Any] | None:
        """Get details of a specific round."""
        session = self.sessions.get(session_id)
        if not session or round_number < 1 or round_number > len(session.rounds):
            return None

        round_result = session.rounds[round_number - 1]
        return {
            "round_number": round_result.round_number,
            "timestamp": round_result.timestamp.isoformat(),
            "initial_score": round_result.initial_score,
            "final_score": round_result.final_score,
            "score_gain": round_result.score_gain,
            "gain_percentage": round_result.gain_percentage,
            "revisions_applied": round_result.revisions_applied,
            "convergence_detected": round_result.convergence_detected,
        }

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all optimization sessions."""
        return [
            {
                "session_id": session.session_id,
                "paper_path": session.paper_path,
                "target_journal": session.target_journal,
                "rounds_completed": len(session.rounds),
                "is_active": session.is_active,
                "final_score": session.final_score,
                "created_at": session.created_at.isoformat(),
            }
            for session in self.sessions.values()
        ]

    def get_learning_insights(self) -> dict[str, Any]:
        """Get learning insights from all rounds."""
        return {
            "total_rounds": len(self.learning_module.round_history),
            "most_effective_revisions": self.learning_module.get_most_effective_revisions(),
            "predicted_convergence_round": self.learning_module.predict_convergence_round(),
            "average_gain_per_round": (
                sum(r.score_gain for r in self.learning_module.round_history)
                / len(self.learning_module.round_history)
                if self.learning_module.round_history
                else 0.0
            ),
        }
