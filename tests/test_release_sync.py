from __future__ import annotations

import re
import tomllib
from pathlib import Path

from crane import __version__
from crane.server import mcp


def test_package_version_matches_pyproject():
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    with pyproject.open("rb") as handle:
        project = tomllib.load(handle)

    assert __version__ == project["project"]["version"]


def test_readme_tool_count_matches_server_registration():
    readme = Path(__file__).resolve().parent.parent / "README.md"
    content = readme.read_text(encoding="utf-8")
    match = re.search(r"CRANE provides \*\*(\d+) MCP Tools\*\*", content)

    assert match is not None
    assert int(match.group(1)) == len(mcp._tool_manager._tools)
