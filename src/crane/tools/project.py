"""
Project management tools: init_research, get_project_info
"""

from pathlib import Path
from typing import Any

from crane.utils import git
from crane.utils.gh import gh, gh_json
from crane.utils.yaml_io import list_paper_keys

DEFAULT_PHASES = [
    "literature-review",
    "proposal",
    "experiment",
    "writing",
    "review",
]

PHASE_COLORS = {
    "literature-review": "0E8A16",
    "proposal": "1D76DB",
    "experiment": "D93F0B",
    "writing": "FBCA04",
    "review": "6F42C1",
}

TYPE_LABEL_COLORS = {
    "search": "C5DEF5",
    "read": "BFD4F2",
    "analysis": "D4C5F9",
    "code": "F9D0C4",
    "write": "FEF2C0",
}

PRIORITY_LABEL_COLORS = {
    "high": "D93F0B",
    "medium": "FBCA04",
    "low": "0E8A16",
}

KIND_LABEL_COLORS = {
    "task": "5319E7",
    "todo": "1D76DB",
}


def _phase_display_name(phase: str) -> str:
    return phase.replace("-", " ").title()


ISSUE_TEMPLATE_CONTENT = """name: Research Task
description: Create a research task
title: "[{PHASE}] "
labels: ["research"]
body:
  - type: dropdown
    id: phase
    attributes:
      label: Research phase
      options:
        - Literature Review
        - Proposal
        - Experiment
        - Writing
        - Review
    validations:
      required: true

  - type: dropdown
    id: task_type
    attributes:
      label: Task type
      options:
        - search
        - read
        - analysis
        - code
        - write
    validations:
      required: true

  - type: textarea
    id: objective
    attributes:
      label: Objective
      placeholder: Describe the goal of this task...
    validations:
      required: true
"""


def register_tools(mcp):
    """Register project management tools with the MCP server."""

    @mcp.tool()
    def init_research(
        phases: list[str] | None = None,
        project_dir: str | None = None,
    ) -> str:
        """
        Initialize the current GitHub repo as a research project.
        Creates phase/type/priority/kind labels, milestones, references/ directory,
        and .github/ISSUE_TEMPLATE/research-task.yml.
        """
        selected_phases = phases or DEFAULT_PHASES

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
                cwd=project_dir,
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
                cwd=project_dir,
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
                cwd=project_dir,
            )

        for kind, color in KIND_LABEL_COLORS.items():
            gh(
                [
                    "label",
                    "create",
                    f"kind:{kind}",
                    "--color",
                    color,
                    "--force",
                ],
                cwd=project_dir,
            )

        owner, repo = git.get_owner_repo(cwd=project_dir)
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
                cwd=project_dir,
            )

        root = Path(project_dir) if project_dir else Path.cwd()
        references_dir = root / "references"
        (references_dir / "papers").mkdir(parents=True, exist_ok=True)
        (references_dir / "pdfs").mkdir(parents=True, exist_ok=True)

        bibliography_path = references_dir / "bibliography.bib"
        bibliography_path.parent.mkdir(parents=True, exist_ok=True)
        bibliography_path.touch(exist_ok=True)

        issue_template_path = root / ".github" / "ISSUE_TEMPLATE" / "research-task.yml"
        issue_template_path.parent.mkdir(parents=True, exist_ok=True)
        issue_template_path.write_text(ISSUE_TEMPLATE_CONTENT, encoding="utf-8")

        return (
            f"Initialized research project in {root}: "
            f"{len(selected_phases)} phase labels, "
            f"{len(TYPE_LABEL_COLORS)} type labels, "
            f"{len(PRIORITY_LABEL_COLORS)} priority labels, "
            f"{len(selected_phases)} milestones, references/ structure, and issue template."
        )

    @mcp.tool()
    def get_project_info(project_dir: str | None = None) -> dict[str, Any]:
        owner, repo = git.get_owner_repo(cwd=project_dir)
        branch = git.get_current_branch(cwd=project_dir)
        last_commit = git.get_last_commit(cwd=project_dir)

        root = Path(project_dir) if project_dir else Path.cwd()
        references_count = len(list_paper_keys(str(root / "references" / "papers")))

        milestone_data = gh_json(["api", f"repos/{owner}/{repo}/milestones"], cwd=project_dir)
        milestones: list[dict[str, Any]] = []
        if isinstance(milestone_data, list):
            for milestone in milestone_data:
                if not isinstance(milestone, dict):
                    continue
                open_issues = int(milestone.get("open_issues", 0))
                closed_issues = int(milestone.get("closed_issues", 0))
                total = open_issues + closed_issues
                progress = int((closed_issues / total) * 100) if total > 0 else 0
                milestones.append(
                    {
                        "name": milestone.get("title", ""),
                        "open": open_issues,
                        "closed": closed_issues,
                        "progress": f"{progress}%",
                    }
                )

        return {
            "repo": f"{owner}/{repo}",
            "branch": branch,
            "last_commit": last_commit,
            "references_count": references_count,
            "milestones": milestones,
        }
