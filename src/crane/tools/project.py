"""
Project management tools: init_research, get_project_info
"""


def register_tools(mcp):
    """Register project management tools with the MCP server."""

    @mcp.tool()
    def init_research(
        phases: list[str] | None = None,
    ) -> str:
        """
        Initialize the current GitHub repo as a research project.
        Creates phase/type/priority labels, milestones, references/ directory,
        and .github/ISSUE_TEMPLATE/research-task.yml.
        """
        raise NotImplementedError

    @mcp.tool()
    def get_project_info() -> dict:
        """
        Get current research project info: repo name, remote URL,
        current branch, recent commit, milestone progress, reference count.
        """
        raise NotImplementedError
