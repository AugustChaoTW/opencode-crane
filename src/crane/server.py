"""
CRANE MCP Server entry point.

Usage:
    python -m crane.server
"""

from mcp.server.fastmcp import FastMCP

from .tools.papers import register_tools as register_paper_tools
from .tools.project import register_tools as register_project_tools
from .tools.references import register_tools as register_reference_tools
from .tools.tasks import register_tools as register_task_tools

mcp = FastMCP("crane", json_response=True)

register_project_tools(mcp)
register_paper_tools(mcp)
register_reference_tools(mcp)
register_task_tools(mcp)


def main():
    """Run the CRANE MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
