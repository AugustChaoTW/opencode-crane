from __future__ import annotations

import runpy


def test_python_m_crane_invokes_server_main(monkeypatch):
    calls = []

    monkeypatch.setattr("crane.server.main", lambda: calls.append("called"))

    runpy.run_module("crane.__main__", run_name="__main__")

    assert calls == ["called"]
