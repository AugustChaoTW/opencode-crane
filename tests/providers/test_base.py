# pyright: reportMissingImports=false
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from crane.providers import ArxivProvider, PaperProvider, ProviderRegistry, UnifiedMetadata


@pytest.fixture
def mock_arxiv_response():
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v5</id>
    <title>Attention Is All You Need</title>
    <summary>The dominant sequence transduction models are based on complex recurrent.</summary>
    <published>2017-06-12T00:00:00Z</published>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
    <link title="pdf" type="application/pdf" href="http://arxiv.org/pdf/1706.03762v5"/>
    <category term="cs.CL"/>
  </entry>
</feed>"""


class DummyProvider(PaperProvider):
    def __init__(self, provider_name: str, results: list[UnifiedMetadata] | None = None):
        self._provider_name = provider_name
        self._results = results or []

    @property
    def name(self) -> str:
        return self._provider_name

    def search(self, query: str, max_results: int = 10) -> list[UnifiedMetadata]:
        return self._results[:max_results]

    def get_by_id(self, paper_id: str) -> UnifiedMetadata | None:
        return None

    def get_by_doi(self, doi: str) -> UnifiedMetadata | None:
        return None


def test_unified_metadata_stores_standardized_fields():
    metadata = UnifiedMetadata(
        title="Attention Is All You Need",
        authors=["Ashish Vaswani", "Noam Shazeer"],
        year=2017,
        doi="10.48550/arXiv.1706.03762",
        abstract="Transformer paper.",
        source="arxiv",
        source_id="1706.03762v5",
        url="https://arxiv.org/abs/1706.03762",
        pdf_url="https://arxiv.org/pdf/1706.03762.pdf",
        citations=0,
        references=["ref-1"],
    )

    assert metadata.source == "arxiv"
    assert metadata.source_id == "1706.03762v5"
    assert metadata.references == ["ref-1"]


def test_paper_provider_is_abstract():
    incomplete_provider = type("IncompleteProvider", (PaperProvider,), {})

    with pytest.raises(TypeError):
        incomplete_provider()


def test_registry_search_all_merges_provider_results():
    arxiv_result = UnifiedMetadata(
        title="Paper A",
        authors=["Author A"],
        year=2024,
        doi="arxiv:paper-a",
        abstract="A",
        source="arxiv",
        source_id="paper-a",
        url="https://example.com/a",
        pdf_url="https://example.com/a.pdf",
        citations=0,
        references=[],
    )
    second_result = UnifiedMetadata(
        title="Paper B",
        authors=["Author B"],
        year=2023,
        doi="doi:paper-b",
        abstract="B",
        source="other",
        source_id="paper-b",
        url="https://example.com/b",
        pdf_url="https://example.com/b.pdf",
        citations=5,
        references=[],
    )
    registry = ProviderRegistry(
        [
            DummyProvider("arxiv", [arxiv_result]),
            DummyProvider("other", [second_result]),
        ]
    )

    results = registry.search_all("transformer")

    assert [result.source for result in results] == ["arxiv", "other"]


def test_registry_search_all_can_limit_to_selected_providers():
    registry = ProviderRegistry(
        [
            DummyProvider("arxiv"),
            DummyProvider("other"),
        ]
    )

    results = registry.search_all("transformer", provider_names=["other"])

    assert results == []


def test_registry_search_all_raises_for_unknown_provider():
    registry = ProviderRegistry([DummyProvider("arxiv")])

    with pytest.raises(KeyError, match="Provider not registered: other"):
        registry.search_all("transformer", provider_names=["other"])


def test_arxiv_provider_search_returns_unified_metadata(mock_arxiv_response):
    provider = ArxivProvider()
    mock_response = MagicMock()
    mock_response.content = mock_arxiv_response.encode("utf-8")
    mock_response.raise_for_status.return_value = None

    with patch("crane.providers.arxiv.requests.get", return_value=mock_response):
        results = provider.search("transformer")

    assert len(results) == 1
    result = results[0]
    assert result.title == "Attention Is All You Need"
    assert result.authors == ["Ashish Vaswani", "Noam Shazeer"]
    assert result.year == 2017
    assert result.doi == "arxiv:1706.03762v5"
    assert result.source == "arxiv"
    assert result.source_id == "1706.03762v5"
    assert result.citations == 0
    assert result.references == []


def test_arxiv_provider_get_by_id_uses_id_list(mock_arxiv_response):
    provider = ArxivProvider()
    mock_response = MagicMock()
    mock_response.content = mock_arxiv_response.encode("utf-8")
    mock_response.raise_for_status.return_value = None

    with patch("crane.providers.arxiv.requests.get", return_value=mock_response) as mock_get:
        result = provider.get_by_id("1706.03762v5")

    assert result is not None
    assert result.source_id == "1706.03762v5"
    assert mock_get.call_args.kwargs["params"] == {"id_list": "1706.03762v5"}


def test_arxiv_provider_get_by_doi_supports_arxiv_doi_shortcut():
    provider = ArxivProvider()
    expected = UnifiedMetadata(
        title="Paper A",
        authors=["Author A"],
        year=2024,
        doi="arxiv:paper-a",
        abstract="A",
        source="arxiv",
        source_id="paper-a",
        url="https://example.com/a",
        pdf_url="https://example.com/a.pdf",
        citations=0,
        references=[],
    )

    with patch.object(provider, "get_by_id", return_value=expected) as mock_get_by_id:
        result = provider.get_by_doi("arxiv:paper-a")

    assert result == expected
    mock_get_by_id.assert_called_once_with("paper-a")
