# pyright: reportMissingImports=false

from __future__ import annotations

import pytest

from crane.models.paper_profile import (
    DimensionScore,
    EvidenceItem,
    EvidenceLedger,
    EvidencePattern,
    EvidenceSignal,
    JournalFit,
    NoveltyShape,
    PaperProfile,
    PaperType,
    RevisionEffort,
    RevisionItem,
    RevisionPlan,
    RevisionPriority,
)


def test_paper_type_enum_values() -> None:
    assert PaperType.EMPIRICAL.value == "empirical"
    assert PaperType.SYSTEM.value == "system"
    assert PaperType.THEORETICAL.value == "theoretical"
    assert PaperType.SURVEY.value == "survey"
    assert PaperType.UNKNOWN.value == "unknown"


def test_evidence_signal_enum_values() -> None:
    assert EvidenceSignal.OBSERVED.value == "observed"
    assert EvidenceSignal.INFERRED.value == "inferred"
    assert EvidenceSignal.MISSING.value == "missing"


def test_evidence_pattern_enum_values() -> None:
    assert EvidencePattern.BENCHMARK_HEAVY.value == "benchmark_heavy"
    assert EvidencePattern.APPLICATION_HEAVY.value == "application_heavy"
    assert EvidencePattern.THEOREM_HEAVY.value == "theorem_heavy"
    assert EvidencePattern.MIXED.value == "mixed"
    assert EvidencePattern.UNKNOWN.value == "unknown"


def test_novelty_shape_enum_values() -> None:
    assert NoveltyShape.NEW_METHOD.value == "new_method"
    assert NoveltyShape.NEW_APPLICATION.value == "new_application"
    assert NoveltyShape.NEW_ANALYSIS.value == "new_analysis"
    assert NoveltyShape.INCREMENTAL.value == "incremental"
    assert NoveltyShape.UNKNOWN.value == "unknown"


def test_revision_priority_enum_values() -> None:
    assert RevisionPriority.IMMEDIATE.value == "immediate"
    assert RevisionPriority.MEDIUM_TERM.value == "medium_term"
    assert RevisionPriority.LONG_TERM.value == "long_term"


def test_revision_effort_enum_values() -> None:
    assert RevisionEffort.LOW.value == "low"
    assert RevisionEffort.MEDIUM.value == "medium"
    assert RevisionEffort.HIGH.value == "high"


def test_evidence_item_valid_defaults() -> None:
    item = EvidenceItem(claim="c", section="intro", span="s")
    assert item.signal == EvidenceSignal.OBSERVED
    assert item.confidence == 1.0


def test_evidence_item_empty_claim_raises() -> None:
    with pytest.raises(ValueError, match="claim cannot be empty"):
        EvidenceItem(claim="", section="intro", span="s")


@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_evidence_item_invalid_confidence_raises(value: float) -> None:
    with pytest.raises(ValueError, match="confidence"):
        EvidenceItem(claim="c", section="intro", span="s", confidence=value)


def test_evidence_ledger_by_section() -> None:
    ledger = EvidenceLedger(
        items=[
            EvidenceItem(claim="a", section="intro", span="x"),
            EvidenceItem(claim="b", section="method", span="y"),
            EvidenceItem(claim="c", section="intro", span="z"),
        ]
    )
    assert [item.claim for item in ledger.by_section("intro")] == ["a", "c"]


def test_evidence_ledger_by_signal() -> None:
    ledger = EvidenceLedger(
        items=[
            EvidenceItem(claim="a", section="intro", span="x", signal=EvidenceSignal.OBSERVED),
            EvidenceItem(claim="b", section="method", span="y", signal=EvidenceSignal.MISSING),
            EvidenceItem(claim="c", section="result", span="z", signal=EvidenceSignal.INFERRED),
        ]
    )
    assert [item.claim for item in ledger.by_signal(EvidenceSignal.MISSING)] == ["b"]


def test_evidence_ledger_counts() -> None:
    ledger = EvidenceLedger(
        items=[
            EvidenceItem(claim="a", section="intro", span="x"),
            EvidenceItem(claim="b", section="method", span="y", signal=EvidenceSignal.MISSING),
            EvidenceItem(claim="c", section="result", span="z"),
        ]
    )
    assert ledger.observed_count == 2
    assert ledger.missing_count == 1


def test_evidence_ledger_empty_filters() -> None:
    ledger = EvidenceLedger(items=[])
    assert ledger.by_section("intro") == []
    assert ledger.by_signal(EvidenceSignal.OBSERVED) == []
    assert ledger.observed_count == 0
    assert ledger.missing_count == 0


def test_paper_profile_defaults() -> None:
    profile = PaperProfile()
    assert profile.paper_type == PaperType.UNKNOWN
    assert profile.keywords == []
    assert profile.num_figures == 0
    assert profile.reproducibility_maturity == 0.0


