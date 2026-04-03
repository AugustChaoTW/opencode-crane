from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
from datetime import datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable


class RemoteBridgeService:
    def __init__(self, project_dir: str | None = None):
        self.project_dir = project_dir
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._host: str | None = None
        self._port: int | None = None
        self._jwt_secret: str | None = None
        self._tool_executor: Callable[[str, dict[str, Any]], Any] | None = None

    def set_tool_executor(self, executor: Callable[[str, dict[str, Any]], Any]) -> None:
        self._tool_executor = executor

    def _json_response(
        self, handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)

    def _b64_encode(self, raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

    def _b64_decode(self, raw: str) -> bytes:
        padding = "=" * ((4 - len(raw) % 4) % 4)
        return base64.urlsafe_b64decode((raw + padding).encode("utf-8"))

    def _encode_hmac_token(self, payload: dict[str, Any]) -> str:
        if not self._jwt_secret:
            raise ValueError("JWT secret is not configured")

        header = {"alg": "HS256", "typ": "JWT"}
        header_part = self._b64_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_part = self._b64_encode(
            json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        )
        signing_input = f"{header_part}.{payload_part}".encode("utf-8")
        signature = hmac.new(
            self._jwt_secret.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        signature_part = self._b64_encode(signature)
        return f"{header_part}.{payload_part}.{signature_part}"

    def _decode_hmac_token(self, token: str) -> dict[str, Any]:
        if not self._jwt_secret:
            raise ValueError("JWT secret is not configured")

        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format")

        header_part, payload_part, signature_part = parts
        signing_input = f"{header_part}.{payload_part}".encode("utf-8")
        expected_signature = hmac.new(
            self._jwt_secret.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        actual_signature = self._b64_decode(signature_part)
        if not hmac.compare_digest(expected_signature, actual_signature):
            raise ValueError("Invalid token signature")

        payload_raw = self._b64_decode(payload_part).decode("utf-8")
        payload = json.loads(payload_raw)
        if not isinstance(payload, dict):
            raise ValueError("Invalid token payload")

        exp = int(payload.get("exp", 0))
        if exp and int(time.time()) >= exp:
            raise ValueError("Token expired")

        return payload

    def _decode_token(self, token: str) -> dict[str, Any]:
        try:
            import jwt  # pyright: ignore[reportMissingImports]

            if self._jwt_secret:
                decoded = jwt.decode(token, self._jwt_secret, algorithms=["HS256"])
                if isinstance(decoded, dict):
                    return decoded
        except Exception:
            pass

        return self._decode_hmac_token(token)

    def start_bridge(
        self,
        host: str = "127.0.0.1",
        port: int = 8766,
        jwt_secret: str = "",
    ) -> dict:
        if self._server is not None:
            return {
                "status": "already_running",
                "host": self._host,
                "port": self._port,
                "endpoints": [
                    "/api/v1/tool/call",
                    "/api/v1/auth/token",
                    "/api/v1/health",
                ],
            }

        self._jwt_secret = jwt_secret or "crane-bridge-dev-secret"
        service = self

        class BridgeHandler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args) -> None:
                return

            def _read_json_body(self) -> dict[str, Any]:
                length = int(self.headers.get("Content-Length", "0") or "0")
                if length <= 0:
                    return {}
                payload = self.rfile.read(length).decode("utf-8")
                if not payload.strip():
                    return {}
                loaded = json.loads(payload)
                if isinstance(loaded, dict):
                    return loaded
                return {}

            def do_GET(self):
                if self.path != "/api/v1/health":
                    service._json_response(
                        self,
                        HTTPStatus.NOT_FOUND,
                        {"status": "error", "error": "not found"},
                    )
                    return

                service._json_response(
                    self,
                    HTTPStatus.OK,
                    {
                        "status": "ok",
                        "running": service._server is not None,
                        "host": service._host,
                        "port": service._port,
                    },
                )

            def do_POST(self):
                try:
                    body = self._read_json_body()
                except json.JSONDecodeError:
                    service._json_response(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {"status": "error", "error": "invalid json"},
                    )
                    return

                if self.path == "/api/v1/auth/token":
                    session_id = str(body.get("session_id", ""))
                    permissions = body.get("permissions", [])
                    expiry_hours = int(body.get("expiry_hours", 24))
                    token = service.generate_jwt(
                        session_id=session_id,
                        permissions=permissions if isinstance(permissions, list) else [],
                        expiry_hours=expiry_hours,
                    )
                    service._json_response(
                        self,
                        HTTPStatus.OK,
                        {"status": "ok", "token": token},
                    )
                    return

                if self.path == "/api/v1/tool/call":
                    auth_header = self.headers.get("Authorization", "")
                    token = str(body.get("jwt_token", ""))
                    if auth_header.startswith("Bearer "):
                        token = auth_header[7:].strip()

                    result = service.handle_tool_call(
                        tool_name=str(body.get("tool_name", "")),
                        args=body.get("args", {}) if isinstance(body.get("args", {}), dict) else {},
                        jwt_token=token,
                    )
                    if result.get("status") == "error":
                        status = HTTPStatus.UNAUTHORIZED
                        if result.get("error") == "forbidden":
                            status = HTTPStatus.FORBIDDEN
                        service._json_response(self, status, result)
                        return

                    service._json_response(self, HTTPStatus.OK, result)
                    return

                service._json_response(
                    self,
                    HTTPStatus.NOT_FOUND,
                    {"status": "error", "error": "not found"},
                )

        self._server = ThreadingHTTPServer((host, port), BridgeHandler)
        self._host = host
        self._port = int(self._server.server_address[1])
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

        return {
            "status": "started",
            "host": self._host,
            "port": self._port,
            "endpoints": [
                "/api/v1/tool/call",
                "/api/v1/auth/token",
                "/api/v1/health",
            ],
        }

    def stop_bridge(self) -> dict:
        if self._server is None:
            return {"status": "not_running"}

        server = self._server
        thread = self._thread
        self._server = None
        self._thread = None

        server.shutdown()
        server.server_close()
        if thread is not None:
            thread.join(timeout=2)

        return {"status": "stopped"}

    def generate_jwt(
        self,
        session_id: str,
        permissions: list[str],
        expiry_hours: int = 24,
    ) -> str:
        issued_at = int(time.time())
        expires_at = int((datetime.now() + timedelta(hours=expiry_hours)).timestamp())
        payload = {
            "session_id": session_id,
            "permissions": permissions,
            "iat": issued_at,
            "exp": expires_at,
        }

        try:
            import jwt  # pyright: ignore[reportMissingImports]

            if self._jwt_secret:
                encoded = jwt.encode(payload, self._jwt_secret, algorithm="HS256")
                if isinstance(encoded, str):
                    return encoded
                return encoded.decode("utf-8")
        except Exception:
            pass

        return self._encode_hmac_token(payload)

    def get_bridge_status(self) -> dict:
        return {
            "running": self._server is not None,
            "host": self._host,
            "port": self._port,
            "has_jwt_secret": bool(self._jwt_secret),
            "has_tool_executor": self._tool_executor is not None,
        }

    def handle_tool_call(self, tool_name: str, args: dict, jwt_token: str) -> dict:
        if not jwt_token:
            return {"status": "error", "error": "unauthorized", "message": "Missing token"}

        try:
            payload = self._decode_token(jwt_token)
        except Exception as exc:
            return {
                "status": "error",
                "error": "unauthorized",
                "message": str(exc),
            }

        permissions = payload.get("permissions", [])
        if not isinstance(permissions, list):
            permissions = []

        if "*" not in permissions and tool_name not in permissions:
            return {
                "status": "error",
                "error": "forbidden",
                "message": f"Tool '{tool_name}' is not permitted",
            }

        if self._tool_executor is None:
            return {
                "status": "error",
                "error": "executor_not_configured",
                "message": "No tool executor configured",
            }

        try:
            result = self._tool_executor(tool_name, args)
        except Exception as exc:
            return {
                "status": "error",
                "error": "execution_failed",
                "message": str(exc),
            }

        return {
            "status": "ok",
            "tool_name": tool_name,
            "session_id": payload.get("session_id", ""),
            "result": result,
        }
