from __future__ import annotations

from pathlib import Path
from typing import Any

from crane.services.reference_service import ReferenceService
from crane.services.task_service import TaskService
from crane.utils.gh import gh_json
from crane.workspace import resolve_workspace

# Maps tool name → list of capability checks required
_TOOL_PREREQUISITES: dict[str, list[str]] = {
    "semantic_search": ["embeddings"],
    "get_research_clusters": ["embeddings"],
    "visualize_citations": ["embeddings"],
    "ask_library": ["chunks"],
    "evaluate_paper_v2": ["paper_file"],
    "review_paper_sections": ["paper_file"],
    "analyze_paper_for_journal": ["paper_file"],
    "match_journal_v2": ["paper_file"],
    "section_review": ["paper_file"],
}


def _list_open_issues(task_service: TaskService, label: str) -> list[dict[str, Any]]:
    issues = gh_json(
        [
            "issue",
            "list",
            "--state",
            "open",
            "--label",
            label,
            "--limit",
            "100",
            "--json",
            "number,title,url,labels,milestone",
        ],
        cwd=task_service.project_dir,
    )
    if not isinstance(issues, list):
        return []

    result: list[dict[str, Any]] = []
    for item in issues:
        if not isinstance(item, dict):
            continue

        milestone = item.get("milestone")
        labels = item.get("labels", [])
        result.append(
            {
                "number": item.get("number", 0),
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "milestone": milestone.get("title", "") if isinstance(milestone, dict) else "",
                "labels": [entry.get("name", "") for entry in labels if isinstance(entry, dict)],
            }
        )
    return result


def _reference_counts(references_dir: str) -> dict[str, Any]:
    refs_path = Path(references_dir)
    if not refs_path.exists():
        return {
            "papers": 0,
            "pdfs": 0,
            "bibliography": False,
        }

    service = ReferenceService(refs_path)
    return {
        "papers": len(service.get_all_keys()),
        "pdfs": len(list(service.pdfs_dir.glob("*.pdf"))),
        "bibliography": service.bib_path.exists(),
    }


def _check_capabilities(references_dir: str) -> dict[str, Any]:
    """Check which CRANE capabilities are available in the workspace."""
    refs_path = Path(references_dir)
    capabilities: dict[str, Any] = {}

    # Semantic search: needs embeddings.yaml
    embeddings_file = refs_path / "embeddings.yaml"
    paper_count = 0
    if refs_path.exists():
        papers_dir = refs_path / "papers"
        if papers_dir.exists():
            paper_count = len(list(papers_dir.glob("*.yaml")))
    capabilities["semantic_search"] = {
        "available": embeddings_file.exists(),
        "paper_count": paper_count,
        **({"fix_with": "build_embeddings"} if not embeddings_file.exists() else {}),
    }

    # Ask library: needs at least one chunks/<key>/chunks.yaml
    chunks_dir = refs_path / "chunks"
    has_chunks = chunks_dir.exists() and any(chunks_dir.glob("*/chunks.yaml"))
    capabilities["ask_library"] = {
        "available": has_chunks,
        **({"fix_with": "chunk_papers"} if not has_chunks else {}),
    }

    # Citation check: needs bibliography.bib and at least one paper YAML
    bib_file = refs_path / "bibliography.bib"
    capabilities["citation_check"] = {
        "available": bib_file.exists() and paper_count > 0,
        "reference_count": paper_count,
    }

    # Paper traceability: check for _paper_trace/ dirs in project
    from crane.models.traceability import TRACE_DIR_NAME

    trace_dirs = list(refs_path.parent.rglob(TRACE_DIR_NAME)) if refs_path.parent.exists() else []
    has_trace = len(trace_dirs) > 0
    capabilities["traceability"] = {
        "available": True,
        "traced_papers": len(trace_dirs),
        "trigger": "Say 'trace this paper', 'do paper trace', or '整理這篇研究' to start",
        **({"fix_with": "trace_paper"} if not has_trace else {}),
    }

    return capabilities


