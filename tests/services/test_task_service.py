"""
Unit tests for TaskService.
Tests GitHub Issues task management via gh CLI.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from crane.services.task_service import TaskService


class MockGh:
    """Mock for gh CLI subprocess calls."""

    def __init__(self):
        self.calls: list[list[str]] = []
        self.responses: dict[str, str] = {}

    def set_response(self, pattern: str, response: str):
        self.responses[pattern] = response

    def run(self, cmd, **kwargs):
        from unittest.mock import MagicMock

        m = MagicMock()
        m.returncode = 0
        m.stderr = ""

        cmd_str = " ".join(cmd)
        for pattern, response in self.responses.items():
            if pattern in cmd_str:
                m.stdout = response
                break
        else:
            if "issue create" in cmd_str:
                m.stdout = "https://github.com/test/repo/issues/42\n"
            elif "issue list" in cmd_str:
                m.stdout = "[]"
            elif "issue view" in cmd_str:
                m.stdout = json.dumps(
                    {
                        "number": 1,
                        "title": "Test",
                        "body": "Body",
                        "state": "OPEN",
                        "labels": [],
                        "comments": [],
                    }
                )
            else:
                m.stdout = ""

        self.calls.append(cmd)
        return m


@pytest.fixture
def mock_gh():
    return MockGh()


@pytest.fixture
def task_service():
    return TaskService(project_dir=None)


class TestTaskServiceCreate:
    """Test creating tasks."""

    def test_create_returns_number_and_url(self, task_service, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            result = task_service.create(title="Test task")

        assert "number" in result
        assert "url" in result
        assert result["number"] == 42

    def test_create_with_labels(self, task_service, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            task_service.create(
                title="Test",
                phase="literature-review",
                task_type="search",
                priority="high",
            )

        cmd = mock_gh.calls[0]
        assert "--label" in cmd
        label_idx = cmd.index("--label") + 1
        labels = cmd[label_idx].split(",")
        assert "phase:literature-review" in labels
        assert "type:search" in labels
        assert "priority:high" in labels


class TestTaskServiceList:
    """Test listing tasks."""

    def test_list_returns_list(self, task_service, mock_gh):
        mock_gh.set_response(
            "issue list",
            json.dumps([{"number": 1, "title": "Task 1", "state": "OPEN"}]),
        )

        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            result = task_service.list()

        assert isinstance(result, list)
        assert len(result) == 1

    def test_list_empty(self, task_service, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            result = task_service.list()

        assert result == []


class TestTaskServiceView:
    """Test viewing task details."""

    def test_view_returns_dict(self, task_service, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            result = task_service.view(1)

        assert isinstance(result, dict)


class TestTaskServiceUpdate:
    """Test updating tasks."""

    def test_update_returns_confirmation(self, task_service, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            result = task_service.update(1, title="New title")

        assert "updated" in result.lower()


class TestTaskServiceReportProgress:
    """Test reporting progress."""

    def test_report_returns_confirmation(self, task_service, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            result = task_service.report_progress(1, "Progress update")

        assert "reported" in result.lower()


class TestTaskServiceClose:
    """Test closing tasks."""

    def test_close_returns_confirmation(self, task_service, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            result = task_service.close(1, reason="completed")

        assert "closed" in result.lower()


class TestTaskServiceMilestoneProgress:
    """Test milestone progress."""

    def test_get_milestone_progress(self, task_service, mock_gh):
        mock_gh.set_response(
            "milestones?state=all",
            json.dumps(
                [
                    {"title": "Phase 1", "open_issues": 2, "closed_issues": 3},
                    {"title": "Phase 2", "open_issues": 5, "closed_issues": 0},
                ]
            ),
        )

        with patch("crane.services.task_service.get_owner_repo", return_value=("user", "repo")):
            with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
                result = task_service.get_milestone_progress()

        assert len(result) == 2
        assert result[0]["title"] == "Phase 1"
        assert result[0]["progress"] == 60.0

    def test_filter_by_milestone_name(self, task_service, mock_gh):
        mock_gh.set_response(
            "milestones?state=all",
            json.dumps(
                [
                    {"title": "Phase 1", "open_issues": 2, "closed_issues": 3},
                    {"title": "Phase 2", "open_issues": 5, "closed_issues": 0},
                ]
            ),
        )

        with patch("crane.services.task_service.get_owner_repo", return_value=("user", "repo")):
            with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
                result = task_service.get_milestone_progress("Phase 2")

        assert len(result) == 1
        assert result[0]["title"] == "Phase 2"
