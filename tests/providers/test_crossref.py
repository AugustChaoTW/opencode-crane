"""Tests for Crossref provider."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def _load():
    import importlib

    return importlib.import_module("crane.providers.crossref")


class TestCrossrefProvider:
    def test_name_property(self):
        mod = _load()
        provider = mod.CrossrefProvider()
        assert provider.name == "crossref"

    def test_search_returns_list(self):
        mod = _load()
        provider = mod.CrossrefProvider()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {
                "items": [
                    {
                        "DOI": "10.1234/test",
                        "title": ["Test Paper"],
                        "author": [{"given": "John", "family": "Doe"}],
                        "published-print": {"date-parts": [[2024]]},
                        "abstract": "Test abstract",
                        "container-title": ["Test Journal"],
                        "is-referenced-by-count": 10,
                        "reference": [],
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("crane.providers.crossref.requests.get", return_value=mock_response):
            results = provider.search("test query")

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0].source == "crossref"
        assert results[0].doi == "10.1234/test"

    def test_get_by_doi(self):
        mod = _load()
        provider = mod.CrossrefProvider()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {
                "DOI": "10.5678/doi-test",
                "title": ["DOI Paper"],
                "author": [],
                "published-online": {"date-parts": [[2023]]},
                "abstract": None,
                "container-title": [],
                "is-referenced-by-count": 5,
                "reference": [],
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("crane.providers.crossref.requests.get", return_value=mock_response):
            result = provider.get_by_doi("10.5678/doi-test")

        assert result is not None
        assert result.title == "DOI Paper"
        assert result.year == 2023
