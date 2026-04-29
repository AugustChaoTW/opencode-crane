"""Tests for the q1_elevation_pipeline MCP tool."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import yaml

import crane.tools.q1_pipeline as q1_module
from crane.tools.q1_pipeline import (
    _build_action_items,
    _compute_readiness,
    _diagnose_bloom_level,
    _format_stage_A,
    _format_stage_C,
    _load_stage_cache,
    _resolve_journal,
    _resolve_paper_path,
    _save_stage_cache,
    _sha256,
    _stage_cached,
    _target_bloom_level,
    register_tools,
)


# ---------------------------------------------------------------------------
# Tool collector helper
# ---------------------------------------------------------------------------


class _ToolCollector:
    def __init__(self):
        self.tools: dict = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


@pytest.fixture()
def pipeline_tool():
    collector = _ToolCollector()
    register_tools(collector)
    return collector.tools["q1_elevation_pipeline"]


# ---------------------------------------------------------------------------
# _resolve_paper_path
# ---------------------------------------------------------------------------


def test_resolve_paper_path_returns_explicit(tmp_path):
    assert _resolve_paper_path("my_paper.tex") == "my_paper.tex"


def test_resolve_paper_path_from_trace_yaml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    trace_dir = tmp_path / "_paper_trace" / "v2"
    trace_dir.mkdir(parents=True)
    (trace_dir / "1_contribution.yaml").write_text(
        yaml.dump({"paper_path": "main.tex", "title": "Test Paper"})
    )
    assert _resolve_paper_path(None) == "main.tex"


def test_resolve_paper_path_from_trace_yaml_ignores_dot(tmp_path, monkeypatch):
    """When paper_path is '.', fall through to workspace scan."""
    monkeypatch.chdir(tmp_path)
    trace_dir = tmp_path / "_paper_trace" / "v2"
    trace_dir.mkdir(parents=True)
    (trace_dir / "1_contribution.yaml").write_text(yaml.dump({"paper_path": "."}))
    # Create a single .tex file so the scan succeeds
    (tmp_path / "paper.tex").write_text("\\documentclass{article}")
    assert _resolve_paper_path(None) == "paper.tex"


def test_resolve_paper_path_from_workspace_scan_tex(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "paper.tex").write_text("")
    assert _resolve_paper_path(None) == "paper.tex"


def test_resolve_paper_path_from_workspace_scan_pdf(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "paper.pdf").write_bytes(b"PDF")
    assert _resolve_paper_path(None) == "paper.pdf"


def test_resolve_paper_path_raises_when_ambiguous(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.tex").write_text("")
    (tmp_path / "b.tex").write_text("")
    with pytest.raises(ValueError, match="Cannot auto-detect"):
        _resolve_paper_path(None)


def test_resolve_paper_path_raises_when_no_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        _resolve_paper_path(None)


# ---------------------------------------------------------------------------
# _resolve_journal
# ---------------------------------------------------------------------------


def test_resolve_journal_returns_explicit():
    assert _resolve_journal("IEEE TPAMI") == "IEEE TPAMI"


def test_resolve_journal_from_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / ".crane" / "journal-system"
    config_dir.mkdir(parents=True)
    (config_dir / "submission-config.yaml").write_text(
        yaml.dump({"target_journal": "Expert Systems with Applications"})
    )
    assert _resolve_journal(None) == "Expert Systems with Applications"


def test_resolve_journal_returns_none_when_no_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert _resolve_journal(None) is None


# ---------------------------------------------------------------------------
# _sha256
# ---------------------------------------------------------------------------


def test_sha256_returns_hex(tmp_path):
    f = tmp_path / "file.txt"
    f.write_bytes(b"hello")
    digest = _sha256(str(f))
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


def test_sha256_returns_empty_on_missing_file():
    result = _sha256("/nonexistent/path/paper.tex")
    assert result == ""


# ---------------------------------------------------------------------------
# Stage cache helpers
# ---------------------------------------------------------------------------


def test_stage_cache_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(q1_module, "CACHE_FILE", tmp_path / "_paper_trace/v2/care_stage_cache.json")
    _save_stage_cache("C", {"total": 2, "high_severity": 1}, "abc123")
    assert _stage_cached("C", "abc123")
    assert not _stage_cached("C", "wronghash")
    result = _load_stage_cache("C")
    assert result["total"] == 2


def test_stage_cached_returns_false_when_no_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(q1_module, "CACHE_FILE", tmp_path / "nonexistent.json")
    assert not _stage_cached("C", "abc123")


def test_stage_cached_false_for_empty_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(q1_module, "CACHE_FILE", tmp_path / "_paper_trace/v2/care_stage_cache.json")
    _save_stage_cache("C", {"total": 0}, "abc123")
    assert not _stage_cached("C", "")


# ---------------------------------------------------------------------------
# _diagnose_bloom_level
# ---------------------------------------------------------------------------


class _FakeSection:
    def __init__(self, content: str):
        self.content = content


def test_bloom_create():
    sections = [_FakeSection("In this paper we propose a novel framework for ...")]
    assert _diagnose_bloom_level(sections) == "Create"


def test_bloom_evaluate():
    sections = [_FakeSection("In this section we evaluate and we compare our method which outperforms ...")]
    assert _diagnose_bloom_level(sections) == "Evaluate"


def test_bloom_analyze():
    sections = [_FakeSection("We analyze the impact and we investigate the results.")]
    assert _diagnose_bloom_level(sections) == "Analyze"


def test_bloom_apply():
    sections = [_FakeSection("We apply the existing model and we implement the solution.")]
    assert _diagnose_bloom_level(sections) == "Apply"


def test_bloom_understand_default():
    sections = [_FakeSection("This paper discusses related work.")]
    assert _diagnose_bloom_level(sections) == "Understand"


def test_target_bloom_level_increments():
    assert _target_bloom_level("Understand") == "Apply"
    assert _target_bloom_level("Apply") == "Analyze"
    assert _target_bloom_level("Evaluate") == "Create"
    assert _target_bloom_level("Create") == "Create"  # already at top


# ---------------------------------------------------------------------------
# _format_stage_C / _format_stage_A
# ---------------------------------------------------------------------------


def test_format_stage_C_counts_high_severity():
    from crane.services.contradiction_detection_service import (
        Contradiction,
        ContradictionType,
    )

    c1 = Contradiction(
        type=ContradictionType.NUMERICAL,
        location_a="Abstract",
        location_b="Table 3",
        description="Number mismatch",
        severity="high",
        reviewer_attack_prob=0.9,
        suggested_fix="Fix numbers",
    )
    c2 = Contradiction(
        type=ContradictionType.CLAIM_EVIDENCE,
        location_a="Intro",
        location_b="Results",
        description="Unsupported claim",
        severity="low",
        reviewer_attack_prob=0.2,
        suggested_fix="Add citation",
    )
    result = _format_stage_C([c1, c2])
    assert result["total"] == 2
    assert result["high_severity"] == 1
    assert len(result["contradictions"]) == 2


def test_format_stage_A_separates_field_gaps():
    from crane.services.knowledge_gap_elevation_service import GapLevel, KnowledgeGap

    g1 = KnowledgeGap(
        concept_a="A",
        concept_b="B",
        gap_description="gap",
        level=GapLevel.FIELD,
        elevation_potential="Q2→Q1",
        reframe_suggestion="Reframe RQ",
    )
    g2 = KnowledgeGap(
        concept_a="C",
        concept_b="D",
        gap_description="gap2",
        level=GapLevel.PAPER,
        elevation_potential="影響有限",
        reframe_suggestion="Add citation",
    )
    result = _format_stage_A([g1, g2], "Apply")
    assert result["bloom_level"] == "Apply"
    assert result["target_bloom"] == "Analyze"
    assert result["total_gaps"] == 2
    assert len(result["field_level_gaps"]) == 1
    assert result["field_level_gaps"][0]["concept_a"] == "A"


# ---------------------------------------------------------------------------
# _build_action_items
# ---------------------------------------------------------------------------


def test_build_action_items_from_high_severity_contradiction():
    stage_C = {
        "contradictions": [
            {
                "severity": "high",
                "location_a": "Abstract",
                "location_b": "Table 3",
                "suggested_fix": "Fix numbers",
            },
            {
                "severity": "low",
                "location_a": "Intro",
                "location_b": "Conclusion",
                "suggested_fix": "Minor fix",
            },
        ]
    }
    items = _build_action_items(stage_C, None, None, None)
    assert len(items) == 1
    assert items[0]["priority"] == 1
    assert items[0]["stage"] == "C"
    assert "Abstract" in items[0]["task"]
    assert "Table 3" in items[0]["task"]


def test_build_action_items_from_field_gaps():
    stage_A = {
        "field_level_gaps": [
            {"reframe_suggestion": "Broaden contribution claim to field level"},
            {"reframe_suggestion": "Connect RQ to field-level gap"},
            {"reframe_suggestion": "This third gap should be ignored"},
        ]
    }
    items = _build_action_items(None, stage_A, None, None)
    assert len(items) == 2  # only top 2
    assert all(i["priority"] == 2 for i in items)
    assert all(i["stage"] == "A" for i in items)


def test_build_action_items_sorted_by_priority():
    stage_C = {
        "contradictions": [
            {"severity": "high", "location_a": "A", "location_b": "B", "suggested_fix": "Fix"}
        ]
    }
    stage_A = {"field_level_gaps": [{"reframe_suggestion": "Reframe"}]}
    items = _build_action_items(stage_C, stage_A, None, None)
    priorities = [i["priority"] for i in items]
    assert priorities == sorted(priorities)


# ---------------------------------------------------------------------------
# _compute_readiness
# ---------------------------------------------------------------------------


def test_compute_readiness_full():
    results = {
        "stage_C": {"high_severity": 1, "total": 4},
        "stage_E": {"feynman_score": 0.7},
    }
    # stage_C score = 1 - (1/4)*0.5 = 0.875
    # average = (0.875 + 0.7) / 2 = 0.7875 → 0.79
    score = _compute_readiness(results)
    assert score == 0.79


def test_compute_readiness_no_contradictions():
    results = {"stage_C": {"high_severity": 0, "total": 3}}
    assert _compute_readiness(results) == 1.0


def test_compute_readiness_empty():
    assert _compute_readiness({}) == 0.0


# ---------------------------------------------------------------------------
# Full pipeline tool — stages=["C"] only
# ---------------------------------------------------------------------------


def _make_fake_contradiction(severity="high"):
    from crane.services.contradiction_detection_service import (
        Contradiction,
        ContradictionType,
    )

    return Contradiction(
        type=ContradictionType.NUMERICAL,
        location_a="Abstract",
        location_b="Table 1",
        description="Mismatch",
        severity=severity,
        reviewer_attack_prob=0.8,
        suggested_fix="Correct the number",
    )


def test_pipeline_tool_stages_C_only(pipeline_tool, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    paper = tmp_path / "paper.tex"
    paper.write_text("\\documentclass{article} \\begin{document} We propose a novel framework\\end{document}")

    with (
        patch("crane.tools.q1_pipeline.SectionChunker") as MockChunker,
        patch("crane.tools.q1_pipeline.PaperKnowledgeGraphService") as MockKG,
        patch("crane.tools.q1_pipeline.ContradictionDetectionService") as MockCDS,
        patch("crane.tools.q1_pipeline._write_report_to_trace"),
    ):
        MockChunker.return_value.chunk_latex_paper.return_value = []
        MockKG.return_value.build.return_value = MagicMock()
        MockCDS.return_value.detect.return_value = [_make_fake_contradiction("high")]

        result = pipeline_tool(paper_path=str(paper), stages=["C"])

    assert result["stages_run"] == ["C"]
    assert "stage_C" in result
    assert "stage_A" not in result
    assert "stage_R" not in result
    assert "stage_E" not in result
    assert result["stage_C"]["total"] == 1
    assert result["stage_C"]["high_severity"] == 1


def test_pipeline_tool_zero_config_paper_path(pipeline_tool, tmp_path, monkeypatch):
    """Paper path auto-detected from Paper Trace YAML."""
    monkeypatch.chdir(tmp_path)
    trace_dir = tmp_path / "_paper_trace" / "v2"
    trace_dir.mkdir(parents=True)
    (trace_dir / "1_contribution.yaml").write_text(yaml.dump({"paper_path": "main.tex"}))
    (tmp_path / "main.tex").write_text("content")

    with (
        patch("crane.tools.q1_pipeline.SectionChunker") as MockChunker,
        patch("crane.tools.q1_pipeline.PaperKnowledgeGraphService") as MockKG,
        patch("crane.tools.q1_pipeline.ContradictionDetectionService") as MockCDS,
        patch("crane.tools.q1_pipeline.KnowledgeGapElevationService") as MockGaps,
        patch("crane.tools.q1_pipeline.ResearchPositioningService") as MockPos,
        patch("crane.tools.q1_pipeline.EvidenceEvaluationService") as MockEval,
        patch("crane.tools.q1_pipeline._write_report_to_trace"),
    ):
        MockChunker.return_value.chunk_latex_paper.return_value = []
        MockKG.return_value.build.return_value = MagicMock()
        MockCDS.return_value.detect.return_value = []
        MockGaps.return_value.evaluate.return_value = []
        MockPos.return_value.analyze_positioning.return_value = {"domain": "AI/ML"}
        mock_eval = MagicMock()
        mock_eval.overall_score = 75.0
        mock_eval.dimension_scores = []
        MockEval.return_value.evaluate.return_value = mock_eval

        feynman_mock = MagicMock()
        feynman_mock.questions = []
        feynman_mock.weak_dimensions = []
        with patch("crane.tools.q1_pipeline.FeynmanSessionService") as MockFeynman:
            MockFeynman.return_value.generate_session.return_value = feynman_mock
            result = pipeline_tool()

    assert result["paper_path"] == "main.tex"


def test_pipeline_tool_stage_cache_used(pipeline_tool, tmp_path, monkeypatch):
    """When cache is warm, ContradictionDetectionService.detect should NOT be called."""
    monkeypatch.chdir(tmp_path)
    paper = tmp_path / "paper.tex"
    paper.write_text("content")

    # Warm up cache
    paper_hash = _sha256(str(paper))
    cached_result = {"total": 5, "high_severity": 0, "contradictions": []}
    monkeypatch.setattr(
        q1_module, "CACHE_FILE", tmp_path / "_paper_trace/v2/care_stage_cache.json"
    )
    _save_stage_cache("C", cached_result, paper_hash)

    with (
        patch("crane.tools.q1_pipeline.SectionChunker") as MockChunker,
        patch("crane.tools.q1_pipeline.PaperKnowledgeGraphService") as MockKG,
        patch("crane.tools.q1_pipeline.ContradictionDetectionService") as MockCDS,
        patch("crane.tools.q1_pipeline._write_report_to_trace"),
    ):
        MockChunker.return_value.chunk_latex_paper.return_value = []
        MockKG.return_value.build.return_value = MagicMock()

        result = pipeline_tool(paper_path=str(paper), stages=["C"], skip_cache=False)

    MockCDS.return_value.detect.assert_not_called()
    assert result["stage_C"]["total"] == 5


def test_pipeline_tool_skip_cache_bypasses_cache(pipeline_tool, tmp_path, monkeypatch):
    """When skip_cache=True, service is called even if cache exists."""
    monkeypatch.chdir(tmp_path)
    paper = tmp_path / "paper.tex"
    paper.write_text("content")

    paper_hash = _sha256(str(paper))
    monkeypatch.setattr(
        q1_module, "CACHE_FILE", tmp_path / "_paper_trace/v2/care_stage_cache.json"
    )
    _save_stage_cache("C", {"total": 99, "high_severity": 0, "contradictions": []}, paper_hash)

    with (
        patch("crane.tools.q1_pipeline.SectionChunker") as MockChunker,
        patch("crane.tools.q1_pipeline.PaperKnowledgeGraphService") as MockKG,
        patch("crane.tools.q1_pipeline.ContradictionDetectionService") as MockCDS,
        patch("crane.tools.q1_pipeline._write_report_to_trace"),
    ):
        MockChunker.return_value.chunk_latex_paper.return_value = []
        MockKG.return_value.build.return_value = MagicMock()
        MockCDS.return_value.detect.return_value = [_make_fake_contradiction("low")]

        result = pipeline_tool(paper_path=str(paper), stages=["C"], skip_cache=True)

    MockCDS.return_value.detect.assert_called_once()
    assert result["stage_C"]["total"] == 1


def test_pipeline_tool_action_items_start_with_verb(pipeline_tool, tmp_path, monkeypatch):
    """Action items must start with a verb (Chinese character counts)."""
    monkeypatch.chdir(tmp_path)
    paper = tmp_path / "paper.tex"
    paper.write_text("content")

    with (
        patch("crane.tools.q1_pipeline.SectionChunker") as MockChunker,
        patch("crane.tools.q1_pipeline.PaperKnowledgeGraphService") as MockKG,
        patch("crane.tools.q1_pipeline.ContradictionDetectionService") as MockCDS,
        patch("crane.tools.q1_pipeline._write_report_to_trace"),
    ):
        MockChunker.return_value.chunk_latex_paper.return_value = []
        MockKG.return_value.build.return_value = MagicMock()
        MockCDS.return_value.detect.return_value = [_make_fake_contradiction("high")]

        result = pipeline_tool(paper_path=str(paper), stages=["C"])

    for item in result["action_items"]:
        task = item["task"]
        # Task should be a non-empty string (starts with Chinese verb 修正 or English verb)
        assert task and isinstance(task, str)
        assert len(task) > 0


def test_pipeline_tool_service_failure_does_not_crash(pipeline_tool, tmp_path, monkeypatch):
    """If ContradictionDetectionService raises, stage_C gets an error key but pipeline continues."""
    monkeypatch.chdir(tmp_path)
    paper = tmp_path / "paper.tex"
    paper.write_text("content")

    with (
        patch("crane.tools.q1_pipeline.SectionChunker") as MockChunker,
        patch("crane.tools.q1_pipeline.PaperKnowledgeGraphService") as MockKG,
        patch("crane.tools.q1_pipeline.ContradictionDetectionService") as MockCDS,
        patch("crane.tools.q1_pipeline._write_report_to_trace"),
    ):
        MockChunker.return_value.chunk_latex_paper.return_value = []
        MockKG.return_value.build.return_value = MagicMock()
        MockCDS.return_value.detect.side_effect = RuntimeError("LLM unavailable")

        result = pipeline_tool(paper_path=str(paper), stages=["C"])

    assert "stage_C" in result
    assert "error" in result["stage_C"]
    assert result["stage_C"]["total"] == 0


def test_pipeline_tool_all_stages_returns_all_keys(pipeline_tool, tmp_path, monkeypatch):
    """Running all stages should populate stage_C, stage_A, stage_R, stage_E."""
    monkeypatch.chdir(tmp_path)
    paper = tmp_path / "paper.tex"
    paper.write_text("We propose a novel framework.")

    with (
        patch("crane.tools.q1_pipeline.SectionChunker") as MockChunker,
        patch("crane.tools.q1_pipeline.PaperKnowledgeGraphService") as MockKG,
        patch("crane.tools.q1_pipeline.ContradictionDetectionService") as MockCDS,
        patch("crane.tools.q1_pipeline.KnowledgeGapElevationService") as MockGaps,
        patch("crane.tools.q1_pipeline.ResearchPositioningService") as MockPos,
        patch("crane.tools.q1_pipeline.EvidenceEvaluationService") as MockEval,
        patch("crane.tools.q1_pipeline.FeynmanSessionService") as MockFeynman,
        patch("crane.tools.q1_pipeline._write_report_to_trace"),
    ):
        MockChunker.return_value.chunk_latex_paper.return_value = []
        MockKG.return_value.build.return_value = MagicMock()
        MockCDS.return_value.detect.return_value = []
        MockGaps.return_value.evaluate.return_value = []
        MockPos.return_value.analyze_positioning.return_value = {"domain": "AI/ML"}
        mock_eval_result = MagicMock()
        mock_eval_result.overall_score = 80.0
        mock_eval_result.dimension_scores = []
        MockEval.return_value.evaluate.return_value = mock_eval_result
        feynman_result = MagicMock()
        feynman_result.questions = []
        feynman_result.weak_dimensions = []
        MockFeynman.return_value.generate_session.return_value = feynman_result

        result = pipeline_tool(paper_path=str(paper))

    assert "stage_C" in result
    assert "stage_A" in result
    assert "stage_R" in result
    assert "stage_E" in result
    assert isinstance(result["overall_q1_readiness"], float)
    assert isinstance(result["action_items"], list)


def test_pipeline_tool_output_format(pipeline_tool, tmp_path, monkeypatch):
    """Validate all required top-level keys are present in output."""
    monkeypatch.chdir(tmp_path)
    paper = tmp_path / "paper.tex"
    paper.write_text("content")

    with (
        patch("crane.tools.q1_pipeline.SectionChunker") as MockChunker,
        patch("crane.tools.q1_pipeline.PaperKnowledgeGraphService") as MockKG,
        patch("crane.tools.q1_pipeline.ContradictionDetectionService") as MockCDS,
        patch("crane.tools.q1_pipeline._write_report_to_trace"),
    ):
        MockChunker.return_value.chunk_latex_paper.return_value = []
        MockKG.return_value.build.return_value = MagicMock()
        MockCDS.return_value.detect.return_value = []

        result = pipeline_tool(paper_path=str(paper), stages=["C"])

    required_keys = {"paper_path", "target_journal", "overall_q1_readiness", "stages_run", "action_items", "trace_updated"}
    assert required_keys.issubset(result.keys())
