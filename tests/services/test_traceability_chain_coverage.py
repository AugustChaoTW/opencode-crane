"""Tests for Chain Coverage (Issue #83).

Coverage:
  A. TraceabilityInferenceService.infer_figure_tables()
  B. TraceabilityService.compute_chain_coverage() — all-isolated, partial, full
  C. get_chain_coverage MCP tool
  D. crane_help intent routing
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from crane.services.traceability_inference_service import TraceabilityInferenceService
from crane.services.traceability_service import TraceabilityService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False)


def _make_version_dir(tmp_path: Path) -> Path:
    vdir = tmp_path / "_paper_trace" / "v1"
    vdir.mkdir(parents=True)
    return vdir


def _write_trace_files(
    vdir: Path,
    rqs: list[dict],
    contributions: list[dict],
    experiments: list[dict],
    figure_tables: list[dict],
) -> None:
    _write_yaml(vdir / "6_research_question.yaml", {"research_questions": rqs})
    _write_yaml(vdir / "1_contribution.yaml", {"contributions": contributions})
    _write_yaml(vdir / "2_experiment.yaml", {"experiments": experiments, "experiment_registry": []})
    _write_yaml(vdir / "5_figure_table_map.yaml", {"entries": figure_tables})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def svc(tmp_path):
    """TraceabilityService with tmp_path as project root."""
    return TraceabilityService(paper_path="dummy.tex", output_dir=str(tmp_path))


@pytest.fixture
def all_isolated_vdir(tmp_path):
    """Version dir where every node is isolated (0% coverage)."""
    vdir = _make_version_dir(tmp_path)
    _write_trace_files(
        vdir,
        rqs=[{"rq_id": "RQ1", "text": "RQ1", "tested_by_experiments": [], "related_contributions": []}],
        contributions=[{
            "contribution_id": "C1", "claim": "C1",
            "evidence_figures": [], "evidence_tables": [],
            "evidence_experiments": [], "evidence_sections": [],
        }],
        experiments=[{
            "exp_id": "E1", "goal": "E1",
            "related_rqs": [], "related_contributions": [],
        }],
        figure_tables=[],
    )
    return vdir


@pytest.fixture
def fully_linked_vdir(tmp_path):
    """Version dir where all nodes are linked (100% coverage)."""
    vdir = _make_version_dir(tmp_path)
    _write_trace_files(
        vdir,
        rqs=[{"rq_id": "RQ1", "text": "RQ1", "tested_by_experiments": ["E1"], "related_contributions": []}],
        contributions=[{
            "contribution_id": "C1", "claim": "C1",
            "evidence_figures": [], "evidence_tables": [],
            "evidence_experiments": ["E1"], "evidence_sections": [],
        }],
        experiments=[{
            "exp_id": "E1", "goal": "E1",
            "related_rqs": ["RQ1"], "related_contributions": ["C1"],
        }],
        figure_tables=[{
            "ft_id": "Fig:1", "caption": "Results",
            "source_experiments": ["E1"],
        }],
    )
    return vdir


@pytest.fixture
def partial_vdir(tmp_path):
    """2 RQs, 2 contributions, 2 experiments — only half linked."""
    vdir = _make_version_dir(tmp_path)
    _write_trace_files(
        vdir,
        rqs=[
            {"rq_id": "RQ1", "text": "RQ1", "tested_by_experiments": ["E1"], "related_contributions": []},
            {"rq_id": "RQ2", "text": "RQ2", "tested_by_experiments": [], "related_contributions": []},
        ],
        contributions=[
            {
                "contribution_id": "C1", "claim": "C1",
                "evidence_figures": [], "evidence_tables": [],
                "evidence_experiments": ["E1"], "evidence_sections": [],
            },
            {
                "contribution_id": "C2", "claim": "C2",
                "evidence_figures": [], "evidence_tables": [],
                "evidence_experiments": [], "evidence_sections": [],
            },
        ],
        experiments=[
            {
                "exp_id": "E1", "goal": "E1",
                "related_rqs": ["RQ1"], "related_contributions": ["C1"],
            },
            {
                "exp_id": "E2", "goal": "E2",
                "related_rqs": [], "related_contributions": [],
            },
        ],
        figure_tables=[{
            "ft_id": "Fig:1", "caption": "Results for E1",
            "source_experiments": ["E1"],
        }],
    )
    return vdir


# ===========================================================================
# A. infer_figure_tables
# ===========================================================================


class TestInferFigureTables:
    def _make_tex(self, tmp_path: Path, content: str) -> Path:
        tex = tmp_path / "paper.tex"
        tex.write_text(content, encoding="utf-8")
        return tex

    def test_detects_figure_n(self, tmp_path):
        tex = self._make_tex(tmp_path, "As shown in Figure 1, the results are clear.")
        svc = TraceabilityInferenceService(str(tex))
        results = svc.infer_figure_tables()
        fig_ids = [r["fig_id"] for r in results]
        assert "Fig:1" in fig_ids

    def test_detects_fig_abbreviation(self, tmp_path):
        tex = self._make_tex(tmp_path, "See Fig. 3 for details.")
        svc = TraceabilityInferenceService(str(tex))
        results = svc.infer_figure_tables()
        fig_ids = [r["fig_id"] for r in results]
        assert "Fig:3" in fig_ids

    def test_detects_table(self, tmp_path):
        tex = self._make_tex(tmp_path, "Table 2 shows the comparison.")
        svc = TraceabilityInferenceService(str(tex))
        results = svc.infer_figure_tables()
        fig_ids = [r["fig_id"] for r in results]
        assert "Tab:2" in fig_ids

    def test_detects_multiple_figures(self, tmp_path):
        tex = self._make_tex(tmp_path, "Figure 1 and Figure 2 confirm the hypothesis.")
        svc = TraceabilityInferenceService(str(tex))
        results = svc.infer_figure_tables()
        assert len(results) >= 2

    def test_no_duplicates(self, tmp_path):
        tex = self._make_tex(tmp_path, "Figure 1 is great. See Figure 1 again.")
        svc = TraceabilityInferenceService(str(tex))
        results = svc.infer_figure_tables()
        fig_ids = [r["fig_id"] for r in results]
        assert fig_ids.count("Fig:1") == 1

    def test_returns_label_figure(self, tmp_path):
        tex = self._make_tex(tmp_path, "Figure 1 shows the results.")
        svc = TraceabilityInferenceService(str(tex))
        results = svc.infer_figure_tables()
        fig = next(r for r in results if r["fig_id"] == "Fig:1")
        assert fig["label"] == "figure"

    def test_returns_label_table(self, tmp_path):
        tex = self._make_tex(tmp_path, "Table 1 shows the results.")
        svc = TraceabilityInferenceService(str(tex))
        results = svc.infer_figure_tables()
        tab = next(r for r in results if r["fig_id"] == "Tab:1")
        assert tab["label"] == "table"

    def test_context_snippet_present(self, tmp_path):
        tex = self._make_tex(tmp_path, "As shown in Figure 1, the results are clear.")
        svc = TraceabilityInferenceService(str(tex))
        results = svc.infer_figure_tables()
        fig = next(r for r in results if r["fig_id"] == "Fig:1")
        assert "context" in fig
        assert len(fig["context"]) > 0

    def test_empty_when_no_paper(self, tmp_path):
        svc = TraceabilityInferenceService(str(tmp_path / "nonexistent.tex"))
        results = svc.infer_figure_tables()
        assert results == []

    def test_infer_all_includes_figure_tables(self, tmp_path):
        tex = self._make_tex(tmp_path, "See Figure 1 and Table 2.")
        svc = TraceabilityInferenceService(str(tex))
        result = svc.infer_all()
        assert "figure_tables" in result
        assert isinstance(result["figure_tables"], list)
        assert len(result["figure_tables"]) >= 2

    def test_detects_latex_ref(self, tmp_path):
        tex = self._make_tex(tmp_path, r"As shown in \ref{fig:results}, the model works.")
        svc = TraceabilityInferenceService(str(tex))
        results = svc.infer_figure_tables()
        labels = [r["label"] for r in results]
        assert "figure" in labels


# ===========================================================================
# B. compute_chain_coverage
# ===========================================================================


class TestComputeChainCoverageAllIsolated:
    def test_coverage_is_zero(self, svc, all_isolated_vdir):
        result = svc.compute_chain_coverage(all_isolated_vdir)
        assert result["chain_coverage"] == 0.0

    def test_covered_nodes_is_zero(self, svc, all_isolated_vdir):
        result = svc.compute_chain_coverage(all_isolated_vdir)
        assert result["covered_nodes"] == 0

    def test_total_nodes_is_three(self, svc, all_isolated_vdir):
        result = svc.compute_chain_coverage(all_isolated_vdir)
        assert result["total_nodes"] == 3

    def test_isolated_nodes_contains_all(self, svc, all_isolated_vdir):
        result = svc.compute_chain_coverage(all_isolated_vdir)
        assert "RQ1" in result["isolated_nodes"]
        assert "C1" in result["isolated_nodes"]
        assert "E1" in result["isolated_nodes"]

    def test_breakdown_rqs_isolated(self, svc, all_isolated_vdir):
        result = svc.compute_chain_coverage(all_isolated_vdir)
        assert "RQ1" in result["breakdown"]["rqs"]["isolated"]

    def test_breakdown_contributions_isolated(self, svc, all_isolated_vdir):
        result = svc.compute_chain_coverage(all_isolated_vdir)
        assert "C1" in result["breakdown"]["contributions"]["isolated"]

    def test_breakdown_experiments_isolated(self, svc, all_isolated_vdir):
        result = svc.compute_chain_coverage(all_isolated_vdir)
        assert "E1" in result["breakdown"]["experiments"]["isolated"]

    def test_suggested_actions_non_empty(self, svc, all_isolated_vdir):
        result = svc.compute_chain_coverage(all_isolated_vdir)
        assert len(result["suggested_actions"]) > 0

    def test_rq_action_contains_trace_add(self, svc, all_isolated_vdir):
        result = svc.compute_chain_coverage(all_isolated_vdir)
        rq_actions = [a for a in result["suggested_actions"] if "RQ1" in a]
        assert any("trace_add" in a for a in rq_actions)

    def test_experiment_action_contains_link_artifacts(self, svc, all_isolated_vdir):
        result = svc.compute_chain_coverage(all_isolated_vdir)
        exp_actions = [a for a in result["suggested_actions"] if "E1" in a]
        assert any("link_artifacts" in a for a in exp_actions)


class TestComputeChainCoverageFull:
    def test_coverage_is_one(self, svc, fully_linked_vdir):
        result = svc.compute_chain_coverage(fully_linked_vdir)
        assert result["chain_coverage"] == 1.0

    def test_covered_nodes_equals_total(self, svc, fully_linked_vdir):
        result = svc.compute_chain_coverage(fully_linked_vdir)
        assert result["covered_nodes"] == result["total_nodes"]

    def test_isolated_nodes_empty(self, svc, fully_linked_vdir):
        result = svc.compute_chain_coverage(fully_linked_vdir)
        assert result["isolated_nodes"] == []

    def test_suggested_actions_empty(self, svc, fully_linked_vdir):
        result = svc.compute_chain_coverage(fully_linked_vdir)
        assert result["suggested_actions"] == []

    def test_breakdown_covered_matches_total(self, svc, fully_linked_vdir):
        result = svc.compute_chain_coverage(fully_linked_vdir)
        bd = result["breakdown"]
        assert bd["rqs"]["covered"] == bd["rqs"]["total"]
        assert bd["contributions"]["covered"] == bd["contributions"]["total"]
        assert bd["experiments"]["covered"] == bd["experiments"]["total"]


class TestComputeChainCoveragePartial:
    def test_coverage_is_half(self, svc, partial_vdir):
        result = svc.compute_chain_coverage(partial_vdir)
        # 3 covered out of 6 total
        assert result["chain_coverage"] == pytest.approx(0.5, abs=0.01)

    def test_rq2_is_isolated(self, svc, partial_vdir):
        result = svc.compute_chain_coverage(partial_vdir)
        assert "RQ2" in result["isolated_nodes"]

    def test_c2_is_isolated(self, svc, partial_vdir):
        result = svc.compute_chain_coverage(partial_vdir)
        assert "C2" in result["isolated_nodes"]

    def test_e2_is_isolated(self, svc, partial_vdir):
        result = svc.compute_chain_coverage(partial_vdir)
        assert "E2" in result["isolated_nodes"]

    def test_rq1_not_isolated(self, svc, partial_vdir):
        result = svc.compute_chain_coverage(partial_vdir)
        assert "RQ1" not in result["isolated_nodes"]

    def test_c1_not_isolated(self, svc, partial_vdir):
        result = svc.compute_chain_coverage(partial_vdir)
        assert "C1" not in result["isolated_nodes"]

    def test_e1_not_isolated(self, svc, partial_vdir):
        result = svc.compute_chain_coverage(partial_vdir)
        assert "E1" not in result["isolated_nodes"]

    def test_suggested_actions_only_for_isolated(self, svc, partial_vdir):
        result = svc.compute_chain_coverage(partial_vdir)
        actions = result["suggested_actions"]
        # RQ1, C1, E1 are linked → no action for them
        assert not any("RQ1" in a for a in actions)
        assert not any("C1\"" in a for a in actions)
        # RQ2, C2, E2 are isolated → have actions
        assert any("RQ2" in a for a in actions)
        assert any("C2" in a for a in actions)
        assert any("E2" in a for a in actions)


class TestComputeChainCoverageEdgeCases:
    def test_empty_version_dir_returns_zero(self, svc, tmp_path):
        vdir = _make_version_dir(tmp_path)
        _write_trace_files(vdir, [], [], [], [])
        result = svc.compute_chain_coverage(vdir)
        assert result["chain_coverage"] == 0.0
        assert result["total_nodes"] == 0
        assert result["isolated_nodes"] == []
        assert result["suggested_actions"] == []

    def test_return_has_all_required_keys(self, svc, all_isolated_vdir):
        result = svc.compute_chain_coverage(all_isolated_vdir)
        for key in ["chain_coverage", "covered_nodes", "total_nodes",
                    "breakdown", "isolated_nodes", "suggested_actions"]:
            assert key in result

    def test_breakdown_has_all_categories(self, svc, all_isolated_vdir):
        result = svc.compute_chain_coverage(all_isolated_vdir)
        for cat in ["rqs", "contributions", "experiments"]:
            assert cat in result["breakdown"]
            assert "total" in result["breakdown"][cat]
            assert "covered" in result["breakdown"][cat]
            assert "isolated" in result["breakdown"][cat]

    def test_coverage_in_range(self, svc, partial_vdir):
        result = svc.compute_chain_coverage(partial_vdir)
        assert 0.0 <= result["chain_coverage"] <= 1.0


# ===========================================================================
# C. get_chain_coverage MCP tool
# ===========================================================================


class _ToolCollector:
    def __init__(self):
        self.tools: dict[str, Any] = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn
        return decorator


@pytest.fixture
def traceability_tools():
    from crane.tools.traceability import register_tools
    col = _ToolCollector()
    register_tools(col)
    return col.tools


class TestGetChainCoverageTool:
    def test_tool_is_registered(self, traceability_tools):
        assert "get_chain_coverage" in traceability_tools

    def test_returns_chain_coverage_key(self, traceability_tools, tmp_path):
        vdir = _make_version_dir(tmp_path)
        _write_trace_files(
            vdir,
            rqs=[{"rq_id": "RQ1", "text": "RQ1", "tested_by_experiments": [], "related_contributions": []}],
            contributions=[{
                "contribution_id": "C1", "claim": "c",
                "evidence_figures": [], "evidence_tables": [],
                "evidence_experiments": [], "evidence_sections": [],
            }],
            experiments=[{"exp_id": "E1", "goal": "g", "related_rqs": [], "related_contributions": []}],
            figure_tables=[],
        )
        tex = tmp_path / "paper.tex"
        tex.write_text("dummy", encoding="utf-8")

        fn = traceability_tools["get_chain_coverage"]
        result = fn(paper_path=str(tex), output_dir=str(tmp_path))
        assert "chain_coverage" in result

    def test_returns_suggested_actions(self, traceability_tools, tmp_path):
        vdir = _make_version_dir(tmp_path)
        _write_trace_files(
            vdir,
            rqs=[{"rq_id": "RQ1", "text": "t", "tested_by_experiments": [], "related_contributions": []}],
            contributions=[{
                "contribution_id": "C1", "claim": "c",
                "evidence_figures": [], "evidence_tables": [],
                "evidence_experiments": [], "evidence_sections": [],
            }],
            experiments=[{"exp_id": "E1", "goal": "g", "related_rqs": [], "related_contributions": []}],
            figure_tables=[],
        )
        tex = tmp_path / "paper.tex"
        tex.write_text("dummy", encoding="utf-8")

        fn = traceability_tools["get_chain_coverage"]
        result = fn(paper_path=str(tex), output_dir=str(tmp_path))
        assert "suggested_actions" in result
        assert isinstance(result["suggested_actions"], list)

    def test_paper_path_echoed(self, traceability_tools, tmp_path):
        vdir = _make_version_dir(tmp_path)
        _write_trace_files(vdir, [], [], [], [])
        tex = tmp_path / "paper.tex"
        tex.write_text("dummy", encoding="utf-8")

        fn = traceability_tools["get_chain_coverage"]
        result = fn(paper_path=str(tex), output_dir=str(tmp_path))
        assert "paper_path" in result


# ===========================================================================
# D. crane_help intent
# ===========================================================================


@pytest.fixture
def crane_help_tools():
    from crane.tools.crane_help import register_tools
    col = _ToolCollector()
    register_tools(col)
    return col.tools


class TestCraneHelpChainCoverage:
    def test_chain_coverage_maps_to_get_chain_coverage(self, crane_help_tools):
        result = crane_help_tools["crane_help"](topic="chain coverage")
        tools = [m["tool"] for m in result["matches"]]
        assert "get_chain_coverage" in tools

    def test_isolated_nodes_maps_correctly(self, crane_help_tools):
        result = crane_help_tools["crane_help"](topic="isolated nodes")
        tools = [m["tool"] for m in result["matches"]]
        assert "get_chain_coverage" in tools

    def test_trace_coverage_maps_correctly(self, crane_help_tools):
        result = crane_help_tools["crane_help"](topic="trace coverage")
        tools = [m["tool"] for m in result["matches"]]
        assert "get_chain_coverage" in tools

    def test_chinese_trigger(self, crane_help_tools):
        result = crane_help_tools["crane_help"](topic="鏈條覆蓋率")
        tools = [m["tool"] for m in result["matches"]]
        assert "get_chain_coverage" in tools

    def test_result_has_call_template(self, crane_help_tools):
        result = crane_help_tools["crane_help"](topic="chain coverage")
        match = next(m for m in result["matches"] if m["tool"] == "get_chain_coverage")
        assert "get_chain_coverage(" in match["call"]

    def test_result_has_see_also(self, crane_help_tools):
        result = crane_help_tools["crane_help"](topic="chain coverage")
        match = next(m for m in result["matches"] if m["tool"] == "get_chain_coverage")
        assert "see_also" in match
        assert "verify_traceability_chain" in match["see_also"]
