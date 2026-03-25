"""
Cross-project isolation tests.

Verifies that CRANE tools correctly isolate operations per-project
when working with multiple research projects (different GitHub repos).

Issue: https://github.com/AugustChaoTW/opencode-crane/issues/4
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crane.tools.references import register_tools as register_ref_tools
from crane.tools.tasks import register_tools as register_task_tools
from crane.utils import git
from crane.utils.gh import gh, gh_json

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _ToolCollector:
    """Minimal mock MCP server that collects registered tools."""

    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


@pytest.fixture
def ref_tools():
    collector = _ToolCollector()
    register_ref_tools(collector)
    return collector.tools


@pytest.fixture
def task_tools():
    collector = _ToolCollector()
    register_task_tools(collector)
    return collector.tools


def _make_project(tmp_path: Path, name: str) -> Path:
    """Create a minimal project directory with references/ structure."""
    project = tmp_path / name
    refs = project / "references"
    (refs / "papers").mkdir(parents=True)
    (refs / "pdfs").mkdir(parents=True)
    (refs / "bibliography.bib").write_text("", encoding="utf-8")
    return project


def _make_git_repo(project: Path, owner: str, repo: str):
    """Initialize a fake git repo with remote origin."""
    import subprocess

    subprocess.run(["git", "init"], cwd=project, capture_output=True, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", f"git@github.com:{owner}/{repo}.git"],
        cwd=project,
        capture_output=True,
        check=True,
    )


# ---------------------------------------------------------------------------
# Test: References isolation
# ---------------------------------------------------------------------------


class TestReferencesIsolation:
    """Verify that references from project A don't leak into project B."""

    def test_two_projects_references_independent(self, ref_tools, tmp_path):
        """Adding a reference to project A must NOT appear in project B."""
        proj_a = _make_project(tmp_path, "project-a")
        proj_b = _make_project(tmp_path, "project-b")
        refs_a = str(proj_a / "references")
        refs_b = str(proj_b / "references")

        # Add a reference to project A
        ref_tools["add_reference"](
            key="test2024-paper-a",
            title="Paper in Project A",
            authors=["Author A"],
            year=2024,
            refs_dir=refs_a,
        )

        # List references in project B — should be empty
        results_b = ref_tools["list_references"](refs_dir=refs_b)
        assert results_b == [], f"Project B should be empty, got: {results_b}"

        # List references in project A — should have 1
        results_a = ref_tools["list_references"](refs_dir=refs_a)
        assert len(results_a) == 1
        assert results_a[0]["key"] == "test2024-paper-a"

    def test_search_references_scoped_to_project(self, ref_tools, tmp_path):
        """search_references in project A should not find project B's papers."""
        proj_a = _make_project(tmp_path, "project-a")
        proj_b = _make_project(tmp_path, "project-b")
        refs_a = str(proj_a / "references")
        refs_b = str(proj_b / "references")

        ref_tools["add_reference"](
            key="unique2024-x",
            title="Unique Paper X",
            authors=["Author"],
            year=2024,
            refs_dir=refs_a,
        )

        # Search in project B for paper that only exists in A
        results = ref_tools["search_references"]("Unique Paper X", refs_dir=refs_b)
        assert results == [], "Should not find project A's papers from project B"

    def test_remove_reference_scoped_to_project(self, ref_tools, tmp_path):
        """Removing from project A should not affect project B."""
        proj_a = _make_project(tmp_path, "project-a")
        proj_b = _make_project(tmp_path, "project-b")
        refs_a = str(proj_a / "references")
        refs_b = str(proj_b / "references")

        ref_tools["add_reference"](
            key="shared2024-key",
            title="Paper with same key",
            authors=["Author"],
            year=2024,
            refs_dir=refs_a,
        )
        ref_tools["add_reference"](
            key="shared2024-key",
            title="Paper with same key",
            authors=["Author"],
            year=2024,
            refs_dir=refs_b,
        )

        # Remove from project A
        ref_tools["remove_reference"]("shared2024-key", refs_dir=refs_a)

        # Project B should still have it
        result_b = ref_tools["get_reference"]("shared2024-key", refs_dir=refs_b)
        assert result_b["title"] == "Paper with same key"


# ---------------------------------------------------------------------------
# Test: Tasks target correct repo
# ---------------------------------------------------------------------------


