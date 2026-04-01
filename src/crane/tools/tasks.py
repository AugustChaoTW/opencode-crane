"""
Task management tools via GitHub Issues + gh CLI.
Thin MCP wrapper around TaskService.
"""

from crane.services.task_service import TaskService
from crane.workspace import resolve_workspace


def register_tools(mcp):
    """Register task management tools with the MCP server."""

    def _get_service(project_dir: str | None) -> TaskService:
        """Get service instance for specified project_dir."""
        workspace = resolve_workspace(project_dir)
        return TaskService(workspace.project_root or project_dir)

    @mcp.tool()
    def create_task(
        title: str,
        body: str = "",
        phase: str = "",
        task_type: str = "",
        priority: str = "",
        kind: str = "",
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
        service = _get_service(project_dir)
        return service.create(
            title=title,
            body=body,
            phase=phase,
            task_type=task_type,
            priority=priority,
            kind=kind,
            milestone=milestone,
            assignee=assignee,
        )

    @mcp.tool()
    def list_tasks(
        phase: str = "",
        state: str = "open",
        task_type: str = "",
        milestone: str = "",
        limit: int = 30,
        kind: str = "",
        project_dir: str | None = None,
    ) -> list[dict[str, object]]:
        service = _get_service(project_dir)
        return service.list(phase, state, task_type, milestone, limit, kind=kind)

    @mcp.tool()
    def view_task(
        issue_number: int,
        project_dir: str | None = None,
    ) -> dict[str, object]:
        service = _get_service(project_dir)
        return service.view(issue_number)

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
        service = _get_service(project_dir)
        return service.update(
            issue_number=issue_number,
            title=title,
            add_labels=add_labels,
            remove_labels=remove_labels,
            milestone=milestone,
            assignee=assignee,
        )

    @mcp.tool()
    def report_progress(
        issue_number: int,
        comment: str,
        project_dir: str | None = None,
    ) -> str:
        service = _get_service(project_dir)
        return service.report_progress(issue_number, comment)

    @mcp.tool()
    def close_task(
        issue_number: int,
        reason: str = "completed",
        comment: str = "",
        project_dir: str | None = None,
    ) -> str:
        service = _get_service(project_dir)
        return service.close(issue_number, reason, comment)

    @mcp.tool()
    def get_milestone_progress(
        milestone_name: str = "",
        project_dir: str | None = None,
    ) -> list[dict[str, object]]:
        service = _get_service(project_dir)
        return service.get_milestone_progress(milestone_name)
