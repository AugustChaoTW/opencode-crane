"""Paper index MCP tools — fast single-pass scan + pipeline orchestration.

build_paper_index : Scan a LaTeX file once with Linux tools, emit paper_index.yaml.
run_review_pipeline: Orchestrate review steps in optimal order using the index.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from crane.services.paper_index_service import PaperIndexService

_svc = PaperIndexService()


def _resolve(paper_path: str, project_dir: str | None) -> str:
    p = Path(paper_path)
    if p.is_absolute():
        return str(p)
    root = Path(project_dir) if project_dir else Path(".")
    return str(root / p)


def register_tools(mcp):
    """Register paper index tools with the MCP server."""

    @mcp.tool()
    def build_paper_index(
        paper_path: str,
        force: bool = False,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Fast single-pass scan of a LaTeX paper using Linux tools (grep, sed).

        Builds a hidden .{stem}_index.yaml alongside the paper that all
        downstream review tools can read instead of re-parsing independently.
        Subsequent calls return a cached copy when file mtime is unchanged.

        Use this as Step 1 before: evaluate_paper_v2, run_submission_check,
        crane_diagnose, simulate_submission_outcome.

        Args:
            paper_path: Path to .tex file (absolute or relative to project_dir)
            force: Rebuild even when a fresh cache exists (default False)
            project_dir: Project root directory (auto-detected if None)

        Returns:
            {
                "_meta":     {"source": str, "mtime": float, "built_at": str, "schema": "1"},
                "structure": {"title": str, "abstract": str, "sections": [...],
                              "total_lines": int},
                "counts":    {"words": int, "figures": int, "tables": int,
                              "equations": int, "citations": int},
                "flags":     {"has_code": bool, "has_appendix": bool},
                "prescan":   {"informal_language": int, "method_claims": int,
                              "novelty_keywords": int, "benchmark_keywords": int,
                              "limitation_keywords": int, "repro_keywords": int},
                "results":   {"crane_review_full": null, "evaluate_paper_v2": null,
                              "crane_diagnose": null}
            }
        """
        resolved = _resolve(paper_path, project_dir)
        try:
            index = _svc.build(resolved, force=force)
            return {
                **index,
                "cache_hit": not force and _svc.load(resolved) is not None,
            }
        except FileNotFoundError as e:
            return {"error": str(e), "paper_path": resolved}

    @mcp.tool()
    def run_review_pipeline(
        paper_path: str,
        journal_name: str = "",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Orchestrate full paper review in optimal order with result accumulation.

        Runs four steps sequentially; each step writes results back to the
        paper index so subsequent steps can reuse already-computed data without
        re-parsing the LaTeX file.

        Steps:
            1. build_paper_index  — Linux scan (<0.5 s) → paper_index.yaml
            2. crane_review_full  — defect detection via ReviewInspector (<1 s)
            3. evaluate_paper_v2  — 7-dimension evidence scoring (~5–10 s)
            4. section_review     — section-level issues via SectionReviewService (<2 s)

        Args:
            paper_path: Path to .tex file
            journal_name: Target journal (used in step 3 context, optional)
            project_dir: Project root directory

        Returns:
            {
                "paper_path": str,
                "journal_name": str,
                "steps": {
                    "build_paper_index": {"status": "done", "sections": int, "words": int},
                    "crane_review_full": {"critical": int, "major": int, "minor": int, ...},
                    "evaluate_paper_v2": {"overall_score": float, "readiness": str, ...},
                    "section_review":    {"total_issues": int, "sections": int},
                },
                "index": { ... }    # full index with accumulated results
            }
        """
        resolved = _resolve(paper_path, project_dir)
        steps: dict[str, Any] = {}

        # ── Step 1: build index ────────────────────────────────────────────
        try:
            idx = _svc.build(resolved)
            steps["build_paper_index"] = {
                "status": "done",
                "sections": len(idx["structure"]["sections"]),
                "words": idx["counts"]["words"],
                "figures": idx["counts"]["figures"],
                "tables": idx["counts"]["tables"],
            }
        except Exception as e:
            return {"paper_path": resolved, "error": f"build_paper_index failed: {e}"}

        # ── Step 2: crane_review_full ──────────────────────────────────────
        try:
            from crane.services.submission_workflow_service import SubmissionWorkflowService

            raw = Path(resolved).read_text(encoding="utf-8")
            workflow = SubmissionWorkflowService(project_dir=project_dir)
            review_result = workflow.full_review(paper_content=raw)
            steps["crane_review_full"] = {
                "critical": review_result.get("critical_count", 0),
                "major": review_result.get("major_count", 0),
                "minor": review_result.get("minor_count", 0),
                "total": review_result.get("total_defects", 0),
            }
            _svc.update_results(resolved, "crane_review_full", steps["crane_review_full"])
        except Exception as e:
            steps["crane_review_full"] = {"error": str(e)}

        # ── Step 3: evaluate_paper_v2 ──────────────────────────────────────
        try:
            from crane.services.evidence_evaluation_service import EvidenceEvaluationService

            ev = EvidenceEvaluationService().evaluate(resolved)
            eval_summary = {
                "overall_score": round(ev.overall_score, 2),
                "gates_passed": ev.gates_passed,
                "readiness": ev.readiness,
                "dimensions": {
                    d.dimension: round(d.score, 2)
                    for d in ev.dimension_scores
                },
            }
            steps["evaluate_paper_v2"] = eval_summary
            _svc.update_results(resolved, "evaluate_paper_v2", eval_summary)
        except Exception as e:
            steps["evaluate_paper_v2"] = {"error": str(e)}

        # ── Step 4: section_review ─────────────────────────────────────────
        try:
            from crane.services.section_review_service import SectionReviewService

            review_svc = SectionReviewService()
            # single review call — all types at once
            review = review_svc.review_paper(resolved)
            section_summary = {
                "total_issues": sum(len(s.issues) for s in review.sections),
                "sections": len(review.sections),
            }
            steps["section_review"] = section_summary
            _svc.update_results(resolved, "crane_diagnose", section_summary)
        except Exception as e:
            steps["section_review"] = {"error": str(e)}

        # Reload index to capture all written results
        final_idx = _svc.load(resolved) or idx

        return {
            "paper_path": resolved,
            "journal_name": journal_name,
            "steps": steps,
            "index": final_idx,
        }
