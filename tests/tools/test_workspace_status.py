"""
Tests for workspace_status tool.
Validates workspace overview functionality.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crane.tools.workspace import register_tools


class _ToolCollector:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


@pytest.fixture
def workspace_tools():
    collector = _ToolCollector()
    register_tools(collector)
    return collector.tools


@pytest.fixture
def sample_workspace(tmp_path):
    """Create a sample workspace with references."""
    refs_dir = tmp_path / "references"
    papers_dir = refs_dir / "papers"
    pdfs_dir = refs_dir / "pdfs"
    papers_dir.mkdir(parents=True)
    pdfs_dir.mkdir(parents=True)
    (refs_dir / "bibliography.bib").write_text("@article{test,}", encoding="utf-8")

    # Create sample paper
    (papers_dir / "test2024-paper.yaml").write_text(
        """key: test2024-paper
title: Test Paper
authors: [Author]
year: 2024
""",
        encoding="utf-8",
    )

    # Create sample PDF
    (pdfs_dir / "test2024-paper.pdf").write_bytes(b"fake pdf")

    return tmp_path


class MockGh:
    """Mock for gh CLI calls."""

    def __init__(self):
        self.calls: list[list[str]] = []

    def run(self, cmd, **kwargs):
        m = MagicMock()
        m.returncode = 0
        m.stderr = ""
        cmd_str = " ".join(cmd)

        if "issue list" in cmd_str:
            if "kind:todo" in cmd_str:
                m.stdout = json.dumps([{"number": 10, "title": "Review paper X", "state": "OPEN"}])
            elif "kind:task" in cmd_str:
                m.stdout = json.dumps(
                    [
                        {"number": 5, "title": "Search for papers", "state": "OPEN"},
                        {"number": 6, "title": "Write introduction", "state": "OPEN"},
                    ]
                )
            else:
                m.stdout = "[]"
        elif "milestones" in cmd_str:
            m.stdout = json.dumps(
                [
                    {"title": "Phase 1", "open_issues": 3, "closed_issues": 2},
                ]
            )
        else:
            m.stdout = ""

        self.calls.append(cmd)
        return m


class TestWorkspaceStatusRegistered:
    """Test tool registration."""

    def test_registered(self, workspace_tools):
        assert "workspace_status" in workspace_tools


class TestWorkspaceStatusReturnsOverview:
    """Test workspace_status returns correct overview."""

    def test_returns_workspace_info(self, workspace_tools, sample_workspace, tmp_path):
        mock_gh = MockGh()

        with patch("crane.workspace.get_repo_root", return_value=str(sample_workspace)):
            with patch("crane.workspace.get_owner_repo", return_value=("testuser", "test-repo")):
                with patch(
                    "crane.services.task_service.get_owner_repo",
                    return_value=("testuser", "test-repo"),
                ):
                    with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
                        result = workspace_tools["workspace_status"]()

        assert "workspace" in result
        assert result["workspace"]["repo"] == "testuser/test-repo"

    def test_returns_reference_counts(self, workspace_tools, sample_workspace, tmp_path):
        mock_gh = MockGh()

        with patch("crane.workspace.get_repo_root", return_value=str(sample_workspace)):
            with patch("crane.workspace.get_owner_repo", return_value=("testuser", "test-repo")):
                with patch(
                    "crane.services.task_service.get_owner_repo",
                    return_value=("testuser", "test-repo"),
                ):
                    with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
                        result = workspace_tools["workspace_status"]()

        assert "references" in result
        assert result["references"]["papers"] == 1
        assert result["references"]["pdfs"] == 1
        assert result["references"]["bibliography"] is True

    def test_returns_tasks(self, workspace_tools, sample_workspace, tmp_path):
        mock_gh = MockGh()

        with patch("crane.workspace.get_repo_root", return_value=str(sample_workspace)):
            with patch("crane.workspace.get_owner_repo", return_value=("testuser", "test-repo")):
                with patch(
                    "crane.services.task_service.get_owner_repo",
                    return_value=("testuser", "test-repo"),
                ):
                    with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
                        result = workspace_tools["workspace_status"]()

        assert "tasks" in result
        assert len(result["tasks"]) == 2

    def test_returns_todos(self, workspace_tools, sample_workspace, tmp_path):
        mock_gh = MockGh()

        with patch("crane.workspace.get_repo_root", return_value=str(sample_workspace)):
            with patch("crane.workspace.get_owner_repo", return_value=("testuser", "test-repo")):
                with patch(
                    "crane.services.task_service.get_owner_repo",
                    return_value=("testuser", "test-repo"),
                ):
                    with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
                        result = workspace_tools["workspace_status"]()

        assert "todos" in result
        assert len(result["todos"]) == 1

    def test_returns_milestones(self, workspace_tools, sample_workspace, tmp_path):
        mock_gh = MockGh()

        with patch("crane.workspace.get_repo_root", return_value=str(sample_workspace)):
            with patch("crane.workspace.get_owner_repo", return_value=("testuser", "test-repo")):
                with patch(
                    "crane.services.task_service.get_owner_repo",
                    return_value=("testuser", "test-repo"),
                ):
                    with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
                        result = workspace_tools["workspace_status"]()

        assert "milestones" in result
        assert len(result["milestones"]) == 1


class TestWorkspaceStatusAutoDetect:
    """Test auto-detection from git context."""

    def test_auto_detect_from_none(self, workspace_tools, sample_workspace, tmp_path):
        mock_gh = MockGh()

        with patch("crane.workspace.get_repo_root", return_value=str(sample_workspace)):
            with patch("crane.workspace.get_owner_repo", return_value=("auto", "detect")):
                with patch(
                    "crane.services.task_service.get_owner_repo", return_value=("auto", "detect")
                ):
                    with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
                        result = workspace_tools["workspace_status"](project_dir=None)

        assert result["workspace"]["repo"] == "auto/detect"


class TestWorkspaceStatusEmptyWorkspace:
    """Test with empty references directory."""

    def test_empty_references(self, workspace_tools, tmp_path):
        refs_dir = tmp_path / "references"
        refs_dir.mkdir(parents=True)
        (refs_dir / "bibliography.bib").touch()

        mock_gh = MockGh()

        with patch("crane.workspace.get_repo_root", return_value=str(tmp_path)):
            with patch("crane.workspace.get_owner_repo", return_value=("user", "repo")):
                with patch(
                    "crane.services.task_service.get_owner_repo", return_value=("user", "repo")
                ):
                    with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
                        result = workspace_tools["workspace_status"]()

        assert result["references"]["papers"] == 0
        assert result["references"]["pdfs"] == 0
