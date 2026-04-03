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
    def start_sse_server(
        host: str = "127.0.0.1",
        port: int = 8765,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        service = _get_sse_service(project_dir)
        return service.start_server(host=host, port=port)

    @mcp.tool()
    def stop_sse_server(project_dir: str | None = None) -> dict[str, Any]:
        service = _get_sse_service(project_dir)
        return service.stop_server()

    @mcp.tool()
    def broadcast_sse_event(
        event_type: str,
        data: dict,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        service = _get_sse_service(project_dir)
        return service.broadcast_event(event_type=event_type, data=data)

    @mcp.tool()
    def get_sse_status(project_dir: str | None = None) -> dict[str, Any]:
        service = _get_sse_service(project_dir)
        return service.get_server_status()

    @mcp.tool()
    def create_session(
        name: str,
        context: dict | None = None,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        service = _get_session_service(project_dir)
        session_id = service.create_session(name=name, context=context)
        return {"session_id": session_id}

    @mcp.tool()
    def save_session(
        session_id: str,
        messages: list[dict],
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        service = _get_session_service(project_dir)
        return service.save_session(session_id=session_id, messages=messages)

    @mcp.tool()
    def load_session(session_id: str, project_dir: str | None = None) -> dict[str, Any]:
        service = _get_session_service(project_dir)
        return service.load_session(session_id=session_id)

    @mcp.tool()
    def list_sessions(limit: int = 20, project_dir: str | None = None) -> list[dict[str, Any]]:
        service = _get_session_service(project_dir)
        return service.list_sessions(limit=limit)

    @mcp.tool()
    def delete_session(session_id: str, project_dir: str | None = None) -> dict[str, Any]:
        service = _get_session_service(project_dir)
        return service.delete_session(session_id=session_id)

    @mcp.tool()
    def start_remote_bridge(
        host: str = "127.0.0.1",
        port: int = 8766,
        jwt_secret: str = "",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        service = _get_bridge_service(project_dir)
        return service.start_bridge(host=host, port=port, jwt_secret=jwt_secret)

    @mcp.tool()
    def stop_remote_bridge(project_dir: str | None = None) -> dict[str, Any]:
        service = _get_bridge_service(project_dir)
        return service.stop_bridge()

    @mcp.tool()
    def generate_bridge_jwt(
        session_id: str,
        permissions: list[str] | None = None,
        expiry_hours: int = 24,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        service = _get_bridge_service(project_dir)
        token = service.generate_jwt(
            session_id=session_id,
            permissions=permissions or [],
            expiry_hours=expiry_hours,
        )
        return {"token": token}

    @mcp.tool()
    def get_bridge_status(project_dir: str | None = None) -> dict[str, Any]:
        service = _get_bridge_service(project_dir)
        return service.get_bridge_status()
