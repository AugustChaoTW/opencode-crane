"""
Research workflow pipeline tool with checkpoints.
Orchestrates multi-step flows using shared Service layer.
"""

from datetime import date
from pathlib import Path
from typing import Any, cast

from crane.models.paper import AiAnnotations, Paper
from crane.services.paper_service import PaperService
from crane.services.reference_service import ReferenceService
from crane.services.task_service import TaskService
from crane.tools.project import DEFAULT_PHASES
from crane.workspace import resolve_workspace

LITERATURE_REVIEW_STEPS = ["search", "add", "download", "read", "annotate", "create_task"]
FULL_SETUP_STEPS = ["init", "create_starter_tasks"]
SUBMISSION_CHECK_STEPS = [
    "literature_review",
    "experiment_results",
    "framing_analysis",
    "paper_health_check",
]


def _phase_display_name(phase: str) -> str:
    return phase.replace("-", " ").title()


def _build_result(
    pipeline: str,
    status: str,
    completed_steps: list[str],
    artifacts_created: list[str],
    planned_steps: list[str] | None = None,
    failed_step: str | None = None,
    error: str = "",
    next_recommended_action: str = "",
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "pipeline": pipeline,
        "status": status,
        "completed_steps": completed_steps,
        "artifacts_created": artifacts_created,
    }
    if planned_steps is not None:
        result["planned_steps"] = planned_steps
    if failed_step is not None or status == "failed":
        result["failed_step"] = failed_step
        result["error"] = error
    if status in {"stopped", "failed"}:
        result["next_recommended_action"] = next_recommended_action
    return result


def _resolve_steps(
    base_steps: list[str],
    skip_steps: list[str],
    stop_after: str,
) -> list[str]:
    steps = [step for step in base_steps if step not in skip_steps]
    if stop_after and stop_after in steps:
        stop_idx = steps.index(stop_after)
        return steps[: stop_idx + 1]
    return steps


def _paper_key_from_entry(entry: dict[str, Any]) -> str:
    entry_id = str(entry.get("paper_id", ""))
    if not entry_id:
        raw_id = str(entry.get("url", "")).rstrip("/").split("/")[-1]
        entry_id = raw_id.split("v")[0]
    return entry_id.replace("/", "-").replace(".", "-")


