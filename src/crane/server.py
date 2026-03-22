"""
CRANE MCP Server entry point.

Usage:
    python -m crane.server
"""

from mcp.server.fastmcp import FastMCP  # pyright: ignore[reportMissingImports]

from .tools.citations import register_tools as register_citation_tools
from .tools.papers import register_tools as register_paper_tools
from .tools.pipeline import register_tools as register_pipeline_tools
from .tools.project import register_tools as register_project_tools
from .tools.references import register_tools as register_reference_tools
from .tools.tasks import register_tools as register_task_tools
from .tools.workspace import register_tools as register_workspace_tools

mcp = FastMCP("crane", json_response=True)

register_project_tools(mcp)
register_paper_tools(mcp)
register_reference_tools(mcp)
register_task_tools(mcp)
register_workspace_tools(mcp)
register_citation_tools(mcp)
register_pipeline_tools(mcp)


def main():
    """Run the CRANE MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
