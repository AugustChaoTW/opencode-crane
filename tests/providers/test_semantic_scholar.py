"""Tests for Semantic Scholar provider."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def _load_ss():
    import importlib

    return importlib.import_module("crane.providers.semantic_scholar")


class TestSemanticScholarProvider:
    def test_name_property(self):
        mod = _load_ss()
        provider = mod.SemanticScholarProvider()
        assert provider.name == "semantic_scholar"

    def test_search_returns_list(self):
        mod = _load_ss()
        provider = mod.SemanticScholarProvider()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "paperId": "abc123",
                    "title": "Test Paper",
                    "abstract": "Test abstract",
                    "year": 2024,
                    "citationCount": 100,
                    "url": "https://semanticscholar.org/paper/abc123",
                    "externalIds": {"DOI": "10.1234/test"},
                    "authors": [{"name": "Author One"}],
                    "references": [],
                    "openAccessPdf": {"url": "https://example.com/paper.pdf"},
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("crane.providers.semantic_scholar.requests.request", return_value=mock_response):
            results = provider.search("test query")

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0].source == "semantic_scholar"
        assert results[0].title == "Test Paper"
        assert results[0].citations == 100

    def test_get_by_id(self):
        mod = _load_ss()
        provider = mod.SemanticScholarProvider()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "paperId": "def456",
            "title": "ID Paper",
            "abstract": "Test abstract",
            "year": 2023,
            "citationCount": 50,
            "url": "https://semanticscholar.org/paper/def456",
            "externalIds": {"DOI": "10.5678/id-test"},
            "authors": [{"name": "Author Two"}],
            "references": [],
            "openAccessPdf": None,
        }
        mock_response.raise_for_status = MagicMock()

        with patch("crane.providers.semantic_scholar.requests.request", return_value=mock_response):
            result = provider.get_by_id("def456")

        assert result is not None
        assert result.title == "ID Paper"
        assert result.source == "semantic_scholar"