def register_tools(mcp):
    """Register pipeline tools with the MCP server."""

    @mcp.tool()
    def run_pipeline(
        pipeline: str,
        topic: str = "",
        max_papers: int = 5,
        source: str = "arxiv",
        skip_steps: list[str] | None = None,
        stop_after: str = "",
        dry_run: bool = False,
        refs_dir: str = "references",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute a predefined research workflow pipeline.

        Pipelines:
        - "literature-review": search → add → download → read → annotate → create_task
        - "full-setup": init project → create starter tasks for each phase

        Parameters:
        - pipeline: Pipeline name
        - topic: Research topic / search query
        - max_papers: Max papers to process (literature-review)
        - source: Paper source (arxiv)
        - skip_steps: List of step names to skip (e.g. ["download", "annotate"])
        - stop_after: Stop after this step (e.g. "search" to only search)
        - dry_run: Preview steps without executing
        - refs_dir: References directory path
        - project_dir: Project root directory

        Returns dict with:
        - pipeline: Pipeline name
        - status: "completed" | "stopped" | "failed"
        - completed_steps: List of completed step names
        - artifacts_created: List of created files/issues
        - failed_step: Step name that failed (if any)
        - error: Error message (if any)
        - next_recommended_action: Suggested next step for the user
        """
        skip_steps = skip_steps or []
        completed_steps: list[str] = []
        artifacts_created: list[str] = []
        workspace = resolve_workspace(project_dir)
        project_root = Path(workspace.project_root)

        step_map = {
            "literature-review": LITERATURE_REVIEW_STEPS,
            "full-setup": FULL_SETUP_STEPS,
        }
        if pipeline not in step_map:
            return _build_result(
                pipeline=pipeline,
                status="failed",
                completed_steps=completed_steps,
                artifacts_created=artifacts_created,
                failed_step=None,
                error=f"Unknown pipeline: {pipeline}",
                next_recommended_action="Use 'literature-review' or 'full-setup'.",
            )

        steps_to_run = _resolve_steps(step_map[pipeline], skip_steps, stop_after)
        if dry_run:
            return _build_result(
                pipeline=pipeline,
                status="dry_run",
                completed_steps=completed_steps,
                artifacts_created=artifacts_created,
                planned_steps=steps_to_run,
            )

        refs_path = Path(refs_dir)
        if refs_path.is_absolute():
            resolved_refs_path = refs_path
        elif refs_path == Path("references"):
            resolved_refs_path = Path(workspace.references_dir)
        else:
            resolved_refs_path = project_root / refs_path

        # Initialize services
        paper_svc = PaperService()
        ref_svc = ReferenceService(str(resolved_refs_path))
        task_svc = TaskService(workspace.project_root)

        # Ensure directories exist
        papers_dir = resolved_refs_path / "papers"
        pdfs_dir = resolved_refs_path / "pdfs"
        bib_path = resolved_refs_path / "bibliography.bib"
        papers_dir.mkdir(parents=True, exist_ok=True)
        pdfs_dir.mkdir(parents=True, exist_ok=True)
        bib_path.parent.mkdir(parents=True, exist_ok=True)
        bib_path.touch(exist_ok=True)

        searched_papers: list[dict[str, Any]] = []

        for step in step_map[pipeline]:
            if step in skip_steps:
                continue
            try:
                if pipeline == "literature-review":
                    if step == "search":
                        searched_papers = paper_svc.search(topic, max_papers, source)

                    elif step == "add":
                        for paper_data in searched_papers:
                            key = _paper_key_from_entry(paper_data)
                            year = int(paper_data.get("year", 0) or 0)
                            if year <= 0:
                                year = date.today().year
                            paper = Paper(
                                key=key,
                                title=str(paper_data.get("title", "")),
                                authors=list(cast(list[str], paper_data.get("authors", []))),
                                year=year,
                                doi=str(paper_data.get("doi", "")),
                                venue="arXiv",
                                url=str(paper_data.get("url", "")),
                                pdf_url=str(paper_data.get("pdf_url", "")),
                                abstract=str(paper_data.get("abstract", "")),
                                source="arxiv",
                                paper_type="conference",
                                categories=list(cast(list[str], paper_data.get("categories", []))),
                            )
                            paper.bibtex = paper.to_bibtex()
                            from crane.utils.bibtex import append_entry
                            from crane.utils.yaml_io import write_paper_yaml

                            yaml_path = write_paper_yaml(
                                str(papers_dir),
                                key,
                                paper.to_yaml_dict(),
                            )
                            append_entry(str(bib_path), paper.bibtex)
                            artifacts_created.extend([yaml_path, str(bib_path)])

                    elif step == "download":
                        for paper_data in searched_papers:
                            paper_id = str(paper_data.get("paper_id", ""))
                            if not paper_id:
                                paper_id = _paper_key_from_entry(paper_data)
                            try:
                                path = paper_svc.download(paper_id, str(pdfs_dir))
                                artifacts_created.append(str(path))
                            except Exception:
                                continue

                    elif step == "read":
                        for paper_data in searched_papers:
                            paper_id = str(paper_data.get("paper_id", ""))
                            if not paper_id:
                                paper_id = _paper_key_from_entry(paper_data)
                            pdf_path = pdfs_dir / f"{paper_id}.pdf"
                            if not pdf_path.exists():
                                continue
                            text = paper_svc.read(paper_id, str(pdfs_dir))
                            text_path = pdf_path.with_suffix(".txt")
                            text_path.write_text(text, encoding="utf-8")
                            artifacts_created.append(str(text_path))

                    elif step == "annotate":
                        for paper_data in searched_papers:
                            key = _paper_key_from_entry(paper_data)
                            data = ref_svc.get(key)
                            paper = Paper.from_yaml_dict(data)
                            summary = str(paper_data.get("abstract", "")).strip()
                            paper.ai_annotations = AiAnnotations(
                                summary=summary,
                                key_contributions=[],
                                methodology="",
                                relevance_notes="Auto-generated from abstract.",
                                tags=["auto", "pipeline"],
                                related_issues=[],
                                added_date=date.today().isoformat(),
                            )
                            from crane.utils.yaml_io import write_paper_yaml

                            yaml_path = write_paper_yaml(str(papers_dir), key, paper.to_yaml_dict())
                            artifacts_created.append(yaml_path)

                    elif step == "create_task":
                        result = task_svc.create(
                            title=f"[LIT] Literature review: {topic}",
                            body=f"Automated literature-review pipeline for topic: {topic}",
                            phase="literature-review",
                            task_type="search",
                            priority="medium",
                        )
                        if result.get("url"):
                            artifacts_created.append(result["url"])

                elif pipeline == "full-setup":
                    if step == "init":
                        from crane.tools.project import (
                            ISSUE_TEMPLATE_CONTENT,
                            PHASE_COLORS,
                            PRIORITY_LABEL_COLORS,
                            TYPE_LABEL_COLORS,
                        )
                        from crane.utils.gh import gh

                        selected_phases = DEFAULT_PHASES
                        for phase in selected_phases:
                            gh(
                                [
                                    "label",
                                    "create",
                                    f"phase:{phase}",
                                    "--color",
                                    PHASE_COLORS.get(phase, "BFDADC"),
                                    "--force",
                                ],
                                cwd=workspace.project_root,
                            )
                        for task_type, color in TYPE_LABEL_COLORS.items():
                            gh(
                                [
                                    "label",
                                    "create",
                                    f"type:{task_type}",
                                    "--color",
                                    color,
                                    "--force",
                                ],
                                cwd=workspace.project_root,
                            )
                        for priority, color in PRIORITY_LABEL_COLORS.items():
                            gh(
                                [
                                    "label",
                                    "create",
                                    f"priority:{priority}",
                                    "--color",
                                    color,
                                    "--force",
                                ],
                                cwd=workspace.project_root,
                            )

                        owner = workspace.owner
                        repo = workspace.repo_name
                        for idx, phase in enumerate(selected_phases, start=1):
                            gh(
                                [
                                    "api",
                                    "-X",
                                    "POST",
                                    f"repos/{owner}/{repo}/milestones",
                                    "-f",
                                    f"title=Phase {idx}: {_phase_display_name(phase)}",
                                ],
                                cwd=workspace.project_root,
                            )

                        root = project_root
                        references_dir = resolved_refs_path
                        (references_dir / "papers").mkdir(parents=True, exist_ok=True)
                        (references_dir / "pdfs").mkdir(parents=True, exist_ok=True)
                        bibliography_path = references_dir / "bibliography.bib"
                        bibliography_path.parent.mkdir(parents=True, exist_ok=True)
                        bibliography_path.touch(exist_ok=True)
                        issue_template_path = (
                            root / ".github" / "ISSUE_TEMPLATE" / "research-task.yml"
                        )
                        issue_template_path.parent.mkdir(parents=True, exist_ok=True)
                        issue_template_path.write_text(
                            ISSUE_TEMPLATE_CONTENT,
                            encoding="utf-8",
                        )
                        artifacts_created.extend(
                            [
                                str(references_dir / "papers"),
                                str(references_dir / "pdfs"),
                                str(bibliography_path),
                                str(issue_template_path),
                            ]
                        )

                    elif step == "create_starter_tasks":
                        for phase in DEFAULT_PHASES:
                            result = task_svc.create(
                                title=f"[{phase.upper().replace('-', ' ')}] Starter task",
                                body=(
                                    f"Initial task for phase '{phase}'.\n\n"
                                    "Define objectives, deliverables, and first concrete actions."
                                ),
                                phase=phase,
                                task_type="analysis",
                                priority="medium",
                            )
                            if result.get("url"):
                                artifacts_created.append(result["url"])

                completed_steps.append(step)

                if stop_after and step == stop_after:
                    return _build_result(
                        pipeline=pipeline,
                        status="stopped",
                        completed_steps=completed_steps,
                        artifacts_created=artifacts_created,
                        next_recommended_action=(
                            "Resume the pipeline without stop_after to continue remaining steps."
                        ),
                    )

                if pipeline == "literature-review" and step == "search" and not searched_papers:
                    return _build_result(
                        pipeline=pipeline,
                        status="completed",
                        completed_steps=completed_steps,
                        artifacts_created=artifacts_created,
                    )

            except Exception as exc:
                return _build_result(
                    pipeline=pipeline,
                    status="failed",
                    completed_steps=completed_steps,
                    artifacts_created=artifacts_created,
                    failed_step=step,
                    error=str(exc),
                    next_recommended_action=(
                        "Inspect the error and rerun with"
                        " skip_steps or dry_run for troubleshooting."
                    ),
                )

        return _build_result(
            pipeline=pipeline,
            status="completed",
            completed_steps=completed_steps,
            artifacts_created=artifacts_created,
        )
