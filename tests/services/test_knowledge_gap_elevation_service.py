# pyright: reportMissingImports=false
"""Tests for KnowledgeGapElevationService."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from crane.services.knowledge_gap_elevation_service import (
    GapLevel,
    KnowledgeGap,
    KnowledgeGapElevationService,
    LEVEL_TO_POTENTIAL,
)
from crane.services.paper_knowledge_graph_service import (
    KGEdge,
    KGNode,
    PaperKnowledgeGraph,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def svc() -> KnowledgeGapElevationService:
    return KnowledgeGapElevationService()


@pytest.fixture
def simple_kg() -> PaperKnowledgeGraph:
    """KG with three nodes, two connected, one isolated."""
    kg = PaperKnowledgeGraph(paper_path="fake.tex", file_hash="abc")
    kg.nodes["Transformer"] = KGNode("Transformer", "Introduction", 3, "method")
    kg.nodes["FederatedLearning"] = KGNode("FederatedLearning", "Methods", 4, "method")
    kg.nodes["Accuracy"] = KGNode("Accuracy", "Results", 2, "metric")
    # Transformer → Accuracy edge; FederatedLearning has no edge
    kg.edges.append(KGEdge("Transformer", "Accuracy", "uses", "accuracy measured", 0.9))
    return kg


@pytest.fixture
def paper_file(tmp_path: Path) -> Path:
    """Create a minimal .tex paper file."""
    p = tmp_path / "paper.tex"
    p.write_text(r"\section{Intro} placeholder content.", encoding="utf-8")
    return p


@pytest.fixture
def paper_with_trace(tmp_path: Path) -> Path:
    """Paper with _paper_trace/v2/6_research_question.yaml."""
    paper = tmp_path / "paper.tex"
    paper.write_text(r"\section{Intro} placeholder.", encoding="utf-8")

    trace_dir = tmp_path / "_paper_trace" / "v2"
    trace_dir.mkdir(parents=True)
    trace_file = trace_dir / "6_research_question.yaml"
    trace_file.write_text(
        yaml.dump(
            {
                "research_question": {
                    "text": "How does attention mechanism improve NLP performance?"
                }
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return paper


# ---------------------------------------------------------------------------
# GapLevel classification
# ---------------------------------------------------------------------------


class TestEvaluateLevel:
    def test_field_level_when_types_differ(
        self, svc: KnowledgeGapElevationService, simple_kg: PaperKnowledgeGraph
    ) -> None:
        """Cross-type gap (method vs metric) → FIELD."""
        level = svc._evaluate_level("Transformer", "Accuracy", simple_kg)
        assert level == GapLevel.FIELD

    def test_field_level_when_high_frequency(
        self, svc: KnowledgeGapElevationService
    ) -> None:
        """Same type but one node has frequency >= 3 → FIELD."""
        kg = PaperKnowledgeGraph("p.tex")
        kg.nodes["ModelA"] = KGNode("ModelA", "Intro", 5, "method")
        kg.nodes["ModelB"] = KGNode("ModelB", "Methods", 1, "method")
        level = svc._evaluate_level("ModelA", "ModelB", kg)
        assert level == GapLevel.FIELD

    def test_field_level_when_method_type(
        self, svc: KnowledgeGapElevationService
    ) -> None:
        """Same type = method with low frequency still → FIELD (method/dataset rule)."""
        kg = PaperKnowledgeGraph("p.tex")
        kg.nodes["MethodX"] = KGNode("MethodX", "Intro", 2, "method")
        kg.nodes["MethodY"] = KGNode("MethodY", "Methods", 2, "method")
        level = svc._evaluate_level("MethodX", "MethodY", kg)
        assert level == GapLevel.FIELD

    def test_paper_level_when_both_frequency_one_same_type(
        self, svc: KnowledgeGapElevationService
    ) -> None:
        """Both nodes: same type, frequency == 1 → PAPER."""
        kg = PaperKnowledgeGraph("p.tex")
        kg.nodes["ClaimA"] = KGNode("ClaimA", "Intro", 1, "claim")
        kg.nodes["ClaimB"] = KGNode("ClaimB", "Discussion", 1, "claim")
        level = svc._evaluate_level("ClaimA", "ClaimB", kg)
        assert level == GapLevel.PAPER

    def test_domain_level_otherwise(
        self, svc: KnowledgeGapElevationService
    ) -> None:
        """Same type, one freq == 2, neither is method/dataset → DOMAIN."""
        kg = PaperKnowledgeGraph("p.tex")
        kg.nodes["ConceptA"] = KGNode("ConceptA", "Intro", 2, "concept")
        kg.nodes["ConceptB"] = KGNode("ConceptB", "Methods", 1, "concept")
        level = svc._evaluate_level("ConceptA", "ConceptB", kg)
        assert level == GapLevel.DOMAIN

    def test_domain_level_when_node_not_in_kg(
        self, svc: KnowledgeGapElevationService, simple_kg: PaperKnowledgeGraph
    ) -> None:
        """Concept pair from citation graph (not in KG) → DOMAIN."""
        level = svc._evaluate_level("PaperRef1", "PaperRef2", simple_kg)
        assert level == GapLevel.DOMAIN


# ---------------------------------------------------------------------------
# Elevation potential mapping
# ---------------------------------------------------------------------------


class TestElevationPotentialMapping:
    def test_field_maps_to_q2_q1(self) -> None:
        assert LEVEL_TO_POTENTIAL[GapLevel.FIELD] == "Q2→Q1"

    def test_domain_maps_to_q3_q2(self) -> None:
        assert LEVEL_TO_POTENTIAL[GapLevel.DOMAIN] == "Q3→Q2"

    def test_paper_maps_to_limited(self) -> None:
        assert LEVEL_TO_POTENTIAL[GapLevel.PAPER] == "影響有限"


# ---------------------------------------------------------------------------
# Reframe suggestion
# ---------------------------------------------------------------------------


class TestGenerateReframe:
    def test_uses_current_rq_when_available(
        self, svc: KnowledgeGapElevationService
    ) -> None:
        gap = KnowledgeGap(
            concept_a="Transformer",
            concept_b="FederatedLearning",
            gap_description="No connection",
            level=GapLevel.FIELD,
            elevation_potential="Q2→Q1",
            reframe_suggestion="",
        )
        result = svc._generate_reframe(gap, "How does attention help NLP tasks?")
        assert "Transformer" in result
        assert "FederatedLearning" in result
        assert "How does attention" in result

    def test_fallback_when_no_rq(
        self, svc: KnowledgeGapElevationService
    ) -> None:
        gap = KnowledgeGap(
            concept_a="GAN",
            concept_b="MedicalImaging",
            gap_description="No connection",
            level=GapLevel.DOMAIN,
            elevation_potential="Q3→Q2",
            reframe_suggestion="",
        )
        result = svc._generate_reframe(gap, "")
        assert "GAN" in result
        assert "MedicalImaging" in result


# ---------------------------------------------------------------------------
# Read current RQ
# ---------------------------------------------------------------------------


class TestReadCurrentRQ:
    def test_reads_research_question_text(
        self, svc: KnowledgeGapElevationService, paper_with_trace: Path
    ) -> None:
        rq = svc._read_current_rq(str(paper_with_trace))
        assert "attention mechanism" in rq

    def test_reads_core_research_question_text(
        self, svc: KnowledgeGapElevationService, tmp_path: Path
    ) -> None:
        paper = tmp_path / "paper.tex"
        paper.write_text("content", encoding="utf-8")
        trace_dir = tmp_path / "_paper_trace" / "v2"
        trace_dir.mkdir(parents=True)
        (trace_dir / "6_research_question.yaml").write_text(
            yaml.dump(
                {"core_research_question": {"text": "What is the effect of X on Y?"}},
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        rq = svc._read_current_rq(str(paper))
        assert "effect of X" in rq

    def test_returns_empty_when_no_trace(
        self, svc: KnowledgeGapElevationService, paper_file: Path
    ) -> None:
        rq = svc._read_current_rq(str(paper_file))
        assert rq == ""

    def test_returns_empty_on_malformed_yaml(
        self, svc: KnowledgeGapElevationService, tmp_path: Path
    ) -> None:
        paper = tmp_path / "paper.tex"
        paper.write_text("content", encoding="utf-8")
        trace_dir = tmp_path / "_paper_trace" / "v2"
        trace_dir.mkdir(parents=True)
        (trace_dir / "6_research_question.yaml").write_text(
            ":::invalid yaml:::\n\t[broken", encoding="utf-8"
        )
        rq = svc._read_current_rq(str(paper))
        assert rq == ""


# ---------------------------------------------------------------------------
# Write to trace
# ---------------------------------------------------------------------------


class TestWriteToTrace:
    def test_writes_gap_analysis(
        self, svc: KnowledgeGapElevationService, paper_with_trace: Path
    ) -> None:
        gaps = [
            KnowledgeGap(
                concept_a="A",
                concept_b="B",
                gap_description="desc",
                level=GapLevel.FIELD,
                elevation_potential="Q2→Q1",
                reframe_suggestion="Focus on A-B intersection",
            ),
            KnowledgeGap(
                concept_a="C",
                concept_b="D",
                gap_description="desc2",
                level=GapLevel.DOMAIN,
                elevation_potential="Q3→Q2",
                reframe_suggestion="Explore C under D",
            ),
        ]
        svc._write_to_trace(gaps, str(paper_with_trace))

        trace_file = paper_with_trace.parent / "_paper_trace" / "v2" / "6_research_question.yaml"
        with open(trace_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert "gap_analysis" in data
        ga = data["gap_analysis"]
        assert ga["field_level_count"] == 1
        assert ga["domain_level_count"] == 1
        assert ga["paper_level_count"] == 0
        assert "top_reframe" in ga

    def test_no_error_when_trace_missing(
        self, svc: KnowledgeGapElevationService, paper_file: Path
    ) -> None:
        """_write_to_trace should be a no-op when trace file doesn't exist."""
        # Should not raise
        svc._write_to_trace([], str(paper_file))


