"""
TDD tests for task management tools (GitHub Issues via gh CLI).
RED phase: define expected behavior before implementation.

All gh CLI calls are mocked — no real GitHub API interaction.
"""

import json
from unittest.mock import patch

import pytest

from crane.tools.tasks import register_tools


class _ToolCollector:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


@pytest.fixture
def task_tools():
    collector = _ToolCollector()
    register_tools(collector)
    return collector.tools


class TestCreateTask:
    def test_registered(self, task_tools):
        assert "create_task" in task_tools

    def test_returns_number_and_url(self, task_tools, mock_gh):
        pass

    def test_includes_phase_label(self, task_tools, mock_gh):
        pass

    def test_includes_type_label(self, task_tools, mock_gh):
        pass

    def test_includes_priority_label(self, task_tools, mock_gh):
        pass

    def test_sets_milestone(self, task_tools, mock_gh):
        pass

    def test_sets_assignee(self, task_tools, mock_gh):
        pass


class TestListTasks:
    def test_registered(self, task_tools):
        assert "list_tasks" in task_tools

    def test_returns_list(self, task_tools, mock_gh):
        pass

    def test_filters_by_phase(self, task_tools, mock_gh):
        pass

    def test_filters_by_state(self, task_tools, mock_gh):
        pass

    def test_filters_by_milestone(self, task_tools, mock_gh):
        pass


class TestViewTask:
    def test_registered(self, task_tools):
        assert "view_task" in task_tools

    def test_returns_full_issue(self, task_tools, mock_gh):
        pass

    def test_includes_comments(self, task_tools, mock_gh):
        pass


class TestUpdateTask:
    def test_registered(self, task_tools):
        assert "update_task" in task_tools

    def test_adds_labels(self, task_tools, mock_gh):
        pass

    def test_removes_labels(self, task_tools, mock_gh):
        pass

    def test_changes_milestone(self, task_tools, mock_gh):
        pass


class TestReportProgress:
    def test_registered(self, task_tools):
        assert "report_progress" in task_tools

    def test_posts_comment(self, task_tools, mock_gh):
        pass


class TestCloseTask:
    def test_registered(self, task_tools):
        assert "close_task" in task_tools

    def test_closes_with_reason(self, task_tools, mock_gh):
        pass

    def test_closes_with_comment(self, task_tools, mock_gh):
        pass


class TestGetMilestoneProgress:
    def test_registered(self, task_tools):
        assert "get_milestone_progress" in task_tools

    def test_returns_all_milestones(self, task_tools, mock_gh):
        pass

    def test_filters_by_name(self, task_tools, mock_gh):
        pass
