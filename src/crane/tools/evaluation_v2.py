"""Evidence-first evaluation and revision MCP tools (v2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from crane.models.paper_profile import (
    CostAssessment,
    DimensionScore,
    JournalFit,
    PaperProfile,
    RevisionPlan,
)
from crane.services.apc_analysis_service import APCAnalysisService
from crane.services.evidence_evaluation_service import EvidenceEvaluationService
from crane.services.feynman_session_service import FeynmanSession, FeynmanSessionService
from crane.services.journal_matching_service import JournalMatchingService
from crane.services.paper_profile_service import PaperProfileService
from crane.services.revision_planning_service import RevisionPlanningService
from crane.workspace import resolve_workspace


def _resolve_paper_path(paper_path: str, project_dir: str | None) -> str:
    path = Path(paper_path)
    if path.is_absolute():
        return str(path)

    workspace = resolve_workspace(project_dir)
    return str(Path(workspace.project_root) / path)


def _profile_to_dict(profile: PaperProfile) -> dict[str, Any]:
    return {
        "paper_type": profile.paper_type.value,
        "method_family": profile.method_family,
        "evidence_pattern": profile.evidence_pattern.value,
        "validation_scale": profile.validation_scale,
        "citation_neighborhood": profile.citation_neighborhood,
        "novelty_shape": profile.novelty_shape.value,
        "reproducibility_maturity": profile.reproducibility_maturity,
        "problem_domain": profile.problem_domain,
        "keywords": profile.keywords,
        "word_count": profile.word_count,
        "has_code": profile.has_code,
        "has_appendix": profile.has_appendix,
        "num_figures": profile.num_figures,
        "num_tables": profile.num_tables,
        "num_equations": profile.num_equations,
        "num_references": profile.num_references,
        "budget_usd": profile.budget_usd,
    }


def _scores_to_dict(scores: list[DimensionScore]) -> list[dict[str, Any]]:
    return [
        {
            "dimension": score.dimension,
            "score": score.score,
            "confidence": score.confidence,
            "reason_codes": score.reason_codes,
            "evidence_spans": score.evidence_spans,
            "missing_evidence": score.missing_evidence,
            "suggestions": score.suggestions,
        }
        for score in scores
    ]


def _revision_plan_to_dict(plan: RevisionPlan) -> dict[str, Any]:
    return {
        "current_score": plan.current_score,
        "projected_score": plan.projected_score,
        "items": [
            {
                "dimension": item.dimension,
                "suggestion": item.suggestion,
                "priority": item.priority.value,
                "effort": item.effort.value,
                "expected_impact": item.expected_impact,
                "depends_on": item.depends_on,
                "status": item.status,
            }
            for item in plan.items
        ],
    }


def _journal_fit_to_dict(fit: JournalFit | None) -> dict[str, Any] | None:
    if fit is None:
        return None
    return {
        "journal_name": fit.journal_name,
        "scope_fit": fit.scope_fit,
        "contribution_style_fit": fit.contribution_style_fit,
        "evaluation_style_fit": fit.evaluation_style_fit,
        "citation_neighborhood_fit": fit.citation_neighborhood_fit,
        "operational_fit": fit.operational_fit,
        "overall_fit": fit.overall_fit,
        "desk_reject_risk": fit.desk_reject_risk,
        "risk_factors": fit.risk_factors,
        "recommendation": fit.recommendation,
        "cost_assessment": _cost_assessment_to_dict(fit.cost_assessment),
    }


def _cost_assessment_to_dict(cost: CostAssessment | None) -> dict[str, Any] | None:
    if cost is None:
        return None
    return {
        "apc_usd": cost.apc_usd,
        "publication_model": cost.publication_model,
        "affordability_status": cost.affordability_status,
        "budget_delta_usd": cost.budget_delta_usd,
        "apc_stale": cost.apc_stale,
        "waiver_available": cost.waiver_available,
    }


def _feynman_session_to_dict(session: FeynmanSession) -> dict[str, Any]:
    return {
        "paper_path": session.paper_path,
        "mode": session.mode,
        "focus_dimensions": session.focus_dimensions,
        "total_questions": session.total_questions,
        "weak_dimensions": session.weak_dimensions,
        "questions": [
            {
                "dimension": question.dimension,
                "question": question.question,
                "section": question.section,
                "difficulty": question.difficulty,
                "expected_insight": question.expected_insight,
            }
            for question in session.questions
        ],
    }


def register_tools(mcp):
    """Register evaluation-v2 tools with the MCP server."""

    @mcp.tool()
    def evaluate_paper_v2(
        paper_path: str,
        mode: str = "hybrid",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Evaluate paper using evidence-first hybrid engine.

        Returns scorecard with 7-dimension scores, gates status,
        readiness assessment, and revision plan.

        Args:
            paper_path: Path to LaTeX file
            mode: 'hybrid' (default) or 'heuristic'
            project_dir: Project root directory
        """
        resolved_paper_path = _resolve_paper_path(paper_path, project_dir)
        evaluation = EvidenceEvaluationService(mode=mode).evaluate(resolved_paper_path)
        return {
            "paper_path": evaluation.paper_path,
            "mode": mode,
            "profile": _profile_to_dict(evaluation.profile),
            "scores": _scores_to_dict(evaluation.dimension_scores),
            "overall_score": evaluation.overall_score,
            "gates_passed": evaluation.gates_passed,
            "readiness": evaluation.readiness,
            "revision_plan": _revision_plan_to_dict(evaluation.revision_plan),
        }

    @mcp.tool()
    def match_journal_v2(
        paper_path: str,
        budget_usd: float = 0.0,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Match paper against Q1 journals using profile-based scoring.

        Returns target/backup/safe recommendations with fit scores
        and desk-reject risk assessment.
        """
        resolved_paper_path = _resolve_paper_path(paper_path, project_dir)
        profile = PaperProfileService().extract_profile(resolved_paper_path)
        recommendations = JournalMatchingService().recommend_top3(profile, budget_usd=budget_usd)
        return {
            "paper_path": resolved_paper_path,
            "budget_usd": budget_usd,
            "profile": _profile_to_dict(profile),
            "recommendations": {
                "target": _journal_fit_to_dict(recommendations.get("target")),
                "backup": _journal_fit_to_dict(recommendations.get("backup")),
                "safe": _journal_fit_to_dict(recommendations.get("safe")),
            },
        }

    @mcp.tool()
    def analyze_apc(
        paper_path: str,
        budget_usd: float = 0.0,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Analyze APC costs across Q1 journals for your paper.

        Returns affordability assessment, cost comparison,
        and budget-optimized recommendations.
        """
        resolved_paper_path = _resolve_paper_path(paper_path, project_dir)
        profile = PaperProfileService().extract_profile(resolved_paper_path)
        matching_service = JournalMatchingService()
        fits = matching_service.match(profile, budget_usd=budget_usd)
        costs = [fit.cost_assessment for fit in fits if fit.cost_assessment is not None]
        apc_service = APCAnalysisService()
        report = apc_service.generate_apc_report(fits, costs, budget_usd=budget_usd)
        affordable_count = sum(
            1 for cost in costs if cost.affordability_status in {"within_budget", "near_budget"}
        )

        return {
            "paper_path": resolved_paper_path,
            "budget_usd": budget_usd,
            "profile": _profile_to_dict(profile),
            "affordability_summary": {
                "total_journals": len(fits),
                "affordable_journals": affordable_count,
            },
            "recommendations": {
                "target": _journal_fit_to_dict(fits[0] if len(fits) > 0 else None),
                "backup": _journal_fit_to_dict(fits[1] if len(fits) > 1 else None),
                "safe": _journal_fit_to_dict(fits[2] if len(fits) > 2 else None),
            },
            "apc_analysis": [
                {
                    "journal_name": fit.journal_name,
                    "overall_fit": fit.overall_fit,
                    "cost_assessment": _cost_assessment_to_dict(fit.cost_assessment),
                }
                for fit in fits
            ],
            "report_markdown": report,
        }

    @mcp.tool()
    def generate_revision_report(
        paper_path: str,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Generate complete 3-layer revision report for a paper.

        Returns markdown report with:
        - Layer 1: Scorecard (scores, gates, readiness)
        - Layer 2: Evidence view (per-dimension evidence)
        - Layer 3: Revision backlog (prioritized action items)
        """
        resolved_paper_path = _resolve_paper_path(paper_path, project_dir)
        evaluation = EvidenceEvaluationService(mode="hybrid").evaluate(resolved_paper_path)

        planning_service = RevisionPlanningService()
        report = planning_service.generate_full_report(
            evaluation.dimension_scores,
            evaluation.gates_passed,
            evaluation.readiness,
            evaluation.revision_plan,
        )

        return {
            "paper_path": evaluation.paper_path,
            "overall_score": evaluation.overall_score,
            "gates_passed": evaluation.gates_passed,
            "readiness": evaluation.readiness,
            "scores": _scores_to_dict(evaluation.dimension_scores),
            "revision_plan": _revision_plan_to_dict(evaluation.revision_plan),
            "report_markdown": report,
        }

    @mcp.tool()
    def generate_feynman_session(
        paper_path: str,
        mode: str = "post_evaluation",
        focus_dimensions: list[str] | None = None,
        num_questions: int = 5,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Generate Feynman-style probing questions about your paper.

        Uses evaluation scores to identify weak spots, then generates
        questions a confused student would ask. Forces you to articulate
        and defend your work clearly.

        Modes: post_evaluation, pre_submission, methodology, writing
        """
        resolved_paper_path = _resolve_paper_path(paper_path, project_dir)
        evaluation = EvidenceEvaluationService(mode="hybrid").evaluate(resolved_paper_path)
        session_service = FeynmanSessionService()
        session = session_service.generate_session(
            dimension_scores=evaluation.dimension_scores,
            mode=mode,
            focus_dimensions=focus_dimensions,
            num_questions=num_questions,
            paper_path=resolved_paper_path,
        )
        report = session_service.generate_session_report(session)

        return {
            "paper_path": evaluation.paper_path,
            "overall_score": evaluation.overall_score,
            "gates_passed": evaluation.gates_passed,
            "readiness": evaluation.readiness,
            "scores": _scores_to_dict(evaluation.dimension_scores),
            "session": _feynman_session_to_dict(session),
            "report_markdown": report,
        }