# ---------------------------------------------------------------------------
# _gaps_from_kg filtering
# ---------------------------------------------------------------------------


class TestGapsFromKG:
    def test_filters_marginal_same_type_low_freq_pairs(
        self, svc: KnowledgeGapElevationService
    ) -> None:
        """Pairs where both nodes have same type and frequency < 2 are filtered out."""
        kg = PaperKnowledgeGraph("p.tex")
        kg.nodes["X"] = KGNode("X", "Intro", 1, "claim")
        kg.nodes["Y"] = KGNode("Y", "Intro", 1, "claim")
        # No edge between X and Y
        pairs = svc._gaps_from_kg(kg)
        # Both freq < 2 and same type → filtered
        pair_set = {frozenset([a, b]) for a, b in pairs}
        assert frozenset(["X", "Y"]) not in pair_set

    def test_keeps_cross_type_pairs_even_if_low_freq(
        self, svc: KnowledgeGapElevationService
    ) -> None:
        """Cross-type pairs pass through even with low frequency."""
        kg = PaperKnowledgeGraph("p.tex")
        kg.nodes["MethodA"] = KGNode("MethodA", "Intro", 1, "method")
        kg.nodes["DatasetB"] = KGNode("DatasetB", "Intro", 1, "dataset")
        pairs = svc._gaps_from_kg(kg)
        pair_set = {frozenset([a, b]) for a, b in pairs}
        assert frozenset(["MethodA", "DatasetB"]) in pair_set


