"""Tests for paper traceability MCP tools (v0.13.0)."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_paper(tmp_path: Path) -> Path:
    """Create a minimal fake LaTeX paper for testing."""
    paper_dir = tmp_path / "JLE"
    paper_dir.mkdir()
    paper_file = paper_dir / "JLE-main.tex"
    paper_file.write_text(
        textwrap.dedent("""\
        \\title{Does Affect Recognition improve HCI on Affective Corpora?}
        \\begin{document}
        \\begin{abstract}
        We propose a novel approach that improves emotion recognition accuracy.
        We investigate whether self-attention mechanisms outperform CNNs.
        RQ1: Does affect-aware training improve user engagement?
        Our contributions include a new dataset and a stronger baseline.
        We evaluate our method on three standard benchmarks.
        We compare our approach with BERT and GPT-2 baselines.
        State-of-the-art results are achieved on all datasets.
        We do not address multilingual settings.
        Future work includes extending to non-verbal cues.
        \\end{abstract}
        \\end{document}
        """),
        encoding="utf-8",
    )
    return paper_file


@pytest.fixture()
def mcp_mock():
    """Return a minimal mock MCP that records registered tools."""
    tools: dict = {}

    class FakeMCP:
        def tool(self):
            def decorator(fn):
                tools[fn.__name__] = fn
                return fn

            return decorator

    fake = FakeMCP()
    fake._tools = tools
    return fake


@pytest.fixture()
def traceability_tools(mcp_mock):
    """Register traceability tools on the fake MCP and return the tool dict."""
    from crane.tools.traceability import register_tools

    register_tools(mcp_mock)
    return mcp_mock._tools


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


class TestToolRegistration:
    def test_all_24_tools_registered(self, traceability_tools):
        expected = {
            "trace_paper",
            "list_active_papers",
            "get_traceability_status",
            "init_traceability",
            "add_research_question",
            "add_contribution",
            "add_experiment",
            "add_figure_table",
            "add_trace_reference",
            "add_reviewer_risk",
            "add_dataset",
            "add_baseline",
            "link_artifacts",
            "log_change",
            "get_change_impact",
            "get_pending_changes",
            "mark_change_resolved",
            "verify_traceability_chain",
            "find_orphan_artifacts",
            "generate_artifact_index",
            "get_traceability_mermaid",
            "get_traceability_dot",
            "diff_trace_versions",
            "generate_rtm",
        }
        assert expected == set(traceability_tools.keys())

    def test_tools_are_callable(self, traceability_tools):
        for name, fn in traceability_tools.items():
            assert callable(fn), f"{name} is not callable"

    def test_all_tools_have_docstrings(self, traceability_tools):
        for name, fn in traceability_tools.items():
            assert fn.__doc__, f"{name} has no docstring"


# ---------------------------------------------------------------------------
# init_traceability
# ---------------------------------------------------------------------------


class TestInitTraceability:
    def test_creates_version_directory(self, tmp_paper, traceability_tools):
        result = traceability_tools["init_traceability"](str(tmp_paper))
        assert result["status"] == "initialized"
        vdir = Path(result["version_dir"])
        assert vdir.exists()
        assert vdir.name == "v1"

    def test_creates_all_10_yaml_files(self, tmp_paper, traceability_tools):
        result = traceability_tools["init_traceability"](str(tmp_paper))
        vdir = Path(result["version_dir"])
        expected_files = {
            "1_contribution.yaml",
            "2_experiment.yaml",
            "3_section_outline.yaml",
            "4_citation_map.yaml",
            "5_figure_table_map.yaml",
            "6_research_question.yaml",
            "7_change_log_impact.yaml",
            "8_limitation_reviewer_risk.yaml",
            "9_dataset_baseline_protocol.yaml",
            "10_artifact_index.yaml",
        }
        created = {f.name for f in vdir.iterdir() if f.is_file() and f.suffix == ".yaml"}
        assert expected_files == created

    def test_second_init_creates_v2(self, tmp_paper, traceability_tools):
        traceability_tools["init_traceability"](str(tmp_paper))
        result2 = traceability_tools["init_traceability"](str(tmp_paper))
        assert Path(result2["version_dir"]).name == "v2"

    def test_creates_readme(self, tmp_paper, traceability_tools):
        result = traceability_tools["init_traceability"](str(tmp_paper), trigger="test trigger")
        trace_root = Path(result["version_dir"]).parent
        readme = trace_root / "README.md"
        assert readme.exists()
        content = readme.read_text()
        assert "v1" in content

    def test_paper_stage_recorded(self, tmp_paper, traceability_tools):
        result = traceability_tools["init_traceability"](
            str(tmp_paper), paper_stage="revision"
        )
        assert result["paper_stage"] == "revision"


# ---------------------------------------------------------------------------
# trace_paper
# ---------------------------------------------------------------------------


class TestTracePaper:
    def test_full_mode_creates_version(self, tmp_paper, traceability_tools):
        result = traceability_tools["trace_paper"](str(tmp_paper), mode="full")
        assert result["mode"] == "full"
        assert Path(result["version_dir"]).exists()
        assert "inferred" in result

    def test_init_mode_no_inference(self, tmp_paper, traceability_tools):
        result = traceability_tools["trace_paper"](str(tmp_paper), mode="init")
        assert result["status"] == "initialized"
        assert "inferred" not in result

    def test_status_mode_reads_existing(self, tmp_paper, traceability_tools):
        traceability_tools["init_traceability"](str(tmp_paper))
        result = traceability_tools["trace_paper"](str(tmp_paper), mode="status")
        assert "chain_completeness" in result
        assert "summary" in result

    def test_viz_mode_returns_mermaid_and_dot(self, tmp_paper, traceability_tools):
        traceability_tools["init_traceability"](str(tmp_paper))
        result = traceability_tools["trace_paper"](str(tmp_paper), mode="viz")
        assert "mermaid" in result
        assert "dot" in result

    def test_full_mode_summary_keys(self, tmp_paper, traceability_tools):
        result = traceability_tools["trace_paper"](str(tmp_paper), mode="full")
        summary = result["summary"]
        for key in ["rq_count", "contribution_count", "experiment_count",
                    "figure_table_count", "risk_count", "pending_changes", "chain_coverage"]:
            assert key in summary, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# add_* tools
# ---------------------------------------------------------------------------


class TestAddTools:
    @pytest.fixture(autouse=True)
    def _init(self, tmp_paper, traceability_tools):
        traceability_tools["init_traceability"](str(tmp_paper))
        self.paper_path = str(tmp_paper)
        self.tools = traceability_tools

    def test_add_research_question(self):
        result = self.tools["add_research_question"](
            self.paper_path,
            rq_id="RQ1",
            text="Does affect-aware training improve HCI?",
            motivation="HCI apps need emotion context",
            hypothesis="Yes, training with affect data improves engagement",
        )
        assert result["status"] == "added"
        assert result["rq_id"] == "RQ1"

    def test_add_contribution(self):
        result = self.tools["add_contribution"](
            self.paper_path,
            contribution_id="C1",
            claim="Our model achieves 87% accuracy on AffectCorpus",
            why_it_matters="Sets new benchmark for affect recognition",
            rq_ids=["RQ1"],
        )
        assert result["status"] == "added"
        assert result["contribution_id"] == "C1"

    def test_add_experiment(self):
        result = self.tools["add_experiment"](
            self.paper_path,
            exp_id="E1",
            goal="Compare affect-aware vs baseline on AffectCorpus",
            dataset="AffectCorpus",
            model="AffectNet-v2",
            related_contributions=["C1"],
            related_rqs=["RQ1"],
        )
        assert result["status"] == "added"
        assert result["exp_id"] == "E1"

    def test_add_figure_table(self):
        result = self.tools["add_figure_table"](
            self.paper_path,
            ft_id="Fig:1",
            ft_type="figure",
            purpose="Show accuracy comparison across models",
            source_experiments=["E1"],
            related_rqs=["RQ1"],
        )
        assert result["status"] == "added"
        assert result["ft_id"] == "Fig:1"

    def test_add_trace_reference(self):
        result = self.tools["add_trace_reference"](
            self.paper_path,
            ref_key="vaswani2017attention",
            title="Attention Is All You Need",
            purpose="Foundation for our self-attention mechanism",
            role="foundation",
            should_appear_in=["Related Work", "Methodology"],
        )
        assert result["status"] == "added"
        assert result["ref_key"] == "vaswani2017attention"

    def test_add_reviewer_risk(self):
        result = self.tools["add_reviewer_risk"](
            self.paper_path,
            risk_id="R1",
            description="Reviewer may claim BERT baseline is outdated",
            severity="high",
            likely_appears_in="Reviewer 2",
            response_strategy="Add GPT-4 comparison in rebuttal",
            related_contributions=["C1"],
        )
        assert result["status"] == "added"
        assert result["risk_id"] == "R1"

    def test_add_dataset(self):
        result = self.tools["add_dataset"](
            self.paper_path,
            dataset_id="DS1",
            name="AffectCorpus",
            description="Multimodal affect dataset with 10K samples",
            split="80/10/10 train/val/test",
            metrics=["accuracy", "F1"],
            used_in_experiments=["E1"],
        )
        assert result["status"] == "added"
        assert result["dataset_id"] == "DS1"

    def test_add_baseline(self):
        result = self.tools["add_baseline"](
            self.paper_path,
            baseline_id="BL1",
            name="BERT",
            full_name="BERT-base-uncased",
            source_citation="devlin2019bert",
            implementation_source="official",
            used_in_experiments=["E1"],
        )
        assert result["status"] == "added"
        assert result["baseline_id"] == "BL1"

    def test_link_artifacts(self):
        result = self.tools["link_artifacts"](
            self.paper_path,
            artifact_id="A001",
            artifact_path="scripts/train.py",
            artifact_type="script",
            purpose="Main training script for affect model",
            used_by=["E1"],
            generated_by="",
        )
        assert result["status"] == "added"
        assert result["artifact_id"] == "A001"

    def test_duplicate_rq_not_added_twice(self):
        self.tools["add_research_question"](
            self.paper_path, rq_id="RQ1", text="First add"
        )
        self.tools["add_research_question"](
            self.paper_path, rq_id="RQ1", text="Second add"  # duplicate
        )
        # Read YAML directly and count entries
        from crane.services.traceability_service import TraceabilityService
        svc = TraceabilityService(paper_path=self.paper_path)
        vdir = svc.get_version_dir("status")
        data = yaml.safe_load((vdir / "6_research_question.yaml").read_text())
        rqs = [r for r in data.get("research_questions", []) if r.get("rq_id") == "RQ1"]
        assert len(rqs) == 1


# ---------------------------------------------------------------------------
# Change log
# ---------------------------------------------------------------------------


class TestChangeLog:
    @pytest.fixture(autouse=True)
    def _init(self, tmp_paper, traceability_tools):
        traceability_tools["init_traceability"](str(tmp_paper))
        self.paper_path = str(tmp_paper)
        self.tools = traceability_tools

    def test_log_change_returns_change_id(self):
        result = self.tools["log_change"](
            self.paper_path,
            change="Updated accuracy from 0.85 to 0.87",
            why="Re-ran with fixed seed",
            changed_artifact="E1",
            impact_severity="medium",
            must_update=[
                {"artifact": "Fig:1", "artifact_type": "figure", "reason": "Values changed"}
            ],
        )
        assert result["status"] == "logged"
        assert result["change_id"].startswith("CH")
        assert result["must_update_count"] == 1

    def test_second_change_increments_id(self):
        r1 = self.tools["log_change"](
            self.paper_path, change="First change", why="Reason 1", changed_artifact="E1"
        )
        r2 = self.tools["log_change"](
            self.paper_path, change="Second change", why="Reason 2", changed_artifact="E2"
        )
        assert r1["change_id"] == "CH001"
        assert r2["change_id"] == "CH002"

    def test_get_pending_changes_empty_initially(self):
        result = self.tools["get_pending_changes"](self.paper_path)
        assert result["pending_count"] == 0

    def test_get_pending_changes_after_log(self):
        self.tools["log_change"](
            self.paper_path,
            change="Some change",
            why="Reason",
            changed_artifact="E1",
            must_update=[{"artifact": "Fig:1", "artifact_type": "figure", "reason": "Update"}],
        )
        result = self.tools["get_pending_changes"](self.paper_path)
        assert result["pending_count"] == 1

    def test_mark_change_resolved(self):
        self.tools["log_change"](
            self.paper_path,
            change="Change to resolve",
            why="Reason",
            changed_artifact="E1",
            must_update=[{"artifact": "Fig:1", "artifact_type": "figure", "reason": "Update"}],
        )
        result = self.tools["mark_change_resolved"](
            self.paper_path, change_id="CH001", artifact="Fig:1"
        )
        assert result["resolved"] is True

    def test_get_change_impact(self):
        self.tools["log_change"](
            self.paper_path,
            change="Test change",
            why="Reason",
            changed_artifact="E1",
            must_update=[
                {"artifact": "Fig:1", "artifact_type": "figure", "reason": "Values changed"},
                {"artifact": "T:1", "artifact_type": "table", "reason": "Numbers changed"},
            ],
        )
        result = self.tools["get_change_impact"](self.paper_path, change_id="CH001")
        assert result["change_id"] == "CH001"
        assert len(result["must_update"]) == 2


# ---------------------------------------------------------------------------
# Verification tools
# ---------------------------------------------------------------------------


class TestVerificationTools:
    @pytest.fixture(autouse=True)
    def _init(self, tmp_paper, traceability_tools):
        traceability_tools["init_traceability"](str(tmp_paper))
        self.paper_path = str(tmp_paper)
        self.tools = traceability_tools

    def test_verify_chain_returns_dict(self):
        result = self.tools["verify_traceability_chain"](self.paper_path)
        assert isinstance(result, dict)
        assert "version_dir" in result

    def test_find_orphan_artifacts_returns_dict(self):
        result = self.tools["find_orphan_artifacts"](self.paper_path)
        assert "total_orphans" in result
        assert "orphans" in result

    def test_generate_artifact_index_counts(self):
        result = self.tools["generate_artifact_index"](self.paper_path)
        for key in ["rq_count", "contribution_count", "experiment_count",
                    "risk_count", "chain_coverage"]:
            assert key in result

    def test_get_traceability_status_completeness(self):
        result = self.tools["get_traceability_status"](self.paper_path)
        assert "chain_completeness" in result
        assert "summary" in result
        assert "pending_change_count" in result


# ---------------------------------------------------------------------------
# Visualization tools
# ---------------------------------------------------------------------------


class TestVisualizationTools:
    @pytest.fixture(autouse=True)
    def _init(self, tmp_paper, traceability_tools):
        traceability_tools["init_traceability"](str(tmp_paper))
        # Add some nodes to visualize
        self.paper_path = str(tmp_paper)
        self.tools = traceability_tools
        traceability_tools["add_research_question"](
            str(tmp_paper), rq_id="RQ1", text="Test RQ"
        )
        traceability_tools["add_contribution"](
            str(tmp_paper), contribution_id="C1", claim="Test claim",
            why_it_matters="Test", rq_ids=["RQ1"]
        )

    def test_mermaid_output_format(self):
        result = self.tools["get_traceability_mermaid"](self.paper_path)
        assert "mermaid" in result
        assert "flowchart" in result["mermaid"]

    def test_dot_output_format(self):
        result = self.tools["get_traceability_dot"](self.paper_path)
        assert "dot" in result
        assert "digraph" in result["dot"]

    def test_mermaid_contains_node_count(self):
        result = self.tools["get_traceability_mermaid"](self.paper_path)
        assert "node_count" in result
        assert isinstance(result["node_count"], int)


# ---------------------------------------------------------------------------
# diff_trace_versions
# ---------------------------------------------------------------------------


class TestDiffTraceVersions:
    def test_diff_no_versions_returns_error(self, tmp_paper, traceability_tools):
        result = traceability_tools["diff_trace_versions"](str(tmp_paper))
        assert "error" in result

    def test_diff_single_version(self, tmp_paper, traceability_tools):
        traceability_tools["init_traceability"](str(tmp_paper))
        result = traceability_tools["diff_trace_versions"](str(tmp_paper))
        # Single version: compare v1 vs v1
        assert "delta" in result or "error" not in result

    def test_diff_two_versions(self, tmp_paper, traceability_tools):
        traceability_tools["init_traceability"](str(tmp_paper))
        traceability_tools["add_research_question"](
            str(tmp_paper), rq_id="RQ1", text="Added in v1"
        )
        traceability_tools["init_traceability"](str(tmp_paper))  # creates v2
        result = traceability_tools["diff_trace_versions"](str(tmp_paper))
        assert "delta" in result
        assert "summary_a" in result
        assert "summary_b" in result


# ---------------------------------------------------------------------------
# generate_rtm
# ---------------------------------------------------------------------------


class TestGenerateRTM:
    def test_rtm_returns_markdown(self, tmp_paper, traceability_tools):
        traceability_tools["init_traceability"](str(tmp_paper))
        result = traceability_tools["generate_rtm"](str(tmp_paper))
        assert "rtm_markdown" in result
        assert "Requirements Traceability Matrix" in result["rtm_markdown"]

    def test_rtm_saved_to_file(self, tmp_paper, traceability_tools, tmp_path):
        traceability_tools["init_traceability"](str(tmp_paper))
        out_file = str(tmp_path / "rtm.md")
        result = traceability_tools["generate_rtm"](str(tmp_paper), output_path=out_file)
        assert result["saved_to"] == out_file
        assert Path(out_file).exists()

    def test_rtm_with_items(self, tmp_paper, traceability_tools):
        traceability_tools["init_traceability"](str(tmp_paper))
        traceability_tools["add_research_question"](
            str(tmp_paper), rq_id="RQ1", text="Does X work?"
        )
        traceability_tools["add_reviewer_risk"](
            str(tmp_paper), risk_id="R1", description="Baseline is outdated",
            severity="high", likely_appears_in="Reviewer 2", response_strategy="Add GPT-4"
        )
        result = traceability_tools["generate_rtm"](str(tmp_paper))
        assert result["rq_count"] == 1
        assert result["risk_count"] == 1
        assert "RQ1" in result["rtm_markdown"]


# ---------------------------------------------------------------------------
# list_active_papers
# ---------------------------------------------------------------------------


class TestListActivePapers:
    def test_finds_paper_dirs(self, tmp_path, traceability_tools):
        # Create a real paper directory structure
        paper_dir = tmp_path / "JLE"
        paper_dir.mkdir()
        (paper_dir / "JLE-main.tex").write_text("\\begin{document}\\end{document}")

        result = traceability_tools["list_active_papers"](search_root=str(tmp_path))
        assert result["active_paper_count"] >= 1
        names = [p["dir_name"] for p in result["papers"]]
        assert "JLE" in names

    def test_skips_rejected_dirs(self, tmp_path, traceability_tools):
        # Should be included
        active_dir = tmp_path / "JLE"
        active_dir.mkdir()
        (active_dir / "main.tex").write_text("content")

        # Should be skipped (contains "reject" keyword)
        rejected_dir = tmp_path / "TNNLS-reject"
        rejected_dir.mkdir()
        (rejected_dir / "main.tex").write_text("content")

        result = traceability_tools["list_active_papers"](search_root=str(tmp_path))
        names = [p["dir_name"] for p in result["papers"]]
        assert "JLE" in names
        assert "TNNLS-reject" not in names

    def test_skips_nogo_dirs(self, tmp_path, traceability_tools):
        nogo_dir = tmp_path / "TOIS-nogo"
        nogo_dir.mkdir()
        (nogo_dir / "main.tex").write_text("content")

        result = traceability_tools["list_active_papers"](search_root=str(tmp_path))
        names = [p["dir_name"] for p in result["papers"]]
        assert "TOIS-nogo" not in names

    def test_reports_trace_status(self, tmp_path, traceability_tools):
        paper_dir = tmp_path / "ESWA"
        paper_dir.mkdir()
        paper_file = paper_dir / "main.tex"
        paper_file.write_text("content")

        # Init trace for this paper
        traceability_tools["init_traceability"](str(paper_file))

        result = traceability_tools["list_active_papers"](search_root=str(tmp_path))
        eswa = next((p for p in result["papers"] if p["dir_name"] == "ESWA"), None)
        assert eswa is not None
        assert eswa["has_trace"] is True
        assert eswa["trace_version"] == 1


# ---------------------------------------------------------------------------
# Inference (trace_paper full mode)
# ---------------------------------------------------------------------------


class TestInference:
    def test_full_mode_infers_rqs(self, tmp_paper, traceability_tools):
        result = traceability_tools["trace_paper"](str(tmp_paper), mode="full")
        assert "inferred" in result
        assert result["inferred"]["rqs"] >= 1

    def test_full_mode_infers_contributions(self, tmp_paper, traceability_tools):
        result = traceability_tools["trace_paper"](str(tmp_paper), mode="full")
        assert result["inferred"]["contributions"] >= 1

    def test_full_mode_infers_risks(self, tmp_paper, traceability_tools):
        result = traceability_tools["trace_paper"](str(tmp_paper), mode="full")
        assert result["inferred"]["risks"] >= 1

    def test_infer_mode_same_as_full(self, tmp_paper, traceability_tools):
        result = traceability_tools["trace_paper"](str(tmp_paper), mode="infer")
        assert "inferred" in result
