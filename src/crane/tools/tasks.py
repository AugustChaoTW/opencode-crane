"""
Task management tools via GitHub Issues + gh CLI.
create, list, view, update, report_progress, close, get_milestone_progress.
"""


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
    ) -> dict:
        """
        Create a research task (GitHub Issue).
        Automatically adds phase/type/priority labels.
        Returns {number, url}.
        """
        raise NotImplementedError

    @mcp.tool()
    def list_tasks(
        phase: str = "",
        state: str = "open",
        task_type: str = "",
        milestone: str = "",
        limit: int = 30,
    ) -> list[dict]:
        """
        List research tasks. Filter by phase, state, type, milestone.
        Returns JSON list from gh issue list.
        """
        raise NotImplementedError

    @mcp.tool()
    def view_task(issue_number: int) -> dict:
        """
        View a single task's full content including comment history.
        """
        raise NotImplementedError

    @mcp.tool()
    def update_task(
        issue_number: int,
        title: str = "",
        add_labels: list[str] | None = None,
        remove_labels: list[str] | None = None,
        milestone: str = "",
        assignee: str = "",
    ) -> str:
        """
        Update task title, labels, milestone, or assignee.
        """
        raise NotImplementedError

    @mcp.tool()
    def report_progress(issue_number: int, comment: str) -> str:
        """
        Post a progress comment on a task.
        Used to record findings, decisions, and results during research.
        """
        raise NotImplementedError

    @mcp.tool()
    def close_task(
        issue_number: int,
        reason: str = "completed",
        comment: str = "",
    ) -> str:
        """
        Close a task. Reason can be 'completed' or 'not_planned'.
        """
        raise NotImplementedError

    @mcp.tool()
    def get_milestone_progress(milestone_name: str = "") -> list[dict]:
        """
        Get research phase (milestone) progress statistics.
        If milestone_name is empty, returns all milestones.
        """
        raise NotImplementedError
