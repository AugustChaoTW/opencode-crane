"""
Task management tools via GitHub Issues + gh CLI.
create, list, view, update, report_progress, close, get_milestone_progress.
"""

from crane.utils.gh import gh, gh_json
from crane.utils.git import get_owner_repo


def register_tools(mcp):
    """Register task management tools with the MCP server."""

    @mcp.tool()
    def create_task(
        title: str,
        body: str = "",
        phase: str = "",
        task_type: str = "",
        priority: str = "",
        milestone: str = "",
        assignee: str = "@me",
        project_dir: str | None = None,
    ) -> dict[str, object]:
        """
        Create a research task (GitHub Issue).
        Automatically adds phase/type/priority labels.
        Returns {number, url}.

        Args:
            project_dir: Project root directory. When provided, gh commands
                target the git repo in that directory instead of the server CWD.
                Critical for cross-project isolation when MCP server is shared.
        """
        labels: list[str] = []
        if phase:
            labels.append(f"phase:{phase}")
        if task_type:
            labels.append(f"type:{task_type}")
        if priority:
            labels.append(f"priority:{priority}")

        args = ["issue", "create", "--title", title, "--body", body]
        if labels:
            args.extend(["--label", ",".join(labels)])
        if milestone:
            args.extend(["--milestone", milestone])
        if assignee:
            args.extend(["--assignee", assignee])

        url = gh(args, cwd=project_dir)
        number = int(url.rstrip("/").split("/")[-1]) if url else 0
        return {
            "number": number,
            "url": url,
        }

    @mcp.tool()
    def list_tasks(
        phase: str = "",
        state: str = "open",
        task_type: str = "",
        milestone: str = "",
        limit: int = 30,
        project_dir: str | None = None,
    ) -> list[dict[str, object]]:
        args = [
            "issue",
            "list",
            "--json",
            "number,title,labels,state,assignees,milestone,createdAt,updatedAt",
            "--state",
            state,
            "--limit",
            str(limit),
        ]

        labels: list[str] = []
        if phase:
            labels.append(f"phase:{phase}")
        if task_type:
            labels.append(f"type:{task_type}")
        if labels:
            args.extend(["--label", ",".join(labels)])
        if milestone:
            args.extend(["--milestone", milestone])

        tasks = gh_json(args, cwd=project_dir)
        return tasks if isinstance(tasks, list) else []

    @mcp.tool()
    def view_task(
        issue_number: int,
        project_dir: str | None = None,
    ) -> dict[str, object]:
        data = gh_json(
            [
                "issue",
                "view",
                str(issue_number),
                "--json",
                "number,title,body,state,labels,milestone,assignees,comments,createdAt,updatedAt",
            ],
            cwd=project_dir,
        )
        return data if isinstance(data, dict) else {}

    @mcp.tool()
    def update_task(
        issue_number: int,
        title: str = "",
        add_labels: list[str] | None = None,
        remove_labels: list[str] | None = None,
        milestone: str = "",
        assignee: str = "",
        project_dir: str | None = None,
    ) -> str:
        args = ["issue", "edit", str(issue_number)]

        if title:
            args.extend(["--title", title])
        if add_labels:
            args.extend(["--add-label", ",".join(add_labels)])
        if remove_labels:
            args.extend(["--remove-label", ",".join(remove_labels)])
        if milestone:
            args.extend(["--milestone", milestone])
        if assignee:
            args.extend(["--add-assignee", assignee])

        gh(args, cwd=project_dir)
        return f"Task #{issue_number} updated"

    @mcp.tool()
    def report_progress(
        issue_number: int,
        comment: str,
        project_dir: str | None = None,
    ) -> str:
        gh(["issue", "comment", str(issue_number), "--body", comment], cwd=project_dir)
        return f"Progress reported on task #{issue_number}"

    @mcp.tool()
    def close_task(
        issue_number: int,
        reason: str = "completed",
        comment: str = "",
        project_dir: str | None = None,
    ) -> str:
        args = ["issue", "close", str(issue_number), "--reason", reason]
        if comment:
            args.extend(["--comment", comment])
        gh(args, cwd=project_dir)
        return f"Task #{issue_number} closed ({reason})"

    @mcp.tool()
    def get_milestone_progress(
        milestone_name: str = "",
        project_dir: str | None = None,
    ) -> list[dict[str, object]]:
        owner, repo = get_owner_repo(cwd=project_dir)
        milestones = gh_json(
            ["api", f"repos/{owner}/{repo}/milestones?state=all"],
            cwd=project_dir,
        )
        if not isinstance(milestones, list):
            return []

        progress = []
        for item in milestones:
            title = item.get("title", "")
            if milestone_name and title != milestone_name:
                continue

            open_issues = item.get("open_issues", 0)
            closed_issues = item.get("closed_issues", 0)
            total = open_issues + closed_issues
            pct = 0.0 if total == 0 else round((closed_issues / total) * 100, 1)

            progress.append(
                {
                    "title": title,
                    "open": open_issues,
                    "closed": closed_issues,
                    "progress": pct,
                }
            )

        return progress