@pytest.mark.parametrize("value", [-0.001, 1.001])
def test_paper_profile_invalid_reproducibility_raises(value: float) -> None:
    with pytest.raises(ValueError, match="reproducibility_maturity"):
        PaperProfile(reproducibility_maturity=value)


def test_dimension_score_valid() -> None:
    score = DimensionScore(dimension="methodology", score=80.5, confidence=0.7)
    assert score.dimension == "methodology"
    assert score.reason_codes == []


def test_dimension_score_empty_dimension_raises() -> None:
    with pytest.raises(ValueError, match="dimension"):
        DimensionScore(dimension="", score=60.0, confidence=0.5)


@pytest.mark.parametrize("value", [-1.0, 100.1])
def test_dimension_score_out_of_range_raises(value: float) -> None:
    with pytest.raises(ValueError, match="score"):
        DimensionScore(dimension="d", score=value, confidence=0.5)


@pytest.mark.parametrize("value", [-0.2, 1.2])
def test_dimension_confidence_out_of_range_raises(value: float) -> None:
    with pytest.raises(ValueError, match="confidence"):
        DimensionScore(dimension="d", score=50.0, confidence=value)


def test_journal_fit_requires_name() -> None:
    with pytest.raises(ValueError, match="journal_name"):
        JournalFit(journal_name="")


def test_journal_fit_calculate_overall() -> None:
    fit = JournalFit(
        journal_name="NeurIPS",
        scope_fit=0.8,
        contribution_style_fit=0.7,
        evaluation_style_fit=0.9,
        citation_neighborhood_fit=0.6,
        operational_fit=0.5,
    )
    overall = fit.calculate_overall()
    expected = 0.35 * 0.8 + 0.20 * 0.7 + 0.20 * 0.9 + 0.15 * 0.6 + 0.10 * 0.5
    assert overall == pytest.approx(expected)
    assert fit.overall_fit == pytest.approx(expected)


def test_revision_item_defaults() -> None:
    item = RevisionItem(
        dimension="methodology",
        suggestion="Add ablation",
        priority=RevisionPriority.IMMEDIATE,
        effort=RevisionEffort.MEDIUM,
    )
    assert item.expected_impact == 0.0
    assert item.depends_on == []
    assert item.status == "pending"


def test_revision_plan_by_priority() -> None:
    plan = RevisionPlan(
        items=[
            RevisionItem("m", "a", RevisionPriority.IMMEDIATE, RevisionEffort.LOW),
            RevisionItem("n", "b", RevisionPriority.LONG_TERM, RevisionEffort.HIGH),
        ]
    )
    assert len(plan.by_priority(RevisionPriority.IMMEDIATE)) == 1
    assert len(plan.by_priority(RevisionPriority.MEDIUM_TERM)) == 0


def test_revision_plan_immediate_items_property() -> None:
    plan = RevisionPlan(
        items=[
            RevisionItem("m", "a", RevisionPriority.IMMEDIATE, RevisionEffort.LOW),
            RevisionItem("e", "b", RevisionPriority.MEDIUM_TERM, RevisionEffort.MEDIUM),
        ]
    )
    assert [item.dimension for item in plan.immediate_items] == ["m"]


def test_revision_plan_pending_items_property() -> None:
    plan = RevisionPlan(
        items=[
            RevisionItem(
                "m", "a", RevisionPriority.IMMEDIATE, RevisionEffort.LOW, status="pending"
            ),
            RevisionItem(
                "e", "b", RevisionPriority.MEDIUM_TERM, RevisionEffort.MEDIUM, status="completed"
            ),
            RevisionItem(
                "n", "c", RevisionPriority.LONG_TERM, RevisionEffort.HIGH, status="pending"
            ),
        ]
    )
    assert [item.dimension for item in plan.pending_items] == ["m", "n"]


def test_revision_plan_sort_by_impact_descending() -> None:
    plan = RevisionPlan(
        items=[
            RevisionItem(
                "a", "s1", RevisionPriority.IMMEDIATE, RevisionEffort.LOW, expected_impact=1.0
            ),
            RevisionItem(
                "b", "s2", RevisionPriority.IMMEDIATE, RevisionEffort.LOW, expected_impact=5.0
            ),
            RevisionItem(
                "c", "s3", RevisionPriority.IMMEDIATE, RevisionEffort.LOW, expected_impact=3.0
            ),
        ]
    )
    plan.sort_by_impact()
    assert [item.dimension for item in plan.items] == ["b", "c", "a"]


def test_revision_plan_sort_empty_safe() -> None:
    plan = RevisionPlan(items=[])
    plan.sort_by_impact()
    assert plan.items == []
