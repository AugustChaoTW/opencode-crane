"""
Git info utilities for CRANE.
"""

import re
import subprocess


def _git(args: list[str], cwd: str | None = None) -> str:
    """Run a git command and return stripped stdout."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        check=True,
        cwd=cwd,
    )
    return result.stdout.strip()


def get_repo_root(cwd: str | None = None) -> str:
    return _git(["rev-parse", "--show-toplevel"], cwd=cwd)


def get_remote_url(cwd: str | None = None) -> str:
    return _git(["remote", "get-url", "origin"], cwd=cwd)


def get_owner_repo(cwd: str | None = None) -> tuple[str, str]:
    url = get_remote_url(cwd=cwd)
    ssh_match = re.match(r"git@github\.com:(.+)/(.+?)(?:\.git)?$", url)
    if ssh_match:
        return ssh_match.group(1), ssh_match.group(2)
    https_match = re.match(r"https://github\.com/(.+)/(.+?)(?:\.git)?$", url)
    if https_match:
        return https_match.group(1), https_match.group(2)
    raise ValueError(f"Cannot parse GitHub owner/repo from remote URL: {url}")


def get_current_branch(cwd: str | None = None) -> str:
    return _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)


def get_last_commit(cwd: str | None = None) -> str:
    return _git(["log", "-1", "--format=%h %s"], cwd=cwd)
