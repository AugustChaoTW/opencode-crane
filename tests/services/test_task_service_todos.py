"""
Tests for TaskService todo support.
Validates runtime todos as GitHub Issues.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from crane.services.task_service import TaskService


class MockGh:
    """Mock for gh CLI calls."""

    def __init__(self):
        self.calls: list[list[str]] = []

    def run(self, cmd, **kwargs):
        m = MagicMock()
        m.returncode = 0
        m.stderr = ""
        cmd_str = " ".join(cmd)

        if "issue create" in cmd_str:
            m.stdout = "https://github.com/test/repo/issues/99\n"
        elif "issue list" in cmd_str:
            m.stdout = json.dumps([{"number": 1, "title": "Task 1", "state": "OPEN", "labels": []}])
        else:
            m.stdout = ""

        self.calls.append(cmd)
        return m


@pytest.fixture
def task_service():
    return TaskService(project_dir=None)


@pytest.fixture
def mock_gh():
    return MockGh()


class TestTaskServiceCreateTodo:
    """Test creating todos via TaskService."""

    def test_create_todo_has_crane_label(self, task_service, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            task_service.create(title="Review paper X", type="todo")

        cmd = mock_gh.calls[0]
        label_idx = cmd.index("--label") + 1
        labels = cmd[label_idx].split(",")
        assert "crane" in labels

    def test_create_todo_has_kind_todo_label(self, task_service, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            task_service.create(title="Review paper X", type="todo")

        cmd = mock_gh.calls[0]
        label_idx = cmd.index("--label") + 1
        labels = cmd[label_idx].split(",")
        assert "kind:todo" in labels

    def test_create_task_has_kind_task_label(self, task_service, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            task_service.create(title="Search papers", type="task")

        cmd = mock_gh.calls[0]
        label_idx = cmd.index("--label") + 1
        labels = cmd[label_idx].split(",")
        assert "kind:task" in labels

    def test_create_todo_with_phase(self, task_service, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            task_service.create(title="Review", type="todo", phase="writing")

        cmd = mock_gh.calls[0]
        label_idx = cmd.index("--label") + 1
        labels = cmd[label_idx].split(",")
        assert "phase:writing" in labels
        assert "kind:todo" in labels
        assert "crane" in labels


class TestTaskServiceListByType:
    """Test listing tasks filtered by type."""

    def test_list_todos_only(self, task_service, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            result = task_service.list(type="todo")

        cmd = mock_gh.calls[0]
        assert "--label" in cmd
        label_idx = cmd.index("--label") + 1
        assert "kind:todo" in cmd[label_idx]

    def test_list_tasks_only(self, task_service, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            result = task_service.list(type="task")

        cmd = mock_gh.calls[0]
        assert "--label" in cmd
        label_idx = cmd.index("--label") + 1
        assert "kind:task" in cmd[label_idx]


class TestTaskServiceDefaultType:
    """Test default type is task."""

    def test_default_type_is_task(self, task_service, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            task_service.create(title="Default task")

        cmd = mock_gh.calls[0]
        label_idx = cmd.index("--label") + 1
        labels = cmd[label_idx].split(",")
        assert "kind:task" in labels
