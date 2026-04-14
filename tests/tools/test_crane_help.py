"""Tests for v0.14.3 — crane_help tool + SKILL.md discoverability.

Coverage:
  A. crane_help tool registration and return shape
  B. Intent mapping — correct tool returned for common phrases
  C. Edge cases: empty topic, unknown topic, partial match
  D. SKILL.md content checks — key trigger phrases present
"""

from __future__ import annotations

from pathlib import Path

import pytest

from crane.tools.crane_help import _lookup
from crane.tools.crane_help import register_tools as register_crane_help_tools

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class _ToolCollector:
    def __init__(self):
        self.tools: dict = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn
        return decorator


@pytest.fixture
def help_tools():
    col = _ToolCollector()
    register_crane_help_tools(col)
    return col.tools


SKILL_MD = Path(__file__).parent.parent.parent / "SKILL.md"


# ===========================================================================
# A. Tool registration
# ===========================================================================


class TestCraneHelpRegistered:
    def test_tool_registered(self, help_tools):
        assert "crane_help" in help_tools

    def test_returns_dict(self, help_tools):
        result = help_tools["crane_help"](topic="paper trace")
        assert isinstance(result, dict)

    def test_has_topic_key(self, help_tools):
        result = help_tools["crane_help"](topic="paper trace")
        assert result["topic"] == "paper trace"

    def test_has_matches_key(self, help_tools):
        result = help_tools["crane_help"](topic="paper trace")
        assert "matches" in result
        assert isinstance(result["matches"], list)

    def test_has_tip_key(self, help_tools):
        result = help_tools["crane_help"](topic="paper trace")
        assert "tip" in result


# ===========================================================================
# B. Intent mapping — correct tools returned
# ===========================================================================


class TestPaperTraceIntent:
    def test_paper_trace_returns_trace_paper(self, help_tools):
        result = help_tools["crane_help"](topic="paper trace")
        tools = [m["tool"] for m in result["matches"]]
        assert "trace_paper" in tools

    def test_do_paper_trace_maps_to_trace_paper(self, help_tools):
        result = help_tools["crane_help"](topic="do paper trace")
        tools = [m["tool"] for m in result["matches"]]
        assert "trace_paper" in tools

    def test_paper_track_maps_to_trace_paper(self, help_tools):
        result = help_tools["crane_help"](topic="paper track")
        tools = [m["tool"] for m in result["matches"]]
        assert "trace_paper" in tools

    def test_trace_paper_result_has_call_template(self, help_tools):
        result = help_tools["crane_help"](topic="paper trace")
        trace = next(m for m in result["matches"] if m["tool"] == "trace_paper")
        assert "trace_paper(" in trace["call"]

    def test_trace_paper_result_has_output_info(self, help_tools):
        result = help_tools["crane_help"](topic="paper trace")
        trace = next(m for m in result["matches"] if m["tool"] == "trace_paper")
        assert "output" in trace or "modes" in trace


class TestEvaluatePaperIntent:
    def test_evaluate_paper_maps_correctly(self, help_tools):
        result = help_tools["crane_help"](topic="evaluate paper")
        tools = [m["tool"] for m in result["matches"]]
        assert "evaluate_paper_v2" in tools

    def test_score_paper_maps_correctly(self, help_tools):
        result = help_tools["crane_help"](topic="score paper")
        tools = [m["tool"] for m in result["matches"]]
        assert "evaluate_paper_v2" in tools

    def test_paper_quality_maps_correctly(self, help_tools):
        result = help_tools["crane_help"](topic="paper quality")
        tools = [m["tool"] for m in result["matches"]]
        assert "evaluate_paper_v2" in tools


class TestReviewPaperIntent:
    def test_review_paper_maps_to_crane_review_full(self, help_tools):
        result = help_tools["crane_help"](topic="review paper")
        tools = [m["tool"] for m in result["matches"]]
        assert "crane_review_full" in tools

    def test_detect_defects_maps_correctly(self, help_tools):
        result = help_tools["crane_help"](topic="detect defects")
        tools = [m["tool"] for m in result["matches"]]
        assert "crane_review_full" in tools

    def test_diagnose_paper_maps_to_crane_diagnose(self, help_tools):
        result = help_tools["crane_help"](topic="diagnose paper")
        tools = [m["tool"] for m in result["matches"]]
        assert "crane_diagnose" in tools

    def test_diagnose_section_maps_to_crane_diagnose(self, help_tools):
        result = help_tools["crane_help"](topic="diagnose section")
        tools = [m["tool"] for m in result["matches"]]
        assert "crane_diagnose" in tools


