"""
TDD tests for task management tools (GitHub Issues via gh CLI).
RED phase: define expected behavior before implementation.

All gh CLI calls are mocked — no real GitHub API interaction.
"""

# pyright: reportMissingImports=false

import json
from types import SimpleNamespace
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


@pytest.fixture(autouse=True)
def mock_workspace():
    with patch(
        "crane.tools.tasks.resolve_workspace",
        return_value=SimpleNamespace(project_root=None),
    ):
        yield


class TestCreateTask:
    def test_registered(self, task_tools):
        assert "create_task" in task_tools

    def test_returns_number_and_url(self, task_tools, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            result = task_tools["create_task"](title="[LIT] Survey of X", body="task body")

        assert result == {"number": 1, "url": "https://github.com/test/repo/issues/1"}
        assert mock_gh.calls[0][:7] == [
            "gh",
            "issue",
            "create",
            "--title",
            "[LIT] Survey of X",
            "--body",
            "task body",
        ]
        label_idx = mock_gh.calls[0].index("--label")
        labels = mock_gh.calls[0][label_idx + 1].split(",")
        assert "crane" in labels
        assert "kind:task" in labels
        assignee_idx = mock_gh.calls[0].index("--assignee")
        assert mock_gh.calls[0][assignee_idx + 1] == "@me"

    def test_includes_phase_label(self, task_tools, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            task_tools["create_task"](title="Task", phase="literature-review")

        assert "--label" in mock_gh.calls[0]
        label_idx = mock_gh.calls[0].index("--label")
        labels = mock_gh.calls[0][label_idx + 1].split(",")
        assert "crane" in labels
        assert "kind:task" in labels
        assert "phase:literature-review" in labels

    def test_includes_type_label(self, task_tools, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            task_tools["create_task"](title="Task", task_type="analysis")

        label_idx = mock_gh.calls[0].index("--label")
        labels = mock_gh.calls[0][label_idx + 1].split(",")
        assert "crane" in labels
        assert "kind:task" in labels
        assert "type:analysis" in labels

    def test_includes_priority_label(self, task_tools, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            task_tools["create_task"](title="Task", priority="high")

        label_idx = mock_gh.calls[0].index("--label")
        labels = mock_gh.calls[0][label_idx + 1].split(",")
        assert "crane" in labels
        assert "kind:task" in labels
        assert "priority:high" in labels

    def test_sets_milestone(self, task_tools, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            task_tools["create_task"](title="Task", milestone="Literature Review")

        assert "--milestone" in mock_gh.calls[0]
        ms_idx = mock_gh.calls[0].index("--milestone")
        assert mock_gh.calls[0][ms_idx + 1] == "Literature Review"

    def test_sets_assignee(self, task_tools, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            task_tools["create_task"](title="Task", assignee="alice")

        assert "--assignee" in mock_gh.calls[0]
        assignee_idx = mock_gh.calls[0].index("--assignee")
        assert mock_gh.calls[0][assignee_idx + 1] == "alice"


class TestListTasks:
    def test_registered(self, task_tools):
        assert "list_tasks" in task_tools

    def test_returns_list(self, task_tools, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            result = task_tools["list_tasks"]()

        assert isinstance(result, list)
        assert result[0]["number"] == 1
        assert result[0]["title"] == "[LIT] Survey of X"
        assert mock_gh.calls[0][:3] == ["gh", "issue", "list"]

    def test_filters_by_phase(self, task_tools, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            task_tools["list_tasks"](phase="literature-review")

        assert "--label" in mock_gh.calls[0]
        label_idx = mock_gh.calls[0].index("--label")
        labels = mock_gh.calls[0][label_idx + 1].split(",")
        assert "crane" in labels
        assert "kind:task" in labels
        assert "phase:literature-review" in labels

    def test_filters_by_state(self, task_tools, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            task_tools["list_tasks"](state="closed")

        state_idx = mock_gh.calls[0].index("--state")
        assert mock_gh.calls[0][state_idx + 1] == "closed"

    def test_filters_by_milestone(self, task_tools, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            task_tools["list_tasks"](milestone="M1")

        assert "--milestone" in mock_gh.calls[0]
        ms_idx = mock_gh.calls[0].index("--milestone")
        assert mock_gh.calls[0][ms_idx + 1] == "M1"


class TestViewTask:
    def test_registered(self, task_tools):
        assert "view_task" in task_tools

    def test_returns_full_issue(self, task_tools, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            result = task_tools["view_task"](1)

        assert result["number"] == 1
        assert result["title"] == "[LIT] Survey of X"
        assert result["body"] == "task body"
        assert mock_gh.calls[0][:4] == ["gh", "issue", "view", "1"]

    def test_includes_comments(self, task_tools, mock_gh):
        mock_gh.set_response(
            "issue view",
            json.dumps(
                {
                    "number": 2,
                    "title": "Task",
                    "body": "Body",
                    "state": "open",
                    "comments": [{"author": {"login": "alice"}, "body": "update"}],
                }
            ),
        )
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            result = task_tools["view_task"](2)

        assert "comments" in result
        assert len(result["comments"]) == 1
        assert result["comments"][0]["body"] == "update"


class TestUpdateTask:
    def test_registered(self, task_tools):
        assert "update_task" in task_tools

    def test_adds_labels(self, task_tools, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            result = task_tools["update_task"](
                1,
                add_labels=["phase:experiment", "priority:high"],
            )

        assert result == "Task #1 updated"
        assert "--add-label" in mock_gh.calls[0]
        label_idx = mock_gh.calls[0].index("--add-label")
        assert mock_gh.calls[0][label_idx + 1] == "phase:experiment,priority:high"

    def test_removes_labels(self, task_tools, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            task_tools["update_task"](1, remove_labels=["priority:low", "type:read"])

        assert "--remove-label" in mock_gh.calls[0]
        label_idx = mock_gh.calls[0].index("--remove-label")
        assert mock_gh.calls[0][label_idx + 1] == "priority:low,type:read"

    def test_changes_milestone(self, task_tools, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            task_tools["update_task"](1, milestone="Experiment")

        assert "--milestone" in mock_gh.calls[0]
        ms_idx = mock_gh.calls[0].index("--milestone")
        assert mock_gh.calls[0][ms_idx + 1] == "Experiment"


class TestReportProgress:
    def test_registered(self, task_tools):
        assert "report_progress" in task_tools

    def test_posts_comment(self, task_tools, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            result = task_tools["report_progress"](1, "Finished baseline run")

        assert result == "Progress reported on task #1"
        assert mock_gh.calls[0] == [
            "gh",
            "issue",
            "comment",
            "1",
            "--body",
            "Finished baseline run",
        ]


class TestCloseTask:
    def test_registered(self, task_tools):
        assert "close_task" in task_tools

    def test_closes_with_reason(self, task_tools, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            result = task_tools["close_task"](1, reason="not_planned")

        assert result == "Task #1 closed (not_planned)"
        assert mock_gh.calls[0] == [
            "gh",
            "issue",
            "close",
            "1",
            "--reason",
            "not_planned",
        ]

    def test_closes_with_comment(self, task_tools, mock_gh):
        with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
            task_tools["close_task"](1, comment="superseded by #2")

        assert "--comment" in mock_gh.calls[0]
        comment_idx = mock_gh.calls[0].index("--comment")
        assert mock_gh.calls[0][comment_idx + 1] == "superseded by #2"


class TestGetMilestoneProgress:
    def test_registered(self, task_tools):
        assert "get_milestone_progress" in task_tools

    def test_returns_all_milestones(self, task_tools, mock_gh):
        mock_gh.set_response(
            "api repos/testuser/test-research/milestones?state=all",
            json.dumps(
                [
                    {"title": "Literature", "open_issues": 2, "closed_issues": 3},
                    {"title": "Experiment", "open_issues": 1, "closed_issues": 1},
                ]
            ),
        )

        with patch(
            "crane.services.task_service.get_owner_repo", return_value=("testuser", "test-research")
        ):
            with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
                result = task_tools["get_milestone_progress"]()

        assert len(result) == 2
        assert result[0] == {
            "title": "Literature",
            "open": 2,
            "closed": 3,
            "progress": 60.0,
        }
        assert mock_gh.calls[0] == [
            "gh",
            "api",
            "repos/testuser/test-research/milestones?state=all",
        ]

    def test_filters_by_name(self, task_tools, mock_gh):
        mock_gh.set_response(
            "api repos/testuser/test-research/milestones?state=all",
            json.dumps(
                [
                    {"title": "Literature", "open_issues": 2, "closed_issues": 3},
                    {"title": "Experiment", "open_issues": 1, "closed_issues": 1},
                ]
            ),
        )

        with patch(
            "crane.services.task_service.get_owner_repo", return_value=("testuser", "test-research")
        ):
            with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
                result = task_tools["get_milestone_progress"]("Experiment")

        assert len(result) == 1
        assert result[0]["title"] == "Experiment"
        assert result[0]["progress"] == 50.0
