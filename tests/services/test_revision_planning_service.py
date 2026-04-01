# pyright: reportMissingImports=false

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Any

from crane.models.paper_profile import (
    DimensionScore,
    RevisionEffort,
    RevisionPlan,
    RevisionPriority,
)


def _load_service_class():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "crane"
        / "services"
        / "revision_planning_service.py"
    )
    module_name = "crane.services.revision_planning_service"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load revision_planning_service module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module.RevisionPlanningService


RevisionPlanningService = _load_service_class()


def _dim(
    dimension: str,
    score: float,
    confidence: float = 0.8,
    suggestions: list[str] | None = None,
    reason_codes: list[str] | None = None,
    evidence_spans: list[str] | None = None,
    missing_evidence: list[str] | None = None,
) -> DimensionScore:
    return DimensionScore(
        dimension=dimension,
        score=score,
        confidence=confidence,
        suggestions=suggestions or [],
        reason_codes=reason_codes or [],
        evidence_spans=evidence_spans or [],
        missing_evidence=missing_evidence or [],
    )


def _service() -> Any:
    return RevisionPlanningService()


def test_generate_plan_uses_dimension_count_and_current_score() -> None:
    svc = _service()
    dims = [_dim("methodology", 55), _dim("presentation", 82)]

    plan = svc.generate_plan(dims, current_overall=67.5)

    assert len(plan.items) == 2
    assert plan.current_score == 67.5


def test_generate_plan_prefers_first_suggestion() -> None:
    svc = _service()
    dims = [_dim("novelty", 50, suggestions=["Add stronger novelty claim", "Unused"])]

    plan = svc.generate_plan(dims, current_overall=50)

    assert plan.items[0].suggestion == "Add stronger novelty claim"


def test_generate_plan_fallback_suggestion_when_missing() -> None:
    svc = _service()
    dims = [_dim("evaluation", 40)]

    plan = svc.generate_plan(dims, current_overall=40)

    assert "Improve evaluation" in plan.items[0].suggestion


def test_generate_plan_empty_scores() -> None:
    svc = _service()
    plan = svc.generate_plan([], current_overall=72)
    assert plan.items == []
    assert plan.projected_score == 72


def test_generate_plan_all_high_scores() -> None:
    svc = _service()
    dims = [_dim("methodology", 90), _dim("novelty", 88), _dim("evaluation", 84)]
    plan = svc.generate_plan(dims, current_overall=87)
    assert all(item.priority == RevisionPriority.LONG_TERM for item in plan.items)


def test_generate_plan_all_low_scores_gate_dimensions_immediate() -> None:
    svc = _service()
    dims = [_dim("methodology", 20), _dim("novelty", 30), _dim("evaluation", 59)]
    plan = svc.generate_plan(dims, current_overall=36)
    assert all(item.priority == RevisionPriority.IMMEDIATE for item in plan.items)


def test_generate_plan_single_dimension() -> None:
    svc = _service()
    plan = svc.generate_plan([_dim("presentation", 70)], current_overall=70)
    assert len(plan.items) == 1
    assert plan.items[0].priority == RevisionPriority.MEDIUM_TERM


def test_generate_plan_populates_pending_status() -> None:
    svc = _service()
    plan = svc.generate_plan([_dim("methodology", 40)], current_overall=40)
    assert plan.items[0].status == "pending"


def test_generate_plan_sets_projected_score_using_immediate_items() -> None:
    svc = _service()
    dims = [_dim("methodology", 50), _dim("presentation", 50)]
    plan = svc.generate_plan(dims, current_overall=40)
    assert plan.projected_score == 55


def test_generate_plan_impact_capped_to_20() -> None:
    svc = _service()
    plan = svc.generate_plan([_dim("methodology", 0)], current_overall=20)
    assert plan.items[0].expected_impact == 20


import pytest


