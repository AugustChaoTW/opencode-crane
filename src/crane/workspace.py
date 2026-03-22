"""
Workspace resolution for CRANE.
Stateless workspace identification via git context.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from crane.utils.git import get_owner_repo, get_repo_root


class WorkspaceContext:
    """Immutable workspace context resolved from git."""

    def __init__(
        self,
        project_root: str,
        owner: str,
        repo: str,
        references_dir: str,
    ):
        self._project_root = project_root
        self._owner = owner
        self._repo = repo
        self._references_dir = references_dir

    @property
    def project_root(self) -> str:
        return self._project_root

    @property
    def owner(self) -> str:
        return self._owner

    @property
    def repo(self) -> str:
        return f"{self._owner}/{self._repo}"

    @property
    def repo_name(self) -> str:
        return self._repo

    @property
    def references_dir(self) -> str:
        return self._references_dir

    @property
    def papers_dir(self) -> str:
        return str(Path(self._references_dir) / "papers")

    @property
    def pdfs_dir(self) -> str:
        return str(Path(self._references_dir) / "pdfs")

    @property
    def bib_path(self) -> str:
        return str(Path(self._references_dir) / "bibliography.bib")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for MCP tool responses."""
        return {
            "project_root": self._project_root,
            "repo": self.repo,
            "references_dir": self._references_dir,
        }


def resolve_workspace(project_dir: str | None = None) -> WorkspaceContext:
    """
    Resolve workspace context from git repository.

    Args:
        project_dir: Explicit project directory. If None, auto-detect from cwd.

    Returns:
        WorkspaceContext with project_root, owner/repo, and references path.

    Raises:
        ValueError: If not a git repository or not a GitHub repo.
    """
    cwd = project_dir or str(Path.cwd())

    try:
        project_root = get_repo_root(cwd=cwd)
    except Exception:
        raise ValueError(
            f"Not a git repository: {cwd}\n"
            "CRANE requires a git repository with GitHub remote for full functionality."
        )

    try:
        owner, repo = get_owner_repo(cwd=project_root)
    except ValueError:
        raise ValueError(
            f"No GitHub remote found in: {project_root}\n"
            "CRANE requires a GitHub remote for issue-backed features."
        )

    references_dir = str(Path(project_root) / "references")

    return WorkspaceContext(
        project_root=project_root,
        owner=owner,
        repo=repo,
        references_dir=references_dir,
    )
