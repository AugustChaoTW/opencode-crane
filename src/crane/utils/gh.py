"""
GitHub CLI (gh) subprocess wrapper for CRANE.
"""

import json
import subprocess


def gh(args: list[str], cwd: str | None = None) -> str:
    """Execute a gh command and return stdout.

    Args:
        args: gh CLI arguments (e.g. ["issue", "create", "--title", "T"]).
        cwd: Working directory for the subprocess. If None, inherits from
             the current process. Pass the project root to target a specific
             GitHub repo when multiple projects share one MCP server.
    """
    cmd = ["gh"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=cwd)
    return result.stdout.strip()


def gh_json(args: list[str], cwd: str | None = None) -> dict | list:
    """Execute a gh command that returns JSON and parse it.

    Args:
        args: gh CLI arguments.
        cwd: Working directory for the subprocess (see gh()).
    """
    output = gh(args, cwd=cwd)
    return json.loads(output) if output else {}