@pytest.mark.parametrize(
    ("dimension", "score", "expected"),
    [
        ("methodology", 59, RevisionPriority.IMMEDIATE),
        ("novelty", 10, RevisionPriority.IMMEDIATE),
        ("evaluation", 0, RevisionPriority.IMMEDIATE),
        ("methodology", 60, RevisionPriority.MEDIUM_TERM),
        ("novelty", 79, RevisionPriority.MEDIUM_TERM),
        ("evaluation", 80, RevisionPriority.LONG_TERM),
        ("presentation", 59, RevisionPriority.MEDIUM_TERM),
        ("writing", 60, RevisionPriority.MEDIUM_TERM),
        ("reproducibility", 79, RevisionPriority.MEDIUM_TERM),
        ("limitations", 81, RevisionPriority.LONG_TERM),
    ],
)
def test_generate_plan_priority_rules(
    dimension: str, score: float, expected: RevisionPriority
) -> None:
    svc = _service()
    plan = svc.generate_plan([_dim(dimension, score)], current_overall=70)
    assert plan.items[0].priority == expected


@pytest.mark.parametrize(
    ("score", "expected_effort"),
    [
        (0, RevisionEffort.HIGH),
        (29.9, RevisionEffort.HIGH),
        (30, RevisionEffort.MEDIUM),
        (59.9, RevisionEffort.MEDIUM),
        (60, RevisionEffort.LOW),
        (79.9, RevisionEffort.LOW),
        (95, RevisionEffort.LOW),
    ],
)
def test_generate_plan_effort_rules(score: float, expected_effort: RevisionEffort) -> None:
    svc = _service()
    plan = svc.generate_plan([_dim("presentation", score)], current_overall=70)
    assert plan.items[0].effort == expected_effort


@pytest.mark.parametrize(
    ("score", "expected_impact"),
    [
        (0, 20),
        (30, 20),
        (60, 10),
        (79, 0.5),
        (80, 0),
        (95, 0),
    ],
)
def test_generate_plan_impact_formula(score: float, expected_impact: float) -> None:
    svc = _service()
    plan = svc.generate_plan([_dim("evaluation", score)], current_overall=70)
    assert plan.items[0].expected_impact == expected_impact


def test_sort_by_roi_orders_descending() -> None:
    svc = _service()
    plan = RevisionPlan(
        items=[
            svc.generate_plan([_dim("methodology", 50)], 60).items[0],
            svc.generate_plan([_dim("presentation", 70)], 60).items[0],
            svc.generate_plan([_dim("novelty", 20)], 60).items[0],
        ],
        current_score=60,
        projected_score=60,
    )

    sorted_plan = svc.sort_by_roi(plan)

    rois = []
    effort_weight = {RevisionEffort.LOW: 1, RevisionEffort.MEDIUM: 2, RevisionEffort.HIGH: 4}
    for item in sorted_plan.items:
        rois.append(item.expected_impact / effort_weight[item.effort])
    assert rois == sorted(rois, reverse=True)


def test_sort_by_roi_returns_same_instance() -> None:
    svc = _service()
    plan = svc.generate_plan([_dim("methodology", 40), _dim("presentation", 70)], 60)
    assert svc.sort_by_roi(plan) is plan


def test_group_by_timeline_correct_grouping() -> None:
    svc = _service()
    plan = svc.generate_plan(
        [_dim("methodology", 40), _dim("presentation", 70), _dim("writing", 90)],
        55,
    )
    grouped = svc.group_by_timeline(plan)
    assert [item.dimension for item in grouped["immediate"]] == ["methodology"]
    assert [item.dimension for item in grouped["medium_term"]] == ["presentation"]
    assert [item.dimension for item in grouped["long_term"]] == ["writing"]


def test_group_by_timeline_empty_plan() -> None:
    svc = _service()
    grouped = svc.group_by_timeline(RevisionPlan())
    assert grouped == {"immediate": [], "medium_term": [], "long_term": []}


def test_estimate_projected_score_adds_only_immediate_impact() -> None:
    svc = _service()
    plan = svc.generate_plan(
        [_dim("methodology", 40), _dim("presentation", 40), _dim("novelty", 50)],
        50,
    )
    assert svc.estimate_projected_score(plan) == 85


def test_estimate_projected_score_caps_at_100() -> None:
    svc = _service()
    plan = svc.generate_plan([_dim("methodology", 0), _dim("novelty", 0)], 90)
    assert svc.estimate_projected_score(plan) == 100


def test_check_dependencies_detects_expected_pairs() -> None:
    svc = _service()
    plan = svc.generate_plan(
        [_dim("methodology", 50), _dim("evaluation", 50), _dim("reproducibility", 50)],
        50,
    )
    deps = svc.check_dependencies(plan)
    assert ("methodology", "evaluation") in deps
    assert ("methodology", "reproducibility") in deps


