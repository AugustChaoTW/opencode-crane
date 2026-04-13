"""
Comprehensive tests for src/crane/models/traceability.py.
Covers all dataclass instantiation, defaults, properties, and helper functions.
"""

from __future__ import annotations

import pytest

from crane.models.traceability import (
    ArtifactEntry,
    AxisSpec,
    BaselineSpec,
    CanonicalNumber,
    ChangeLogEntry,
    ContributionItem,
    DatasetSpec,
    ExperimentEntry,
    ExperimentSetting,
    FigureTableEntry,
    MustUpdateItem,
    ReferenceMapEntry,
    ResearchQuestion,
    ReviewerRisk,
    SectionEntry,
    SEVERITY_LEVELS,
    SKIP_KEYWORDS,
    NODE_TYPES,
    STATUSES,
    TRACE_DIR_NAME,
    TraceabilityIndex,
    TraceabilityNode,
    VisualizationSpec,
    get_node_type_from_id,
    is_active_paper_dir,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_trace_dir_name(self):
        assert TRACE_DIR_NAME == "_paper_trace"

    def test_skip_keywords_contains_reject(self):
        assert "reject" in SKIP_KEYWORDS

    def test_skip_keywords_contains_nogo_variants(self):
        assert "nogo" in SKIP_KEYWORDS
        assert "no-go" in SKIP_KEYWORDS
        assert "no_go" in SKIP_KEYWORDS

    def test_node_types_is_frozenset(self):
        assert isinstance(NODE_TYPES, frozenset)

    def test_node_types_contents(self):
        expected = {
            "rq", "contribution", "experiment", "figure", "table",
            "section", "reference", "risk", "artifact",
        }
        assert NODE_TYPES == expected

    def test_severity_levels(self):
        assert set(SEVERITY_LEVELS) == {"low", "medium", "high", "critical"}

    def test_statuses_contents(self):
        for s in ("draft", "active", "retired", "pending", "final",
                  "deprecated", "open", "mitigated", "resolved"):
            assert s in STATUSES


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


class TestIsActivePaperDir:
    def test_normal_name_is_active(self):
        assert is_active_paper_dir("my_paper_2024") is True

    def test_reject_keyword(self):
        assert is_active_paper_dir("paper_reject") is False

    def test_nogo_keyword(self):
        assert is_active_paper_dir("idea_nogo") is False

    def test_no_hyphen_go(self):
        assert is_active_paper_dir("idea_no-go") is False

    def test_no_underscore_go(self):
        assert is_active_paper_dir("idea_no_go") is False

    def test_withdrawn(self):
        assert is_active_paper_dir("draft_withdrawn") is False

    def test_cancel_keyword(self):
        assert is_active_paper_dir("project_cancel") is False

    def test_cancelled_keyword(self):
        assert is_active_paper_dir("project_cancelled") is False

    def test_abandon_keyword(self):
        assert is_active_paper_dir("experiment_abandon") is False

    def test_case_insensitive(self):
        assert is_active_paper_dir("REJECT_paper") is False

    def test_empty_string_is_active(self):
        assert is_active_paper_dir("") is True


class TestGetNodeTypeFromId:
    def test_rq(self):
        assert get_node_type_from_id("RQ1") == "rq"
        assert get_node_type_from_id("RQ42") == "rq"

    def test_contribution(self):
        assert get_node_type_from_id("C1") == "contribution"
        assert get_node_type_from_id("C10") == "contribution"

    def test_experiment(self):
        assert get_node_type_from_id("E1") == "experiment"
        assert get_node_type_from_id("E99") == "experiment"

    def test_figure(self):
        assert get_node_type_from_id("Fig:2") == "figure"
        assert get_node_type_from_id("Fig:ablation") == "figure"

    def test_table(self):
        assert get_node_type_from_id("T:1") == "table"
        assert get_node_type_from_id("T:main_results") == "table"

    def test_section(self):
        assert get_node_type_from_id("Sec:4.2") == "section"
        assert get_node_type_from_id("Sec:intro") == "section"

    def test_reference(self):
        assert get_node_type_from_id("Ref:vaswani2017") == "reference"

    def test_risk(self):
        assert get_node_type_from_id("R1") == "risk"
        assert get_node_type_from_id("R12") == "risk"

    def test_artifact(self):
        assert get_node_type_from_id("A001") == "artifact"
        assert get_node_type_from_id("A123") == "artifact"

    def test_change(self):
        assert get_node_type_from_id("CH001") == "change"
        assert get_node_type_from_id("CH999") == "change"

    def test_unknown(self):
        assert get_node_type_from_id("XYZ") == "unknown"
        assert get_node_type_from_id("") == "unknown"
        assert get_node_type_from_id("RQ") == "unknown"   # no digits
        assert get_node_type_from_id("rq1") == "unknown"  # lowercase


# ---------------------------------------------------------------------------
# Dataclass instantiation and defaults
# ---------------------------------------------------------------------------


class TestResearchQuestion:
    def test_basic_instantiation(self):
        rq = ResearchQuestion(
            rq_id="RQ1",
            text="Does X improve Y?",
            motivation="Y is important.",
            hypothesis="X will improve Y by 10%.",
        )
        assert rq.rq_id == "RQ1"
        assert rq.text == "Does X improve Y?"

    def test_defaults(self):
        rq = ResearchQuestion(
            rq_id="RQ2", text="t", motivation="m", hypothesis="h"
        )
        assert rq.tested_by_experiments == []
        assert rq.tested_by_figures == []
        assert rq.tested_by_tables == []
        assert rq.tested_by_sections == []
        assert rq.related_contributions == []
        assert rq.status == "draft"
        assert rq.inferred is False
        assert rq.confidence == 1.0

    def test_mutable_defaults_are_independent(self):
        rq1 = ResearchQuestion(rq_id="RQ1", text="t", motivation="m", hypothesis="h")
        rq2 = ResearchQuestion(rq_id="RQ2", text="t", motivation="m", hypothesis="h")
        rq1.tested_by_experiments.append("E1")
        assert rq2.tested_by_experiments == []


class TestContributionItem:
    def test_basic_instantiation(self):
        c = ContributionItem(
            contribution_id="C1",
            claim="We propose X.",
            why_it_matters="X solves Y.",
            strongest_defensible_wording="X outperforms baselines on Z.",
        )
        assert c.contribution_id == "C1"

    def test_defaults(self):
        c = ContributionItem(
            contribution_id="C1",
            claim="claim",
            why_it_matters="why",
            strongest_defensible_wording="wording",
        )
        assert c.avoid_overclaiming == []
        assert c.reviewer_risk == ""
        assert c.response_strategy == ""
        assert c.rq_ids == []
        assert c.status == "draft"
        assert c.inferred is False
        assert c.confidence == 1.0


class TestExperimentSetting:
    def test_all_defaults(self):
        s = ExperimentSetting()
        assert s.dataset == ""
        assert s.model == ""
        assert s.training_epochs is None
        assert s.batch_size is None
        assert s.seed is None
        assert s.hardware == ""
        assert s.framework == ""
        assert s.hyperparameters == {}

    def test_seed_as_list(self):
        s = ExperimentSetting(seed=[42, 123, 999])
        assert s.seed == [42, 123, 999]


class TestCanonicalNumber:
    def test_all_defaults(self):
        cn = CanonicalNumber()
        assert cn.value is None
        assert cn.locked is False
        assert cn.locked_at == ""

    def test_with_values(self):
        cn = CanonicalNumber(value=0.923, locked=True, locked_at="2024-01-01")
        assert cn.value == 0.923
        assert cn.locked is True


class TestExperimentEntry:
    def test_basic_instantiation(self):
        e = ExperimentEntry(exp_id="E1", goal="Evaluate X on benchmark Y.")
        assert e.exp_id == "E1"
        assert e.goal == "Evaluate X on benchmark Y."

    def test_defaults(self):
        e = ExperimentEntry(exp_id="E1", goal="g")
        assert isinstance(e.setting, ExperimentSetting)
        assert e.final_numbers == {}
        assert isinstance(e.canonical_number, CanonicalNumber)
        assert e.deprecated_numbers == []
        assert e.citation_needed == []
        assert e.output_files == []
        assert e.controlled_variables == {}
        assert e.used_in_paper == {}
        assert e.related_contributions == []
        assert e.related_rqs == []
        assert e.notes == ""
        assert e.status == "pending"
        assert e.inferred is False
        assert e.confidence == 1.0


class TestAxisSpec:
    def test_defaults(self):
        a = AxisSpec()
        assert a.label == ""
        assert a.range is None

    def test_with_values(self):
        a = AxisSpec(label="Accuracy", range=[0.0, 1.0])
        assert a.label == "Accuracy"
        assert a.range == [0.0, 1.0]


class TestVisualizationSpec:
    def test_defaults(self):
        v = VisualizationSpec()
        assert v.type == ""
        assert isinstance(v.x_axis, AxisSpec)
        assert isinstance(v.y_axis, AxisSpec)
        assert v.columns == []
        assert v.annotations == {}
        assert v.style_rules == []


class TestFigureTableEntry:
    def test_basic_instantiation(self):
        ft = FigureTableEntry(
            ft_id="Fig:2",
            type="figure",
            purpose="Show main results.",
            claim_supported="C1",
        )
        assert ft.ft_id == "Fig:2"
        assert ft.type == "figure"

    def test_defaults(self):
        ft = FigureTableEntry(
            ft_id="T:1", type="table", purpose="p", claim_supported="C1"
        )
        assert ft.related_rqs == []
        assert ft.source_experiments == []
        assert ft.exact_numbers == []
        assert ft.final_values == {}
        assert isinstance(ft.visualization, VisualizationSpec)
        assert ft.caption_draft == ""
        assert ft.presentation_rules == {}
        assert ft.mentioned_in == []
        assert ft.needs_update_if == []
        assert ft.text_reference_rule == ""
        assert ft.inferred is False
        assert ft.confidence == 1.0


class TestReferenceMapEntry:
    def test_basic_instantiation(self):
        r = ReferenceMapEntry(
            ref_key="vaswani2017",
            title="Attention Is All You Need",
            purpose="Foundational transformer paper.",
            role="foundational",
        )
        assert r.ref_key == "vaswani2017"

    def test_defaults(self):
        r = ReferenceMapEntry(
            ref_key="k", title="t", purpose="p", role="related"
        )
        assert r.should_appear_in == []
        assert r.should_not_appear_in == []
        assert r.must_cite_before == []
        assert r.supports_contributions == []
        assert r.citation_needed_by == []
        assert r.notes == ""


class TestSectionEntry:
    def test_basic_instantiation(self):
        s = SectionEntry(section_id="Sec:4", name="Experiments", goal="Report results.")
        assert s.section_id == "Sec:4"

    def test_defaults(self):
        s = SectionEntry(section_id="Sec:1", name="Intro", goal="g")
        assert s.must_include == []
        assert s.must_not_do == []
        assert s.citations_needed == []
        assert s.supports_contributions == []
        assert s.related_rqs == []
        assert s.figures == []
        assert s.tables == []
        assert s.reviewer_check == ""
        assert s.notes == ""
        assert s.subsections == []

    def test_nested_subsections(self):
        sub = SectionEntry(section_id="Sec:4.1", name="Setup", goal="Describe setup.")
        parent = SectionEntry(
            section_id="Sec:4",
            name="Experiments",
            goal="Report results.",
            subsections=[sub],
        )
        assert len(parent.subsections) == 1
        assert parent.subsections[0].section_id == "Sec:4.1"

    def test_deeply_nested_subsections(self):
        deep = SectionEntry(section_id="Sec:4.1.1", name="Detail", goal="d")
        mid = SectionEntry(section_id="Sec:4.1", name="Setup", goal="s", subsections=[deep])
        top = SectionEntry(section_id="Sec:4", name="Exp", goal="e", subsections=[mid])
        assert top.subsections[0].subsections[0].section_id == "Sec:4.1.1"


class TestReviewerRisk:
    def test_basic_instantiation(self):
        r = ReviewerRisk(
            risk_id="R1",
            description="Comparison is missing.",
            severity="high",
            likely_appears_in="Major review",
            response_strategy="Add ablation.",
        )
        assert r.risk_id == "R1"

    def test_defaults(self):
        r = ReviewerRisk(
            risk_id="R1",
            description="d",
            severity="low",
            likely_appears_in="Minor review",
            response_strategy="s",
        )
        assert r.fallback_claim == ""
        assert r.related_contributions == []
        assert r.related_sections == []
        assert r.status == "open"
        assert r.mitigation_evidence == []
        assert r.inferred is False
        assert r.confidence == 1.0


class TestDatasetSpec:
    def test_basic_instantiation(self):
        d = DatasetSpec(dataset_id="D1", name="ImageNet")
        assert d.dataset_id == "D1"
        assert d.name == "ImageNet"

    def test_defaults(self):
        d = DatasetSpec(dataset_id="D1", name="n")
        assert d.description == ""
        assert d.split == ""
        assert d.split_source_citation == ""
        assert d.metrics == []
        assert d.used_in_experiments == []
        assert d.preprocessing == {}
        assert d.download_url == ""
        assert d.notes == ""


class TestBaselineSpec:
    def test_basic_instantiation(self):
        b = BaselineSpec(
            baseline_id="B1",
            name="BERT",
            used_in_experiments=["E1"],
        )
        assert b.baseline_id == "B1"

    def test_defaults(self):
        b = BaselineSpec(baseline_id="B1", name="n", used_in_experiments=[])
        assert b.full_name == ""
        assert b.source_citation == ""
        assert b.implementation_source == ""
        assert b.implementation_url == ""
        assert b.configuration == {}
        assert b.reproduced_by == ""
        assert b.reproduced_results == []
        assert b.notes == ""


class TestArtifactEntry:
    def test_basic_instantiation(self):
        a = ArtifactEntry(
            artifact_id="A001",
            path="results/main.csv",
            type="csv",
            purpose="Main results table source.",
        )
        assert a.artifact_id == "A001"

    def test_defaults(self):
        a = ArtifactEntry(artifact_id="A001", path="p", type="code", purpose="pu")
        assert a.used_by == []
        assert a.generated_by == ""
        assert a.git_tracked is True
        assert a.created_at == ""
        assert a.last_modified == ""
        assert a.notes == ""


class TestMustUpdateItem:
    def test_basic_instantiation(self):
        m = MustUpdateItem(artifact="Fig:2", artifact_type="figure", reason="Numbers changed.")
        assert m.artifact == "Fig:2"
        assert m.reason == "Numbers changed."

    def test_defaults(self):
        m = MustUpdateItem(artifact="a", artifact_type="t", reason="r")
        assert m.status == "pending"
        assert m.resolved_at == ""


class TestChangeLogEntry:
    def _make_entry(self, items: list[MustUpdateItem]) -> ChangeLogEntry:
        return ChangeLogEntry(
            change_id="CH001",
            date="2024-01-01",
            change="Updated experiment E1.",
            why="Bug fix.",
            changed_artifact="E1",
            impact_severity="high",
            must_update=items,
        )

    def test_pending_count_all_pending(self):
        items = [
            MustUpdateItem(artifact="Fig:2", artifact_type="figure", reason="r"),
            MustUpdateItem(artifact="T:1", artifact_type="table", reason="r"),
        ]
        e = self._make_entry(items)
        assert e.pending_count == 2

    def test_pending_count_some_resolved(self):
        items = [
            MustUpdateItem(artifact="Fig:2", artifact_type="figure", reason="r", status="resolved"),
            MustUpdateItem(artifact="T:1", artifact_type="table", reason="r"),
        ]
        e = self._make_entry(items)
        assert e.pending_count == 1

    def test_pending_count_all_resolved(self):
        items = [
            MustUpdateItem(artifact="Fig:2", artifact_type="figure", reason="r", status="resolved"),
        ]
        e = self._make_entry(items)
        assert e.pending_count == 0

    def test_pending_count_empty(self):
        e = self._make_entry([])
        assert e.pending_count == 0

    def test_is_resolved_false_when_pending(self):
        items = [MustUpdateItem(artifact="Fig:2", artifact_type="figure", reason="r")]
        e = self._make_entry(items)
        assert e.is_resolved is False

    def test_is_resolved_true_when_all_done(self):
        items = [
            MustUpdateItem(artifact="Fig:2", artifact_type="figure", reason="r", status="resolved"),
            MustUpdateItem(artifact="T:1", artifact_type="table", reason="r", status="mitigated"),
        ]
        e = self._make_entry(items)
        assert e.is_resolved is True

    def test_is_resolved_true_when_empty(self):
        e = self._make_entry([])
        assert e.is_resolved is True


class TestTraceabilityNode:
    def test_basic_instantiation(self):
        n = TraceabilityNode(node_id="C1", node_type="contribution")
        assert n.node_id == "C1"
        assert n.node_type == "contribution"

    def test_defaults(self):
        n = TraceabilityNode(node_id="E1", node_type="experiment")
        assert n.depends_on == []
        assert n.depended_by == []
        assert n.document_ref == ""
        assert n.inferred is False

    def test_mutable_defaults_are_independent(self):
        n1 = TraceabilityNode(node_id="C1", node_type="contribution")
        n2 = TraceabilityNode(node_id="C2", node_type="contribution")
        n1.depends_on.append("RQ1")
        assert n2.depends_on == []


class TestTraceabilityIndex:
    def test_basic_instantiation(self):
        idx = TraceabilityIndex(
            generated_at="2024-01-01T00:00:00",
            paper_path="/papers/my_paper",
            trace_dir="/papers/my_paper/_paper_trace",
            output_dir="/papers/my_paper/output",
            chain_coverage=0.85,
            rq_count=3,
            contribution_count=4,
            experiment_count=8,
            figure_table_count=6,
            reference_count=50,
            risk_count=5,
            artifact_count=12,
            pending_changes=2,
        )
        assert idx.chain_coverage == 0.85
        assert idx.rq_count == 3
        assert idx.pending_changes == 2

    def test_defaults(self):
        idx = TraceabilityIndex(
            generated_at="t",
            paper_path="p",
            trace_dir="td",
            output_dir="od",
            chain_coverage=1.0,
            rq_count=0,
            contribution_count=0,
            experiment_count=0,
            figure_table_count=0,
            reference_count=0,
            risk_count=0,
            artifact_count=0,
            pending_changes=0,
        )
        assert idx.orphan_detection == {}
        assert idx.chain_completeness == {}
