"""
TDD tests for project management tools.
RED phase: define expected behavior before implementation.

gh and git calls are mocked.
"""

import pytest
from unittest.mock import patch

from crane.tools.project import register_tools


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
        pass

    def test_creates_bibliography_bib(self, project_tools, tmp_project, mock_gh, mock_git):
        pass

    def test_creates_phase_labels(self, project_tools, tmp_project, mock_gh, mock_git):
        """Should call gh label create for each phase."""
        pass

    def test_creates_type_labels(self, project_tools, tmp_project, mock_gh, mock_git):
        pass

    def test_creates_priority_labels(self, project_tools, tmp_project, mock_gh, mock_git):
        pass

    def test_creates_milestones(self, project_tools, tmp_project, mock_gh, mock_git):
        pass

    def test_creates_issue_template(self, project_tools, tmp_project, mock_gh, mock_git):
        pass

    def test_custom_phases(self, project_tools, tmp_project, mock_gh, mock_git):
        """Should accept custom phase list."""
        pass


class TestGetProjectInfo:
    def test_registered(self, project_tools):
        assert "get_project_info" in project_tools

    def test_returns_repo_name(self, project_tools, mock_git):
        pass

    def test_returns_branch(self, project_tools, mock_git):
        pass

    def test_returns_milestone_progress(self, project_tools, mock_git, mock_gh):
        pass

    def test_returns_reference_count(self, project_tools, mock_git, tmp_project):
        pass
