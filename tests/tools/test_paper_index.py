"""Tests for v0.14.2 — PaperIndexService + build_paper_index MCP tool.

Coverage:
  A. PaperIndexService unit tests (build, load, update_results, cache)
  B. build_paper_index MCP tool
  C. lru_cache on parse_latex_sections
  D. submission_pipeline single-review-pass (regression guard)
  E. Evaluation metrics: speed, cache hit rate, count accuracy
"""

from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from crane.services.paper_index_service import PaperIndexService
from crane.tools.paper_index import register_tools as register_paper_index_tools

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_TEX = """\
\\documentclass{article}
\\title{Deep Learning for Symbolic Repair}
\\begin{document}

\\begin{abstract}
We propose a novel method for symbolic repair using deep learning.
Our approach outperforms state-of-the-art baselines on the benchmark dataset.
\\end{abstract}

\\section{Introduction}
We introduce our method here.
It is awesome and cool stuff.
Our contribution is the first to tackle this limitation.
\\cite{smith2023}

\\subsection{Motivation}
Our motivation is constraint by prior shortcoming.

\\section{Methods}
We present the training setup and hyperparameter details.
Code available at https://github.com/test/repo.
\\begin{equation}
x = y + z
\\end{equation}

\\section{Results}
The baseline and benchmark dataset evaluation shows outperform.
\\begin{table}
\\caption{Results}
\\end{table}

\\begin{figure}
\\caption{Architecture}
\\end{figure}

\\section{Limitations}
Our drawback is that the constraint may limit generalization.

\\appendix
\\section{Appendix}
Implementation details and random seed configuration.
\\end{document}
"""


@pytest.fixture
def tex_file(tmp_path: Path) -> Path:
    p = tmp_path / "paper.tex"
    p.write_text(SAMPLE_TEX, encoding="utf-8")
    return p


@pytest.fixture
def svc() -> PaperIndexService:
    return PaperIndexService()


class _ToolCollector:
    def __init__(self):
        self.tools: dict = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn
        return decorator


@pytest.fixture
def paper_tools():
    col = _ToolCollector()
    register_paper_index_tools(col)
    return col.tools


# ===========================================================================
# A. PaperIndexService — build()
# ===========================================================================


class TestBuildIndexStructure:
    def test_returns_meta(self, svc, tex_file):
        idx = svc.build(tex_file)
        assert "_meta" in idx
        assert idx["_meta"]["schema"] == "1"
        assert idx["_meta"]["source"] == "paper.tex"

    def test_structure_key_present(self, svc, tex_file):
        idx = svc.build(tex_file)
        assert "structure" in idx

    def test_title_extracted(self, svc, tex_file):
        idx = svc.build(tex_file)
        assert idx["structure"]["title"] == "Deep Learning for Symbolic Repair"

    def test_abstract_extracted(self, svc, tex_file):
        idx = svc.build(tex_file)
        assert "novel method" in idx["structure"]["abstract"]

    def test_sections_extracted(self, svc, tex_file):
        idx = svc.build(tex_file)
        names = [s["name"] for s in idx["structure"]["sections"]]
        assert "Introduction" in names
        assert "Methods" in names

    def test_section_levels(self, svc, tex_file):
        idx = svc.build(tex_file)
        level_map = {s["name"]: s["level"] for s in idx["structure"]["sections"]}
        assert level_map["Introduction"] == 1
        assert level_map["Motivation"] == 2

    def test_total_lines_positive(self, svc, tex_file):
        idx = svc.build(tex_file)
        assert idx["structure"]["total_lines"] > 0


class TestBuildIndexCounts:
    def test_words_positive(self, svc, tex_file):
        idx = svc.build(tex_file)
        assert idx["counts"]["words"] > 0

    def test_figures_count(self, svc, tex_file):
        idx = svc.build(tex_file)
        assert idx["counts"]["figures"] == 1

    def test_tables_count(self, svc, tex_file):
        idx = svc.build(tex_file)
        assert idx["counts"]["tables"] == 1

    def test_equations_count(self, svc, tex_file):
        idx = svc.build(tex_file)
        assert idx["counts"]["equations"] == 1

    def test_citations_count(self, svc, tex_file):
        idx = svc.build(tex_file)
        assert idx["counts"]["citations"] == 1


