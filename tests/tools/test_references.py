"""
TDD tests for reference management tools.
RED phase: define expected behavior before implementation.

These tests verify the MCP tool functions directly,
mocking the filesystem via tmp_project fixture.
"""

import pytest

from crane.tools.references import register_tools


# To test the tool functions, we register them on a mock MCP and extract them.
# This pattern allows testing tool logic without a running MCP server.


class _ToolCollector:
    """Minimal mock MCP server that collects registered tools."""

    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


@pytest.fixture
def ref_tools():
    collector = _ToolCollector()
    register_tools(collector)
    return collector.tools


class TestAddReference:
    def test_registered(self, ref_tools):
        assert "add_reference" in ref_tools

    def test_creates_yaml_file(self, ref_tools, tmp_project):
        # Will test after implementation lands
        pass

    def test_appends_to_bibtex(self, ref_tools, tmp_project):
        pass


class TestListReferences:
    def test_registered(self, ref_tools):
        assert "list_references" in ref_tools

    def test_empty_returns_empty_list(self, ref_tools):
        pass

    def test_returns_summary_fields(self, ref_tools):
        pass

    def test_filter_by_keyword(self, ref_tools):
        pass

    def test_filter_by_tag(self, ref_tools):
        pass


class TestGetReference:
    def test_registered(self, ref_tools):
        assert "get_reference" in ref_tools

    def test_returns_full_data(self, ref_tools):
        pass

    def test_nonexistent_key(self, ref_tools):
        pass


class TestSearchReferences:
    def test_registered(self, ref_tools):
        assert "search_references" in ref_tools

    def test_matches_title(self, ref_tools):
        pass

    def test_matches_abstract(self, ref_tools):
        pass

    def test_no_match_returns_empty(self, ref_tools):
        pass


class TestRemoveReference:
    def test_registered(self, ref_tools):
        assert "remove_reference" in ref_tools

    def test_removes_yaml(self, ref_tools):
        pass

    def test_removes_bibtex_entry(self, ref_tools):
        pass

    def test_optionally_removes_pdf(self, ref_tools):
        pass


class TestAnnotateReference:
    def test_registered(self, ref_tools):
        assert "annotate_reference" in ref_tools

    def test_writes_annotations(self, ref_tools):
        pass

    def test_updates_existing_annotations(self, ref_tools):
        pass
