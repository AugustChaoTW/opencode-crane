"""Tests for MultiSourceEvidenceCollector service - Issue #72 Feynman integration."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from crane.services.multi_source_evidence_service import (
    MultiSourceEvidenceCollector,
    EvidenceRecord,
)


class TestEvidenceRecord:
    def test_initialization(self):
        record = EvidenceRecord(
            id="paper1",
            title="Test Paper",
            authors=["Author1", "Author2"],
            year=2024,
            source="arxiv",
            doi="10.1234/test",
        )

        assert record.id == "paper1"
        assert record.title == "Test Paper"
        assert len(record.authors) == 2
        assert record.year == 2024
        assert record.source == "arxiv"
        assert record.doi == "10.1234/test"
        assert record.similarity_score == 0.0
        assert record.cited_by_count == 0

    def test_default_values(self):
        record = EvidenceRecord(
            id="paper1",
            title="Test",
            authors=[],
            year=0,
            source="arxiv",
        )

        assert record.doi == ""
        assert record.url == ""
        assert record.abstract == ""
        assert record.similarity_score == 0.0
        assert record.cited_by_count == 0


class TestMultiSourceEvidenceCollector:
    @pytest.fixture
    def collector(self):
        return MultiSourceEvidenceCollector()

    def test_initialization(self, collector: MultiSourceEvidenceCollector):
        assert collector.paper_service is not None
        assert collector.semantic_service is not None
        assert collector.citation_service is not None

    def test_collect_evidence_from_arxiv(self, collector: MultiSourceEvidenceCollector):
        mock_results = [
            {
                "id": "paper1",
                "title": "Test Paper 1",
                "authors": ["Author1"],
                "year": 2024,
                "doi": "10.1234/test1",
            }
        ]

        with patch.object(collector.paper_service, "search", return_value=mock_results):
            results = collector.collect_evidence(
                query="test query", sources=["arxiv"], max_results=10
            )

            assert len(results) == 1
            assert results[0].id == "paper1"
            assert results[0].source == "arxiv"

    def test_collect_evidence_from_multiple_sources(self, collector: MultiSourceEvidenceCollector):
        mock_arxiv_results = [{"id": "paper1", "title": "Paper 1", "authors": [], "year": 2024}]
        mock_semantic_results = [
            {"key": "paper2", "title": "Paper 2", "authors": [], "year": 2024, "similarity": 0.8},
        ]

        with patch.object(collector.paper_service, "search", return_value=mock_arxiv_results):
            with patch.object(
                collector.semantic_service, "search_similar", return_value=mock_semantic_results
            ):
                results = collector.collect_evidence(
                    query="test", sources=["arxiv", "semantic_scholar"]
                )

                assert len(results) >= 1
                sources = {r.source for r in results}
                assert "arxiv" in sources

    def test_deduplication_by_doi(self, collector: MultiSourceEvidenceCollector):
        """Test that papers with the same DOI are deduplicated."""
        mock_results = [
            {
                "id": "paper1",
                "title": "Same Paper",
                "authors": [],
                "year": 2024,
                "doi": "10.1234/same",
            },
            {
                "id": "paper2",
                "title": "Same Paper",
                "authors": [],
                "year": 2024,
                "doi": "10.1234/same",
            },
        ]

        with patch.object(collector.paper_service, "search", return_value=mock_results):
            results = collector.collect_evidence(query="test", sources=["arxiv"], deduplicate=True)

            assert len(results) == 1  # Should deduplicate

    def test_deduplication_by_title(self, collector: MultiSourceEvidenceCollector):
        """Test deduplication when DOI is missing."""
        mock_results = [
            {"id": "paper1", "title": "Unique Title", "authors": [], "year": 2024},
            {"id": "paper2", "title": "Unique Title", "authors": [], "year": 2024},
        ]

        with patch.object(collector.paper_service, "search", return_value=mock_results):
            results = collector.collect_evidence(query="test", sources=["arxiv"], deduplicate=True)

            assert len(results) == 1

    def test_error_handling_for_source(self, collector: MultiSourceEvidenceCollector):
        """Test that errors in one source don't crash the whole collection."""
        with patch.object(
            collector.paper_service, "search", side_effect=Exception("Network error")
        ):
            results = collector.collect_evidence(query="test", sources=["arxiv"], max_results=10)

            assert results == []

    def test_find_similar_papers(self, collector: MultiSourceEvidenceCollector):
        mock_similar = [
            {
                "key": "paper1",
                "title": "Similar 1",
                "authors": [],
                "year": 2024,
                "similarity": 0.85,
            },
            {
                "key": "paper2",
                "title": "Similar 2",
                "authors": [],
                "year": 2024,
                "similarity": 0.65,
            },
        ]

        with patch.object(collector.semantic_service, "search_similar", return_value=mock_similar):
            results = collector.find_similar_papers(
                paper_id="test_paper", similarity_threshold=0.7, max_results=10
            )

            assert len(results) == 1
            assert results[0].similarity_score == 0.85

    def test_find_similar_papers_with_low_threshold(self, collector: MultiSourceEvidenceCollector):
        mock_similar = [
            {"key": "paper1", "title": "Similar", "authors": [], "year": 2024, "similarity": 0.5},
        ]

        with patch.object(collector.semantic_service, "search_similar", return_value=mock_similar):
            results = collector.find_similar_papers(paper_id="test_paper", similarity_threshold=0.6)

            assert len(results) == 0  # Below threshold

    def test_expand_citations_backward(self, collector: MultiSourceEvidenceCollector):
        mock_graph = {
            "test_paper": {
                "cited_by": [
                    {
                        "key": "citing1",
                        "title": "Citing Paper",
                        "authors": [],
                        "year": 2024,
                        "cited_by_count": 10,
                    },
                ],
                "cites": [],
            }
        }

        with patch.object(
            collector.citation_service, "build_citation_graph", return_value=mock_graph
        ):
            results = collector.expand_citations(paper_id="test_paper", direction="backward")

            assert len(results) == 1
            assert results[0].citation_context == "backward"

    def test_expand_citations_forward(self, collector: MultiSourceEvidenceCollector):
        mock_graph = {
            "test_paper": {
                "cited_by": [],
                "cites": [
                    {
                        "key": "cited1",
                        "title": "Cited Paper",
                        "authors": [],
                        "year": 2023,
                        "cited_by_count": 50,
                    },
                ],
            }
        }

        with patch.object(
            collector.citation_service, "build_citation_graph", return_value=mock_graph
        ):
            results = collector.expand_citations(paper_id="test_paper", direction="forward")

            assert len(results) == 1
            assert results[0].citation_context == "forward"

    def test_expand_citations_with_papers(self, collector: MultiSourceEvidenceCollector):
        mock_graph = {
            "test_paper": {
                "cited_by": [
                    {
                        "key": "citing1",
                        "title": "Citing",
                        "authors": [],
                        "year": 2024,
                        "cited_by_count": 10,
                    },
                ],
                "cites": [
                    {
                        "key": "cited1",
                        "title": "Cited",
                        "authors": [],
                        "year": 2023,
                        "cited_by_count": 50,
                    },
                ],
            }
        }

        with patch.object(
            collector.citation_service, "build_citation_graph", return_value=mock_graph
        ):
            results = collector.expand_citations(paper_id="test_paper", direction="both")

            assert len(results) == 2

    def test_get_evidence_statistics(self, collector: MultiSourceEvidenceCollector):
        records = [
            EvidenceRecord("id1", "Title", [], 2024, "arxiv", cited_by_count=10),
            EvidenceRecord("id2", "Title", [], 2024, "arxiv", cited_by_count=20),
            EvidenceRecord("id3", "Title", [], 2023, "crossref", cited_by_count=0),
        ]

        stats = collector.get_evidence_statistics(records)

        assert stats["total_count"] == 3
        assert stats["by_source"]["arxiv"] == 2
        assert stats["by_source"]["crossref"] == 1
        assert stats["by_year"]["2024"] == 2
        assert stats["by_year"]["2023"] == 1
        assert stats["avg_citations"] == 15.0  # (10 + 20) / 2

    def test_generate_dedup_key_with_doi(self, collector: MultiSourceEvidenceCollector):
        record = EvidenceRecord("id1", "Title", [], 2024, "arxiv", doi="10.1234/test")
        key = collector._generate_dedup_key(record)

        assert key == "doi:10.1234/test"

    def test_generate_dedup_key_without_doi(self, collector: MultiSourceEvidenceCollector):
        record = EvidenceRecord("id1", "Unique Title", [], 2024, "arxiv")
        key = collector._generate_dedup_key(record)

        assert key.startswith("title:")
        assert "unique title" in key

    def test_max_results_limit(self, collector: MultiSourceEvidenceCollector):
        mock_results = [
            {"id": f"paper{i}", "title": f"Paper {i}", "authors": [], "year": 2024}
            for i in range(100)
        ]

        with patch.object(collector.paper_service, "search", return_value=mock_results):
            results = collector.collect_evidence(query="test", sources=["arxiv"], max_results=10)

            assert len(results) <= 10

    def test_empty_query_handling(self, collector: MultiSourceEvidenceCollector):
        with patch.object(collector.paper_service, "search", return_value=[]):
            results = collector.collect_evidence(query="", sources=["arxiv"])

            assert results == []

    def test_unsupported_source_raises_error(self, collector: MultiSourceEvidenceCollector):
        """Test that unsupported source raises ValueError."""
        with pytest.raises(ValueError):
            collector._collect_from_source("test", "unsupported_source", 10)

    def test_extract_year_from_string(self, collector: MultiSourceEvidenceCollector):
        result = {"year": "2024-05-15"}
        year = collector._extract_year_from_result(result)

        assert year == 2024

    def test_extract_year_from_int(self, collector: MultiSourceEvidenceCollector):
        result = {"year": 2024}
        year = collector._extract_year_from_result(result)

        assert year == 2024

    def test_extract_year_default(self, collector: MultiSourceEvidenceCollector):
        result = {}
        year = collector._extract_year_from_result(result)

        assert year == 0