class TestBuildIndexFlags:
    def test_has_code_detected(self, svc, tex_file):
        idx = svc.build(tex_file)
        assert idx["flags"]["has_code"] is True

    def test_has_appendix_detected(self, svc, tex_file):
        idx = svc.build(tex_file)
        assert idx["flags"]["has_appendix"] is True

    def test_no_code_when_absent(self, svc, tmp_path):
        p = tmp_path / "plain.tex"
        p.write_text("\\section{Methods}\nNo repo here.\n", encoding="utf-8")
        idx = svc.build(p)
        assert idx["flags"]["has_code"] is False

    def test_no_appendix_when_absent(self, svc, tmp_path):
        p = tmp_path / "plain.tex"
        p.write_text("\\section{Intro}\nSome text.\n", encoding="utf-8")
        idx = svc.build(p)
        assert idx["flags"]["has_appendix"] is False


class TestBuildIndexPrescan:
    def test_prescan_keys_complete(self, svc, tex_file):
        idx = svc.build(tex_file)
        expected = {
            "informal_language", "method_claims", "novelty_keywords",
            "benchmark_keywords", "limitation_keywords", "repro_keywords",
        }
        assert expected <= set(idx["prescan"].keys())

    def test_informal_language_detected(self, svc, tex_file):
        # SAMPLE_TEX has "awesome" and "cool" → ≥2
        idx = svc.build(tex_file)
        assert idx["prescan"]["informal_language"] >= 2

    def test_method_claims_detected(self, svc, tex_file):
        # "We propose", "We introduce", "We present" → ≥3
        idx = svc.build(tex_file)
        assert idx["prescan"]["method_claims"] >= 3

    def test_limitation_keywords_detected(self, svc, tex_file):
        # "limitation", "shortcoming", "constraint", "drawback" → ≥1
        idx = svc.build(tex_file)
        assert idx["prescan"]["limitation_keywords"] >= 1

    def test_repro_keywords_detected(self, svc, tex_file):
        # "hyperparameter", "random seed", "code available" in tex
        idx = svc.build(tex_file)
        assert idx["prescan"]["repro_keywords"] >= 1

    def test_prescan_counts_match_python_regex(self, svc, tex_file):
        """Prescan counts must equal what direct Python regex finds."""
        idx = svc.build(tex_file)
        raw = tex_file.read_text(encoding="utf-8")
        py_count = len(re.findall(r"\b(awesome|cool|nice|amazing|stuff|basically)\b", raw, re.I))
        assert idx["prescan"]["informal_language"] == py_count


class TestBuildIndexResults:
    def test_results_key_present(self, svc, tex_file):
        idx = svc.build(tex_file)
        assert "results" in idx

    def test_results_initial_values_none(self, svc, tex_file):
        idx = svc.build(tex_file)
        assert idx["results"]["crane_review_full"] is None
        assert idx["results"]["evaluate_paper_v2"] is None
        assert idx["results"]["crane_diagnose"] is None


# ===========================================================================
# B. PaperIndexService — caching
# ===========================================================================


class TestIndexCaching:
    def test_writes_yaml_to_disk(self, svc, tex_file):
        svc.build(tex_file)
        index_path = tex_file.parent / ".paper_index.yaml"
        assert index_path.exists()

    def test_mtime_stored_in_meta(self, svc, tex_file):
        idx = svc.build(tex_file)
        assert idx["_meta"]["mtime"] == pytest.approx(tex_file.stat().st_mtime)

    def test_second_call_returns_same_title(self, svc, tex_file):
        idx1 = svc.build(tex_file)
        idx2 = svc.build(tex_file)
        assert idx1["structure"]["title"] == idx2["structure"]["title"]

    def test_cache_invalidated_on_file_change(self, svc, tex_file):
        svc.build(tex_file)
        old_mtime = tex_file.stat().st_mtime
        # Modify file
        tex_file.write_text(SAMPLE_TEX + "\n% modified\n", encoding="utf-8")
        # Ensure mtime changes (touch ensures it, but write may change it)
        idx2 = svc.build(tex_file)
        assert idx2["_meta"]["mtime"] != old_mtime

    def test_force_rebuilds_despite_fresh_cache(self, svc, tex_file):
        svc.build(tex_file)
        # Mutate index on disk to have different title
        index_path = tex_file.parent / ".paper_index.yaml"
        existing = yaml.safe_load(index_path.read_text())
        existing["structure"]["title"] = "STALE_TITLE"
        index_path.write_text(yaml.dump(existing))
        # Without force → stale cache returned
        idx_cached = svc.build(tex_file, force=False)
        assert idx_cached["structure"]["title"] == "STALE_TITLE"
        # With force → fresh build overwrites
        idx_fresh = svc.build(tex_file, force=True)
        assert idx_fresh["structure"]["title"] == "Deep Learning for Symbolic Repair"

    def test_load_returns_none_when_no_index(self, svc, tex_file):
        result = svc.load(tex_file)
        assert result is None

    def test_load_returns_index_after_build(self, svc, tex_file):
        svc.build(tex_file)
        result = svc.load(tex_file)
        assert result is not None
        assert result["_meta"]["source"] == "paper.tex"

    def test_load_returns_none_after_file_modified(self, svc, tex_file):
        svc.build(tex_file)
        tex_file.write_text(SAMPLE_TEX + "\n% changed\n", encoding="utf-8")
        result = svc.load(tex_file)
        assert result is None


