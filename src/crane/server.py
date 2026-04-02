"""
CRANE MCP Server entry point.

Usage:
    python -m crane.server
"""

import os
import warnings

from mcp.server.fastmcp import FastMCP  # pyright: ignore[reportMissingImports]

from .tools.citations import register_tools as register_citation_tools
from .tools.citation_graph import register_tools as register_citation_graph_tools
from .tools.evaluation_v2 import register_tools as register_evaluation_v2_tools
from .tools.ask_library import register_tools as register_ask_library_tools
from .tools.figures import register_tools as register_figure_tools
from .tools.journal_strategy import register_tools as register_journal_strategy_tools
from .tools.papers import register_tools as register_paper_tools
from .tools.pipeline import register_tools as register_pipeline_tools
from .tools.project import register_tools as register_project_tools
from .tools.q1_evaluation import register_tools as register_q1_evaluation_tools
from .tools.references import register_tools as register_reference_tools
from .tools.screening import register_tools as register_screening_tools
from .tools.section_review import register_tools as register_section_review_tools
from .tools.semantic_search import register_tools as register_semantic_search_tools
from .tools.submission_check import register_tools as register_submission_check_tools
from .tools.tasks import register_tools as register_task_tools
from .tools.workspace import register_tools as register_workspace_tools
from .tools.version_tools import register_tools as register_version_tools

mcp = FastMCP("crane", json_response=True)

register_project_tools(mcp)
register_paper_tools(mcp)
register_reference_tools(mcp)
register_semantic_search_tools(mcp)
register_citation_graph_tools(mcp)
register_ask_library_tools(mcp)
register_task_tools(mcp)
register_workspace_tools(mcp)
register_citation_tools(mcp)
register_figure_tools(mcp)
register_screening_tools(mcp)
register_section_review_tools(mcp)
register_q1_evaluation_tools(mcp)
register_journal_strategy_tools(mcp)
register_pipeline_tools(mcp)
register_submission_check_tools(mcp)
register_evaluation_v2_tools(mcp)
register_version_tools(mcp)


def _check_version_on_startup():
    """Check for updates on startup if CRANE_CHECK_VERSION_ON_START is set."""
    if os.environ.get("CRANE_CHECK_VERSION_ON_START", "true").lower() != "true":
        return
    try:
        from .services.version_check_service import VersionCheckService

        service = VersionCheckService()
        info = service.check_update()
        if info.is_update_available:
            warnings.warn(
                f"CRANE update available: {info.local_version} → {info.latest_version} "
                f"({info.update_type}). Run check_crane_version for details.",
                UserWarning,
            )
    except Exception:
        pass  # Never block startup on version check failures


_check_version_on_startup()


def main():
    """Run the CRANE MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
