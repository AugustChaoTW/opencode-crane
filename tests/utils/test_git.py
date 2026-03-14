"""
TDD tests for git info utilities.
RED phase: define expected behavior before implementation.
"""

from unittest.mock import patch, MagicMock

import pytest

from crane.utils.git import (
    get_current_branch,
    get_last_commit,
    get_owner_repo,
    get_remote_url,
    get_repo_root,
)


def _mock_run(stdout):
    """Helper to create a mock subprocess.run result."""
    m = MagicMock()
    m.stdout = stdout
    m.returncode = 0
    return m


class TestGetRepoRoot:
    def test_returns_trimmed_path(self):
        with patch(
            "crane.utils.git.subprocess.run", return_value=_mock_run("/home/user/project\n")
        ):
            assert get_repo_root() == "/home/user/project"


class TestGetRemoteUrl:
    def test_returns_remote_url(self):
        with patch(
            "crane.utils.git.subprocess.run",
            return_value=_mock_run("git@github.com:user/repo.git\n"),
        ):
            assert get_remote_url() == "git@github.com:user/repo.git"


class TestGetOwnerRepo:
    def test_ssh_url(self):
        with patch(
            "crane.utils.git.subprocess.run",
            return_value=_mock_run("git@github.com:myorg/myrepo.git\n"),
        ):
            owner, repo = get_owner_repo()
            assert owner == "myorg"
            assert repo == "myrepo"

    def test_https_url(self):
        with patch(
            "crane.utils.git.subprocess.run",
            return_value=_mock_run("https://github.com/myorg/myrepo.git\n"),
        ):
            owner, repo = get_owner_repo()
            assert owner == "myorg"
            assert repo == "myrepo"

    def test_https_url_no_git_suffix(self):
        with patch(
            "crane.utils.git.subprocess.run",
            return_value=_mock_run("https://github.com/myorg/myrepo\n"),
        ):
            owner, repo = get_owner_repo()
            assert owner == "myorg"
            assert repo == "myrepo"

    def test_invalid_url_raises(self):
        with patch("crane.utils.git.subprocess.run", return_value=_mock_run("not-a-url\n")):
            with pytest.raises(ValueError, match="Cannot parse"):
                get_owner_repo()


class TestGetCurrentBranch:
    def test_returns_branch_name(self):
        with patch("crane.utils.git.subprocess.run", return_value=_mock_run("feature/xyz\n")):
            assert get_current_branch() == "feature/xyz"


class TestGetLastCommit:
    def test_returns_hash_and_message(self):
        with patch(
            "crane.utils.git.subprocess.run", return_value=_mock_run("abc1234 initial commit\n")
        ):
            result = get_last_commit()
            assert "abc1234" in result
            assert "initial commit" in result