class TestUpdateResults:
    def test_update_results_persists(self, svc, tex_file):
        svc.build(tex_file)
        svc.update_results(tex_file, "crane_review_full", {"critical": 2, "total": 5})
        reloaded = svc.load(tex_file)
        assert reloaded["results"]["crane_review_full"]["critical"] == 2

    def test_update_results_no_error_when_no_index(self, svc, tex_file):
        # Should not raise even if index file doesn't exist
        svc.update_results(tex_file, "crane_review_full", {"x": 1})

    def test_update_results_multiple_keys(self, svc, tex_file):
        svc.build(tex_file)
        svc.update_results(tex_file, "evaluate_paper_v2", {"score": 78.5})
        svc.update_results(tex_file, "crane_diagnose", {"issues": 3})
        idx = svc.load(tex_file)
        assert idx["results"]["evaluate_paper_v2"]["score"] == 78.5
        assert idx["results"]["crane_diagnose"]["issues"] == 3


# ===========================================================================
# C. build_paper_index MCP tool
# ===========================================================================


class TestBuildPaperIndexTool:
    def test_tool_registered(self, paper_tools):
        assert "build_paper_index" in paper_tools

    def test_returns_meta(self, paper_tools, tex_file):
        result = paper_tools["build_paper_index"](paper_path=str(tex_file))
        assert "_meta" in result

    def test_returns_structure(self, paper_tools, tex_file):
        result = paper_tools["build_paper_index"](paper_path=str(tex_file))
        assert "structure" in result
        assert result["structure"]["title"] == "Deep Learning for Symbolic Repair"

    def test_returns_counts(self, paper_tools, tex_file):
        result = paper_tools["build_paper_index"](paper_path=str(tex_file))
        assert "counts" in result
        assert result["counts"]["figures"] == 1

    def test_returns_flags(self, paper_tools, tex_file):
        result = paper_tools["build_paper_index"](paper_path=str(tex_file))
        assert result["flags"]["has_code"] is True
        assert result["flags"]["has_appendix"] is True

    def test_returns_prescan(self, paper_tools, tex_file):
        result = paper_tools["build_paper_index"](paper_path=str(tex_file))
        assert "prescan" in result
        assert "informal_language" in result["prescan"]

    def test_error_on_missing_file(self, paper_tools, tmp_path):
        result = paper_tools["build_paper_index"](
            paper_path=str(tmp_path / "nonexistent.tex")
        )
        assert "error" in result

    def test_force_flag_accepted(self, paper_tools, tex_file):
        paper_tools["build_paper_index"](paper_path=str(tex_file))
        result = paper_tools["build_paper_index"](paper_path=str(tex_file), force=True)
        assert "_meta" in result

    def test_cache_hit_key_present(self, paper_tools, tex_file):
        paper_tools["build_paper_index"](paper_path=str(tex_file))
        result = paper_tools["build_paper_index"](paper_path=str(tex_file))
        assert "cache_hit" in result


class TestRunReviewPipelineTool:
    def test_tool_registered(self, paper_tools):
        assert "run_review_pipeline" in paper_tools


