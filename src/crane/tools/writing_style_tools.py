"""Writing style analysis MCP tools (v0.10.1 Phase C + D)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from crane.models.writing_style_models import (
    ExemplarSnippet,
    RewriteSuggestion,
    SectionDiagnosis,
    StyleGuide,
    StyleIssue,
    StyleMetrics,
)
from crane.services.interactive_rewrite_service import InteractiveRewriteService
from crane.services.preference_learner_service import PreferenceLearnerService
from crane.services.writing_style_service import WritingStyleService, _flatten_metrics
from crane.workspace import resolve_workspace


def _resolve_paper_path(paper_path: str, project_dir: str | None = None) -> str:
    path = Path(paper_path)
    if path.is_absolute():
        return str(path)
    workspace = resolve_workspace(project_dir)
    return str(Path(workspace.project_root) / path)


def _style_metrics_to_dict(metrics: StyleMetrics) -> dict[str, Any]:
    return _flatten_metrics(metrics)


def _style_issue_to_dict(issue: StyleIssue) -> dict[str, str]:
    return {
        "category": issue.category,
        "severity": issue.severity,
        "description": issue.description,
        "example_span": issue.example_span,
        "journal_target": issue.journal_target,
        "recommended_fix": issue.recommended_fix,
    }


def _rewrite_to_dict(rw: RewriteSuggestion) -> dict[str, Any]:
    return {
        "original_text": rw.original_text,
        "suggested_text": rw.suggested_text,
        "rationale": rw.rationale,
        "exemplar_source": rw.exemplar_source,
        "confidence": rw.confidence,
    }


def _diagnosis_to_dict(diag: SectionDiagnosis) -> dict[str, Any]:
    return {
        "section_name": diag.section_name,
        "current_metrics": _style_metrics_to_dict(diag.current_metrics),
        "target_metrics": _style_metrics_to_dict(diag.target_metrics),
        "deviation_score": diag.deviation_score,
        "issues": [_style_issue_to_dict(i) for i in diag.issues],
        "suggestions": [_rewrite_to_dict(s) for s in diag.suggestions],
    }


def _exemplar_to_dict(ex: ExemplarSnippet) -> dict[str, Any]:
    return {
        "text": ex.text,
        "section": ex.section,
        "source_paper": ex.source_paper,
    }


def register_tools(mcp):
    """Register writing style analysis tools with the MCP server."""

    @mcp.tool()
    def crane_extract_journal_style_guide(
        journal_name: str,
    ) -> dict[str, Any]:
        """Extract or build writing style guide for a journal.

        Returns target metrics, domain, confidence, and exemplar count
        for all canonical sections.
        """
        try:
            service = WritingStyleService(journal_name)
            guide = service.style_guide
            return {
                "journal": journal_name,
                "domain": guide.domain,
                "sample_size": guide.sample_size,
                "confidence": guide.confidence_score,
                "target_metrics": _style_metrics_to_dict(guide.metrics),
                "section_targets": guide.section_targets,
                "exemplar_count": len(guide.exemplars),
            }
        except (ValueError, FileNotFoundError) as exc:
            return {"error": str(exc), "journal": journal_name}

    @mcp.tool()
    def crane_diagnose_section(
        paper_path: str,
        section_name: str,
        journal_name: str,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Analyse one section against journal style targets.

        Computes current metrics, deviation score, issues, and suggestions
        for the specified section (Introduction, Methods, Results, etc.).
        """
        try:
            resolved = _resolve_paper_path(paper_path, project_dir)
            service = WritingStyleService(journal_name)
            sections = service.section_chunker.chunk_latex_paper(resolved)

            target_section = None
            for sec in sections:
                if (
                    sec.canonical_name.lower() == section_name.lower()
                    or sec.name.lower() == section_name.lower()
                ):
                    target_section = sec
                    break

            if target_section is None:
                return {
                    "error": f"Section '{section_name}' not found in {paper_path}",
                    "section": section_name,
                    "journal": journal_name,
                }

            diagnosis = service.diagnose_section(target_section)
            result = _diagnosis_to_dict(diagnosis)
            result["journal"] = journal_name
            return result
        except (ValueError, FileNotFoundError) as exc:
            return {"error": str(exc), "section": section_name, "journal": journal_name}

    @mcp.tool()
    def crane_diagnose_paper(
        paper_path: str,
        journal_name: str,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Full paper diagnosis across all sections.

        Returns per-section deviation scores, issues, suggestions,
        and an overall deviation average.
        """
        try:
            resolved = _resolve_paper_path(paper_path, project_dir)
            service = WritingStyleService(journal_name)
            diagnoses = service.diagnose_full_paper(resolved)

            sections_result: dict[str, Any] = {}
            deviation_scores: list[float] = []
            for name, diag in diagnoses.items():
                sections_result[name] = _diagnosis_to_dict(diag)
                deviation_scores.append(diag.deviation_score)

            overall = sum(deviation_scores) / len(deviation_scores) if deviation_scores else 0.0

            return {
                "paper": paper_path,
                "journal": journal_name,
                "sections": sections_result,
                "overall_deviation": round(overall, 2),
                "sections_analysed": len(diagnoses),
                "total_issues": sum(len(d.issues) for d in diagnoses.values()),
                "total_suggestions": sum(len(d.suggestions) for d in diagnoses.values()),
            }
        except (ValueError, FileNotFoundError) as exc:
            return {"error": str(exc), "paper": paper_path, "journal": journal_name}

    @mcp.tool()
    def crane_get_style_exemplars(
        journal_name: str,
        section_name: str,
        count: int = 3,
    ) -> dict[str, Any]:
        """Return exemplar writing patterns showing target style for a journal section."""
        try:
            service = WritingStyleService(journal_name)
            exemplars = service.get_exemplars(section_name, count)
            return {
                "journal": journal_name,
                "section": section_name,
                "exemplars": [_exemplar_to_dict(ex) for ex in exemplars],
                "count": len(exemplars),
            }
        except (ValueError, FileNotFoundError) as exc:
            return {"error": str(exc), "journal": journal_name, "section": section_name}

    @mcp.tool()
    def crane_suggest_rewrites(
        paper_path: str,
        section_name: str,
        journal_name: str,
        count: int = 5,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Generate rewrite suggestions for a section based on journal style targets."""
        try:
            resolved = _resolve_paper_path(paper_path, project_dir)
            service = WritingStyleService(journal_name)
            sections = service.section_chunker.chunk_latex_paper(resolved)

            target_section = None
            for sec in sections:
                if (
                    sec.canonical_name.lower() == section_name.lower()
                    or sec.name.lower() == section_name.lower()
                ):
                    target_section = sec
                    break

            if target_section is None:
                return {
                    "error": f"Section '{section_name}' not found",
                    "section": section_name,
                    "journal": journal_name,
                }

            diagnosis = service.diagnose_section(target_section)
            suggestions = service.suggest_rewrites(diagnosis, max_suggestions=count)
            return {
                "section": section_name,
                "journal": journal_name,
                "deviation_score": diagnosis.deviation_score,
                "suggestions": [_rewrite_to_dict(s) for s in suggestions],
                "count": len(suggestions),
            }
        except (ValueError, FileNotFoundError) as exc:
            return {"error": str(exc), "section": section_name, "journal": journal_name}

    @mcp.tool()
    def crane_compare_sections(
        paper_path: str,
        section_name: str,
        journal1: str,
        journal2: str,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Compare style expectations across two journals for a section."""
        try:
            service1 = WritingStyleService(journal1)
            service2 = WritingStyleService(journal2)
            comparison = service1.compare_journals([journal2], section_name=section_name)

            targets1 = comparison.get(journal1, {})
            targets2 = comparison.get(journal2, {})

            differences: list[dict[str, Any]] = []
            for metric in targets1:
                v1, v2 = targets1.get(metric, 0.0), targets2.get(metric, 0.0)
                diff = abs(v1 - v2)
                if diff > 0.01:
                    differences.append(
                        {
                            "metric": metric,
                            journal1: round(v1, 3),
                            journal2: round(v2, 3),
                            "difference": round(diff, 3),
                        }
                    )
            differences.sort(key=lambda x: x["difference"], reverse=True)

            recommendation = "Both journals have very similar style expectations for this section."
            if differences:
                top = differences[0]
                recommendation = (
                    f"Largest difference is in '{top['metric']}' (delta={top['difference']}). "
                    f"Adjust this metric first when switching target journals."
                )

            return {
                "section": section_name,
                "journals": [journal1, journal2],
                "journal1_targets": targets1,
                "journal2_targets": targets2,
                "differences": differences,
                "recommendation": recommendation,
            }
        except (ValueError, FileNotFoundError) as exc:
            return {"error": str(exc), "journal1": journal1, "journal2": journal2}

    @mcp.tool()
    def crane_export_style_report(
        paper_path: str,
        journal_name: str,
        output_path: str = "",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Generate comprehensive Markdown style report for a paper."""
        try:
            resolved = _resolve_paper_path(paper_path, project_dir)
            service = WritingStyleService(journal_name)
            diagnoses = service.diagnose_full_paper(resolved)

            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_name = journal_name.replace(" ", "_").replace("/", "_")
                output_path = f"reports/style_report_{safe_name}_{timestamp}.md"

            if project_dir:
                workspace = resolve_workspace(project_dir)
                output_path = str(Path(workspace.project_root) / output_path)

            report = _generate_markdown_report(service, diagnoses)
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(report, encoding="utf-8")

            return {
                "report_path": output_path,
                "journal": journal_name,
                "sections_analysed": len(diagnoses),
                "total_issues": sum(len(d.issues) for d in diagnoses.values()),
                "total_suggestions": sum(len(d.suggestions) for d in diagnoses.values()),
                "report_length": len(report),
            }
        except (ValueError, FileNotFoundError) as exc:
            return {"error": str(exc), "paper": paper_path, "journal": journal_name}


def _generate_markdown_report(
    service: WritingStyleService,
    diagnoses: dict[str, SectionDiagnosis],
) -> str:
    lines: list[str] = [
        f"# Writing Style Report: {service.journal_name}",
        "",
        f"**Domain**: {service.domain}",
        f"**Confidence**: {service.style_guide.confidence_score:.0%}",
        f"**Generated**: {datetime.now().isoformat()}",
        "",
    ]
    total_issues = 0
    total_suggestions = 0

    for name, diag in diagnoses.items():
        lines.append(f"## {name}")
        lines.append(f"**Deviation score**: {diag.deviation_score:.2f}")
        lines.append("")

        current_d = _flatten_metrics(diag.current_metrics)
        target_d = _flatten_metrics(diag.target_metrics)
        lines.append("| Metric | Current | Target | Delta |")
        lines.append("|--------|---------|--------|-------|")
        for metric in current_d:
            c, t = current_d[metric], target_d.get(metric, 0.0)
            lines.append(f"| {metric} | {c:.2f} | {t:.2f} | {c - t:+.2f} |")
        lines.append("")

        if diag.issues:
            lines.append("### Issues")
            for issue in diag.issues:
                lines.append(f"- [{issue.severity}] **{issue.category}**: {issue.description}")
            total_issues += len(diag.issues)
        lines.append("")

        if diag.suggestions:
            lines.append("### Suggestions")
            for sug in diag.suggestions:
                lines.append(f"- {sug.rationale}")
            total_suggestions += len(diag.suggestions)
        lines.append("")

    lines.append("---")
    lines.append(
        f"**Summary**: {len(diagnoses)} sections, {total_issues} issues, {total_suggestions} suggestions."
    )
    return "\n".join(lines)


def register_phase_d_tools(mcp):  # noqa: C901
    """Register Phase D interactive rewrite and preference learning tools."""

    @mcp.tool()
    def crane_start_rewrite_session(
        paper_path: str,
        journal_name: str,
        section_name: str,
        max_suggestions: int = 5,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Start an interactive rewrite session for a paper section."""
        try:
            resolved = _resolve_paper_path(paper_path, project_dir)
            service = InteractiveRewriteService()
            session = service.start_session(resolved, journal_name, section_name, max_suggestions)
            pending = service.get_pending_suggestions(session)
            return {
                "session_id": session.session_id,
                "journal": journal_name,
                "section": section_name,
                "total_suggestions": len(session.suggestions),
                "pending": [_rewrite_to_dict(s) for s in pending],
                "status": session.status,
            }
        except (ValueError, FileNotFoundError) as exc:
            return {"error": str(exc), "paper": paper_path, "journal": journal_name}

    @mcp.tool()
    def crane_submit_rewrite_choice(
        session_id: str,
        suggestion_index: int,
        decision: str,
        modified_text: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        """Submit accept/reject/modify decision for a rewrite suggestion."""
        try:
            service = InteractiveRewriteService()
            session = service._load_session(session_id)
            session = service.submit_choice(
                session, suggestion_index, decision, modified_text, reason
            )
            summary = service.get_session_summary(session)
            pending = service.get_pending_suggestions(session)
            summary["pending_count"] = len(pending)
            return summary
        except (ValueError, FileNotFoundError, IndexError) as exc:
            return {"error": str(exc), "session_id": session_id}

    @mcp.tool()
    def crane_get_rewrite_session(
        session_id: str,
    ) -> dict[str, Any]:
        """Get current state and summary of a rewrite session."""
        try:
            service = InteractiveRewriteService()
            session = service._load_session(session_id)
            return service.get_session_summary(session)
        except (ValueError, FileNotFoundError) as exc:
            return {"error": str(exc), "session_id": session_id}

    @mcp.tool()
    def crane_list_rewrite_sessions(
        status: str = "",
    ) -> dict[str, Any]:
        """List all rewrite sessions, optionally filtered by status."""
        service = InteractiveRewriteService()
        sessions = service.list_sessions(status=status)
        return {"sessions": sessions, "count": len(sessions)}

    @mcp.tool()
    def crane_get_user_preferences(
        user_id: str = "default",
    ) -> dict[str, Any]:
        """Get learned writing preferences for a user."""
        service = PreferenceLearnerService()
        return service.get_preference_summary(user_id)

    @mcp.tool()
    def crane_reset_user_preferences(
        user_id: str = "default",
    ) -> dict[str, Any]:
        """Reset all learned preferences for a user."""
        service = PreferenceLearnerService()
        state = service.reset_preferences(user_id)
        return {
            "user_id": state.user_id,
            "status": "reset",
            "total_sessions": state.total_sessions,
            "total_choices": state.total_choices,
        }
