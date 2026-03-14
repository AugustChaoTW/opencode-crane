"""
TDD integration tests for end-to-end research workflows.
RED phase: define expected behavior before implementation.

These tests simulate a full research session:
init → search → add references → create tasks → report → close.
All external calls (gh, git, arXiv) are mocked.
"""

import pytest


class TestLiteratureReviewWorkflow:
    """Phase 1: init project → search papers → add references → annotate."""

    def test_init_then_add_reference(self, tmp_project):
        """After init_research, add_reference should write to references/papers/."""
        pass

    def test_search_then_add_creates_valid_yaml(self, tmp_project, mock_arxiv_response):
        """search_papers result can be passed to add_reference and produce valid YAML."""
        pass

    def test_add_reference_then_list(self, tmp_project):
        """After adding 2 references, list_references returns both."""
        pass

    def test_annotate_then_get(self, tmp_project):
        """annotate_reference updates ai_annotations, get_reference shows them."""
        pass


class TestTaskTrackingWorkflow:
    """Phase 2: create tasks → list → report progress → close."""

    def test_create_then_list(self, mock_gh):
        """create_task then list_tasks returns the created task."""
        pass

    def test_report_progress_then_view(self, mock_gh):
        """report_progress adds comment visible in view_task."""
        pass

    def test_close_task_changes_state(self, mock_gh):
        """close_task marks the issue as completed."""
        pass


class TestCrossPhaseWorkflow:
    """Connecting references to tasks."""

    def test_annotate_with_related_issues(self, tmp_project, mock_gh):
        """annotate_reference with related_issues links papers to tasks."""
        pass

    def test_milestone_progress_after_closing_tasks(self, mock_gh):
        """get_milestone_progress reflects closed tasks."""
        pass
