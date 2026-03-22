"""Tests for PaperProvider abstraction layer."""

from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

import pytest


def _load_providers():
    return importlib.import_module("crane.providers")


def _load_base():
    return importlib.import_module("crane.providers.base")


def _load_arxiv():
    return importlib.import_module("crane.providers.arxiv")


def _load_registry():
    return importlib.import_module("crane.providers.registry")


class TestUnifiedMetadata:
    def test_creation_with_all_fields(self):
        base = _load_base()
        metadata = base.UnifiedMetadata(
            title="Attention Is All You Need",
            authors=["Vaswani", "Shazeer"],
            year=2017,
            doi="10.48550/arXiv.1706.03762",
            abstract="The dominant sequence transduction models.",
            source="arxiv",
            source_id="1706.03762",
            url="https://arxiv.org/abs/1706.03762",
            pdf_url="https://arxiv.org/pdf/1706.03762.pdf",
            citations=100000,
            references=["vaswani2017"],
        )
        assert metadata.title == "Attention Is All You Need"
        assert metadata.year == 2017
        assert metadata.source == "arxiv"


class TestPaperProviderABC:
    def test_cannot_instantiate(self):
        base = _load_base()
        with pytest.raises(TypeError):
            base.PaperProvider()


class TestArxivProvider:
    def test_name_property(self):
        arxiv = _load_arxiv()
        provider = arxiv.ArxivProvider()
        assert provider.name == "arxiv"

    def test_search_returns_list(self):
        arxiv = _load_arxiv()
        provider = arxiv.ArxivProvider()

        mock_response = MagicMock()
        mock_response.content = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v5</id>
    <title>Attention Is All You Need</title>
    <summary>Test abstract</summary>
    <published>2017-06-12T00:00:00Z</published>
    <author><name>Vaswani</name></author>
    <link title="pdf" type="application/pdf" href="http://arxiv.org/pdf/1706.03762v5"/>
  </entry>
</feed>"""
        mock_response.raise_for_status = MagicMock()

        with patch("crane.providers.arxiv.requests.get", return_value=mock_response):
            results = provider.search("transformer")

        assert isinstance(results, list)
        assert len(results) > 0
        assert results[0].source == "arxiv"


class TestProviderRegistry:
    def test_register_adds_provider(self):
        registry_mod = _load_registry()
        arxiv_mod = _load_arxiv()
        registry = registry_mod.ProviderRegistry()
        provider = arxiv_mod.ArxivProvider()

        registry.register(provider)
        assert "arxiv" in registry._providers

    def test_search_all_queries_all_providers(self):
        registry_mod = _load_registry()
        arxiv_mod = _load_arxiv()
        registry = registry_mod.ProviderRegistry()
        provider = arxiv_mod.ArxivProvider()
        registry.register(provider)

        mock_response = MagicMock()
        mock_response.content = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v5</id>
    <title>Test</title>
    <summary>Test</summary>
    <published>2017-01-01</published>
    <author><name>Author</name></author>
  </entry>
</feed>"""
        mock_response.raise_for_status = MagicMock()

        with patch("crane.providers.arxiv.requests.get", return_value=mock_response):
            results = registry.search_all("test")

        assert isinstance(results, list)
