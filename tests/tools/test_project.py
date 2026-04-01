"""
TDD tests for project management tools.
RED phase: define expected behavior before implementation.

gh and git calls are mocked.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from crane.tools.project import register_tools


def _mock_subprocess_dispatch(mock_gh, mock_git):
    def _run(cmd, **kwargs):
        if cmd and cmd[0] == "gh":
            return mock_gh.run(cmd, **kwargs)
        return mock_git.run(cmd, **kwargs)

    return _run


class _ToolCollector:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


@pytest.fixture
def project_tools():
    collector = _ToolCollector()
    register_tools(collector)
    return collector.tools


class TestInitResearch:
    def test_registered(self, project_tools):
        assert "init_research" in project_tools

    def test_creates_references_dirs(self, project_tools, tmp_project, mock_gh, mock_git):
        dispatcher = _mock_subprocess_dispatch(mock_gh, mock_git)
        with (
            patch("crane.utils.gh.subprocess.run", side_effect=dispatcher),
            patch("crane.utils.git.subprocess.run", side_effect=dispatcher),
        ):
            project_tools["init_research"](project_dir=str(tmp_project))

        assert (tmp_project / "references" / "papers").is_dir()
        assert (tmp_project / "references" / "pdfs").is_dir()

    def test_creates_bibliography_bib(self, project_tools, tmp_project, mock_gh, mock_git):
        dispatcher = _mock_subprocess_dispatch(mock_gh, mock_git)
        with (
            patch("crane.utils.gh.subprocess.run", side_effect=dispatcher),
            patch("crane.utils.git.subprocess.run", side_effect=dispatcher),
        ):
            project_tools["init_research"](project_dir=str(tmp_project))

        assert (tmp_project / "references" / "bibliography.bib").is_file()

    def test_creates_phase_labels(self, project_tools, tmp_project, mock_gh, mock_git):
        """Should call gh label create for each phase."""
        dispatcher = _mock_subprocess_dispatch(mock_gh, mock_git)
        with (
            patch("crane.utils.gh.subprocess.run", side_effect=dispatcher),
            patch("crane.utils.git.subprocess.run", side_effect=dispatcher),
        ):
            project_tools["init_research"](project_dir=str(tmp_project))

        calls_as_str = [" ".join(cmd) for cmd in mock_gh.calls]
        for phase in ["literature-review", "proposal", "experiment", "writing", "review"]:
            assert any(f"label create phase:{phase}" in cmd for cmd in calls_as_str)

    def test_creates_type_labels(self, project_tools, tmp_project, mock_gh, mock_git):
        dispatcher = _mock_subprocess_dispatch(mock_gh, mock_git)
        with (
            patch("crane.utils.gh.subprocess.run", side_effect=dispatcher),
            patch("crane.utils.git.subprocess.run", side_effect=dispatcher),
        ):
            project_tools["init_research"](project_dir=str(tmp_project))

        calls_as_str = [" ".join(cmd) for cmd in mock_gh.calls]
        for task_type in ["search", "read", "analysis", "code", "write"]:
            assert any(f"label create type:{task_type}" in cmd for cmd in calls_as_str)

    def test_creates_priority_labels(self, project_tools, tmp_project, mock_gh, mock_git):
        dispatcher = _mock_subprocess_dispatch(mock_gh, mock_git)
        with (
            patch("crane.utils.gh.subprocess.run", side_effect=dispatcher),
            patch("crane.utils.git.subprocess.run", side_effect=dispatcher),
        ):
            project_tools["init_research"](project_dir=str(tmp_project))

        calls_as_str = [" ".join(cmd) for cmd in mock_gh.calls]
        for priority in ["high", "medium", "low"]:
            assert any(f"label create priority:{priority}" in cmd for cmd in calls_as_str)

    def test_creates_kind_labels(self, project_tools, tmp_project, mock_gh, mock_git):
        dispatcher = _mock_subprocess_dispatch(mock_gh, mock_git)
        with (
            patch("crane.utils.gh.subprocess.run", side_effect=dispatcher),
            patch("crane.utils.git.subprocess.run", side_effect=dispatcher),
        ):
            project_tools["init_research"](project_dir=str(tmp_project))

        calls_as_str = [" ".join(cmd) for cmd in mock_gh.calls]
        assert any("label create kind:task" in cmd for cmd in calls_as_str)
        assert any("label create kind:todo" in cmd for cmd in calls_as_str)

    def test_creates_milestones(self, project_tools, tmp_project, mock_gh, mock_git):
        dispatcher = _mock_subprocess_dispatch(mock_gh, mock_git)
        with (
            patch("crane.utils.gh.subprocess.run", side_effect=dispatcher),
            patch("crane.utils.git.subprocess.run", side_effect=dispatcher),
        ):
            project_tools["init_research"](project_dir=str(tmp_project))

        calls_as_str = [" ".join(cmd) for cmd in mock_gh.calls]
        milestone_calls = [cmd for cmd in calls_as_str if "api -X POST" in cmd]
        assert len(milestone_calls) == 5
        assert any("title=Phase 1: Literature Review" in cmd for cmd in milestone_calls)

    def test_creates_issue_template(self, project_tools, tmp_project, mock_gh, mock_git):
        dispatcher = _mock_subprocess_dispatch(mock_gh, mock_git)
        with (
            patch("crane.utils.gh.subprocess.run", side_effect=dispatcher),
            patch("crane.utils.git.subprocess.run", side_effect=dispatcher),
        ):
            project_tools["init_research"](project_dir=str(tmp_project))

        issue_template = tmp_project / ".github" / "ISSUE_TEMPLATE" / "research-task.yml"
        assert issue_template.is_file()
        assert "Research Task" in issue_template.read_text(encoding="utf-8")

    def test_custom_phases(self, project_tools, tmp_project, mock_gh, mock_git):
        """Should accept custom phase list."""
        custom_phases = ["discovery", "validation"]

        dispatcher = _mock_subprocess_dispatch(mock_gh, mock_git)
        with (
            patch("crane.utils.gh.subprocess.run", side_effect=dispatcher),
            patch("crane.utils.git.subprocess.run", side_effect=dispatcher),
        ):
            project_tools["init_research"](
                phases=custom_phases,
                project_dir=str(tmp_project),
            )

        calls_as_str = [" ".join(cmd) for cmd in mock_gh.calls]
        assert any("label create phase:discovery" in cmd for cmd in calls_as_str)
        assert any("label create phase:validation" in cmd for cmd in calls_as_str)
        assert not any("label create phase:literature-review" in cmd for cmd in calls_as_str)
        milestone_calls = [cmd for cmd in calls_as_str if "api -X POST" in cmd]
        assert len(milestone_calls) == 2


class TestGetProjectInfo:
    def test_registered(self, project_tools):
        assert "get_project_info" in project_tools

    def test_returns_repo_name(self, project_tools, mock_git, mock_gh):
        dispatcher = _mock_subprocess_dispatch(mock_gh, mock_git)
        with (
            patch("crane.utils.git.subprocess.run", side_effect=dispatcher),
            patch("crane.utils.gh.subprocess.run", side_effect=dispatcher),
        ):
            info = project_tools["get_project_info"]()

        assert info["repo"] == "testuser/test-research"

    def test_returns_branch(self, project_tools, mock_git, mock_gh):
        dispatcher = _mock_subprocess_dispatch(mock_gh, mock_git)
        with (
            patch("crane.utils.git.subprocess.run", side_effect=dispatcher),
            patch("crane.utils.gh.subprocess.run", side_effect=dispatcher),
        ):
            info = project_tools["get_project_info"]()

        assert info["branch"] == "main"

    def test_returns_milestone_progress(self, project_tools, mock_git, mock_gh):
        mock_gh.set_response(
            "api repos/testuser/test-research/milestones",
            '[{"title":"Phase 1: Literature Review","open_issues":3,"closed_issues":7}]',
        )

        dispatcher = _mock_subprocess_dispatch(mock_gh, mock_git)
        with (
            patch("crane.utils.git.subprocess.run", side_effect=dispatcher),
            patch("crane.utils.gh.subprocess.run", side_effect=dispatcher),
        ):
            info = project_tools["get_project_info"]()

        assert info["milestones"][0]["name"] == "Phase 1: Literature Review"
        assert info["milestones"][0]["progress"] == "70%"

    def test_returns_reference_count(self, project_tools, mock_git, mock_gh, tmp_project):
        papers_dir = Path(tmp_project) / "references" / "papers"
        (papers_dir / "one.yaml").write_text("key: one\n", encoding="utf-8")
        (papers_dir / "two.yaml").write_text("key: two\n", encoding="utf-8")

        dispatcher = _mock_subprocess_dispatch(mock_gh, mock_git)
        with (
            patch("crane.utils.git.subprocess.run", side_effect=dispatcher),
            patch("crane.utils.gh.subprocess.run", side_effect=dispatcher),
        ):
            info = project_tools["get_project_info"](project_dir=str(tmp_project))

        assert info["references_count"] == 2