def test_check_dependencies_detects_novelty_evaluation() -> None:
    svc = _service()
    plan = svc.generate_plan([_dim("novelty", 50), _dim("evaluation", 50)], 50)
    deps = svc.check_dependencies(plan)
    assert deps == [("novelty", "evaluation")]


def test_check_dependencies_no_pairs_when_dimensions_missing() -> None:
    svc = _service()
    plan = svc.generate_plan([_dim("writing", 40), _dim("presentation", 50)], 45)
    deps = svc.check_dependencies(plan)
    assert deps == []


def test_check_dependencies_is_case_insensitive() -> None:
    svc = _service()
    plan = svc.generate_plan([_dim("Methodology", 50), _dim("Evaluation", 50)], 50)
    deps = svc.check_dependencies(plan)
    assert ("methodology", "evaluation") in deps


def test_create_snapshot_contains_scores_confidence_and_overall() -> None:
    svc = _service()
    snapshot = svc.create_snapshot([_dim("methodology", 70, 0.7), _dim("novelty", 90, 0.9)])
    assert snapshot["scores"]["methodology"] == 70
    assert snapshot["confidence"]["novelty"] == 0.9
    assert snapshot["overall"] == 80
    assert snapshot["count"] == 2


def test_create_snapshot_empty_scores() -> None:
    svc = _service()
    snapshot = svc.create_snapshot([])
    assert snapshot == {"overall": 0.0, "scores": {}, "confidence": {}, "count": 0}


def test_compare_snapshots_computes_overall_and_dimension_deltas() -> None:
    svc = _service()
    before = {"overall": 60.0, "scores": {"methodology": 50, "novelty": 70}}
    after = {"overall": 75.0, "scores": {"methodology": 80, "novelty": 65}}
    compared = svc.compare_snapshots(before, after)

    assert compared["overall"]["delta"] == 15
    assert compared["dimensions"]["methodology"]["delta"] == 30
    assert compared["dimensions"]["novelty"]["delta"] == -5
    assert compared["summary"] == {"improved": 1, "regressed": 1, "unchanged": 0}


def test_compare_snapshots_handles_added_and_removed_dimensions() -> None:
    svc = _service()
    before = {"overall": 40.0, "scores": {"methodology": 40, "writing": 80}}
    after = {"overall": 45.0, "scores": {"methodology": 45, "evaluation": 60}}
    compared = svc.compare_snapshots(before, after)

    assert compared["dimensions"]["writing"]["after"] == 0
    assert compared["dimensions"]["evaluation"]["before"] == 0
    assert compared["summary"]["improved"] == 2


def test_compare_snapshots_with_missing_keys_defaults_to_zero() -> None:
    svc = _service()
    compared = svc.compare_snapshots({}, {})
    assert compared["overall"] == {"before": 0.0, "after": 0.0, "delta": 0.0}
    assert compared["dimensions"] == {}


def test_generate_scorecard_contains_header_and_table() -> None:
    svc = _service()
    markdown = svc.generate_scorecard(
        [_dim("methodology", 72, 0.8)], gates_passed=True, readiness="ready"
    )
    assert "# Q1 Readiness Scorecard" in markdown
    assert "| Dimension | Score | Confidence | Status |" in markdown
    assert "| methodology | 72 | 0.8 | ⚠️ |" in markdown


def test_generate_scorecard_emoji_statuses() -> None:
    svc = _service()
    markdown = svc.generate_scorecard(
        [_dim("high", 80), _dim("mid", 60), _dim("low", 59)],
        gates_passed=False,
        readiness="needs work",
    )
    assert "| high | 80 | 0.8 | ✅ |" in markdown
    assert "| mid | 60 | 0.8 | ⚠️ |" in markdown
    assert "| low | 59 | 0.8 | ❌ |" in markdown


def test_generate_scorecard_gates_pass_and_fail_labels() -> None:
    svc = _service()
    pass_markdown = svc.generate_scorecard([_dim("methodology", 80)], True, "ready")
    fail_markdown = svc.generate_scorecard([_dim("methodology", 80)], False, "ready")
    assert "**Gates**: pass" in pass_markdown
    assert "**Gates**: fail" in fail_markdown


