"""Tests for metadata normalization service."""

from __future__ import annotations

import importlib


def _load():
    return importlib.import_module("crane.services.metadata_service")


def _load_base():
    return importlib.import_module("crane.providers.base")


class TestNormalizedMetadata:
    def test_primary_source_priority(self):
        mod = _load()
        nm = mod.NormalizedMetadata(
            title="Test",
            authors=[],
            year=2024,
            doi="",
            abstract="",
            sources=["arxiv", "semantic_scholar"],
        )
        assert nm.primary_source == "semantic_scholar"

    def test_max_citations(self):
        mod = _load()
        nm = mod.NormalizedMetadata(
            title="Test",
            authors=[],
            year=2024,
            doi="",
            abstract="",
            citations={"arxiv": 10, "semantic_scholar": 50},
        )
        assert nm.max_citations == 50


class TestMetadataNormalizer:
    def test_normalize_empty_list(self):
        mod = _load()
        normalizer = mod.MetadataNormalizer()
        result = normalizer.normalize([])
        assert result == []

    def test_normalize_single_item(self):
        mod = _load()
        base = _load_base()
        normalizer = mod.MetadataNormalizer()

        metadata = base.UnifiedMetadata(
            title="Test Paper",
            authors=["Author One"],
            year=2024,
            doi="10.1234/test",
            abstract="Test abstract",
            source="arxiv",
            source_id="1234.5678",
            url="https://arxiv.org/abs/1234.5678",
            pdf_url="https://arxiv.org/pdf/1234.5678",
            citations=10,
            references=[],
        )

        result = normalizer.normalize([metadata])
        assert len(result) == 1
        assert result[0].title == "Test Paper"
        assert result[0].sources == ["arxiv"]

    def test_deduplicate_by_doi(self):
        mod = _load()
        base = _load_base()
        normalizer = mod.MetadataNormalizer()

        m1 = base.UnifiedMetadata(
            title="Paper A",
            authors=["Author"],
            year=2024,
            doi="10.1234/duplicate",
            abstract="From arxiv",
            source="arxiv",
            source_id="arxiv1",
            url="https://arxiv.org/abs/arxiv1",
            pdf_url="",
            citations=5,
            references=[],
        )

        m2 = base.UnifiedMetadata(
            title="Paper A",
            authors=["Author"],
            year=2024,
            doi="10.1234/duplicate",
            abstract="From semantic scholar",
            source="semantic_scholar",
            source_id="ss1",
            url="https://semanticscholar.org/paper/ss1",
            pdf_url="",
            citations=10,
            references=[],
        )

        result = normalizer.normalize([m1, m2])
        assert len(result) == 1
        assert set(result[0].sources) == {"arxiv", "semantic_scholar"}
        assert result[0].citations == {"arxiv": 5, "semantic_scholar": 10}

    def test_deduplicate_by_title_similarity(self):
        mod = _load()
        base = _load_base()
        normalizer = mod.MetadataNormalizer()

        m1 = base.UnifiedMetadata(
            title="Attention Is All You Need",
            authors=["Vaswani"],
            year=2017,
            doi="",
            abstract="",
            source="arxiv",
            source_id="1706.03762",
            url="",
            pdf_url="",
            citations=0,
            references=[],
        )

        m2 = base.UnifiedMetadata(
            title="Attention Is All You Need!",
            authors=["Vaswani"],
            year=2017,
            doi="",
            abstract="",
            source="openalex",
            source_id="W123",
            url="",
            pdf_url="",
            citations=0,
            references=[],
        )

        result = normalizer.normalize([m1, m2])
        assert len(result) == 1
