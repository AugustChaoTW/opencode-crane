"""
Tests that installer script stays in sync with actual tool count.

Prevents the installer hardcoding N tools when the server registers M.
Issue: installer expected 18, server had 19 (run_pipeline added later).
"""

import re
from pathlib import Path

import pytest

from crane.server import mcp


def _get_registered_tool_count() -> int:
    return len(mcp._tool_manager._tools) if hasattr(mcp, "_tool_manager") else 0


def _get_installer_expected_tools() -> int:
    installer = Path(__file__).resolve().parent.parent / "scripts" / "install.sh"
    content = installer.read_text(encoding="utf-8")
    match = re.search(r"EXPECTED_TOOLS=(\d+)", content)
    if not match:
        pytest.fail("scripts/install.sh missing EXPECTED_TOOLS variable")
    return int(match.group(1))


class TestToolCountSync:
    """Installer and server must agree on tool count."""

    def test_installer_expected_tools_matches_server(self):
        actual = _get_registered_tool_count()
        expected = _get_installer_expected_tools()
        assert actual == expected, (
            f"Tool count mismatch: server registers {actual}, "
            f"installer expects {expected}. "
            f"Update scripts/install.sh EXPECTED_TOOLS to {actual}."
        )

    def test_server_has_minimum_tools(self):
        actual = _get_registered_tool_count()
        assert actual >= 19, f"Expected at least 19 tools, got {actual}"


class TestRegisteredTools:
    """Verify the expected set of tools is registered."""

    def test_has_run_pipeline(self):
        tools = mcp._tool_manager._tools if hasattr(mcp, "_tool_manager") else {}
        assert "run_pipeline" in tools, "run_pipeline tool not registered"

    def test_all_tool_names_unique(self):
        tools = mcp._tool_manager._tools if hasattr(mcp, "_tool_manager") else {}
        names = list(tools.keys())
        assert len(names) == len(set(names)), "Duplicate tool names detected"
