"""Tests for CARE pipeline trigger engineering (v0.15).

Coverage:
  A. evaluate_paper_v2 — next_step injected when overall_score < 70
  B. evaluate_paper_v2 — no next_step when overall_score >= 70
  C. workspace_status — next_action in 3 CARE-trigger states
  D. crane_help("q1") — returns q1_elevation_pipeline entry
  E. crane_help("stuck") — returns advice list
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _ToolCollector:
    def __init__(self):
        self.tools: dict = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def eval_tools():
    from crane.tools.evaluation_v2 import register_tools

    col = _ToolCollector()
    register_tools(col)
    return col.tools


@pytest.fixture
def workspace_tools():
    from crane.tools.workspace import register_tools

    col = _ToolCollector()
    register_tools(col)
    return col.tools


@pytest.fixture
def help_tools():
    from crane.tools.crane_help import register_tools

    col = _ToolCollector()
    register_tools(col)
    return col.tools


def _make_dim_score(dimension: str, score: float):
    """Build a minimal DimensionScore-like object."""
    m = MagicMock()
    m.dimension = dimension
    m.score = score
    m.confidence = 0.8
    m.reason_codes = []
    m.evidence_spans = []
    m.missing_evidence = []
    m.suggestions = []
    return m


def _make_evaluation(overall_score: float, dim_scores=None):
    """Build a minimal evaluation result."""
    if dim_scores is None:
        dim_scores = [
            _make_dim_score("methodology", overall_score),
            _make_dim_score("novelty", overall_score),
            _make_dim_score("evaluation", overall_score),
        ]
    ev = MagicMock()
    ev.paper_path = "/tmp/paper.tex"
    ev.overall_score = overall_score
    ev.gates_passed = overall_score >= 70
    ev.readiness = "ready" if overall_score >= 70 else "needs_revision"
    ev.dimension_scores = dim_scores
    # revision plan
    plan = MagicMock()
    plan.current_score = overall_score
    plan.projected_score = min(100, overall_score + 10)
    plan.items = []
    ev.revision_plan = plan
    # profile
    profile = MagicMock()
    profile.paper_type = MagicMock()
    profile.paper_type.value = "empirical"
    profile.method_family = "deep_learning"
    profile.evidence_pattern = MagicMock()
    profile.evidence_pattern.value = "quantitative"
    profile.validation_scale = "medium"
    profile.citation_neighborhood = []
    profile.novelty_shape = MagicMock()
    profile.novelty_shape.value = "incremental"
    profile.reproducibility_maturity = "partial"
    profile.problem_domain = "nlp"
    profile.keywords = []
    profile.word_count = 5000
    profile.has_code = True
    profile.has_appendix = False
    profile.num_figures = 3
    profile.num_tables = 2
    profile.num_equations = 5
    profile.num_references = 30
    profile.budget_usd = 0.0
    ev.profile = profile
    return ev


# ===========================================================================
# A + B  evaluate_paper_v2 next_step injection
# ===========================================================================


class TestEvaluatePaperV2NextStep:
    def test_next_step_present_when_score_below_70(self, eval_tools, tmp_path):
        paper = tmp_path / "paper.tex"
        paper.write_text(r"\documentclass{article}\begin{document}Hello\end{document}")

        weak_dims = [
            _make_dim_score("methodology", 50),
            _make_dim_score("novelty", 45),
            _make_dim_score("evaluation", 60),
        ]
        ev = _make_evaluation(55.0, weak_dims)

        with patch(
            "crane.tools.evaluation_v2.EvidenceEvaluationService"
        ) as MockSvc:
            MockSvc.return_value.evaluate.return_value = ev
            with patch("crane.tools.evaluation_v2._resolve_paper_path", return_value=str(paper)):
                result = eval_tools["evaluate_paper_v2"](paper_path=str(paper))

        assert "next_step" in result
        ns = result["next_step"]
        assert ns["action"] == "q1_elevation_pipeline"
        assert "CARE" in ns["reason"] or "care" in ns["reason"].lower()
        assert "q1_elevation_pipeline" in ns["command"]
        assert "estimated_minutes" in ns

    def test_next_step_absent_when_score_at_or_above_70(self, eval_tools, tmp_path):
        paper = tmp_path / "paper.tex"
        paper.write_text(r"\documentclass{article}\begin{document}Hello\end{document}")

        good_dims = [
            _make_dim_score("methodology", 80),
            _make_dim_score("novelty", 75),
            _make_dim_score("evaluation", 85),
        ]
        ev = _make_evaluation(80.0, good_dims)

        with patch(
            "crane.tools.evaluation_v2.EvidenceEvaluationService"
        ) as MockSvc:
            MockSvc.return_value.evaluate.return_value = ev
            with patch("crane.tools.evaluation_v2._resolve_paper_path", return_value=str(paper)):
                result = eval_tools["evaluate_paper_v2"](paper_path=str(paper))

        assert "next_step" not in result

    def test_next_step_exact_70_absent(self, eval_tools, tmp_path):
        paper = tmp_path / "paper.tex"
        paper.write_text(r"\documentclass{article}\begin{document}Hello\end{document}")

        dims = [_make_dim_score("methodology", 70)]
        ev = _make_evaluation(70.0, dims)

        with patch(
            "crane.tools.evaluation_v2.EvidenceEvaluationService"
        ) as MockSvc:
            MockSvc.return_value.evaluate.return_value = ev
            with patch("crane.tools.evaluation_v2._resolve_paper_path", return_value=str(paper)):
                result = eval_tools["evaluate_paper_v2"](paper_path=str(paper))

        assert "next_step" not in result

    def test_next_step_weak_dimension_names_in_reason(self, eval_tools, tmp_path):
        paper = tmp_path / "paper.tex"
        paper.write_text(r"\documentclass{article}\begin{document}Hello\end{document}")

        weak_dims = [
            _make_dim_score("methodology", 50),
            _make_dim_score("novelty", 45),
        ]
        ev = _make_evaluation(47.5, weak_dims)

        with patch(
            "crane.tools.evaluation_v2.EvidenceEvaluationService"
        ) as MockSvc:
            MockSvc.return_value.evaluate.return_value = ev
            with patch("crane.tools.evaluation_v2._resolve_paper_path", return_value=str(paper)):
                result = eval_tools["evaluate_paper_v2"](paper_path=str(paper))

        assert "next_step" in result
        reason = result["next_step"]["reason"]
        assert "methodology" in reason or "novelty" in reason


# ===========================================================================
# C  workspace_status next_action in 3 CARE-trigger states
# ===========================================================================


class TestWorkspaceStatusNextAction:
    def _run_workspace_status(self, workspace_tools, project_dir: str):
        """Run workspace_status with mocked git + gh calls."""
        with patch("crane.workspace.get_repo_root", return_value=project_dir):
            with patch(
                "crane.workspace.get_owner_repo", return_value=("testuser", "test-repo")
            ):
                with patch(
                    "crane.services.task_service.get_owner_repo",
                    return_value=("testuser", "test-repo"),
                ):
                    with patch("crane.utils.gh.subprocess.run") as mock_run:
                        m = MagicMock()
                        m.returncode = 0
                        m.stderr = ""
                        m.stdout = "[]"
                        mock_run.return_value = m
                        return workspace_tools["workspace_status"](project_dir=project_dir)

    def test_no_paper_no_next_action(self, workspace_tools, tmp_path):
        """Empty project — no paper, no trace → no next_action."""
        result = self._run_workspace_status(workspace_tools, str(tmp_path))
        assert "next_action" not in result

    def test_paper_without_trace_suggests_init_traceability(self, workspace_tools, tmp_path):
        """Project has .tex but no Paper Trace → init_traceability."""
        (tmp_path / "paper.tex").write_text(r"\documentclass{article}\begin{document}\end{document}")
        result = self._run_workspace_status(workspace_tools, str(tmp_path))
        assert "next_action" in result
        assert result["next_action"]["action"] == "init_traceability"

    def test_trace_without_cache_suggests_care(self, workspace_tools, tmp_path):
        """Paper Trace exists but CARE cache absent → q1_elevation_pipeline."""
        (tmp_path / "paper.tex").write_text(r"\documentclass{article}\begin{document}\end{document}")
        trace_dir = tmp_path / "_paper_trace" / "v2"
        trace_dir.mkdir(parents=True)
        (trace_dir / "1_contribution.yaml").write_text("contribution: test")
        result = self._run_workspace_status(workspace_tools, str(tmp_path))
        assert "next_action" in result
        assert result["next_action"]["action"] == "q1_elevation_pipeline"

    def test_stale_cache_suggests_rerun_care(self, workspace_tools, tmp_path):
        """CARE cache exists but last_run > 7 days ago → q1_elevation_pipeline."""
        (tmp_path / "paper.tex").write_text(r"\documentclass{article}\begin{document}\end{document}")
        trace_dir = tmp_path / "_paper_trace" / "v2"
        trace_dir.mkdir(parents=True)
        (trace_dir / "1_contribution.yaml").write_text("contribution: test")
        old_dt = datetime.now(timezone.utc) - timedelta(days=10)
        cache = {"last_run": old_dt.isoformat(), "stages": ["C", "A", "R", "E"]}
        (trace_dir / "care_stage_cache.json").write_text(json.dumps(cache))
        result = self._run_workspace_status(workspace_tools, str(tmp_path))
        assert "next_action" in result
        assert result["next_action"]["action"] == "q1_elevation_pipeline"
        assert "10" in result["next_action"]["message"] or "天" in result["next_action"]["message"]

    def test_fresh_cache_no_next_action(self, workspace_tools, tmp_path):
        """CARE cache exists and last_run < 7 days → no next_action."""
        (tmp_path / "paper.tex").write_text(r"\documentclass{article}\begin{document}\end{document}")
        trace_dir = tmp_path / "_paper_trace" / "v2"
        trace_dir.mkdir(parents=True)
        (trace_dir / "1_contribution.yaml").write_text("contribution: test")
        recent_dt = datetime.now(timezone.utc) - timedelta(days=2)
        cache = {"last_run": recent_dt.isoformat(), "stages": ["C", "A", "R", "E"]}
        (trace_dir / "care_stage_cache.json").write_text(json.dumps(cache))
        result = self._run_workspace_status(workspace_tools, str(tmp_path))
        assert "next_action" not in result


# ===========================================================================
# D  crane_help("q1") returns q1_elevation_pipeline entry
# ===========================================================================


class TestCraneHelpQ1:
    def test_q1_topic_returns_match(self, help_tools):
        result = help_tools["crane_help"](topic="q1")
        assert isinstance(result, dict)
        assert result["matches"], "Expected at least one match for topic 'q1'"

    def test_q1_match_contains_q1_elevation_pipeline(self, help_tools):
        result = help_tools["crane_help"](topic="q1")
        tools_mentioned = []
        for match in result["matches"]:
            if "tool" in match:
                tools_mentioned.append(match["tool"])
            if "tools" in match:
                tools_mentioned.extend(match["tools"])
            if "call" in match:
                tools_mentioned.append(match["call"])
        combined = " ".join(str(t) for t in tools_mentioned)
        assert "q1_elevation_pipeline" in combined

    def test_care_alias_returns_same(self, help_tools):
        result = help_tools["crane_help"](topic="care")
        assert result["matches"], "Expected matches for topic 'care'"

    def test_提升_returns_q1_match(self, help_tools):
        result = help_tools["crane_help"](topic="提升")
        assert result["matches"], "Expected matches for topic '提升'"


# ===========================================================================
# E  crane_help("stuck") returns advice list
# ===========================================================================


class TestCraneHelpStuck:
    def test_stuck_topic_returns_match(self, help_tools):
        result = help_tools["crane_help"](topic="stuck")
        assert result["matches"], "Expected matches for topic 'stuck'"

    def test_stuck_match_has_advice_list(self, help_tools):
        result = help_tools["crane_help"](topic="stuck")
        advice_found = False
        for match in result["matches"]:
            if "advice" in match and isinstance(match["advice"], list):
                advice_found = True
                assert len(match["advice"]) >= 3
        assert advice_found, "Expected at least one match with 'advice' list"

    def test_stuck_advice_mentions_evaluate(self, help_tools):
        result = help_tools["crane_help"](topic="stuck")
        all_advice = []
        for match in result["matches"]:
            all_advice.extend(match.get("advice", []))
        combined = " ".join(all_advice)
        assert "evaluate_paper_v2" in combined

    def test_stuck_advice_mentions_q1_elevation(self, help_tools):
        result = help_tools["crane_help"](topic="stuck")
        all_advice = []
        for match in result["matches"]:
            all_advice.extend(match.get("advice", []))
        combined = " ".join(all_advice)
        assert "q1_elevation_pipeline" in combined