# ---------------------------------------------------------------------------
# _gaps_from_citation_graph
# ---------------------------------------------------------------------------


class TestGapsFromCitationGraph:
    def test_returns_empty_when_refs_dir_missing(
        self, svc: KnowledgeGapElevationService, tmp_path: Path
    ) -> None:
        result = svc._gaps_from_citation_graph(str(tmp_path / "nonexistent_refs"))
        assert result == []

    def test_returns_pairs_from_semantic_gaps(
        self, svc: KnowledgeGapElevationService, tmp_path: Path
    ) -> None:
        refs_dir = tmp_path / "references"
        refs_dir.mkdir()

        mock_gaps = [
            {"cluster_id": 0, "size": 2, "representative_papers": ["paper_a", "paper_b"]},
        ]

        mock_instance = MagicMock()
        mock_instance.find_semantic_gaps.return_value = mock_gaps

        with patch(
            "crane.services.knowledge_gap_elevation_service.CitationGraphService",
            return_value=mock_instance,
        ):
            result = svc._gaps_from_citation_graph(str(refs_dir))

        assert ("paper_a", "paper_b") in result

    def test_graceful_on_exception(
        self, svc: KnowledgeGapElevationService, tmp_path: Path
    ) -> None:
        refs_dir = tmp_path / "references"
        refs_dir.mkdir()

        with patch(
            "crane.services.knowledge_gap_elevation_service.CitationGraphService",
            side_effect=RuntimeError("boom"),
        ):
            result = svc._gaps_from_citation_graph(str(refs_dir))

        assert result == []


