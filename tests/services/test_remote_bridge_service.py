from __future__ import annotations

import json
from urllib import request

from crane.services.remote_bridge_service import RemoteBridgeService


def _http_post_json(url: str, payload: dict) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=3) as resp:  # noqa: S310
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _http_get_json(url: str) -> tuple[int, dict]:
    with request.urlopen(url, timeout=3) as resp:  # noqa: S310
        return resp.status, json.loads(resp.read().decode("utf-8"))


def test_generate_jwt_and_handle_tool_call_success(tmp_path):
    service = RemoteBridgeService(project_dir=str(tmp_path))
    service.start_bridge(port=0, jwt_secret="secret")
    service.set_tool_executor(lambda tool_name, args: {"tool": tool_name, "args": args})

    token = service.generate_jwt("sess_1", ["test_tool"], expiry_hours=1)
    result = service.handle_tool_call("test_tool", {"x": 1}, token)

    assert result["status"] == "ok"
    assert result["tool_name"] == "test_tool"
    assert result["result"]["args"]["x"] == 1

    service.stop_bridge()


def test_handle_tool_call_permission_denied(tmp_path):
    service = RemoteBridgeService(project_dir=str(tmp_path))
    service.start_bridge(port=0, jwt_secret="secret")
    service.set_tool_executor(lambda _name, _args: {"ok": True})

    token = service.generate_jwt("sess_2", ["allowed_tool"], expiry_hours=1)
    denied = service.handle_tool_call("forbidden_tool", {}, token)

    assert denied["status"] == "error"
    assert denied["error"] == "forbidden"

    service.stop_bridge()


def test_handle_tool_call_invalid_token(tmp_path):
    service = RemoteBridgeService(project_dir=str(tmp_path))
    service.start_bridge(port=0, jwt_secret="secret")
    service.set_tool_executor(lambda _name, _args: {"ok": True})

    result = service.handle_tool_call("tool", {}, "bad.token.value")
    assert result["status"] == "error"
    assert result["error"] == "unauthorized"

    service.stop_bridge()


def test_http_bridge_endpoints(tmp_path):
    service = RemoteBridgeService(project_dir=str(tmp_path))
    started = service.start_bridge(port=0, jwt_secret="secret")
    service.set_tool_executor(
        lambda tool_name, args: {"tool": tool_name, "ok": args.get("ok", False)}
    )

    base = f"http://{started['host']}:{started['port']}"

    status_code, health = _http_get_json(f"{base}/api/v1/health")
    assert status_code == 200
    assert health["status"] == "ok"

    token_status, token_resp = _http_post_json(
        f"{base}/api/v1/auth/token",
        {
            "session_id": "sess_3",
            "permissions": ["bridge_tool"],
            "expiry_hours": 1,
        },
    )
    assert token_status == 200
    token = token_resp["token"]

    call_status, call_resp = _http_post_json(
        f"{base}/api/v1/tool/call",
        {
            "tool_name": "bridge_tool",
            "args": {"ok": True},
            "jwt_token": token,
        },
    )
    assert call_status == 200
    assert call_resp["status"] == "ok"
    assert call_resp["result"]["ok"] is True

    service.stop_bridge()
