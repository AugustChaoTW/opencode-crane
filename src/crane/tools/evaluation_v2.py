"""Evidence-first evaluation and revision MCP tools (v2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from crane.models.paper_profile import DimensionScore, JournalFit, PaperProfile, RevisionPlan
from crane.services.evidence_evaluation_service import EvidenceEvaluationService
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
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Match paper against Q1 journals using profile-based scoring.

        Returns target/backup/safe recommendations with fit scores
        and desk-reject risk assessment.
        """
        resolved_paper_path = _resolve_paper_path(paper_path, project_dir)
        profile = PaperProfileService().extract_profile(resolved_paper_path)
        recommendations = JournalMatchingService().recommend_top3(profile)
        return {
            "paper_path": resolved_paper_path,
            "profile": _profile_to_dict(profile),
            "recommendations": {
                "target": _journal_fit_to_dict(recommendations.get("target")),
                "backup": _journal_fit_to_dict(recommendations.get("backup")),
                "safe": _journal_fit_to_dict(recommendations.get("safe")),
            },
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
