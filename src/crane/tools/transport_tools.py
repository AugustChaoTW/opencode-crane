from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from ..services.session_service import SessionService
from ..services.sse_transport_service import SSETransportService
from ..workspace import resolve_workspace

_SSE_SERVICES: dict[str, SSETransportService] = {}
_SESSION_SERVICES: dict[str, SessionService] = {}
_BRIDGE_SERVICES: dict[str, Any] = {}


def _resolve_project_root(project_dir: str | None) -> str:
    try:
        return resolve_workspace(project_dir).project_root
    except ValueError:
        if project_dir:
            return str(Path(project_dir).resolve())
        raise


def _get_sse_service(project_dir: str | None) -> SSETransportService:
    project_root = _resolve_project_root(project_dir)
    service = _SSE_SERVICES.get(project_root)
    if service is None:
        service = SSETransportService(project_root)
        _SSE_SERVICES[project_root] = service
    return service


def _get_session_service(project_dir: str | None) -> SessionService:
    project_root = _resolve_project_root(project_dir)
    service = _SESSION_SERVICES.get(project_root)
    if service is None:
        service = SessionService(project_root)
        _SESSION_SERVICES[project_root] = service
    return service


def _default_tool_executor(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    return {
        "error": "remote_bridge_execution_not_configured",
        "tool_name": tool_name,
        "args": args,
    }


def _get_bridge_service(project_dir: str | None) -> Any:
    project_root = _resolve_project_root(project_dir)
    service = _BRIDGE_SERVICES.get(project_root)
    if service is None:
        module = importlib.import_module("crane.services.remote_bridge_service")
        service = module.RemoteBridgeService(project_root)
        service.set_tool_executor(_default_tool_executor)
        _BRIDGE_SERVICES[project_root] = service
    return service


def register_tools(mcp):
    @mcp.tool()
    def transport_control(
        transport: str,
        action: str,
        host: str = "127.0.0.1",
        port: int | None = None,
        jwt_secret: str = "",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Start, stop, or query the status of a transport server.

        Consolidates start/stop/status for both SSE and Remote Bridge
        into a single tool.

        Args:
            transport:   "sse"    — Server-Sent Events server (default port 8765).
                         "bridge" — Remote Bridge server    (default port 8766).
            action:      "start"  — Start the server.
                         "stop"   — Stop the server.
                         "status" — Query current server status.
            host:        Bind host (start action only, default 127.0.0.1).
            port:        Bind port (start action only).
                         Defaults: sse=8765, bridge=8766.
            jwt_secret:  JWT signing secret (bridge start only).
            project_dir: Project root directory.

        Returns:
            Transport-specific status dict.
        """
        if transport == "sse":
            svc = _get_sse_service(project_dir)
            if action == "start":
                return svc.start_server(host=host, port=port or 8765)
            if action == "stop":
                return svc.stop_server()
            return svc.get_server_status()

        if transport == "bridge":
            svc = _get_bridge_service(project_dir)
            if action == "start":
                return svc.start_bridge(host=host, port=port or 8766, jwt_secret=jwt_secret)
            if action == "stop":
                return svc.stop_bridge()
            return svc.get_bridge_status()

        return {"error": f"Unknown transport '{transport}'. Use 'sse' or 'bridge'."}

    @mcp.tool()
    def broadcast_sse_event(
        event_type: str,
        data: dict,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Broadcast an event to all connected SSE clients."""
        service = _get_sse_service(project_dir)
        return service.broadcast_event(event_type=event_type, data=data)

    @mcp.tool()
    def create_session(
        name: str,
        context: dict | None = None,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Create a new named session for context persistence."""
        service = _get_session_service(project_dir)
        session_id = service.create_session(name=name, context=context)
        return {"session_id": session_id}

    @mcp.tool()
    def save_session(
        session_id: str,
        messages: list[dict],
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Save messages to an existing session."""
        service = _get_session_service(project_dir)
        return service.save_session(session_id=session_id, messages=messages)

    @mcp.tool()
    def load_session(session_id: str, project_dir: str | None = None) -> dict[str, Any]:
        """Load a session by ID."""
        service = _get_session_service(project_dir)
        return service.load_session(session_id=session_id)

    @mcp.tool()
    def list_sessions(limit: int = 20, project_dir: str | None = None) -> list[dict[str, Any]]:
        """List recent sessions."""
        service = _get_session_service(project_dir)
        return service.list_sessions(limit=limit)

    @mcp.tool()
    def delete_session(session_id: str, project_dir: str | None = None) -> dict[str, Any]:
        """Delete a session by ID."""
        service = _get_session_service(project_dir)
        return service.delete_session(session_id=session_id)

    @mcp.tool()
    def generate_bridge_jwt(
        session_id: str,
        permissions: list[str] | None = None,
        expiry_hours: int = 24,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Generate a JWT token for authenticating Remote Bridge calls."""
        service = _get_bridge_service(project_dir)
        token = service.generate_jwt(
            session_id=session_id,
            permissions=permissions or [],
            expiry_hours=expiry_hours,
        )
        return {"token": token}