def test_generate_scorecard_top_blockers_uses_reason_code() -> None:
    svc = _service()
    markdown = svc.generate_scorecard(
        [_dim("evaluation", 40, reason_codes=["missing-baselines"])],
        gates_passed=False,
        readiness="not ready",
    )
    assert "1. evaluation (40) — missing-baselines" in markdown


def test_generate_scorecard_top_blockers_none_when_no_blockers() -> None:
    svc = _service()
    markdown = svc.generate_scorecard(
        [_dim("methodology", 80)], gates_passed=True, readiness="ready"
    )
    assert "## Top Blockers" in markdown
    assert "1. None" in markdown


def test_generate_scorecard_empty_scores() -> None:
    svc = _service()
    markdown = svc.generate_scorecard([], gates_passed=True, readiness="ready")
    assert "**Overall**: 0.0/100" in markdown
    assert "1. None" in markdown


def test_generate_evidence_view_contains_dimension_sections_and_lists() -> None:
    svc = _service()
    markdown = svc.generate_evidence_view(
        [
            _dim(
                "methodology",
                70,
                evidence_spans=["Method section with equations"],
                missing_evidence=["Ablation details"],
                reason_codes=["partial-method-rigor"],
            )
        ]
    )
    assert "# Evidence View" in markdown
    assert "## methodology" in markdown
    assert "- Score: 70" in markdown
    assert "  - Method section with equations" in markdown
    assert "  - Ablation details" in markdown
    assert "  - partial-method-rigor" in markdown


def test_generate_evidence_view_includes_none_for_empty_lists() -> None:
    svc = _service()
    markdown = svc.generate_evidence_view([_dim("novelty", 60)])
    assert markdown.count("  - None") == 3


def test_generate_evidence_view_empty_input() -> None:
    svc = _service()
    markdown = svc.generate_evidence_view([])
    assert "No dimensions to evaluate." in markdown


def test_generate_revision_backlog_contains_checkbox_format() -> None:
    svc = _service()
    plan = svc.generate_plan(
        [_dim("methodology", 50, suggestions=["Strengthen method"]), _dim("writing", 85)],
        current_overall=70,
    )
    markdown = svc.generate_revision_backlog(plan)

    assert "# Revision Backlog" in markdown
    assert "## Immediate (Must Fix)" in markdown
    assert "- [ ] Strengthen method | Dimension: methodology" in markdown


def test_generate_revision_backlog_includes_medium_and_long_sections() -> None:
    svc = _service()
    plan = svc.generate_plan([_dim("presentation", 70), _dim("writing", 85)], current_overall=74)
    markdown = svc.generate_revision_backlog(plan)
    assert "## Medium Term" in markdown
    assert "## Long Term (Polish)" in markdown


def test_generate_revision_backlog_displays_none_for_empty_sections() -> None:
    svc = _service()
    plan = RevisionPlan(items=[], current_score=50, projected_score=50)
    markdown = svc.generate_revision_backlog(plan)
    assert markdown.count("- [ ] None") == 3


def test_generate_revision_backlog_projected_score_uses_immediate_only() -> None:
    svc = _service()
    plan = svc.generate_plan([_dim("methodology", 40), _dim("writing", 40)], current_overall=60)
    markdown = svc.generate_revision_backlog(plan)
    assert "**Current Score**: 60 → **Projected**: 80" in markdown


def test_generate_full_report_combines_three_layers() -> None:
    svc = _service()
    dims = [_dim("methodology", 50), _dim("evaluation", 55), _dim("writing", 88)]
    plan = svc.generate_plan(dims, current_overall=64)
    report = svc.generate_full_report(dims, gates_passed=False, readiness="not ready", plan=plan)

    assert "# Q1 Readiness Scorecard" in report
    assert "# Evidence View" in report
    assert "# Revision Backlog" in report
    assert report.count("\n---\n") == 2


def test_generate_full_report_works_for_empty_dimensions_and_plan() -> None:
    svc = _service()
    plan = RevisionPlan(items=[], current_score=0, projected_score=0)
    report = svc.generate_full_report([], gates_passed=True, readiness="ready", plan=plan)
    assert "No dimensions to evaluate." in report
    assert "- [ ] None" in report
