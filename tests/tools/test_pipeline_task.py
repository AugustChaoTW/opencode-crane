"""
Tests for pipeline task creation.
Verifies that create_task step uses only existing labels.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


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
            # Check that only existing labels are used
            if "--label" in cmd:
                label_idx = cmd.index("--label") + 1
                labels = cmd[label_idx].split(",")
                # Verify no non-existent labels
                invalid_labels = [l for l in labels if l in ["crane", "kind:task", "kind:todo"]]
                if invalid_labels:
                    m.returncode = 1
                    m.stderr = f"Invalid labels: {invalid_labels}"
                    m.stdout = ""
                    self.calls.append(cmd)
                    return m

            m.stdout = "https://github.com/test/repo/issues/99\n"
        else:
            m.stdout = ""

        self.calls.append(cmd)
        return m


class TestPipelineTaskCreation:
    """Test that pipeline creates tasks with valid labels."""

    def test_create_task_uses_existing_labels_only(self):
        """Verify create_task only uses labels that exist in repo."""
        from crane.services.task_service import TaskService

        mock_gh = MockGh()
        svc = TaskService(project_dir=None)

        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            result = svc.create(
                title="[LIT] Literature review: test",
                body="Test task",
                phase="literature-review",
                task_type="search",
                priority="medium",
            )

        # Verify gh was called
        assert len(mock_gh.calls) == 1
        cmd = mock_gh.calls[0]

        # Verify labels are valid
        if "--label" in cmd:
            label_idx = cmd.index("--label") + 1
            labels = cmd[label_idx].split(",")
            # Should only contain existing labels
            assert "crane" not in labels
            assert "kind:task" not in labels
            assert "phase:literature-review" in labels
            assert "type:search" in labels
            assert "priority:medium" in labels

    def test_build_labels_excludes_nonexistent(self):
        """Verify _build_labels doesn't include crane or kind:*."""
        from crane.services.task_service import TaskService

        labels = TaskService._build_labels(
            TaskService,
            phase="literature-review",
            task_type="search",
            priority="high",
            item_type="task",
        )

        assert "crane" not in labels
        assert "kind:task" not in labels
        assert "phase:literature-review" in labels
        assert "type:search" in labels
        assert "priority:high" in labels