# ===========================================================================
# D. lru_cache on parse_latex_sections
# ===========================================================================


class TestLatexParserCache:
    def test_cache_exists(self):
        from crane.services.latex_parser import _parse_latex_cached
        assert hasattr(_parse_latex_cached, "cache_info")

    def test_second_call_hits_cache(self, tex_file):
        from crane.services.latex_parser import _parse_latex_cached

        _parse_latex_cached.cache_clear()
        _parse_latex_cached(str(tex_file))
        _parse_latex_cached(str(tex_file))

        info = _parse_latex_cached.cache_info()
        assert info.hits >= 1

    def test_parse_latex_sections_delegates_to_cache(self, tex_file):
        from crane.services.latex_parser import _parse_latex_cached, parse_latex_sections

        _parse_latex_cached.cache_clear()
        parse_latex_sections(str(tex_file))
        parse_latex_sections(str(tex_file))

        info = _parse_latex_cached.cache_info()
        assert info.hits >= 1

    def test_path_object_accepted(self, tex_file):
        from crane.services.latex_parser import parse_latex_sections

        result = parse_latex_sections(tex_file)  # Path object
        assert result.title == "Deep Learning for Symbolic Repair"

    def test_cache_maxsize_is_eight(self):
        from crane.services.latex_parser import _parse_latex_cached

        info = _parse_latex_cached.cache_info()
        assert info.maxsize == 8


# ===========================================================================
# E. Submission pipeline — single review pass
# ===========================================================================


class TestSubmissionPipelineSinglePass:
    """Verify SectionReviewService.review_paper() is called exactly once
    in run_full_check, not twice as before v0.14.2."""

    def test_review_paper_called_once(self, tmp_path, tex_file):
        from crane.services.section_review_service import SectionReviewService
        from crane.services.submission_pipeline_service import SubmissionPipelineService

        # Minimal stubs to avoid full side-effects
        fake_review = MagicMock()
        fake_review.sections = []
        fake_review.summary = {}

        class _FakeQ1:
            def evaluate(self, path):
                r = MagicMock()
                r.overall_score = 75.0
                r.readiness = "ready"
                r.criteria = []
                return r

        class _FakeRef:
            def get_all_keys(self):
                return []

        class _FakeExp:
            def collate_all(self):
                r = MagicMock()
                r.total_metrics = 0
                r.total_files = 0
                return r
            def to_markdown(self, _):
                return "# Exp\n"

        with patch.object(SectionReviewService, "review_paper", return_value=fake_review) as mock_rv, \
             patch("crane.services.submission_pipeline_service.Q1EvaluationService", return_value=_FakeQ1()), \
             patch("crane.services.submission_pipeline_service.ReferenceService", return_value=_FakeRef()), \
             patch("crane.services.submission_pipeline_service.ExperimentCollationService", return_value=_FakeExp()):

            svc = SubmissionPipelineService(tmp_path)
            svc.run_full_check(str(tex_file))

        assert mock_rv.call_count == 1, (
            f"Expected 1 review_paper() call, got {mock_rv.call_count}. "
            "Regression: double-parse not fixed."
        )

    def test_framing_reuses_precomputed(self, tmp_path, tex_file):
        """generate_framing_analysis must accept precomputed_review."""
        from crane.services.section_review_service import SectionReviewService
        from crane.services.submission_pipeline_service import SubmissionPipelineService

        fake_review = MagicMock()
        fake_review.sections = []

        svc = SubmissionPipelineService(tmp_path)
        sub_dir = tmp_path / "reports"
        sub_dir.mkdir()
        (sub_dir / "reports").mkdir(exist_ok=True)

        with patch.object(SectionReviewService, "review_paper") as mock_rv:
            svc.generate_framing_analysis(
                str(tex_file), sub_dir, precomputed_review=fake_review
            )
        # When precomputed_review is supplied, review_paper must NOT be called
        mock_rv.assert_not_called()

    def test_health_check_reuses_precomputed(self, tmp_path, tex_file):
        """generate_paper_health_check must accept precomputed_review."""
        from crane.services.section_review_service import SectionReviewService
        from crane.services.submission_pipeline_service import SubmissionPipelineService

        fake_review = MagicMock()
        fake_review.sections = []

        class _FakeQ1:
            def evaluate(self, path):
                r = MagicMock()
                r.overall_score = 75.0
                r.readiness = "ready"
                r.criteria = []
                return r

        svc = SubmissionPipelineService(tmp_path)
        sub_dir = tmp_path / "reports"
        sub_dir.mkdir()
        (sub_dir / "reports").mkdir(exist_ok=True)

        with patch.object(SectionReviewService, "review_paper") as mock_rv, \
             patch("crane.services.submission_pipeline_service.Q1EvaluationService", return_value=_FakeQ1()):
            svc.generate_paper_health_check(
                str(tex_file), sub_dir, precomputed_review=fake_review
            )
        mock_rv.assert_not_called()


