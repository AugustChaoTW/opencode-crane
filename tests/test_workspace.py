"""
Tests for workspace resolution.
Validates stateless workspace identification via git context.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from crane.workspace import WorkspaceContext, resolve_workspace


class TestWorkspaceContext:
    """Test WorkspaceContext properties."""

    def test_repo_format(self):
        ctx = WorkspaceContext(
            project_root="/tmp/test",
            owner="testuser",
            repo="test-repo",
            references_dir="/tmp/test/references",
        )
        assert ctx.repo == "testuser/test-repo"

    def test_owner_property(self):
        ctx = WorkspaceContext(
            project_root="/tmp/test",
            owner="testuser",
            repo="test-repo",
            references_dir="/tmp/test/references",
        )
        assert ctx.owner == "testuser"

    def test_references_dir(self):
        ctx = WorkspaceContext(
            project_root="/tmp/test",
            owner="testuser",
            repo="test-repo",
            references_dir="/tmp/test/references",
        )
        assert ctx.references_dir == "/tmp/test/references"

    def test_papers_dir(self):
        ctx = WorkspaceContext(
            project_root="/tmp/test",
            owner="testuser",
            repo="test-repo",
            references_dir="/tmp/test/references",
        )
        assert ctx.papers_dir == "/tmp/test/references/papers"

    def test_pdfs_dir(self):
        ctx = WorkspaceContext(
            project_root="/tmp/test",
            owner="testuser",
            repo="test-repo",
            references_dir="/tmp/test/references",
        )
        assert ctx.pdfs_dir == "/tmp/test/references/pdfs"

    def test_bib_path(self):
        ctx = WorkspaceContext(
            project_root="/tmp/test",
            owner="testuser",
            repo="test-repo",
            references_dir="/tmp/test/references",
        )
        assert ctx.bib_path == "/tmp/test/references/bibliography.bib"

    def test_to_dict(self):
        ctx = WorkspaceContext(
            project_root="/tmp/test",
            owner="testuser",
            repo="test-repo",
            references_dir="/tmp/test/references",
        )
        result = ctx.to_dict()
        assert result == {
            "project_root": "/tmp/test",
            "repo": "testuser/test-repo",
            "references_dir": "/tmp/test/references",
        }


class TestResolveWorkspace:
    """Test workspace resolution from git context."""

    def test_resolve_from_project_dir(self):
        with patch("crane.workspace.get_repo_root", return_value="/tmp/test"):
            with patch("crane.workspace.get_owner_repo", return_value=("user", "repo")):
                ctx = resolve_workspace("/tmp/test")

        assert ctx.project_root == "/tmp/test"
        assert ctx.repo == "user/repo"
        assert ctx.references_dir == "/tmp/test/references"

    def test_resolve_auto_detect(self):
        with patch("crane.workspace.get_repo_root", return_value="/home/user/project"):
            with patch("crane.workspace.get_owner_repo", return_value=("owner", "myrepo")):
                ctx = resolve_workspace(None)

        assert ctx.project_root == "/home/user/project"
        assert ctx.repo == "owner/myrepo"

    def test_not_git_repo_raises(self):
        with patch("crane.workspace.get_repo_root", side_effect=Exception("not a git repo")):
            with pytest.raises(ValueError, match="Not a git repository"):
                resolve_workspace("/nonexistent")

    def test_no_github_remote_raises(self):
        with patch("crane.workspace.get_repo_root", return_value="/tmp/test"):
            with patch("crane.workspace.get_owner_repo", side_effect=ValueError("no remote")):
                with pytest.raises(ValueError, match="No GitHub remote"):
                    resolve_workspace("/tmp/test")


class TestWorkspaceIsolation:
    """Test workspace isolation between different repos."""

    def test_different_repos_different_contexts(self):
        with patch("crane.workspace.get_repo_root", return_value="/repo1"):
            with patch("crane.workspace.get_owner_repo", return_value=("user1", "repo1")):
                ctx1 = resolve_workspace("/repo1")

        with patch("crane.workspace.get_repo_root", return_value="/repo2"):
            with patch("crane.workspace.get_owner_repo", return_value=("user2", "repo2")):
                ctx2 = resolve_workspace("/repo2")

        assert ctx1.repo != ctx2.repo
        assert ctx1.references_dir != ctx2.references_dir

    def test_same_repo_same_context(self):
        with patch("crane.workspace.get_repo_root", return_value="/repo"):
            with patch("crane.workspace.get_owner_repo", return_value=("user", "repo")):
                ctx1 = resolve_workspace("/repo")
                ctx2 = resolve_workspace("/repo")

        assert ctx1.repo == ctx2.repo
        assert ctx1.references_dir == ctx2.references_dir
