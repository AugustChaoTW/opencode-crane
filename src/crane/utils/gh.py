"""
GitHub CLI (gh) subprocess wrapper for CRANE.
"""

import json
import subprocess
from typing import Union


def gh(args: list[str]) -> str:
    """Execute a gh command and return stdout."""
    cmd = ["gh"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def gh_json(args: list[str]) -> Union[dict, list]:
    """Execute a gh command that returns JSON and parse it."""
    output = gh(args)
    return json.loads(output) if output else {}
