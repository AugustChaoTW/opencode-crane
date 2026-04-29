"""Tests for Issue #109: Token optimization validation."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from crane.services.contradiction_detection_service import (
    _safe_json_parse as cd_safe_json_parse,
)
from crane.services.paper_knowledge_graph_service import (
    KGEdge,
    KGNode,
    PaperKnowledgeGraph,
    PaperKnowledgeGraphService,
)
from crane.services.paper_knowledge_graph_service import (
    _safe_json_parse as kg_safe_json_parse,
)

# ---------------------------------------------------------------------------
# Design 2: KG Cache
# ---------------------------------------------------------------------------


class TestKGCache:
    def test_cache_hit_skips_llm(self, tmp_path):
        """Same paper hash → load from cache, never call LLM."""
        paper = tmp_path / "paper.tex"
        paper.write_text(r"\section{Intro} Hello world.", encoding="utf-8")

        svc = PaperKnowledgeGraphService(api_key=None)

        # Pre-populate cache manually
        cache_dir = paper.parent / "_paper_trace" / "v2"
        cache_dir.mkdir(parents=True)
        real_hash = svc._sha256(paper)
        cache = cache_dir / "kg_cache.json"
        cached_kg = {
            "paper_path": str(paper),
            "file_hash": real_hash,
            "nodes": {
                "CachedConcept": {
                    "concept": "CachedConcept",
                    "section": "intro",
                    "frequency": 1,
                    "node_type": "concept",
                }
            },
            "edges": [],
        }
        cache.write_text(json.dumps(cached_kg), encoding="utf-8")

        with patch.object(svc, "_call_llm") as mock_llm:
            kg = svc.build(str(paper))

        mock_llm.assert_not_called()
        assert "CachedConcept" in kg.nodes

    def test_cache_miss_on_changed_hash(self, tmp_path):
        """Different hash → rebuild (not return stale cache)."""
        paper = tmp_path / "paper.tex"
        paper.write_text(r"\section{Intro} Hello.", encoding="utf-8")

        svc = PaperKnowledgeGraphService(api_key=None)

        # Cache with a stale hash
        cache_dir = paper.parent / "_paper_trace" / "v2"
        cache_dir.mkdir(parents=True)
        cache = cache_dir / "kg_cache.json"
        stale = {
            "paper_path": str(paper),
            "file_hash": "stale_hash_000",
            "nodes": {"StaleNode": {"concept": "StaleNode", "section": "x", "frequency": 1, "node_type": "concept"}},
            "edges": [],
        }
        cache.write_text(json.dumps(stale), encoding="utf-8")

        kg = svc.build(str(paper))
        # StaleNode should NOT be there (cache was invalidated)
        assert "StaleNode" not in kg.nodes

    def test_is_cache_valid_missing_file(self, tmp_path):
        paper = tmp_path / "paper.tex"
        paper.write_text("content")
        svc = PaperKnowledgeGraphService(api_key=None)
        assert svc._is_cache_valid(str(paper)) is False

    def test_save_and_load_cache(self, tmp_path):
        paper = tmp_path / "paper.tex"
        paper.write_text("content", encoding="utf-8")
        svc = PaperKnowledgeGraphService(api_key=None)

        kg = PaperKnowledgeGraph(
            paper_path=str(paper),
            file_hash="abc123",
            nodes={"X": KGNode("X", "intro", 1, "concept")},
            edges=[KGEdge("X", "Y", "supports", "evidence", 0.9)],
        )
        svc._save_cache(str(paper), kg)
        loaded = svc._load_cache(str(paper))

        assert loaded.file_hash == "abc123"
        assert "X" in loaded.nodes
        assert len(loaded.edges) == 1


# ---------------------------------------------------------------------------
# Design 5 / Safe JSON parse
# ---------------------------------------------------------------------------


class TestSafeJsonParse:
    @pytest.mark.parametrize("fn", [kg_safe_json_parse, cd_safe_json_parse])
    def test_valid_json_parsed(self, fn):
        text = '{"key": "value", "num": 42}'
        result = fn(text, {"fallback": True})
        assert result == {"key": "value", "num": 42}

    @pytest.mark.parametrize("fn", [kg_safe_json_parse, cd_safe_json_parse])
    def test_garbage_returns_fallback(self, fn):
        fallback = {"is_contradiction": False}
        result = fn("This is plain text garbage 🤷", fallback)
        assert result == fallback

    @pytest.mark.parametrize("fn", [kg_safe_json_parse, cd_safe_json_parse])
    def test_json_embedded_in_text(self, fn):
        text = 'Sure! Here is your answer: {"concepts": [], "relations": []} done.'
        result = fn(text, {"fallback": True})
        assert result == {"concepts": [], "relations": []}

    @pytest.mark.parametrize("fn", [kg_safe_json_parse, cd_safe_json_parse])
    def test_malformed_json_returns_fallback(self, fn):
        fallback = {"error": "parse_failed"}
        result = fn("{bad json: [}", fallback)
        assert result == fallback

    @pytest.mark.parametrize("fn", [kg_safe_json_parse, cd_safe_json_parse])
    def test_empty_string_returns_fallback(self, fn):
        fallback = {"default": 1}
        result = fn("", fallback)
        assert result == fallback


# ---------------------------------------------------------------------------
# Design 3: Semantic Prefilter
# ---------------------------------------------------------------------------


class TestSemanticPrefilter:
    def _make_section(self, name: str, content: str):
        from crane.services.section_chunker import Section

        return Section(name=name, canonical_name=name, content=content, word_count=len(content.split()))

    def test_fallback_pairs_returned_when_no_api(self):
        from crane.services.contradiction_detection_service import ContradictionDetectionService

        svc = ContradictionDetectionService(api_key=None)
        sections = [
            self._make_section("Abstract", "This paper proposes X which outperforms baseline."),
            self._make_section("Introduction", "We introduce X."),
            self._make_section("Discussion", "X has limitations not discussed elsewhere."),
            self._make_section("Conclusion", "X achieves state-of-the-art results."),
        ]
        pairs = svc._semantic_prefilter(sections)
        # fallback always returns canonical-name matched pairs
        assert len(pairs) > 0

    def test_low_similarity_pairs_excluded_when_embeddings_available(self):
        """Pairs with cosine sim < 0.3 must not be included."""
        from crane.services.contradiction_detection_service import ContradictionDetectionService

        svc = ContradictionDetectionService(api_key="fake")

        # Mock embed returns orthogonal vectors for most pairs
        call_count = [0]

        def fake_embed(text: str):
            call_count[0] += 1
            # Section A and B share direction; rest are orthogonal
            if "alpha" in text:
                return [1.0, 0.0, 0.0]
            if "beta" in text:
                return [0.0, 1.0, 0.0]  # orthogonal → sim=0
            return [0.0, 0.0, 1.0]

        with patch.object(svc, "_embed_text", side_effect=fake_embed):
            sections = [
                self._make_section("Alpha", "alpha " * 50),
                self._make_section("Beta", "beta " * 50),
            ]
            pairs = svc._try_embedding_prefilter(sections)

        # sim(alpha, beta) == 0 < 0.3 → excluded
        assert pairs == [] or pairs is None or len(pairs) == 0

    def test_returns_none_without_api_key(self):
        from crane.services.contradiction_detection_service import ContradictionDetectionService

        svc = ContradictionDetectionService(api_key=None)
        sections = [self._make_section("A", "some text"), self._make_section("B", "other text")]
        result = svc._try_embedding_prefilter(sections)
        assert result is None