def register_tools(mcp):
    @mcp.tool()
    def workspace_status(project_dir: str | None = None) -> dict[str, Any]:
        """
        Return a workspace overview for the current or specified project.

        Includes capabilities showing which tools are ready to use (semantic_search,
        ask_library, citation_check) and suggested_next_actions for onboarding.

        Args:
            project_dir: Project root directory (auto-detected from git if None)

        Returns:
            Dict with workspace info, references, tasks, todos, milestones,
            capabilities, and suggested_next_actions.
        """
        workspace = resolve_workspace(project_dir)
        task_service = TaskService(workspace.project_root)
        capabilities = _check_capabilities(workspace.references_dir)

        suggested: list[str] = []
        if not capabilities["semantic_search"]["available"]:
            suggested.append("Run build_embeddings() to enable semantic_search")
        if not capabilities["ask_library"]["available"]:
            suggested.append("Run chunk_papers() to enable ask_library Q&A")
        if capabilities["citation_check"]["reference_count"] == 0:
            suggested.append(
                "Run run_pipeline('literature-review', topic='...') to start your library"
            )

        return {
            "workspace": workspace.to_dict(),
            "references": _reference_counts(workspace.references_dir),
            "tasks": _list_open_issues(task_service, "kind:task"),
            "todos": _list_open_issues(task_service, "kind:todo"),
            "milestones": task_service.get_milestone_progress(),
            "capabilities": capabilities,
            "suggested_next_actions": suggested,
        }

    @mcp.tool()
    def check_prerequisites(
        tool_name: str,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """
        Check if all prerequisites are met before calling a tool.

        Use this before calling tools with known dependencies to avoid failed calls
        and wasted round-trips. Returns a ready flag plus a list of what is missing
        and how to fix each item.

        Tools with prerequisites:
        - semantic_search / semantic_search_by_paper / get_research_clusters
          → requires build_embeddings() to have been run
        - ask_library
          → requires chunk_papers() to have been run
        - evaluate_paper_v2 / review_paper_sections / analyze_paper_for_journal / match_journal_v2
          → requires at least one PDF in the workspace

        Args:
            tool_name: Name of the tool you plan to call
            project_dir: Project root directory (auto-detected from git if None)

        Returns:
            {
                "tool": str,
                "ready": bool,
                "missing": [{"name": str, "fix_with": str, "reason": str}],
                "warnings": [str]
            }
        """
        workspace = resolve_workspace(project_dir)
        refs_path = Path(workspace.references_dir)
        missing: list[dict[str, str]] = []
        warnings: list[str] = []

        required_checks = _TOOL_PREREQUISITES.get(tool_name, [])

        if "embeddings" in required_checks:
            embeddings_file = refs_path / "embeddings.yaml"
            if not embeddings_file.exists():
                missing.append({
                    "name": "embeddings",
                    "fix_with": "build_embeddings",
                    "reason": "Vector index not found — embeddings.yaml does not exist",
                })

        if "chunks" in required_checks:
            chunks_dir = refs_path / "chunks"
            has_chunks = chunks_dir.exists() and any(chunks_dir.glob("*/chunks.yaml"))
            if not has_chunks:
                missing.append({
                    "name": "paper_chunks",
                    "fix_with": "chunk_papers",
                    "reason": "No chunked papers found — chunks/ directory is empty",
                })

        if "paper_file" in required_checks:
            pdfs_dir = refs_path / "pdfs"
            has_pdfs = pdfs_dir.exists() and any(pdfs_dir.glob("*.pdf"))
            if not has_pdfs:
                missing.append({
                    "name": "paper_file",
                    "fix_with": "download_paper",
                    "reason": "No PDF files found in references/pdfs/",
                })

        if tool_name not in _TOOL_PREREQUISITES:
            warnings.append(
                f"No prerequisite checks defined for '{tool_name}'. "
                "The tool may still have runtime requirements."
            )

        return {
            "tool": tool_name,
            "ready": len(missing) == 0,
            "missing": missing,
            "warnings": warnings,
        }