# ---------------------------------------------------------------------------
# evaluate() integration (light — no real LLM or network)
# ---------------------------------------------------------------------------


class TestEvaluate:
    def test_evaluate_accepts_prebuilt_kg(
        self, svc: KnowledgeGapElevationService, paper_file: Path, simple_kg: PaperKnowledgeGraph
    ) -> None:
        """evaluate() skips PaperKnowledgeGraphService.build() when kg is passed."""
        simple_kg.paper_path = str(paper_file)

        mock_pkgs = MagicMock()

        with (
            patch(
                "crane.services.knowledge_gap_elevation_service.PaperKnowledgeGraphService",
                return_value=mock_pkgs,
            ),
            patch.object(svc, "_gaps_from_citation_graph", return_value=[]),
        ):
            result = svc.evaluate(
                paper_path=str(paper_file),
                kg=simple_kg,
                top_n=10,
                refs_dir=str(paper_file.parent / "refs"),
            )
            # Build should NOT have been called
            mock_pkgs.build.assert_not_called()

        assert isinstance(result, list)

    def test_evaluate_returns_at_most_top_n(
        self, svc: KnowledgeGapElevationService, paper_file: Path, simple_kg: PaperKnowledgeGraph
    ) -> None:
        simple_kg.paper_path = str(paper_file)
        with patch.object(svc, "_gaps_from_citation_graph", return_value=[]):
            result = svc.evaluate(
                paper_path=str(paper_file), kg=simple_kg, top_n=1
            )
        assert len(result) <= 1

    def test_evaluate_sorted_field_first(
        self, svc: KnowledgeGapElevationService, paper_file: Path, simple_kg: PaperKnowledgeGraph
    ) -> None:
        simple_kg.paper_path = str(paper_file)
        with patch.object(svc, "_gaps_from_citation_graph", return_value=[]):
            result = svc.evaluate(
                paper_path=str(paper_file), kg=simple_kg, top_n=10
            )

        if len(result) >= 2:
            _order = {GapLevel.FIELD: 0, GapLevel.DOMAIN: 1, GapLevel.PAPER: 2}
            for i in range(len(result) - 1):
                assert _order[result[i].level] <= _order[result[i + 1].level]

    def test_evaluate_graceful_when_no_trace(
        self, svc: KnowledgeGapElevationService, paper_file: Path, simple_kg: PaperKnowledgeGraph
    ) -> None:
        """evaluate() should not raise even when paper_trace is absent."""
        simple_kg.paper_path = str(paper_file)
        with patch.object(svc, "_gaps_from_citation_graph", return_value=[]):
            result = svc.evaluate(
                paper_path=str(paper_file), kg=simple_kg, top_n=5
            )
        # Just verifying no exception
        assert isinstance(result, list)
