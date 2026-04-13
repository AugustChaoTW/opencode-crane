"""
Tests for Claude-usability improvements:
- check_prerequisites() tool
- list_workflows() tool
- workspace_status() capabilities & suggested_next_actions fields
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from crane.tools.pipeline import register_tools as register_pipeline_tools
from crane.tools.workspace import register_tools as register_workspace_tools


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


class _ToolCollector:
    """Minimal MCP stub that collects registered tools by name."""

    def __init__(self):
        self.tools: dict = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


@pytest.fixture
def workspace_tools():
    collector = _ToolCollector()
    register_workspace_tools(collector)
    return collector.tools


@pytest.fixture
def pipeline_tools():
    collector = _ToolCollector()
    register_pipeline_tools(collector)
    return collector.tools


@pytest.fixture
def sample_workspace(tmp_path):
    """Workspace with one paper YAML, one PDF, and a bibliography."""
    refs = tmp_path / "references"
    papers = refs / "papers"
    pdfs = refs / "pdfs"
    papers.mkdir(parents=True)
    pdfs.mkdir(parents=True)
    (refs / "bibliography.bib").write_text("@article{t,}", encoding="utf-8")
    (papers / "t2024.yaml").write_text(
        "key: t2024\ntitle: T\nauthors: [A]\nyear: 2024\n", encoding="utf-8"
    )
    (pdfs / "t2024.pdf").write_bytes(b"%PDF")
    return tmp_path


class _MockGh:
    def run(self, cmd, **kwargs):
        m = MagicMock()
        m.returncode = 0
        m.stderr = ""
        cmd_str = " ".join(cmd)
        if "issue list" in cmd_str and "kind:todo" in cmd_str:
            m.stdout = "[]"
        elif "issue list" in cmd_str:
            m.stdout = "[]"
        elif "milestones" in cmd_str or "milestone" in cmd_str:
            m.stdout = "[]"
        else:
            m.stdout = ""
        return m


def _with_workspace(tmp_path, fn):
    mock_gh = _MockGh()
    with patch("crane.workspace.get_repo_root", return_value=str(tmp_path)):
        with patch("crane.workspace.get_owner_repo", return_value=("u", "r")):
            with patch("crane.services.task_service.get_owner_repo", return_value=("u", "r")):
                with patch("crane.utils.gh.subprocess.run", side_effect=mock_gh.run):
                    return fn()


# ===========================================================================
# check_prerequisites()
# ===========================================================================


class TestCheckPrerequisitesRegistered:
    def test_tool_registered(self, workspace_tools):
        assert "check_prerequisites" in workspace_tools


class TestCheckPrerequisitesEmbeddings:
    """semantic_search requires embeddings.yaml."""

    def test_missing_embeddings_not_ready(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["check_prerequisites"]("semantic_search"),
        )
        assert result["ready"] is False
        names = [m["name"] for m in result["missing"]]
        assert "embeddings" in names

    def test_missing_embeddings_fix_with(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["check_prerequisites"]("semantic_search"),
        )
        fixes = {m["name"]: m["fix_with"] for m in result["missing"]}
        assert fixes["embeddings"] == "build_embeddings"

    def test_embeddings_present_ready(self, workspace_tools, sample_workspace):
        embeddings_file = sample_workspace / "references" / "embeddings.yaml"
        embeddings_file.write_text(yaml.dump({"t2024": [0.1] * 1536}), encoding="utf-8")

        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["check_prerequisites"]("semantic_search"),
        )
        assert result["ready"] is True
        assert result["missing"] == []

    def test_visualize_citations_same_check(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["check_prerequisites"]("visualize_citations"),
        )
        assert result["ready"] is False
        assert any(m["name"] == "embeddings" for m in result["missing"])

    def test_get_research_clusters_same_check(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["check_prerequisites"]("get_research_clusters"),
        )
        assert result["ready"] is False
        assert any(m["name"] == "embeddings" for m in result["missing"])


class TestCheckPrerequisitesChunks:
    """ask_library requires chunked papers."""

    def test_missing_chunks_not_ready(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["check_prerequisites"]("ask_library"),
        )
        assert result["ready"] is False
        assert any(m["name"] == "paper_chunks" for m in result["missing"])

    def test_missing_chunks_fix_with(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["check_prerequisites"]("ask_library"),
        )
        fixes = {m["name"]: m["fix_with"] for m in result["missing"]}
        assert fixes["paper_chunks"] == "chunk_papers"

    def test_chunks_present_ready(self, workspace_tools, sample_workspace):
        chunks_dir = sample_workspace / "references" / "chunks" / "t2024"
        chunks_dir.mkdir(parents=True)
        (chunks_dir / "chunks.yaml").write_text("- text: hello\n", encoding="utf-8")

        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["check_prerequisites"]("ask_library"),
        )
        assert result["ready"] is True


class TestCheckPrerequisitesPaperFile:
    """evaluate_paper_v2 and friends require PDF files."""

    def test_no_pdfs_not_ready(self, workspace_tools, tmp_path):
        refs = tmp_path / "references"
        (refs / "papers").mkdir(parents=True)
        (refs / "pdfs").mkdir(parents=True)
        (refs / "bibliography.bib").touch()

        result = _with_workspace(
            tmp_path,
            lambda: workspace_tools["check_prerequisites"]("evaluate_paper_v2"),
        )
        assert result["ready"] is False
        assert any(m["name"] == "paper_file" for m in result["missing"])

    def test_pdf_present_ready(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["check_prerequisites"]("evaluate_paper_v2"),
        )
        assert result["ready"] is True

    def test_review_paper_sections_same_check(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["check_prerequisites"]("review_paper_sections"),
        )
        assert result["ready"] is True

    def test_match_journal_v2_same_check(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["check_prerequisites"]("match_journal_v2"),
        )
        assert result["ready"] is True


class TestCheckPrerequisitesUnknownTool:
    """Unknown tool → warning, not failure."""

    def test_unknown_tool_has_warning(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["check_prerequisites"]("nonexistent_tool"),
        )
        assert result["ready"] is True
        assert len(result["warnings"]) > 0
        assert "nonexistent_tool" in result["warnings"][0]

    def test_unknown_tool_empty_missing(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["check_prerequisites"]("nonexistent_tool"),
        )
        assert result["missing"] == []


class TestCheckPrerequisitesReturnShape:
    def test_returns_required_keys(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["check_prerequisites"]("semantic_search"),
        )
        assert "tool" in result
        assert "ready" in result
        assert "missing" in result
        assert "warnings" in result

    def test_tool_name_echoed(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["check_prerequisites"]("semantic_search"),
        )
        assert result["tool"] == "semantic_search"


# ===========================================================================
# list_workflows()
# ===========================================================================


class TestListWorkflowsRegistered:
    def test_tool_registered(self, pipeline_tools):
        assert "list_workflows" in pipeline_tools


class TestListWorkflowsContent:
    @pytest.fixture
    def workflows(self, pipeline_tools):
        return pipeline_tools["list_workflows"]()

    def test_returns_list(self, workflows):
        assert isinstance(workflows, list)

    def test_has_five_workflows(self, workflows):
        assert len(workflows) == 5

    def test_known_workflow_names(self, workflows):
        names = {w["name"] for w in workflows}
        assert "literature-review" in names
        assert "full-setup" in names
        assert "lecun-enhanced-review" in names
        assert "submission-check" in names
        assert "paper-trace" in names

    def test_each_workflow_has_required_keys(self, workflows):
        required = {"name", "description", "use_case", "steps", "prerequisites", "estimated_time"}
        for w in workflows:
            assert required <= set(w.keys()), f"Workflow {w['name']} missing keys"

    def test_literature_review_steps(self, workflows):
        lr = next(w for w in workflows if w["name"] == "literature-review")
        assert "search" in lr["steps"]
        assert "annotate" in lr["steps"]

    def test_lecun_review_has_prerequisites(self, workflows):
        lecun = next(w for w in workflows if w["name"] == "lecun-enhanced-review")
        assert len(lecun["prerequisites"]) > 0

    def test_lecun_review_required_params(self, workflows):
        lecun = next(w for w in workflows if w["name"] == "lecun-enhanced-review")
        assert "paper_path" in lecun.get("required_params", {})

    def test_full_setup_no_required_params(self, workflows):
        fs = next(w for w in workflows if w["name"] == "full-setup")
        assert fs.get("required_params") == {}

    def test_steps_are_lists(self, workflows):
        for w in workflows:
            assert isinstance(w["steps"], list), f"{w['name']} steps should be a list"


# ===========================================================================
# workspace_status() — capabilities & suggested_next_actions
# ===========================================================================


class TestWorkspaceStatusCapabilities:
    def test_capabilities_key_present(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["workspace_status"](),
        )
        assert "capabilities" in result

    def test_suggested_next_actions_key_present(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["workspace_status"](),
        )
        assert "suggested_next_actions" in result

    def test_capabilities_has_semantic_search(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["workspace_status"](),
        )
        assert "semantic_search" in result["capabilities"]

    def test_capabilities_has_ask_library(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["workspace_status"](),
        )
        assert "ask_library" in result["capabilities"]

    def test_capabilities_has_citation_check(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["workspace_status"](),
        )
        assert "citation_check" in result["capabilities"]

    def test_semantic_search_unavailable_without_embeddings(
        self, workspace_tools, sample_workspace
    ):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["workspace_status"](),
        )
        assert result["capabilities"]["semantic_search"]["available"] is False

    def test_semantic_search_available_with_embeddings(self, workspace_tools, sample_workspace):
        embeddings_file = sample_workspace / "references" / "embeddings.yaml"
        embeddings_file.write_text(yaml.dump({"t2024": [0.1] * 1536}), encoding="utf-8")

        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["workspace_status"](),
        )
        assert result["capabilities"]["semantic_search"]["available"] is True

    def test_ask_library_unavailable_without_chunks(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["workspace_status"](),
        )
        assert result["capabilities"]["ask_library"]["available"] is False

    def test_ask_library_available_with_chunks(self, workspace_tools, sample_workspace):
        chunks_dir = sample_workspace / "references" / "chunks" / "t2024"
        chunks_dir.mkdir(parents=True)
        (chunks_dir / "chunks.yaml").write_text("- text: hello\n", encoding="utf-8")

        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["workspace_status"](),
        )
        assert result["capabilities"]["ask_library"]["available"] is True

    def test_fix_with_shown_when_unavailable(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["workspace_status"](),
        )
        ss = result["capabilities"]["semantic_search"]
        assert "fix_with" in ss
        assert ss["fix_with"] == "build_embeddings"

    def test_no_fix_with_when_available(self, workspace_tools, sample_workspace):
        embeddings_file = sample_workspace / "references" / "embeddings.yaml"
        embeddings_file.write_text(yaml.dump({"t2024": [0.1] * 1536}), encoding="utf-8")

        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["workspace_status"](),
        )
        ss = result["capabilities"]["semantic_search"]
        assert "fix_with" not in ss

    def test_suggested_actions_mention_build_embeddings(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["workspace_status"](),
        )
        actions_text = " ".join(result["suggested_next_actions"])
        assert "build_embeddings" in actions_text

    def test_suggested_actions_mention_chunk_papers(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["workspace_status"](),
        )
        actions_text = " ".join(result["suggested_next_actions"])
        assert "chunk_papers" in actions_text

    def test_no_pipeline_suggestion_when_papers_exist(self, workspace_tools, sample_workspace):
        """Pipeline suggestion only appears when reference count is 0."""
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["workspace_status"](),
        )
        # sample_workspace has 1 paper → no pipeline suggestion needed
        actions_text = " ".join(result["suggested_next_actions"])
        assert "run_pipeline" not in actions_text

    def test_pipeline_suggestion_when_no_papers(self, workspace_tools, tmp_path):
        refs = tmp_path / "references"
        refs.mkdir(parents=True)
        (refs / "bibliography.bib").touch()
        (refs / "papers").mkdir()

        result = _with_workspace(
            tmp_path,
            lambda: workspace_tools["workspace_status"](),
        )
        actions_text = " ".join(result["suggested_next_actions"])
        assert "run_pipeline" in actions_text

    def test_citation_check_reference_count(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["workspace_status"](),
        )
        assert result["capabilities"]["citation_check"]["reference_count"] == 1

    def test_paper_count_in_semantic_search_capability(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["workspace_status"](),
        )
        assert result["capabilities"]["semantic_search"]["paper_count"] == 1


# ===========================================================================
# Backward compatibility — existing workspace_status keys still present
# ===========================================================================


class TestWorkspaceStatusBackwardCompat:
    def test_existing_keys_preserved(self, workspace_tools, sample_workspace):
        result = _with_workspace(
            sample_workspace,
            lambda: workspace_tools["workspace_status"](),
        )
        for key in ("workspace", "references", "tasks", "todos", "milestones"):
            assert key in result, f"Key '{key}' missing from workspace_status result"
