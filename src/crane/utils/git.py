"""
Git info utilities for CRANE.
"""

import re
import subprocess


def get_repo_root() -> str:
    """Get the git repository root directory."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def get_remote_url() -> str:
    """Get the origin remote URL."""
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def get_owner_repo() -> tuple[str, str]:
    """Parse owner and repo name from git remote URL."""
    url = get_remote_url()
    # Handle SSH: git@github.com:owner/repo.git
    ssh_match = re.match(r"git@github\.com:(.+)/(.+?)(?:\.git)?$", url)
    if ssh_match:
        return ssh_match.group(1), ssh_match.group(2)
    # Handle HTTPS: https://github.com/owner/repo.git
    https_match = re.match(r"https://github\.com/(.+)/(.+?)(?:\.git)?$", url)
    if https_match:
        return https_match.group(1), https_match.group(2)
    raise ValueError(f"Cannot parse GitHub owner/repo from remote URL: {url}")


def get_current_branch() -> str:
    """Get the current branch name."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def get_last_commit() -> str:
    """Get the last commit hash and message."""
    result = subprocess.run(
        ["git", "log", "-1", "--format=%h %s"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()