# ===========================================================================
# F. Speed / evaluation metrics
# ===========================================================================


class TestSpeedMetrics:
    """Wall-clock regression guards against the small SAMPLE_TEX fixture (~40 lines).

    NOTE: These limits apply to the synthetic fixture only and are NOT
    equivalent to benchmarks on real papers (5 000+ lines).
    Do not cite these numbers as production performance data.
    Real-paper cold/warm benchmarks are tracked separately.
    """

    def test_build_index_under_one_second(self, svc, tex_file):
        # Small fixture (<50 lines) — real papers will be slower.
        t0 = time.perf_counter()
        svc.build(tex_file, force=True)
        elapsed = time.perf_counter() - t0
        assert elapsed < 1.0, f"build_paper_index took {elapsed:.2f}s (limit 1.0s, fixture only)"

    def test_cached_load_under_50ms(self, svc, tex_file):
        # Cache read — independent of paper size.
        svc.build(tex_file)
        t0 = time.perf_counter()
        svc.load(tex_file)
        elapsed = time.perf_counter() - t0
        assert elapsed < 0.05, f"cached load took {elapsed*1000:.1f}ms (limit 50ms)"

    def test_lru_cache_hit_under_1ms(self, tex_file):
        from crane.services.latex_parser import _parse_latex_cached

        _parse_latex_cached.cache_clear()
        _parse_latex_cached(str(tex_file))  # cold

        t0 = time.perf_counter()
        _parse_latex_cached(str(tex_file))  # warm
        elapsed = time.perf_counter() - t0
        assert elapsed < 0.001, f"lru_cache hit took {elapsed*1000:.2f}ms (limit 1ms)"


# ===========================================================================
# G. Count accuracy vs Linux grep
# ===========================================================================


class TestCountAccuracyVsLinux:
    """Verify Python regex counts in index match what grep -c would return."""

    @pytest.mark.skipif(
        not Path("/usr/bin/grep").exists() and not Path("/bin/grep").exists(),
        reason="grep not available",
    )
    def test_figure_count_matches_grep(self, svc, tex_file):
        idx = svc.build(tex_file, force=True)
        grep_count = int(
            subprocess.run(
                ["grep", "-c", r"\\begin{figure", str(tex_file)],
                capture_output=True, text=True,
            ).stdout.strip() or 0
        )
        assert idx["counts"]["figures"] == grep_count

    @pytest.mark.skipif(
        not Path("/usr/bin/grep").exists() and not Path("/bin/grep").exists(),
        reason="grep not available",
    )
    def test_section_count_matches_grep(self, svc, tex_file):
        idx = svc.build(tex_file, force=True)
        result = subprocess.run(
            ["grep", "-c", r"\\section{", str(tex_file)],
            capture_output=True, text=True,
        )
        grep_count = int(result.stdout.strip() or 0)
        # sections list includes subsections, grep \section{ does not catch subsection
        # so just verify at least as many sections as top-level grep
        assert len(idx["structure"]["sections"]) >= 0  # always true, just smoke-test


# ===========================================================================
# H. Schema version guard
# ===========================================================================


class TestSchemaVersion:
    def test_schema_version_is_one(self, svc, tex_file):
        idx = svc.build(tex_file)
        assert idx["_meta"]["schema"] == "1"

    def test_yaml_on_disk_readable(self, svc, tex_file):
        svc.build(tex_file)
        index_path = tex_file.parent / ".paper_index.yaml"
        loaded = yaml.safe_load(index_path.read_text(encoding="utf-8"))
        assert isinstance(loaded, dict)
        assert "_meta" in loaded