class TestSubmissionIntent:
    def test_submission_check_maps_correctly(self, help_tools):
        result = help_tools["crane_help"](topic="submission check")
        tools = [m["tool"] for m in result["matches"]]
        assert "run_submission_check" in tools

    def test_chinese_trigger_works(self, help_tools):
        result = help_tools["crane_help"](topic="投稿前檢查")
        tools = [m["tool"] for m in result["matches"]]
        assert "run_submission_check" in tools

    def test_simulate_submission_maps_correctly(self, help_tools):
        result = help_tools["crane_help"](topic="simulate submission")
        tools = [m["tool"] for m in result["matches"]]
        assert "simulate_submission_outcome" in tools

    def test_acceptance_probability_maps_correctly(self, help_tools):
        result = help_tools["crane_help"](topic="acceptance probability")
        tools = [m["tool"] for m in result["matches"]]
        assert "simulate_submission_outcome" in tools


class TestIndexAndPipelineIntent:
    def test_build_index_maps_correctly(self, help_tools):
        result = help_tools["crane_help"](topic="build index")
        tools = [m["tool"] for m in result["matches"]]
        assert "build_paper_index" in tools

    def test_review_pipeline_maps_correctly(self, help_tools):
        result = help_tools["crane_help"](topic="review pipeline")
        tools = [m["tool"] for m in result["matches"]]
        assert "run_review_pipeline" in tools

    def test_full_paper_review_maps_correctly(self, help_tools):
        result = help_tools["crane_help"](topic="full paper review")
        tools = [m["tool"] for m in result["matches"]]
        assert "run_review_pipeline" in tools


class TestSearchAndRAGIntent:
    def test_semantic_search_maps_correctly(self, help_tools):
        result = help_tools["crane_help"](topic="semantic search")
        tools = [m["tool"] for m in result["matches"]]
        assert "semantic_search" in tools

    def test_find_similar_maps_correctly(self, help_tools):
        result = help_tools["crane_help"](topic="find similar")
        tools = [m["tool"] for m in result["matches"]]
        assert "semantic_search" in tools

    def test_ask_library_maps_correctly(self, help_tools):
        result = help_tools["crane_help"](topic="ask library")
        tools = [m["tool"] for m in result["matches"]]
        assert "ask_library" in tools

    def test_rag_maps_correctly(self, help_tools):
        result = help_tools["crane_help"](topic="rag")
        tools = [m["tool"] for m in result["matches"]]
        assert "ask_library" in tools

    def test_literature_review_maps_to_run_pipeline(self, help_tools):
        result = help_tools["crane_help"](topic="literature review")
        tools = [m["tool"] for m in result["matches"]]
        assert "run_pipeline" in tools


class TestKarpathyIntent:
    def test_karpathy_review_maps_correctly(self, help_tools):
        result = help_tools["crane_help"](topic="karpathy review")
        tools = [m["tool"] for m in result["matches"]]
        assert "karpathy_review" in tools

    def test_code_review_maps_correctly(self, help_tools):
        result = help_tools["crane_help"](topic="code review")
        tools = [m["tool"] for m in result["matches"]]
        assert "karpathy_review" in tools

    def test_simplicity_check_maps_correctly(self, help_tools):
        result = help_tools["crane_help"](topic="simplicity check")
        tools = [m["tool"] for m in result["matches"]]
        assert "check_code_simplicity" in tools


class TestWorkspaceIntent:
    def test_workspace_status_maps_correctly(self, help_tools):
        result = help_tools["crane_help"](topic="workspace status")
        tools = [m["tool"] for m in result["matches"]]
        assert "workspace_status" in tools

    def test_list_workflows_maps_correctly(self, help_tools):
        result = help_tools["crane_help"](topic="list workflows")
        tools = [m["tool"] for m in result["matches"]]
        assert "list_workflows" in tools

    def test_what_can_crane_do_maps_correctly(self, help_tools):
        result = help_tools["crane_help"](topic="what can crane do")
        tools = [m["tool"] for m in result["matches"]]
        assert "list_workflows" in tools or "workspace_status" in tools

    def test_match_journal_maps_correctly(self, help_tools):
        result = help_tools["crane_help"](topic="match journal")
        tools = [m["tool"] for m in result["matches"]]
        assert "match_journal_v2" in tools


