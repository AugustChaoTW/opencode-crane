# pyright: reportMissingImports=false
"""Tests for PaperKnowledgeGraphService."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crane.services.paper_knowledge_graph_service import (
    KGEdge,
    KGNode,
    PaperKnowledgeGraph,
    PaperKnowledgeGraphService,
)
from crane.services.section_chunker import Section


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def svc() -> PaperKnowledgeGraphService:
    return PaperKnowledgeGraphService(api_key=None)


@pytest.fixture
def sample_paper(tmp_path: Path) -> Path:
    p = tmp_path / "paper.tex"
    p.write_text(
        r"""\documentclass{article}
\begin{document}
\begin{abstract}
We propose a new method called BestNet for image classification.
\end{abstract}
\section{Introduction}
BestNet is a deep learning method. We evaluate on ImageNet dataset.
Accuracy is our primary metric.
\section{Methods}
BestNet uses attention mechanisms. It extends Transformer architecture.
\end{document}
""",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def simple_kg() -> PaperKnowledgeGraph:
    kg = PaperKnowledgeGraph(paper_path="fake.tex", file_hash="abc")
    kg.nodes["BestNet"] = KGNode("BestNet", "Introduction", 2, "method")
    kg.nodes["ImageNet"] = KGNode("ImageNet", "Introduction", 1, "dataset")
    kg.nodes["Accuracy"] = KGNode("Accuracy", "Introduction", 1, "metric")
    kg.edges.append(
        KGEdge("BestNet", "ImageNet", "uses", "evaluated on ImageNet", 0.9)
    )
    return kg


# ---------------------------------------------------------------------------
# SHA-256 helper
# ---------------------------------------------------------------------------


class TestSha256:
    def test_returns_empty_for_missing_file(self, tmp_path: Path) -> None:
        result = PaperKnowledgeGraphService._sha256(tmp_path / "nonexistent.tex")
        assert result == ""

    def test_returns_hex_digest_for_existing_file(self, sample_paper: Path) -> None:
        result = PaperKnowledgeGraphService._sha256(sample_paper)
        expected = hashlib.sha256(sample_paper.read_bytes()).hexdigest()
        assert result == expected


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


class TestCacheHelpers:
    def test_cache_invalid_when_no_file(self, svc: PaperKnowledgeGraphService, tmp_path: Path) -> None:
        paper = tmp_path / "paper.tex"
        paper.write_text("content", encoding="utf-8")
        assert not svc._is_cache_valid(str(paper))

    def test_cache_invalid_when_hash_mismatch(
        self, svc: PaperKnowledgeGraphService, tmp_path: Path
    ) -> None:
        paper = tmp_path / "paper.tex"
        paper.write_text("content", encoding="utf-8")

        cache_path = paper.parent / PaperKnowledgeGraphService._CACHE_SUBPATH
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({"file_hash": "wrong_hash"}), encoding="utf-8")

        assert not svc._is_cache_valid(str(paper))

    def test_cache_valid_when_hash_matches(
        self, svc: PaperKnowledgeGraphService, tmp_path: Path
    ) -> None:
        paper = tmp_path / "paper.tex"
        paper.write_text("content", encoding="utf-8")
        h = PaperKnowledgeGraphService._sha256(paper)

        cache_path = paper.parent / PaperKnowledgeGraphService._CACHE_SUBPATH
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({"file_hash": h}), encoding="utf-8")

        assert svc._is_cache_valid(str(paper), h)

    def test_save_and_load_roundtrip(
        self, svc: PaperKnowledgeGraphService, tmp_path: Path, simple_kg: PaperKnowledgeGraph
    ) -> None:
        paper = tmp_path / "paper.tex"
        paper.write_text("hi", encoding="utf-8")
        simple_kg.paper_path = str(paper)

        svc._save_cache(str(paper), simple_kg)
        loaded = svc._load_cache(str(paper))

        assert loaded.file_hash == simple_kg.file_hash
        assert set(loaded.nodes.keys()) == set(simple_kg.nodes.keys())
        assert len(loaded.edges) == len(simple_kg.edges)


# ---------------------------------------------------------------------------
# Keyword fallback
# ---------------------------------------------------------------------------


class TestKeywordFallback:
    def test_returns_concepts_and_relations(self) -> None:
        text = "BestNet is a Transformer model. ImageNet is used as Dataset for Accuracy evaluation."
        result = PaperKnowledgeGraphService._keyword_fallback(text, "Introduction")
        assert "concepts" in result
        assert "relations" in result
        assert len(result["concepts"]) > 0

    def test_empty_text_returns_empty(self) -> None:
        result = PaperKnowledgeGraphService._keyword_fallback("", "Abstract")
        assert result["concepts"] == []
        assert result["relations"] == []

    def test_metric_type_hint(self) -> None:
        # Keyword fallback uses [A-Z] regex — metric words must be capitalised
        text = "We measure Accuracy, Precision, and Recall on the Benchmark."
        result = PaperKnowledgeGraphService._keyword_fallback(text, "Results")
        types = {c["name"]: c["type"] for c in result["concepts"]}
        # At least one metric concept should be detected
        assert any(t == "metric" for t in types.values())


# ---------------------------------------------------------------------------
# _merge_into_kg
# ---------------------------------------------------------------------------


class TestMergeIntoKG:
    def test_adds_new_nodes(self, svc: PaperKnowledgeGraphService) -> None:
        kg = PaperKnowledgeGraph("p.tex")
        extracted = {
            "concepts": [{"name": "Transformer", "type": "method"}],
            "relations": [],
        }
        svc._merge_into_kg(kg, extracted, "Introduction")
        assert "Transformer" in kg.nodes
        assert kg.nodes["Transformer"].node_type == "method"

    def test_increments_frequency_for_existing_node(self, svc: PaperKnowledgeGraphService) -> None:
        kg = PaperKnowledgeGraph("p.tex")
        kg.nodes["BERT"] = KGNode("BERT", "Intro", 1, "method")
        extracted = {"concepts": [{"name": "BERT", "type": "method"}], "relations": []}
        svc._merge_into_kg(kg, extracted, "Methods")
        assert kg.nodes["BERT"].frequency == 2

    def test_adds_edges(self, svc: PaperKnowledgeGraphService) -> None:
        kg = PaperKnowledgeGraph("p.tex")
        extracted = {
            "concepts": [],
            "relations": [
                {"from": "A", "to": "B", "type": "uses", "evidence": "A uses B for evaluation"}
            ],
        }
        svc._merge_into_kg(kg, extracted, "Methods")
        assert len(kg.edges) == 1
        assert kg.edges[0].source == "A"
        assert kg.edges[0].target == "B"

    def test_invalid_node_type_defaults_to_concept(self, svc: PaperKnowledgeGraphService) -> None:
        kg = PaperKnowledgeGraph("p.tex")
        extracted = {"concepts": [{"name": "X", "type": "garbage"}], "relations": []}
        svc._merge_into_kg(kg, extracted, "Results")
        assert kg.nodes["X"].node_type == "concept"

    def test_invalid_relation_type_defaults_to_supports(self, svc: PaperKnowledgeGraphService) -> None:
        kg = PaperKnowledgeGraph("p.tex")
        extracted = {
            "concepts": [],
            "relations": [{"from": "A", "to": "B", "type": "unknown", "evidence": "..."}],
        }
        svc._merge_into_kg(kg, extracted, "Results")
        assert kg.edges[0].relation == "supports"

    def test_skips_empty_concept_names(self, svc: PaperKnowledgeGraphService) -> None:
        kg = PaperKnowledgeGraph("p.tex")
        extracted = {"concepts": [{"name": "", "type": "method"}], "relations": []}
        svc._merge_into_kg(kg, extracted, "Abstract")
        assert len(kg.nodes) == 0

    def test_evidence_truncated_to_100_chars(self, svc: PaperKnowledgeGraphService) -> None:
        kg = PaperKnowledgeGraph("p.tex")
        long_evidence = "x" * 200
        extracted = {
            "concepts": [],
            "relations": [{"from": "A", "to": "B", "type": "supports", "evidence": long_evidence}],
        }
        svc._merge_into_kg(kg, extracted, "Methods")
        assert len(kg.edges[0].evidence) <= 100


# ---------------------------------------------------------------------------
# find_concept_gaps
# ---------------------------------------------------------------------------


class TestFindConceptGaps:
    def test_no_gap_when_fully_connected(self, svc: PaperKnowledgeGraphService) -> None:
        kg = PaperKnowledgeGraph("p.tex")
        kg.nodes["A"] = KGNode("A", "Intro", 1, "method")
        kg.nodes["B"] = KGNode("B", "Intro", 1, "dataset")
        kg.edges.append(KGEdge("A", "B", "uses", "evidence", 0.9))
        gaps = svc.find_concept_gaps(kg)
        assert gaps == []

    def test_gap_detected_when_no_edge(self, svc: PaperKnowledgeGraphService) -> None:
        kg = PaperKnowledgeGraph("p.tex")
        kg.nodes["A"] = KGNode("A", "Intro", 2, "method")
        kg.nodes["B"] = KGNode("B", "Intro", 3, "dataset")
        gaps = svc.find_concept_gaps(kg)
        assert len(gaps) == 1
        assert gaps[0]["source"] in {"A", "B"}
        assert gaps[0]["target"] in {"A", "B"}

    def test_single_node_returns_no_gaps(self, svc: PaperKnowledgeGraphService) -> None:
        kg = PaperKnowledgeGraph("p.tex")
        kg.nodes["A"] = KGNode("A", "Intro", 1, "method")
        assert svc.find_concept_gaps(kg) == []

    def test_gaps_sorted_by_combined_frequency(self, svc: PaperKnowledgeGraphService) -> None:
        kg = PaperKnowledgeGraph("p.tex")
        kg.nodes["A"] = KGNode("A", "Intro", 5, "method")
        kg.nodes["B"] = KGNode("B", "Intro", 1, "dataset")
        kg.nodes["C"] = KGNode("C", "Intro", 10, "metric")
        # Only A-C edge exists; gaps: B-A (6), B-C (11)
        kg.edges.append(KGEdge("A", "C", "uses", "ev", 0.8))
        gaps = svc.find_concept_gaps(kg)
        # highest combined_frequency gap should come first
        assert gaps[0]["combined_frequency"] >= gaps[-1]["combined_frequency"]

    def test_partial_edges_find_remaining_gaps(
        self, svc: PaperKnowledgeGraphService, simple_kg: PaperKnowledgeGraph
    ) -> None:
        # simple_kg has BestNet→ImageNet edge; BestNet-Accuracy and ImageNet-Accuracy are gaps
        gaps = svc.find_concept_gaps(simple_kg)
        gap_pairs = {frozenset([g["source"], g["target"]]) for g in gaps}
        assert frozenset(["BestNet", "Accuracy"]) in gap_pairs
        assert frozenset(["ImageNet", "Accuracy"]) in gap_pairs


# ---------------------------------------------------------------------------
# to_mermaid
# ---------------------------------------------------------------------------


class TestToMermaid:
    def test_starts_with_graph_td(
        self, svc: PaperKnowledgeGraphService, simple_kg: PaperKnowledgeGraph
    ) -> None:
        mermaid = svc.to_mermaid(simple_kg)
        assert mermaid.startswith("graph TD")

    def test_contains_node_labels(
        self, svc: PaperKnowledgeGraphService, simple_kg: PaperKnowledgeGraph
    ) -> None:
        mermaid = svc.to_mermaid(simple_kg)
        assert "BestNet" in mermaid
        assert "ImageNet" in mermaid

    def test_contains_edge_relation(
        self, svc: PaperKnowledgeGraphService, simple_kg: PaperKnowledgeGraph
    ) -> None:
        mermaid = svc.to_mermaid(simple_kg)
        assert "uses" in mermaid

    def test_empty_graph_has_placeholder(self, svc: PaperKnowledgeGraphService) -> None:
        kg = PaperKnowledgeGraph("p.tex")
        mermaid = svc.to_mermaid(kg)
        assert "No concepts extracted" in mermaid

    def test_special_chars_replaced_in_node_ids(self, svc: PaperKnowledgeGraphService) -> None:
        kg = PaperKnowledgeGraph("p.tex")
        kg.nodes["BERT-base"] = KGNode("BERT-base", "Intro", 1, "method")
        mermaid = svc.to_mermaid(kg)
        # Node ID should not contain hyphen
        assert "BERT_base" in mermaid


# ---------------------------------------------------------------------------
# build() with cache bypass and LLM mock
# ---------------------------------------------------------------------------


class TestBuild:
    def test_build_uses_cache_when_valid(
        self, svc: PaperKnowledgeGraphService, tmp_path: Path, simple_kg: PaperKnowledgeGraph
    ) -> None:
        paper = tmp_path / "paper.tex"
        paper.write_text("content", encoding="utf-8")
        h = PaperKnowledgeGraphService._sha256(paper)
        simple_kg.paper_path = str(paper)
        simple_kg.file_hash = h
        svc._save_cache(str(paper), simple_kg)

        with patch.object(svc._chunker, "chunk_latex_paper") as mock_chunk:
            result = svc.build(str(paper))
            mock_chunk.assert_not_called()

        assert result.file_hash == h
        assert "BestNet" in result.nodes

    def test_force_rebuild_bypasses_cache(
        self, svc: PaperKnowledgeGraphService, tmp_path: Path, simple_kg: PaperKnowledgeGraph
    ) -> None:
        paper = tmp_path / "paper.tex"
        paper.write_text(r"\section{Intro} BestNet uses Transformer.", encoding="utf-8")
        h = PaperKnowledgeGraphService._sha256(paper)
        simple_kg.paper_path = str(paper)
        simple_kg.file_hash = h
        svc._save_cache(str(paper), simple_kg)

        fake_section = Section(
            name="Intro",
            canonical_name="Introduction",
            content="BestNet uses Transformer.",
            character_count=25,
            word_count=4,
        )
        with patch.object(svc._chunker, "chunk_latex_paper", return_value=[fake_section]):
            result = svc.build(str(paper), force_rebuild=True)

        # Should have rebuilt; nodes come from keyword fallback
        assert result.file_hash == h

    def test_build_calls_llm_when_api_key_set(self, tmp_path: Path) -> None:
        svc_with_key = PaperKnowledgeGraphService(api_key="fake-key")
        paper = tmp_path / "paper.tex"
        paper.write_text(r"\section{Intro} content", encoding="utf-8")

        fake_section = Section(
            name="Introduction",
            canonical_name="Introduction",
            content="BestNet is a method.",
            character_count=20,
            word_count=5,
        )

        llm_response = {
            "concepts": [{"name": "BestNet", "type": "method"}],
            "relations": [],
        }

        with (
            patch.object(svc_with_key._chunker, "chunk_latex_paper", return_value=[fake_section]),
            patch.object(svc_with_key, "_call_llm", return_value=llm_response) as mock_llm,
        ):
            result = svc_with_key.build(str(paper), force_rebuild=True)

        mock_llm.assert_called_once()
        assert "BestNet" in result.nodes

    def test_build_falls_back_when_llm_fails(self, tmp_path: Path) -> None:
        svc_with_key = PaperKnowledgeGraphService(api_key="fake-key")
        paper = tmp_path / "paper.tex"
        paper.write_text(r"\section{Intro} BestNet Transformer ImageNet Accuracy.", encoding="utf-8")

        fake_section = Section(
            name="Introduction",
            canonical_name="Introduction",
            content="BestNet Transformer ImageNet Accuracy are used.",
            character_count=47,
            word_count=7,
        )

        with (
            patch.object(svc_with_key._chunker, "chunk_latex_paper", return_value=[fake_section]),
            patch.object(svc_with_key, "_call_llm", return_value=None),
        ):
            result = svc_with_key.build(str(paper), force_rebuild=True)

        # Fallback should still populate some nodes
        assert len(result.nodes) > 0

    def test_build_pdf_calls_chunk_pdf(self, tmp_path: Path) -> None:
        svc = PaperKnowledgeGraphService(api_key=None)
        paper = tmp_path / "paper.pdf"
        paper.write_bytes(b"fake pdf content")

        fake_section = Section(
            name="Body",
            canonical_name="Body",
            content="Some content about Transformer and Dataset.",
            character_count=42,
            word_count=7,
        )

        with patch.object(svc._chunker, "chunk_pdf_paper", return_value=[fake_section]):
            result = svc.build(str(paper), force_rebuild=True)

        assert len(result.nodes) > 0
