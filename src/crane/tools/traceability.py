"""Paper Traceability System MCP tools (v0.13.0).

Natural language triggers:
  "trace this paper" | "do paper trace" | "整理這篇研究"

All 24 tools provide end-to-end traceability from RQ → Contribution →
Experiment → Figure/Table → Citation → Change Impact.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def register_tools(mcp):  # noqa: C901
    """Register all 24 paper traceability tools with the MCP server."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_service(paper_path: str, output_dir: str = "", project_dir: str = ""):
        from crane.services.traceability_service import TraceabilityService

        return TraceabilityService(
            paper_path=paper_path,
            output_dir=output_dir,
            project_dir=project_dir,
        )

    def _version_dir(svc, mode: str) -> Path:
        return svc.get_version_dir(mode)

    # ------------------------------------------------------------------
    # 1. trace_paper — master entry point
    # ------------------------------------------------------------------

    @mcp.tool()
    def trace_paper(
        paper_path: str,
        mode: str = "full",
        paper_stage: str = "draft",
        output_dir: str = "",
        project_dir: str = "",
        trigger: str = "",
    ) -> dict[str, Any]:
        """Trace a paper's complete research lifecycle.

        This is the primary entry point for the paper traceability system.
        Invoke with natural language: "trace this paper", "do paper trace",
        or "整理這篇研究".

        Creates a versioned `_paper_trace/v{n}/` directory co-located with
        the paper file, containing 10 YAML documents covering the full
        research control chain:

            RQ → Contribution → Experiment → Figure/Table →
            Citation → Change Impact → Risk → Dataset → Artifact

        Modes:
            full        — Init fresh v{n} dir + infer all items from paper
            init        — Init fresh v{n} dir with blank templates only
            infer       — Init fresh v{n} dir + infer all (same as full)
            update      — Add/edit items in existing latest version
            status      — Show chain completeness status (read-only)
            viz         — Generate Mermaid + DOT visualization (read-only)

        Args:
            paper_path:  Path to .tex or .pdf file (absolute or relative)
            mode:        Trace mode (full | init | infer | update | status | viz)
            paper_stage: draft | revision | camera_ready
            output_dir:  Custom base directory (default: co-located with paper)
            project_dir: Project root (fallback for path resolution)
            trigger:     Original natural language trigger (logged in README)

        Returns:
            Dict with version_dir, mode, status, inferred counts,
            chain_completeness, and optionally visualization strings.

        NATURAL LANGUAGE TRIGGERS:
            "trace this paper"     → mode="full"
            "do paper trace"       → mode="full"
            "整理這篇研究"          → mode="full"
            "show trace status"    → mode="status"
            "visualize trace"      → mode="viz"
        """
        from crane.services.traceability_inference_service import TraceabilityInferenceService

        svc = _make_service(paper_path, output_dir, project_dir)
        vdir = _version_dir(svc, mode)

        result: dict[str, Any] = {
            "paper_path": paper_path,
            "mode": mode,
            "paper_stage": paper_stage,
        }

        if mode in {"full", "init", "infer"}:
            vdir = svc.init_documents(mode=mode, paper_stage=paper_stage)
            if trigger:
                version_num = int(vdir.name[1:])
                svc._update_readme(version_num, mode, paper_stage, trigger)
            result["version_dir"] = str(vdir)
            result["status"] = "initialized"
        else:
            result["version_dir"] = str(vdir)

        if mode in {"full", "infer"}:
            infer_svc = TraceabilityInferenceService(paper_path)
            inferred = infer_svc.infer_all()
            counts = infer_svc.write_to_traceability_dir(vdir, inferred, svc)
            result["inferred"] = counts

        if mode in {"status", "update", "full", "infer", "init"}:
            verify = svc.verify_chain(vdir)
            index = svc.generate_index(vdir)
            result["chain_completeness"] = verify
            result["summary"] = {
                "rq_count": index.rq_count,
                "contribution_count": index.contribution_count,
                "experiment_count": index.experiment_count,
                "figure_table_count": index.figure_table_count,
                "risk_count": index.risk_count,
                "artifact_count": index.artifact_count,
                "pending_changes": index.pending_changes,
                "chain_coverage": index.chain_coverage,
            }

        if mode == "viz":
            from crane.services.traceability_viz_service import TraceabilityVizService

            graph = svc.build_graph(vdir)
            viz_svc = TraceabilityVizService()
            result["mermaid"] = viz_svc.get_mermaid(graph)
            result["dot"] = viz_svc.get_dot(graph)

        return result

    # ------------------------------------------------------------------
    # 2. list_active_papers
    # ------------------------------------------------------------------

    @mcp.tool()
    def list_active_papers(
        search_root: str = "",
        max_depth: int = 3,
        project_dir: str = "",
    ) -> dict[str, Any]:
        """List active paper directories in the workspace.

        Scans for directories containing .tex or .pdf files, skipping any
        that match rejection/abandonment keywords (reject, nogo, no-go,
        withdrawn, abandon, cancelled, cancel, withdraw).

        Args:
            search_root: Directory to scan (default: project root or cwd)
            max_depth:   Maximum recursion depth (default: 3)
            project_dir: Project root hint for workspace resolution

        Returns:
            Dict with active papers list. Each entry includes:
            {dir_name, path, paper_files, has_trace, trace_version}
        """
        from crane.workspace import resolve_workspace

        if search_root:
            root = Path(search_root)
        else:
            workspace = resolve_workspace(project_dir)
            root = Path(workspace.project_root)

        svc = _make_service(str(root / "dummy.tex"), "", project_dir)
        papers = svc.list_active_papers(root, max_depth=max_depth)

        return {
            "search_root": str(root),
            "active_paper_count": len(papers),
            "papers": papers,
        }

    # ------------------------------------------------------------------
    # 3. get_traceability_status
    # ------------------------------------------------------------------

    @mcp.tool()
    def get_traceability_status(
        paper_path: str,
        output_dir: str = "",
        project_dir: str = "",
    ) -> dict[str, Any]:
        """Get current traceability chain completeness status.

        Shows chain coverage, pending changes, orphan nodes, and
        per-dimension completeness without creating a new version.

        Args:
            paper_path:  Path to .tex or .pdf file
            output_dir:  Custom trace base directory
            project_dir: Project root hint

        Returns:
            Dict with chain_completeness, pending_changes, orphans,
            summary counts, and overall chain_coverage score.
        """
        svc = _make_service(paper_path, output_dir, project_dir)
        vdir = _version_dir(svc, "status")

        verify = svc.verify_chain(vdir)
        orphans = svc.find_orphans(vdir)
        pending = svc.get_pending_changes(vdir)
        index = svc.generate_index(vdir)

        return {
            "paper_path": paper_path,
            "version_dir": str(vdir),
            "chain_completeness": verify,
            "orphans": orphans,
            "pending_change_count": len(pending),
            "pending_changes": pending,
            "summary": {
                "rq_count": index.rq_count,
                "contribution_count": index.contribution_count,
                "experiment_count": index.experiment_count,
                "figure_table_count": index.figure_table_count,
                "risk_count": index.risk_count,
                "artifact_count": index.artifact_count,
                "pending_changes": index.pending_changes,
                "chain_coverage": index.chain_coverage,
            },
        }

    # ------------------------------------------------------------------
    # 4. init_traceability
    # ------------------------------------------------------------------

    @mcp.tool()
    def init_traceability(
        paper_path: str,
        paper_stage: str = "draft",
        output_dir: str = "",
        project_dir: str = "",
        trigger: str = "",
    ) -> dict[str, Any]:
        """Initialize a new traceability version with blank templates.

        Creates _paper_trace/v{n}/ directory with all 10 YAML documents.
        Does NOT run inference — use trace_paper(mode="full") for that.

        Args:
            paper_path:  Path to .tex or .pdf file
            paper_stage: draft | revision | camera_ready
            output_dir:  Custom trace base directory
            project_dir: Project root hint
            trigger:     Original trigger command (logged in README)

        Returns:
            Dict with version_dir and list of created files.
        """
        svc = _make_service(paper_path, output_dir, project_dir)
        vdir = svc.init_documents(mode="init", paper_stage=paper_stage)
        if trigger:
            version_num = int(vdir.name[1:])
            svc._update_readme(version_num, "init", paper_stage, trigger)

        files = [f.name for f in sorted(vdir.iterdir()) if f.is_file()]
        return {
            "paper_path": paper_path,
            "version_dir": str(vdir),
            "paper_stage": paper_stage,
            "files_created": files,
            "status": "initialized",
        }

    # ------------------------------------------------------------------
    # 5. add_research_question
    # ------------------------------------------------------------------

    @mcp.tool()
    def trace_add(
        paper_path: str,
        item_type: str,
        item_id: str,
        data: dict,
        output_dir: str = "",
        project_dir: str = "",
    ) -> dict[str, Any]:
        """Add any traceability item to the paper trace chain.

        Unified entry-point replacing the individual add_research_question,
        add_contribution, add_experiment, add_figure_table, add_trace_reference,
        add_reviewer_risk, add_dataset, and add_baseline tools.

        item_type     item_id format    required data keys
        ─────────────────────────────────────────────────────────────────
        rq            RQ1, RQ2, …       text
        contribution  C1, C2, …         claim
        experiment    E1, E2, …         goal
        figure_table  Fig:1, T:1, …     ft_type, purpose
        reference     <bib key>          title, purpose
        risk          R1, R2, …         description
        dataset       DS1, DS2, …       name
        baseline      BL1, BL2, …       name

        All other keys in data are optional and map directly to the
        original add_* parameter names (e.g. motivation, rq_ids, dataset,
        role, severity, split, full_name, …).

        Args:
            paper_path:  Path to .tex or .pdf file.
            item_type:   One of the types listed above.
            item_id:     Unique ID for this item (e.g. "RQ1", "C2", "E1").
            data:        Dict of type-specific fields.
            output_dir:  Custom trace base directory (optional).
            project_dir: Project root hint (optional).

        Returns:
            {"status": "added", "item_type": ..., "item_id": ..., "version_dir": ...}
        """
        svc = _make_service(paper_path, output_dir, project_dir)
        vdir = _version_dir(svc, "update")
        d = data or {}

        if item_type == "rq":
            svc.add_research_question(
                vdir,
                rq_id=item_id,
                text=d.get("text", ""),
                motivation=d.get("motivation", ""),
                hypothesis=d.get("hypothesis", ""),
            )
        elif item_type == "contribution":
            svc.add_contribution(
                vdir,
                contribution_id=item_id,
                claim=d.get("claim", ""),
                why_it_matters=d.get("why_it_matters", ""),
                strongest_defensible_wording=d.get("strongest_defensible_wording", ""),
                reviewer_risk=d.get("reviewer_risk", ""),
                response_strategy=d.get("response_strategy", ""),
                rq_ids=d.get("rq_ids") or [],
            )
        elif item_type == "experiment":
            svc.add_experiment(
                vdir,
                exp_id=item_id,
                goal=d.get("goal", ""),
                dataset=d.get("dataset", ""),
                model=d.get("model", ""),
                hardware=d.get("hardware", ""),
                framework=d.get("framework", ""),
                related_contributions=d.get("related_contributions") or [],
                related_rqs=d.get("related_rqs") or [],
                notes=d.get("notes", ""),
            )
        elif item_type == "figure_table":
            svc.add_figure_table(
                vdir,
                ft_id=item_id,
                ft_type=d.get("ft_type", "figure"),
                purpose=d.get("purpose", ""),
                claim_supported=d.get("claim_supported", ""),
                source_experiments=d.get("source_experiments") or [],
                related_rqs=d.get("related_rqs") or [],
                caption_draft=d.get("caption_draft", ""),
            )
        elif item_type == "reference":
            svc.add_reference(
                vdir,
                ref_key=item_id,
                title=d.get("title", ""),
                purpose=d.get("purpose", ""),
                role=d.get("role", "comparison"),
                should_appear_in=d.get("should_appear_in") or [],
                should_not_appear_in=d.get("should_not_appear_in") or [],
                supports_contributions=d.get("supports_contributions") or [],
            )
        elif item_type == "risk":
            svc.add_reviewer_risk(
                vdir,
                risk_id=item_id,
                description=d.get("description", ""),
                severity=d.get("severity", "medium"),
                likely_appears_in=d.get("likely_appears_in", ""),
                response_strategy=d.get("response_strategy", ""),
                fallback_claim=d.get("fallback_claim", ""),
                related_contributions=d.get("related_contributions") or [],
            )
        elif item_type == "dataset":
            svc.add_dataset(
                vdir,
                dataset_id=item_id,
                name=d.get("name", ""),
                description=d.get("description", ""),
                split=d.get("split", ""),
                metrics=d.get("metrics") or [],
                used_in_experiments=d.get("used_in_experiments") or [],
                download_url=d.get("download_url", ""),
            )
        elif item_type == "baseline":
            svc.add_baseline(
                vdir,
                baseline_id=item_id,
                name=d.get("name", ""),
                full_name=d.get("full_name", ""),
                source_citation=d.get("source_citation", ""),
                implementation_source=d.get("implementation_source", "official"),
                implementation_url=d.get("implementation_url", ""),
                used_in_experiments=d.get("used_in_experiments") or [],
            )
        else:
            return {
                "status": "error",
                "error": f"Unknown item_type '{item_type}'. "
                "Use: rq | contribution | experiment | figure_table | "
                "reference | risk | dataset | baseline",
            }

        return {
            "status": "added",
            "item_type": item_type,
            "item_id": item_id,
            "version_dir": str(vdir),
        }

    # ------------------------------------------------------------------
    # 13. link_artifacts
    # ------------------------------------------------------------------

    @mcp.tool()
    def link_artifacts(
        paper_path: str,
        artifact_id: str,
        artifact_path: str,
        artifact_type: str,
        purpose: str,
        used_by: list[str] | None = None,
        generated_by: str = "",
        git_tracked: bool = True,
        output_dir: str = "",
        project_dir: str = "",
    ) -> dict[str, Any]:
        """Add an artifact to the artifact index.

        Updates 10_artifact_index.yaml in the latest trace version.

        Args:
            paper_path:     Path to .tex or .pdf file
            artifact_id:    ID in format A001, A002, ...
            artifact_path:  Relative path to artifact from project root
            artifact_type:  script | notebook | checkpoint | figure | table | dataset | config | other
            purpose:        What this artifact is for
            used_by:        List of IDs (E{n}, Fig:{n}, etc.) that use this
            generated_by:   E{n} that generated this, or "" if manual
            git_tracked:    Whether this artifact is tracked by git
            output_dir:     Custom trace base directory
            project_dir:    Project root hint
        """
        svc = _make_service(paper_path, output_dir, project_dir)
        vdir = _version_dir(svc, "update")
        svc.add_artifact(
            vdir,
            artifact_id=artifact_id,
            artifact_path=artifact_path,
            artifact_type=artifact_type,
            purpose=purpose,
            used_by=used_by or [],
            generated_by=generated_by,
            git_tracked=git_tracked,
        )
        return {"status": "added", "artifact_id": artifact_id, "version_dir": str(vdir)}

    # ------------------------------------------------------------------
    # 14. log_change
    # ------------------------------------------------------------------

    @mcp.tool()
    def log_change(
        paper_path: str,
        change: str,
        why: str,
        changed_artifact: str,
        impact_severity: str = "low",
        must_update: list[dict] | None = None,
        output_dir: str = "",
        project_dir: str = "",
    ) -> dict[str, Any]:
        """Log a change and its downstream impact requirements.

        Updates 7_change_log_impact.yaml in the latest trace version.
        Auto-generates a CH{n} ID.

        Args:
            paper_path:       Path to .tex or .pdf file
            change:           What changed (e.g., "Updated accuracy from 0.85 to 0.87")
            why:              Why the change was made
            changed_artifact: ID of changed item (E1, Fig:3, etc.)
            impact_severity:  low | medium | high | critical
            must_update:      List of {artifact, artifact_type, reason} dicts
            output_dir:       Custom trace base directory
            project_dir:      Project root hint

        Returns:
            Dict with generated change_id and version_dir.
        """
        svc = _make_service(paper_path, output_dir, project_dir)
        vdir = _version_dir(svc, "update")
        change_id = svc.log_change(
            vdir,
            change=change,
            why=why,
            changed_artifact=changed_artifact,
            impact_severity=impact_severity,
            must_update=must_update,
        )
        return {
            "status": "logged",
            "change_id": change_id,
            "impact_severity": impact_severity,
            "must_update_count": len(must_update) if must_update else 0,
            "version_dir": str(vdir),
        }

    # ------------------------------------------------------------------
    # 15. get_change_impact
    # ------------------------------------------------------------------

    @mcp.tool()
    def get_change_impact(
        paper_path: str,
        change_id: str,
        output_dir: str = "",
        project_dir: str = "",
    ) -> dict[str, Any]:
        """Get the downstream impact of a specific change.

        Returns all must_update items for a CH{n} change ID,
        with their resolution status.

        Args:
            paper_path:  Path to .tex or .pdf file
            change_id:   CH{n} change ID to look up
            output_dir:  Custom trace base directory
            project_dir: Project root hint
        """
        svc = _make_service(paper_path, output_dir, project_dir)
        vdir = _version_dir(svc, "status")
        impact = svc.get_change_impact(vdir, change_id)
        return {"change_id": change_id, "version_dir": str(vdir), **impact}

    # ------------------------------------------------------------------
    # 16. get_pending_changes
    # ------------------------------------------------------------------

    @mcp.tool()
    def get_pending_changes(
        paper_path: str,
        output_dir: str = "",
        project_dir: str = "",
    ) -> dict[str, Any]:
        """List all unresolved change impact items.

        Returns all must_update items across all changes where
        status is still "pending".

        Args:
            paper_path:  Path to .tex or .pdf file
            output_dir:  Custom trace base directory
            project_dir: Project root hint

        Returns:
            Dict with pending_count and list of pending items.
        """
        svc = _make_service(paper_path, output_dir, project_dir)
        vdir = _version_dir(svc, "status")
        pending = svc.get_pending_changes(vdir)
        return {
            "paper_path": paper_path,
            "version_dir": str(vdir),
            "pending_count": len(pending),
            "pending_items": pending,
        }

    # ------------------------------------------------------------------
    # 17. mark_change_resolved
    # ------------------------------------------------------------------

    @mcp.tool()
    def mark_change_resolved(
        paper_path: str,
        change_id: str,
        artifact: str,
        output_dir: str = "",
        project_dir: str = "",
    ) -> dict[str, Any]:
        """Mark a specific must_update item as resolved.

        Updates the status of one must_update item in
        7_change_log_impact.yaml to "resolved".

        Args:
            paper_path:  Path to .tex or .pdf file
            change_id:   CH{n} change ID
            artifact:    Artifact name that has been updated
            output_dir:  Custom trace base directory
            project_dir: Project root hint
        """
        svc = _make_service(paper_path, output_dir, project_dir)
        vdir = _version_dir(svc, "update")
        success = svc.mark_change_resolved(vdir, change_id, artifact)
        return {
            "change_id": change_id,
            "artifact": artifact,
            "resolved": success,
            "version_dir": str(vdir),
        }

    # ------------------------------------------------------------------
    # 18. verify_traceability_chain
    # ------------------------------------------------------------------

    @mcp.tool()
    def verify_traceability_chain(
        paper_path: str,
        output_dir: str = "",
        project_dir: str = "",
    ) -> dict[str, Any]:
        """Verify the completeness of the RQ → Contribution → Experiment → Figure chain.

        Checks:
        - Every RQ has ≥1 testing experiment
        - Every contribution has ≥1 evidence item
        - Every experiment has ≥1 figure/table output
        - No broken cross-references

        Args:
            paper_path:  Path to .tex or .pdf file
            output_dir:  Custom trace base directory
            project_dir: Project root hint

        Returns:
            Dict with per-chain check results and overall coverage score.
        """
        svc = _make_service(paper_path, output_dir, project_dir)
        vdir = _version_dir(svc, "status")
        verify = svc.verify_chain(vdir)
        return {
            "paper_path": paper_path,
            "version_dir": str(vdir),
            **verify,
        }

    # ------------------------------------------------------------------
    # 18b. get_chain_coverage
    # ------------------------------------------------------------------

    @mcp.tool()
    def get_chain_coverage(
        paper_path: str,
        output_dir: str = "",
        project_dir: str = "",
    ) -> dict[str, Any]:
        """Show chain coverage score with per-node breakdown and fix actions.

        More actionable than verify_traceability_chain: for each isolated
        node it generates a ready-to-execute trace_add or link_artifacts call.

        Formula::

            coverage = (RQ→Exp + Contribution→Evidence + Experiment→Figure)
                       / (total_RQs + total_Contributions + total_Experiments)

        Args:
            paper_path:  Path to .tex or .pdf file.
            output_dir:  Custom trace base directory.
            project_dir: Project root hint.

        Returns:
            Dict with chain_coverage (0.0–1.0), covered_nodes, total_nodes,
            breakdown per category, isolated_nodes list, and suggested_actions.

        Example output::

            {
              "chain_coverage": 0.0,
              "covered_nodes": 0,
              "total_nodes": 3,
              "breakdown": {
                "rqs":           {"total": 1, "covered": 0, "isolated": ["RQ1"]},
                "contributions": {"total": 1, "covered": 0, "isolated": ["C1"]},
                "experiments":   {"total": 1, "covered": 0, "isolated": ["E1"]},
              },
              "isolated_nodes": ["RQ1", "C1", "E1"],
              "suggested_actions": [
                'trace_add(item_type="experiment", data={"related_rqs": ["RQ1"], ...})',
                'link_artifacts(paper_path="<path>", exp_id="E1", artifact_path="<fig>")',
              ]
            }
        """
        svc = _make_service(paper_path, output_dir, project_dir)
        vdir = _version_dir(svc, "status")
        coverage = svc.compute_chain_coverage(vdir)
        return {
            "paper_path": paper_path,
            "version_dir": str(vdir),
            **coverage,
        }

    # ------------------------------------------------------------------
    # 19. find_orphan_artifacts
    # ------------------------------------------------------------------

    @mcp.tool()
    def find_orphan_artifacts(
        paper_path: str,
        output_dir: str = "",
        project_dir: str = "",
    ) -> dict[str, Any]:
        """Find traceability nodes with no connections.

        Identifies orphan items: RQs with no experiments, experiments
        with no figures/tables, figures with no contributing experiments, etc.

        Args:
            paper_path:  Path to .tex or .pdf file
            output_dir:  Custom trace base directory
            project_dir: Project root hint

        Returns:
            Dict with orphan lists per node type.
        """
        svc = _make_service(paper_path, output_dir, project_dir)
        vdir = _version_dir(svc, "status")
        orphans = svc.find_orphans(vdir)
        total = sum(len(v) for v in orphans.values() if isinstance(v, list))
        return {
            "paper_path": paper_path,
            "version_dir": str(vdir),
            "total_orphans": total,
            "orphans": orphans,
        }

    # ------------------------------------------------------------------
    # 20. generate_artifact_index
    # ------------------------------------------------------------------

    @mcp.tool()
    def generate_artifact_index(
        paper_path: str,
        output_dir: str = "",
        project_dir: str = "",
    ) -> dict[str, Any]:
        """Generate a summary index of all traceability artifacts.

        Counts all tracked items, computes chain coverage, and
        identifies orphans and pending changes.

        Args:
            paper_path:  Path to .tex or .pdf file
            output_dir:  Custom trace base directory
            project_dir: Project root hint

        Returns:
            Complete TraceabilityIndex as dict.
        """
        svc = _make_service(paper_path, output_dir, project_dir)
        vdir = _version_dir(svc, "status")
        index = svc.generate_index(vdir)
        return {
            "paper_path": index.paper_path,
            "trace_dir": index.trace_dir,
            "generated_at": index.generated_at,
            "rq_count": index.rq_count,
            "contribution_count": index.contribution_count,
            "experiment_count": index.experiment_count,
            "figure_table_count": index.figure_table_count,
            "reference_count": index.reference_count,
            "risk_count": index.risk_count,
            "artifact_count": index.artifact_count,
            "pending_changes": index.pending_changes,
            "chain_coverage": index.chain_coverage,
            "chain_completeness": index.chain_completeness,
            "orphan_detection": index.orphan_detection,
        }

    # ------------------------------------------------------------------
    # 21. get_traceability_mermaid
    # ------------------------------------------------------------------

    @mcp.tool()
    def get_traceability_viz(
        paper_path: str,
        output_format: str = "mermaid",
        output_dir: str = "",
        project_dir: str = "",
    ) -> dict[str, Any]:
        """Generate a visualization of the traceability graph.

        Consolidates get_traceability_mermaid and get_traceability_dot.

        Node color coding:
          RQ → blue, Contribution → orange, Experiment → purple,
          Figure/Table → green, Risk → red diamond, Section → gray,
          Reference → teal, Artifact → brown, Change → yellow

        Args:
            paper_path:    Path to .tex or .pdf file.
            output_format: "mermaid" — Mermaid flowchart (default, embed in Markdown).
                           "dot"     — Graphviz DOT format (render with graphviz).
            output_dir:    Custom trace base directory.
            project_dir:   Project root hint.

        Returns:
            Dict with node_count and either mermaid or dot string.
        """
        from crane.services.traceability_viz_service import TraceabilityVizService

        svc = _make_service(paper_path, output_dir, project_dir)
        vdir = _version_dir(svc, "viz")
        graph = svc.build_graph(vdir)
        viz = TraceabilityVizService()
        result: dict[str, Any] = {
            "paper_path": paper_path,
            "version_dir": str(vdir),
            "output_format": output_format,
            "node_count": len(graph.get_all_nodes()),
        }
        if output_format == "dot":
            result["dot"] = viz.get_dot(graph)
        else:
            result["mermaid"] = viz.get_mermaid(graph)
        return result

    # ------------------------------------------------------------------
    # 23. diff_trace_versions
    # ------------------------------------------------------------------

    @mcp.tool()
    def diff_trace_versions(
        paper_path: str,
        version_a: int | None = None,
        version_b: int | None = None,
        output_dir: str = "",
        project_dir: str = "",
    ) -> dict[str, Any]:
        """Compare two trace versions to see what changed.

        Compares item counts, chain coverage, and pending changes
        between two versions. Default: compare latest vs previous.

        Args:
            paper_path:  Path to .tex or .pdf file
            version_a:   First version number (default: latest - 1)
            version_b:   Second version number (default: latest)
            output_dir:  Custom trace base directory
            project_dir: Project root hint

        Returns:
            Dict with per-dimension deltas between versions.
        """
        import re as _re

        svc = _make_service(paper_path, output_dir, project_dir)
        trace_root = svc.trace_root

        if not trace_root.exists():
            return {"error": f"No trace directory found at {trace_root}"}

        existing = sorted([
            int(m.group(1))
            for d in trace_root.iterdir()
            if d.is_dir() and (m := _re.fullmatch(r"v(\d+)", d.name))
        ])

        if len(existing) < 1:
            return {"error": "No trace versions found"}

        if version_b is None:
            version_b = existing[-1]
        if version_a is None:
            version_a = existing[-2] if len(existing) >= 2 else existing[-1]

        vdir_a = trace_root / f"v{version_a}"
        vdir_b = trace_root / f"v{version_b}"

        def _index(vdir):
            if not vdir.exists():
                return None
            return svc.generate_index(vdir)

        idx_a = _index(vdir_a)
        idx_b = _index(vdir_b)

        if idx_a is None or idx_b is None:
            return {
                "error": f"Version {'a' if idx_a is None else 'b'} not found",
                "available_versions": existing,
            }

        def _delta(a, b):
            return b - a if isinstance(a, (int, float)) and isinstance(b, (int, float)) else None

        return {
            "version_a": version_a,
            "version_b": version_b,
            "delta": {
                "rq_count": _delta(idx_a.rq_count, idx_b.rq_count),
                "contribution_count": _delta(idx_a.contribution_count, idx_b.contribution_count),
                "experiment_count": _delta(idx_a.experiment_count, idx_b.experiment_count),
                "figure_table_count": _delta(idx_a.figure_table_count, idx_b.figure_table_count),
                "risk_count": _delta(idx_a.risk_count, idx_b.risk_count),
                "artifact_count": _delta(idx_a.artifact_count, idx_b.artifact_count),
                "pending_changes": _delta(idx_a.pending_changes, idx_b.pending_changes),
                "chain_coverage": _delta(idx_a.chain_coverage, idx_b.chain_coverage),
            },
            "summary_a": {
                "rq_count": idx_a.rq_count,
                "contribution_count": idx_a.contribution_count,
                "chain_coverage": idx_a.chain_coverage,
                "pending_changes": idx_a.pending_changes,
            },
            "summary_b": {
                "rq_count": idx_b.rq_count,
                "contribution_count": idx_b.contribution_count,
                "chain_coverage": idx_b.chain_coverage,
                "pending_changes": idx_b.pending_changes,
            },
        }

    # ------------------------------------------------------------------
    # 24. generate_rtm
    # ------------------------------------------------------------------

    @mcp.tool()
    def generate_rtm(
        paper_path: str,
        output_path: str = "",
        output_dir: str = "",
        project_dir: str = "",
    ) -> dict[str, Any]:
        """Generate a Requirements Traceability Matrix (RTM) in Markdown.

        Produces a cross-reference table linking every RQ to its
        supporting contributions, experiments, figures/tables, and risks.
        Useful as a submission checklist and for reviewer response letters.

        Args:
            paper_path:   Path to .tex or .pdf file
            output_path:  Optional path to save RTM markdown file
            output_dir:   Custom trace base directory
            project_dir:  Project root hint

        Returns:
            Dict with rtm_markdown string and coverage statistics.
        """
        import yaml as _yaml

        svc = _make_service(paper_path, output_dir, project_dir)
        vdir = _version_dir(svc, "status")

        def _load(fname):
            p = vdir / fname
            if not p.exists():
                return {}
            try:
                return _yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            except Exception:
                return {}

        rqs_data = _load("6_research_question.yaml")
        contrib_data = _load("1_contribution.yaml")
        exp_data = _load("2_experiment.yaml")
        ft_data = _load("5_figure_table_map.yaml")
        risk_data = _load("8_limitation_reviewer_risk.yaml")

        rqs = rqs_data.get("research_questions", [])
        contribs = contrib_data.get("contributions", [])
        exps = exp_data.get("experiments", [])
        fts = ft_data.get("entries", [])
        risks = risk_data.get("risks", [])

        lines = [
            "# Requirements Traceability Matrix (RTM)",
            "",
            f"Paper: `{paper_path}`  ",
            f"Trace: `{vdir}`",
            "",
            "## RQ → Contribution → Experiment → Figure/Table",
            "",
            "| RQ | Contributions | Experiments | Figures/Tables | Risks |",
            "|----|----|----|----|-----|",
        ]

        for rq in rqs:
            rq_id = rq.get("rq_id", "")
            related_c = [
                c.get("contribution_id", "")
                for c in contribs
                if rq_id in (c.get("rq_ids") or [])
            ]
            related_e = [
                e.get("exp_id", "")
                for e in exps
                if rq_id in (e.get("related_rqs") or [])
            ]
            related_ft = [
                ft.get("ft_id", "")
                for ft in fts
                if rq_id in (ft.get("related_rqs") or [])
            ]
            related_r = [
                r.get("risk_id", "")
                for r in risks
                if any(
                    rq_id in (rc or [])
                    for rc in [r.get("related_contributions", [])]
                )
            ]
            lines.append(
                f"| {rq_id} | {', '.join(related_c) or '—'} | "
                f"{', '.join(related_e) or '—'} | "
                f"{', '.join(related_ft) or '—'} | "
                f"{', '.join(related_r) or '—'} |"
            )

        lines += [
            "",
            "## Risk Register Summary",
            "",
            "| Risk ID | Severity | Status | Description |",
            "|---------|----------|--------|-------------|",
        ]
        for r in risks:
            lines.append(
                f"| {r.get('risk_id', '')} | {r.get('severity', '')} | "
                f"{r.get('status', '')} | {r.get('description', '')[:60]}... |"
            )

        rtm = "\n".join(lines)

        if output_path:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(rtm, encoding="utf-8")

        return {
            "paper_path": paper_path,
            "version_dir": str(vdir),
            "rq_count": len(rqs),
            "contribution_count": len(contribs),
            "experiment_count": len(exps),
            "figure_table_count": len(fts),
            "risk_count": len(risks),
            "rtm_markdown": rtm,
            "saved_to": output_path if output_path else None,
        }