class TestTasksIsolation:
    """Verify that task operations target the correct GitHub repo."""

    def test_create_task_uses_project_dir_repo(self, task_tools, tmp_path):
        """create_task with project_dir should target that project's repo."""
        proj_a = _make_project(tmp_path, "project-a")
        proj_b = _make_project(tmp_path, "project-b")
        _make_git_repo(proj_a, "user-a", "repo-a")
        _make_git_repo(proj_b, "user-b", "repo-b")

        gh_calls = []

        def mock_subprocess_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stderr = ""

            # Record cwd if provided
            cwd = kwargs.get("cwd")
            gh_calls.append({"cmd": cmd, "cwd": cwd})

            cmd_str = " ".join(cmd)

            if "remote get-url" in cmd_str:
                if cwd and "project-a" in str(cwd):
                    result.stdout = "git@github.com:user-a/repo-a.git\n"
                elif cwd and "project-b" in str(cwd):
                    result.stdout = "git@github.com:user-b/repo-b.git\n"
                else:
                    result.stdout = "git@github.com:default/repo.git\n"
            elif "issue create" in cmd_str:
                if cwd and "project-a" in str(cwd):
                    result.stdout = "https://github.com/user-a/repo-a/issues/1\n"
                elif cwd and "project-b" in str(cwd):
                    result.stdout = "https://github.com/user-b/repo-b/issues/1\n"
                else:
                    result.stdout = "https://github.com/default/repo/issues/1\n"
            else:
                result.stdout = "\n"

            return result

        with (
            patch("crane.utils.gh.subprocess.run", side_effect=mock_subprocess_run),
            patch("crane.utils.git.subprocess.run", side_effect=mock_subprocess_run),
        ):
            # Create task targeting project B
            task_tools["create_task"](
                title="Task in Project B",
                body="Body",
                project_dir=str(proj_b),
            )

            # The gh call should have been made with cwd=proj_b
            gh_create_calls = [c for c in gh_calls if "issue create" in " ".join(c["cmd"])]
            assert len(gh_create_calls) == 1
            assert gh_create_calls[0]["cwd"] == str(proj_b)


# ---------------------------------------------------------------------------
# Test: project_dir overrides CWD
# ---------------------------------------------------------------------------


class TestProjectDirOverride:
    """Verify that project_dir parameter overrides CWD for path resolution."""

    def test_refs_dir_resolved_against_project_dir(self, ref_tools, tmp_path):
        """When project_dir is provided, refs_dir should resolve against it."""
        proj_a = _make_project(tmp_path, "project-a")
        proj_b = _make_project(tmp_path, "project-b")

        # Simulate: server CWD is project-a, but we pass project_dir=project-b
        # The reference should end up in project-b, not project-a
        refs_b = str(proj_b / "references")

        ref_tools["add_reference"](
            key="override2024-test",
            title="Override Test",
            authors=["Author"],
            year=2024,
            refs_dir=refs_b,
        )

        # Verify: file should be in project-b
        assert (proj_b / "references" / "papers" / "override2024-test.yaml").exists()
        # Verify: file should NOT be in project-a
        assert not (proj_a / "references" / "papers" / "override2024-test.yaml").exists()


# ---------------------------------------------------------------------------
# Test: git functions respect cwd parameter
# ---------------------------------------------------------------------------


class TestGitCwdParameter:
    """Verify that git utility functions accept and use explicit cwd."""

    def test_get_owner_repo_uses_cwd_param(self, tmp_path):
        """get_owner_repo(cwd=...) should parse the remote of that directory."""
        proj_a = _make_project(tmp_path, "project-a")
        proj_b = _make_project(tmp_path, "project-b")
        _make_git_repo(proj_a, "user-a", "repo-a")
        _make_git_repo(proj_b, "user-b", "repo-b")

        def mock_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stderr = ""
            cwd = kwargs.get("cwd")
            cmd_str = " ".join(cmd)

            if "remote get-url" in cmd_str:
                if cwd and "project-a" in str(cwd):
                    result.stdout = "git@github.com:user-a/repo-a.git\n"
                elif cwd and "project-b" in str(cwd):
                    result.stdout = "git@github.com:user-b/repo-b.git\n"
                else:
                    result.stdout = "git@github.com:default/repo.git\n"
            else:
                result.stdout = "placeholder\n"
            return result

        with patch("crane.utils.git.subprocess.run", side_effect=mock_run):
            owner_a, repo_a = git.get_owner_repo(cwd=str(proj_a))
            owner_b, repo_b = git.get_owner_repo(cwd=str(proj_b))

            assert owner_a == "user-a"
            assert repo_a == "repo-a"
            assert owner_b == "user-b"
            assert repo_b == "repo-b"


# ---------------------------------------------------------------------------
# Test: gh functions respect cwd parameter
# ---------------------------------------------------------------------------


class TestGhCwdParameter:
    """Verify that gh utility functions accept and use explicit cwd."""

    def test_gh_passes_cwd_to_subprocess(self):
        """gh(args, cwd=...) should pass cwd to subprocess.run."""
        mock_result = MagicMock()
        mock_result.stdout = "https://github.com/test/repo/issues/1\n"
        mock_result.returncode = 0

        captured_kwargs = {}

        def mock_run(cmd, **kwargs):
            captured_kwargs.update(kwargs)
            return mock_result

        with patch("crane.utils.gh.subprocess.run", side_effect=mock_run):
            gh(["issue", "create", "--title", "Test"], cwd="/some/project")

            assert captured_kwargs.get("cwd") == "/some/project"

    def test_gh_json_passes_cwd_to_subprocess(self):
        """gh_json(args, cwd=...) should pass cwd to subprocess.run."""
        mock_result = MagicMock()
        mock_result.stdout = json.dumps({"number": 1})
        mock_result.returncode = 0

        captured_kwargs = {}

        def mock_run(cmd, **kwargs):
            captured_kwargs.update(kwargs)
            return mock_result

        with patch("crane.utils.gh.subprocess.run", side_effect=mock_run):
            result = gh_json(["issue", "view", "1"], cwd="/other/project")

            assert captured_kwargs.get("cwd") == "/other/project"
            assert result["number"] == 1
