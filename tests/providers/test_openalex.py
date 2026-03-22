"""Tests for OpenAlex provider."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _load_openalex():
    import importlib

    return importlib.import_module("crane.providers.openalex")


class TestOpenAlexProvider:
    def test_name_property(self):
        mod = _load_openalex()
        provider = mod.OpenAlexProvider()
        assert provider.name == "openalex"

    def test_search_returns_list(self):
        mod = _load_openalex()
        provider = mod.OpenAlexProvider()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "https://openalex.org/W123456",
                    "title": "Test Paper",
                    "doi": "https://doi.org/10.1234/test",
                    "authorships": [{"author": {"display_name": "Author One"}}],
                    "publication_year": 2024,
                    "abstract_inverted_index": {"This": [0], "is": [1], "abstract": [2]},
                    "cited_by_count": 10,
                    "referenced_works": [],
                    "open_access": {},
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("crane.providers.openalex.requests.get", return_value=mock_response):
            results = provider.search("test query")

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0].source == "openalex"
        assert results[0].title == "Test Paper"

    def test_get_by_doi(self):
        mod = _load_openalex()
        provider = mod.OpenAlexProvider()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "https://openalex.org/W123456",
            "title": "DOI Paper",
            "doi": "https://doi.org/10.1234/doi-test",
            "authorships": [],
            "publication_year": 2023,
            "abstract_inverted_index": None,
            "cited_by_count": 5,
            "referenced_works": [],
            "open_access": {},
        }
        mock_response.raise_for_status = MagicMock()

        with patch("crane.providers.openalex.requests.get", return_value=mock_response):
            result = provider.get_by_doi("10.1234/doi-test")

        assert result is not None
        assert result.title == "DOI Paper"
        assert result.doi == "10.1234/doi-test"
