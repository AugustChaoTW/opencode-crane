"""Tests for TaskService label behavior."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from crane.services.task_service import TaskService


class MockGh:
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


class TestTaskServiceLabels:
    def test_create_with_phase_only(self, task_service, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            task_service.create(title="Test", phase="writing")

        cmd = mock_gh.calls[0]
        label_idx = cmd.index("--label") + 1
        labels = cmd[label_idx].split(",")
        assert "phase:writing" in labels
        assert "crane" not in labels
        assert "kind:task" not in labels

    def test_create_with_all_labels(self, task_service, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            task_service.create(
                title="Test",
                phase="literature-review",
                task_type="search",
                priority="high",
            )

        cmd = mock_gh.calls[0]
        label_idx = cmd.index("--label") + 1
        labels = cmd[label_idx].split(",")
        assert "phase:literature-review" in labels
        assert "type:search" in labels
        assert "priority:high" in labels
        assert "crane" not in labels
        assert "kind:task" not in labels

    def test_create_with_explicit_kind_label(self, task_service, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            task_service.create(title="Test", kind="todo")

        cmd = mock_gh.calls[0]
        label_idx = cmd.index("--label") + 1
        labels = cmd[label_idx].split(",")
        assert "kind:todo" in labels

    def test_list_with_explicit_kind_filter(self, task_service, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            task_service.list(kind="todo")

        cmd = mock_gh.calls[0]
        label_idx = cmd.index("--label") + 1
        labels = cmd[label_idx].split(",")
        assert "kind:todo" in labels


class TestTaskServiceBuildLabels:
    def test_build_labels_excludes_nonexistent(self):
        labels = TaskService._build_labels(
            TaskService,
            phase="literature-review",
            task_type="search",
            priority="high",
        )
        assert "crane" not in labels
        assert "kind:task" not in labels
        assert "phase:literature-review" in labels
        assert "type:search" in labels
        assert "priority:high" in labels
