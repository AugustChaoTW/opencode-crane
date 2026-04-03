from __future__ import annotations

import json
import queue
import threading
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


class SSETransportService:
    def __init__(self, project_dir: str | None = None):
        self.project_dir = project_dir
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._port: int | None = None
        self._host: str | None = None
        self._clients: list[queue.Queue[str]] = []
        self._event_log: list[dict[str, object]] = []
        self._next_event_id = 1
        self._lock = threading.Lock()

    def _format_sse_message(self, event: dict[str, object]) -> str:
        payload = json.dumps(event.get("data", {}), ensure_ascii=False)
        return f"id: {event['id']}\nevent: {event['event_type']}\ndata: {payload}\n\n"

    def start_server(self, host: str = "127.0.0.1", port: int = 8765) -> dict:
        if self._server is not None:
            return {
                "status": "already_running",
                "host": self._host,
                "port": self._port,
                "url": f"http://{self._host}:{self._port}/events",
            }

        service = self

        class SSEHandler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args) -> None:
                return

            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path != "/events":
                    self.send_response(HTTPStatus.NOT_FOUND)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"error":"not found"}')
                    return

                last_event_raw = self.headers.get("Last-Event-ID", "").strip()
                try:
                    last_event_id = int(last_event_raw) if last_event_raw else 0
                except ValueError:
                    last_event_id = 0

                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()

                client_queue: queue.Queue[str] = queue.Queue(maxsize=100)
                with service._lock:
                    replay_events = []
                    for event in service._event_log:
                        event_id = event.get("id", 0)
                        if isinstance(event_id, int) and event_id > last_event_id:
                            replay_events.append(event)
                    service._clients.append(client_queue)

                try:
                    for event in replay_events:
                        self.wfile.write(service._format_sse_message(event).encode("utf-8"))
                    self.wfile.flush()

                    while service._server is not None:
                        try:
                            message = client_queue.get(timeout=15)
                        except queue.Empty:
                            message = ": keep-alive\n\n"

                        self.wfile.write(message.encode("utf-8"))
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, ValueError):
                    pass
                finally:
                    with service._lock:
                        if client_queue in service._clients:
                            service._clients.remove(client_queue)

        self._server = ThreadingHTTPServer((host, port), SSEHandler)
        self._host = host
        self._port = int(self._server.server_address[1])

        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

        return {
            "status": "started",
            "host": self._host,
            "port": self._port,
            "url": f"http://{self._host}:{self._port}/events",
        }

    def stop_server(self) -> dict:
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

        with self._lock:
            self._clients.clear()

        return {"status": "stopped"}

    def broadcast_event(self, event_type: str, data: dict) -> dict:
        with self._lock:
            event_id = self._next_event_id
            self._next_event_id += 1
            event = {
                "id": event_id,
                "event_type": event_type,
                "data": data,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
            self._event_log.append(event)
            self._event_log = self._event_log[-200:]
            clients = list(self._clients)

        message = self._format_sse_message(event)
        delivered = 0
        for client_queue in clients:
            try:
                client_queue.put_nowait(message)
                delivered += 1
            except queue.Full:
                continue

        return {
            "status": "broadcast",
            "event_id": event_id,
            "event_type": event_type,
            "clients_notified": delivered,
        }

    def get_server_status(self) -> dict:
        with self._lock:
            connected_clients = len(self._clients)

        return {
            "running": self._server is not None,
            "host": self._host,
            "port": self._port,
            "connected_clients": connected_clients,
        }
