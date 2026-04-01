"""
Task management service via GitHub Issues.
Core business logic for issue CRUD operations using gh CLI.
"""

from __future__ import annotations

from typing import Any

from crane.utils.gh import gh, gh_json
from crane.utils.git import get_owner_repo


class TaskService:
    """Service for GitHub Issues-based task management."""

    VALID_KINDS = {"task", "todo"}

    def __init__(self, project_dir: str | None = None):
        self.project_dir = project_dir

    @classmethod
    def _normalize_kind(cls, item_type: str) -> str:
        kind = (item_type or "task").strip().lower()
        if kind not in cls.VALID_KINDS:
            raise ValueError("type must be 'task' or 'todo'")
        return kind

    def _build_labels(
        self,
        phase: str = "",
        task_type: str = "",
        priority: str = "",
        item_type: str = "task",
        include_kind: bool = False,
    ) -> list[str]:
        labels: list[str] = []
        if include_kind:
            labels.append(f"kind:{self._normalize_kind(item_type)}")
        if phase:
            labels.append(f"phase:{phase}")
        if task_type:
            labels.append(f"type:{task_type}")
        if priority:
            labels.append(f"priority:{priority}")
        return labels

    def create(
        self,
        title: str,
        body: str = "",
        phase: str = "",
        task_type: str = "",
        priority: str = "",
        milestone: str = "",
        assignee: str = "@me",
        type: str = "task",
        kind: str = "",
    ) -> dict[str, Any]:
        """
        Create a research task (GitHub Issue).

        Args:
            title: Issue title
            body: Issue description
            phase: Research phase (literature-review, proposal, experiment, writing, review)
            task_type: Task type (search, read, analysis, code, write)
            priority: Priority level (high, medium, low)
            milestone: Milestone name
            assignee: Assignee (default "@me")
            type: Backward-compatible default issue kind
            kind: Optional CRANE issue kind label ("task" or "todo")

        Returns:
            Dict with "number" and "url" keys.
        """
        issue_kind = kind or type
        labels = self._build_labels(
            phase=phase,
            task_type=task_type,
            priority=priority,
            item_type=issue_kind,
            include_kind=bool(kind),
        )

        args = ["issue", "create", "--title", title, "--body", body]
        if labels:
            args.extend(["--label", ",".join(labels)])
        if milestone:
            args.extend(["--milestone", milestone])
        if assignee:
            args.extend(["--assignee", assignee])

        url = gh(args, cwd=self.project_dir)
        number = int(url.rstrip("/").split("/")[-1]) if url else 0
        return {"number": number, "url": url}

    def list(
        self,
        phase: str = "",
        state: str = "open",
        task_type: str = "",
        milestone: str = "",
        limit: int = 30,
        type: str = "task",
        kind: str = "",
    ) -> list[dict[str, Any]]:
        """
        List research tasks with filtering.

        Args:
            phase: Filter by research phase
            state: Issue state ("open", "closed", "all")
            task_type: Filter by task type
            milestone: Filter by milestone name
            limit: Maximum results
            type: Backward-compatible default issue kind filter
            kind: Optional CRANE issue kind filter ("task" or "todo")

        Returns:
            List of task dicts.
        """
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

        issue_kind = kind or type
        labels = self._build_labels(
            phase=phase,
            task_type=task_type,
            item_type=issue_kind,
            include_kind=bool(kind),
        )
        if labels:
            args.extend(["--label", ",".join(labels)])
        if milestone:
            args.extend(["--milestone", milestone])

        tasks = gh_json(args, cwd=self.project_dir)
        return tasks if isinstance(tasks, list) else []

    def view(self, issue_number: int) -> dict[str, Any]:
        """
        View task details with comment history.

        Args:
            issue_number: GitHub issue number

        Returns:
            Complete task dict with comments.
        """
        data = gh_json(
            [
                "issue",
                "view",
                str(issue_number),
                "--json",
                "number,title,body,state,labels,milestone,assignees,comments,createdAt,updatedAt",
            ],
            cwd=self.project_dir,
        )
        return data if isinstance(data, dict) else {}

    def update(
        self,
        issue_number: int,
        title: str = "",
        add_labels: list[str] | None = None,
        remove_labels: list[str] | None = None,
        milestone: str = "",
        assignee: str = "",
    ) -> str:
        """
        Update task labels, milestone, or assignee.

        Args:
            issue_number: GitHub issue number
            title: New title (empty to keep current)
            add_labels: Labels to add
            remove_labels: Labels to remove
            milestone: Milestone name
            assignee: Assignee username

        Returns:
            Confirmation message.
        """
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

        gh(args, cwd=self.project_dir)
        return f"Task #{issue_number} updated"

    def report_progress(self, issue_number: int, comment: str) -> str:
        """
        Post progress comment on a task.

        Args:
            issue_number: GitHub issue number
            comment: Progress update text

        Returns:
            Confirmation message.
        """
        gh(["issue", "comment", str(issue_number), "--body", comment], cwd=self.project_dir)
        return f"Progress reported on task #{issue_number}"

    def close(
        self,
        issue_number: int,
        reason: str = "completed",
        comment: str = "",
    ) -> str:
        """
        Close a task with completion reason.

        Args:
            issue_number: GitHub issue number
            reason: Close reason ("completed" or "not_planned")
            comment: Optional closing comment

        Returns:
            Confirmation message.
        """
        args = ["issue", "close", str(issue_number), "--reason", reason]
        if comment:
            args.extend(["--comment", comment])
        gh(args, cwd=self.project_dir)
        return f"Task #{issue_number} closed ({reason})"

    def get_milestone_progress(self, milestone_name: str = "") -> list[dict[str, Any]]:
        """
        Get progress statistics for research phases.

        Args:
            milestone_name: Specific milestone name (empty for all)

        Returns:
            List of milestone progress dicts.
        """
        owner, repo = get_owner_repo(cwd=self.project_dir)
        milestones = gh_json(
            ["api", f"repos/{owner}/{repo}/milestones?state=all"],
            cwd=self.project_dir,
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
