from __future__ import annotations

import http.client
import json
import time

from crane.services.sse_transport_service import SSETransportService


def _read_event_block(response: http.client.HTTPResponse) -> dict[str, str]:
    event: dict[str, str] = {}
    while True:
        raw = response.fp.readline()
        if not raw:
            break
        line = raw.decode("utf-8").strip()
        if not line:
            break
        if ": " in line:
            key, value = line.split(": ", 1)
            event[key] = value
    return event


def test_start_and_stop_server(tmp_path):
    sse_service = SSETransportService(project_dir=str(tmp_path))
    started = sse_service.start_server(port=0)
    assert started["status"] == "started"
    assert started["url"].endswith("/events")
    assert sse_service.get_server_status()["running"] is True

    stopped = sse_service.stop_server()
    assert stopped["status"] == "stopped"
    assert sse_service.get_server_status()["running"] is False


def test_client_connect_and_receive_broadcast_event(tmp_path):
    sse_service = SSETransportService(project_dir=str(tmp_path))
    info = sse_service.start_server(port=0)
    conn = http.client.HTTPConnection(info["host"], info["port"], timeout=3)
    conn.request("GET", "/events")
    response = conn.getresponse()
    assert response.status == 200
    assert response.getheader("Content-Type") == "text/event-stream"

    time.sleep(0.1)
    status = sse_service.get_server_status()
    assert status["connected_clients"] >= 1

    sent = sse_service.broadcast_event("tool_progress", {"step": "run", "pct": 50})
    assert sent["status"] == "broadcast"

    event = _read_event_block(response)
    assert event["event"] == "tool_progress"
    payload = json.loads(event["data"])
    assert payload["step"] == "run"
    assert payload["pct"] == 50

    response.close()
    conn.close()
    sse_service.stop_server()


def test_last_event_id_replays_recent_events(tmp_path):
    sse_service = SSETransportService(project_dir=str(tmp_path))
    info = sse_service.start_server(port=0)
    first = sse_service.broadcast_event("tool_start", {"n": 1})
    second = sse_service.broadcast_event("tool_complete", {"n": 2})
    assert second["event_id"] == first["event_id"] + 1

    conn = http.client.HTTPConnection(info["host"], info["port"], timeout=3)
    conn.putrequest("GET", "/events")
    conn.putheader("Last-Event-ID", str(first["event_id"]))
    conn.endheaders()
    response = conn.getresponse()

    replay = _read_event_block(response)
    assert replay["id"] == str(second["event_id"])
    assert replay["event"] == "tool_complete"

    response.close()
    conn.close()
    sse_service.stop_server()
