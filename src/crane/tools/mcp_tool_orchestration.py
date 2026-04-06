from __future__ import annotations

from typing import Any

from crane.services.mcp_tool_orchestration_service import MCPToolOrchestrationService


def register_tools(mcp):
    service = MCPToolOrchestrationService()

    @mcp.tool()
    def orchestrate_research_tools(
        task_description: str,
        domain: str = "",
        available_tools: list[str] | None = None,
    ) -> dict[str, Any]:
        normalized_domain = domain.strip() or None
        return service.orchestrate_task(
            task_description=task_description,
            domain=normalized_domain,
            available_tools=available_tools,
        )