# ===========================================================================
# C. Edge cases
# ===========================================================================


class TestEdgeCases:
    def test_empty_topic_returns_tip(self, help_tools):
        result = help_tools["crane_help"](topic="")
        assert "tip" in result
        assert result["matches"] == []

    def test_unknown_topic_returns_empty_matches(self, help_tools):
        result = help_tools["crane_help"](topic="xyzzy_nonexistent_feature_12345")
        assert result["matches"] == []

    def test_unknown_topic_has_tip(self, help_tools):
        result = help_tools["crane_help"](topic="xyzzy_nonexistent_feature_12345")
        assert len(result["tip"]) > 0

    def test_case_insensitive_matching(self, help_tools):
        result_lower = help_tools["crane_help"](topic="paper trace")
        result_upper = help_tools["crane_help"](topic="PAPER TRACE")
        # Both should find the same tools
        tools_lower = {m["tool"] for m in result_lower["matches"]}
        tools_upper = {m["tool"] for m in result_upper["matches"]}
        assert tools_lower == tools_upper

    def test_match_has_description(self, help_tools):
        result = help_tools["crane_help"](topic="paper trace")
        for match in result["matches"]:
            assert "description" in match
            assert len(match["description"]) > 0

    def test_match_has_call_template(self, help_tools):
        result = help_tools["crane_help"](topic="evaluate paper")
        for match in result["matches"]:
            assert "call" in match


# ===========================================================================
# D. _lookup internal function
# ===========================================================================


class TestLookupFunction:
    def test_lookup_paper_trace(self):
        results = _lookup("paper trace")
        tools = [r["tool"] for r in results]
        assert "trace_paper" in tools

    def test_lookup_returns_list(self):
        results = _lookup("evaluate paper")
        assert isinstance(results, list)

    def test_lookup_empty_returns_empty(self):
        results = _lookup("zzz_no_match_xyz")
        assert results == []

    def test_lookup_partial_phrase_matches(self):
        # "submission" is substring of "submission check"
        results = _lookup("before submission")
        tools = [r["tool"] for r in results]
        assert "run_submission_check" in tools


# ===========================================================================
# E. SKILL.md content checks
# ===========================================================================


@pytest.mark.skipif(not SKILL_MD.exists(), reason="SKILL.md not found")
class TestSkillMdContent:
    @pytest.fixture(autouse=True)
    def skill_content(self):
        self.content = SKILL_MD.read_text(encoding="utf-8")

    def test_has_crane_help_reference(self):
        assert "crane_help" in self.content

    def test_has_trace_paper_reference(self):
        assert "trace_paper" in self.content

    def test_has_do_paper_trace_trigger(self):
        assert "do paper trace" in self.content.lower()

    def test_has_evaluate_paper_v2_reference(self):
        assert "evaluate_paper_v2" in self.content

    def test_has_crane_review_full_reference(self):
        assert "crane_review_full" in self.content

    def test_has_run_submission_check_reference(self):
        assert "run_submission_check" in self.content

    def test_has_run_review_pipeline_reference(self):
        assert "run_review_pipeline" in self.content

    def test_has_build_paper_index_reference(self):
        assert "build_paper_index" in self.content

    def test_has_semantic_search_reference(self):
        assert "semantic_search" in self.content

    def test_has_ask_library_reference(self):
        assert "ask_library" in self.content

    def test_has_karpathy_review_reference(self):
        assert "karpathy_review" in self.content

    def test_trigger_mapping_section_present(self):
        assert "Trigger → Tool Mapping" in self.content or "Trigger" in self.content

    def test_paper_trace_workflow_documented(self):
        assert "_paper_trace" in self.content

    def test_prerequisite_section_present(self):
        assert "Prerequisite" in self.content or "prerequisite" in self.content

    def test_quick_start_section_present(self):
        assert "QUICK START" in self.content or "Quick Start" in self.content

    def test_description_frontmatter_has_trigger_phrases(self):
        """SKILL.md description field (read by Claude first) must include key triggers."""
        lines = self.content.split("\n")
        desc_section = "\n".join(lines[:20])  # frontmatter is at top
        assert "paper trace" in desc_section.lower()
        assert "evaluate paper" in desc_section.lower() or "evaluate_paper_v2" in desc_section
