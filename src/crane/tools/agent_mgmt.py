"""MCP tools for agent listing, lookup, and memory management."""

from __future__ import annotations

from typing import Any

from crane.services.agent_memory_service import AgentMemoryService
from crane.services.agent_service import AgentService


def register_tools(mcp):
    """Register agent management tools with the MCP server."""

    @mcp.tool()
    def list_agents(project_dir: str | None = None) -> dict[str, Any]:
        """List all agents grouped by source with override status."""
        service = AgentService(project_dir=project_dir)
        return service.list_agents()

    @mcp.tool()
    def get_agent(name: str, project_dir: str | None = None) -> dict[str, Any] | None:
        """Get one active agent by name after override resolution."""
        service = AgentService(project_dir=project_dir)
        return service.get_agent(name)

    @mcp.tool()
    def get_agent_memory(agent_name: str, project_dir: str | None = None) -> list[dict[str, Any]]:
        """Get all memory entries for one agent."""
        service = AgentMemoryService(project_dir=project_dir)
        return service.get_agent_memory(agent_name)

    @mcp.tool()
    def add_agent_memory(
        agent_name: str,
        content: str,
        source: str = "manual",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Add one memory entry for an agent."""
        service = AgentMemoryService(project_dir=project_dir)
        return service.add_agent_memory(agent_name=agent_name, content=content, source=source)

    @mcp.tool()
    def clear_agent_memory(agent_name: str, project_dir: str | None = None) -> dict[str, Any]:
        """Clear all stored memory entries for an agent."""
        service = AgentMemoryService(project_dir=project_dir)
        return service.clear_agent_memory(agent_name)
