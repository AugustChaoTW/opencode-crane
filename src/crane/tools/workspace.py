from __future__ import annotations

from pathlib import Path
from typing import Any

from crane.services.reference_service import ReferenceService
from crane.services.task_service import TaskService
from crane.utils.gh import gh_json
from crane.workspace import resolve_workspace


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


def register_tools(mcp):
    @mcp.tool()
    def workspace_status(project_dir: str | None = None) -> dict[str, Any]:
        """Return a workspace overview for the current or specified project."""
        workspace = resolve_workspace(project_dir)
        task_service = TaskService(workspace.project_root)

        return {
            "workspace": workspace.to_dict(),
            "references": _reference_counts(workspace.references_dir),
            "tasks": _list_open_issues(task_service, "kind:task"),
            "todos": _list_open_issues(task_service, "kind:todo"),
            "milestones": task_service.get_milestone_progress(),
        }
