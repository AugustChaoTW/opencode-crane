from __future__ import annotations

from importlib import import_module
from pathlib import Path
from unittest.mock import MagicMock, patch

pytest = import_module("pytest")
requests = import_module("requests")

alphaxiv_module = import_module("crane.providers.alphaxiv")
paper_service_module = import_module("crane.services.paper_service")
pdf_chunker_module = import_module("crane.services.pdf_chunker")

ALPHAXIV_RETRY_DELAY = alphaxiv_module.ALPHAXIV_RETRY_DELAY
AlphaXivOverview = alphaxiv_module.AlphaXivOverview
AlphaXivProvider = alphaxiv_module.AlphaXivProvider
PaperService = paper_service_module.PaperService
PDFChunker = pdf_chunker_module.PDFChunker


class TestAlphaXivOverview:
    def test_creation_success(self) -> None:
        overview = AlphaXivOverview(
            arxiv_id="1706.03762",
            version_id="v5",
            title="Attention",
            abstract="Abstract text",
            overview="Overview text",
            summary="Summary text",
            citations_bibtex="@article{a}",
        )
        assert overview.arxiv_id == "1706.03762"
        assert overview.source == "alphaxiv"
        assert overview.language == "en"

    def test_creation_rejects_empty_arxiv_id(self) -> None:
        with pytest.raises(ValueError, match="arxiv_id cannot be empty"):
            AlphaXivOverview(
                arxiv_id="",
                version_id="v1",
                title="Title",
                abstract="Abs",
                overview="Body",
                summary="Sum",
                citations_bibtex="",
            )

    def test_to_markdown_includes_all_sections(self) -> None:
        overview = AlphaXivOverview(
            arxiv_id="id",
            version_id="v",
            title="Paper",
            abstract="A",
            overview="O",
            summary="S",
            citations_bibtex="",
        )
        markdown = overview.to_markdown()
        assert markdown.startswith("# Paper")
        assert "## Abstract\nA" in markdown
        assert "## Overview\nO" in markdown
        assert "## Summary\nS" in markdown

    def test_to_markdown_skips_empty_overview(self) -> None:
        overview = AlphaXivOverview(
            arxiv_id="id",
            version_id="v",
            title="Paper",
            abstract="A",
            overview="",
            summary="S",
            citations_bibtex="",
        )
        markdown = overview.to_markdown()
        assert "## Overview" not in markdown
        assert "## Summary" in markdown

    def test_to_markdown_skips_empty_summary(self) -> None:
        overview = AlphaXivOverview(
            arxiv_id="id",
            version_id="v",
            title="Paper",
            abstract="A",
            overview="O",
            summary="",
            citations_bibtex="",
        )
        markdown = overview.to_markdown()
        assert "## Overview" in markdown
        assert "## Summary" not in markdown


class TestAlphaXivProviderBasics:
    def test_name_property(self) -> None:
        provider = AlphaXivProvider()
        assert provider.name == "alphaxiv"

    def test_init_with_auth_token_sets_authorization_header(self) -> None:
        provider = AlphaXivProvider(auth_token="token123")
        assert provider._session.headers["Authorization"] == "Bearer token123"

    def test_init_without_auth_token_has_no_authorization_header(self) -> None:
        provider = AlphaXivProvider()
        assert "Authorization" not in provider._session.headers

    @pytest.mark.parametrize("max_results", [1, 10, 100])
    def test_search_returns_empty_not_supported(self, max_results: int) -> None:
        provider = AlphaXivProvider()
        assert provider.search("transformer", max_results=max_results) == []

    def test_get_by_doi_returns_none(self) -> None:
        provider = AlphaXivProvider()
        assert provider.get_by_doi("10.1000/test") is None


class TestAlphaXivProviderOverview:
    def test_get_overview_returns_none_when_resolve_missing(self) -> None:
        provider = AlphaXivProvider()
        with patch.object(provider, "_resolve_paper", return_value=None):
            assert provider.get_overview("1706.03762") is None

    def test_get_overview_returns_none_without_version_id(self) -> None:
        provider = AlphaXivProvider()
        with patch.object(provider, "_resolve_paper", return_value={"title": "Paper"}):
            assert provider.get_overview("1706.03762") is None

    def test_get_overview_returns_none_when_overview_api_returns_none(self) -> None:
        provider = AlphaXivProvider()
        with patch.object(provider, "_resolve_paper", return_value={"versionId": "v1"}):
            with patch.object(provider, "_fetch_overview", return_value=None):
                assert provider.get_overview("1706.03762") is None

    def test_get_overview_returns_none_when_overview_field_missing(self) -> None:
        provider = AlphaXivProvider()
        with patch.object(provider, "_resolve_paper", return_value={"versionId": "v1"}):
            with patch.object(provider, "_fetch_overview", return_value={"title": "T"}):
                assert provider.get_overview("1706.03762") is None

    def test_get_overview_success_prefers_overview_title_and_abstract(self) -> None:
        provider = AlphaXivProvider()
        with patch.object(
            provider,
            "_resolve_paper",
            return_value={"versionId": "v1", "title": "Paper title", "abstract": "Paper abs"},
        ):
            with patch.object(
                provider,
                "_fetch_overview",
                return_value={
                    "title": "Overview title",
                    "abstract": "Overview abs",
                    "overview": "Long overview",
                    "summary": "Short summary",
                    "citationBibtex": "@article{x}",
                },
            ):
                result = provider.get_overview("1706.03762", language="en")

        assert result is not None
        assert result.version_id == "v1"
        assert result.title == "Overview title"
        assert result.abstract == "Overview abs"
        assert result.overview == "Long overview"

    def test_get_overview_success_falls_back_to_resolved_title_and_abstract(self) -> None:
        provider = AlphaXivProvider()
        with patch.object(
            provider,
            "_resolve_paper",
            return_value={"versionId": "v1", "title": "Paper title", "abstract": "Paper abs"},
        ):
            with patch.object(
                provider,
                "_fetch_overview",
                return_value={
                    "overview": "Long overview",
                    "summary": "Short summary",
                },
            ):
                result = provider.get_overview("1706.03762", language="zh")

        assert result is not None
        assert result.language == "zh"
        assert result.title == "Paper title"
        assert result.abstract == "Paper abs"


class TestAlphaXivProviderRequestRetry:
    def _response(self, status_code: int, payload: object | None = None) -> MagicMock:
        response = MagicMock()
        response.status_code = status_code
        response.json.return_value = payload if payload is not None else {}
        return response

    def test_request_with_retry_returns_payload_on_200_dict(self) -> None:
        provider = AlphaXivProvider()
        provider._session.get = MagicMock(return_value=self._response(200, {"ok": True}))
        assert provider._request_with_retry("https://example") == {"ok": True}

    def test_request_with_retry_returns_none_on_200_non_dict_payload(self) -> None:
        provider = AlphaXivProvider()
        provider._session.get = MagicMock(return_value=self._response(200, ["not", "dict"]))
        assert provider._request_with_retry("https://example") is None

    def test_request_with_retry_returns_none_on_404_without_retry(self) -> None:
        provider = AlphaXivProvider()
        provider._session.get = MagicMock(return_value=self._response(404))
        with patch("crane.providers.alphaxiv.time.sleep") as sleep_mock:
            assert provider._request_with_retry("https://example") is None
        assert provider._session.get.call_count == 1
        sleep_mock.assert_not_called()

    def test_request_with_retry_retries_429_then_succeeds(self) -> None:
        provider = AlphaXivProvider()
        provider._session.get = MagicMock(
            side_effect=[
                self._response(429),
                self._response(429),
                self._response(200, {"ok": "done"}),
            ]
        )
        with patch("crane.providers.alphaxiv.time.sleep") as sleep_mock:
            result = provider._request_with_retry("https://example")

        assert result == {"ok": "done"}
        assert provider._session.get.call_count == 3
        assert sleep_mock.call_args_list[0].args[0] == ALPHAXIV_RETRY_DELAY
        assert sleep_mock.call_args_list[1].args[0] == ALPHAXIV_RETRY_DELAY * 2

    def test_request_with_retry_gives_up_after_max_429_retries(self) -> None:
        provider = AlphaXivProvider()
        provider._session.get = MagicMock(
            side_effect=[self._response(429), self._response(429), self._response(429)]
        )
        with patch("crane.providers.alphaxiv.time.sleep") as sleep_mock:
            result = provider._request_with_retry("https://example")

        assert result is None
        assert provider._session.get.call_count == 3
        assert sleep_mock.call_count == 3

    def test_request_with_retry_retries_500_then_succeeds(self) -> None:
        provider = AlphaXivProvider()
        provider._session.get = MagicMock(
            side_effect=[self._response(500), self._response(200, {"ok": 1})]
        )
        with patch("crane.providers.alphaxiv.time.sleep") as sleep_mock:
            result = provider._request_with_retry("https://example")

        assert result == {"ok": 1}
        assert provider._session.get.call_count == 2
        sleep_mock.assert_called_once_with(ALPHAXIV_RETRY_DELAY)

    def test_request_with_retry_gives_up_after_max_5xx_retries(self) -> None:
        provider = AlphaXivProvider()
        provider._session.get = MagicMock(
            side_effect=[self._response(503), self._response(500), self._response(502)]
        )
        with patch("crane.providers.alphaxiv.time.sleep") as sleep_mock:
            result = provider._request_with_retry("https://example")

        assert result is None
        assert provider._session.get.call_count == 3
        assert sleep_mock.call_count == 3

    def test_request_with_retry_retries_on_request_exception_then_succeeds(self) -> None:
        provider = AlphaXivProvider()
        provider._session.get = MagicMock(
            side_effect=[
                requests.Timeout("timeout"),
                self._response(200, {"ok": True}),
            ]
        )
        with patch("crane.providers.alphaxiv.time.sleep") as sleep_mock:
            result = provider._request_with_retry("https://example")

        assert result == {"ok": True}
        assert provider._session.get.call_count == 2
        sleep_mock.assert_called_once_with(ALPHAXIV_RETRY_DELAY)

    def test_request_with_retry_gives_up_on_request_exception_after_max_attempts(self) -> None:
        provider = AlphaXivProvider()
        provider._session.get = MagicMock(
            side_effect=[
                requests.RequestException("e1"),
                requests.RequestException("e2"),
                requests.RequestException("e3"),
            ]
        )
        with patch("crane.providers.alphaxiv.time.sleep") as sleep_mock:
            result = provider._request_with_retry("https://example")

        assert result is None
        assert provider._session.get.call_count == 3
        assert sleep_mock.call_count == 2


class TestAlphaXivProviderGetById:
    def test_get_by_id_returns_none_when_missing(self) -> None:
        provider = AlphaXivProvider()
        with patch.object(provider, "_resolve_paper", return_value=None):
            assert provider.get_by_id("1706.03762") is None

    def test_get_by_id_maps_string_authors_and_year(self) -> None:
        provider = AlphaXivProvider()
        with patch.object(
            provider,
            "_resolve_paper",
            return_value={
                "title": "Paper",
                "authors": ["Alice", "Bob"],
                "publishedDate": "2021-01-01",
                "abstract": "Abs",
            },
        ):
            result = provider.get_by_id("1706.03762")

        assert result is not None
        assert result.title == "Paper"
        assert result.authors == ["Alice", "Bob"]
        assert result.year == 2021
        assert result.source == "alphaxiv"

    def test_get_by_id_maps_dict_authors_and_filters_empty(self) -> None:
        provider = AlphaXivProvider()
        with patch.object(
            provider,
            "_resolve_paper",
            return_value={
                "title": "Paper",
                "authors": [{"name": "Alice"}, {"name": ""}, {"no": "name"}],
                "publishedDate": "2024-05-09",
                "abstract": "Abs",
            },
        ):
            result = provider.get_by_id("1706.03762")

        assert result is not None
        assert result.authors == ["Alice"]
        assert result.year == 2024

    @pytest.mark.parametrize("published_date", ["", "abcd", "20", "-01-01"])
    def test_get_by_id_uses_year_zero_for_invalid_published_date(self, published_date: str) -> None:
        provider = AlphaXivProvider()
        with patch.object(
            provider,
            "_resolve_paper",
            return_value={"title": "Paper", "authors": [], "publishedDate": published_date},
        ):
            result = provider.get_by_id("1706.03762")

        assert result is not None
        assert result.year == 0


class TestPaperServiceReadStructured:
    def test_read_structured_cache_hit_skips_provider_and_pdf(self, tmp_path: Path) -> None:
        service = PaperService()
        save_dir = tmp_path / "pdfs"
        save_dir.mkdir(parents=True)
        cache_file = tmp_path / "overviews" / "1706.03762.md"
        cache_file.parent.mkdir(parents=True)
        cache_file.write_text("cached markdown", encoding="utf-8")

        with patch("crane.providers.alphaxiv.AlphaXivProvider") as provider_cls:
            with patch.object(service, "read") as read_mock:
                out = service.read_structured("1706.03762", save_dir=save_dir)

        assert out == "cached markdown"
        provider_cls.assert_not_called()
        read_mock.assert_not_called()

    def test_read_structured_alphaxiv_success_writes_cache(self, tmp_path: Path) -> None:
        service = PaperService()
        save_dir = tmp_path / "pdfs"
        save_dir.mkdir(parents=True)

        overview = AlphaXivOverview(
            arxiv_id="1706.03762",
            version_id="v1",
            title="Paper",
            abstract="Abs",
            overview="Overview",
            summary="Summary",
            citations_bibtex="",
        )
        with patch("crane.providers.alphaxiv.AlphaXivProvider.get_overview", return_value=overview):
            with patch.object(service, "read") as read_mock:
                out = service.read_structured("1706.03762", save_dir=save_dir)

        assert "## Overview" in out
        read_mock.assert_not_called()
        cached = (tmp_path / "overviews" / "1706.03762.md").read_text(encoding="utf-8")
        assert cached == out

    def test_read_structured_falls_back_when_alphaxiv_unavailable(self, tmp_path: Path) -> None:
        service = PaperService()
        save_dir = tmp_path / "pdfs"
        save_dir.mkdir(parents=True)

        with patch("crane.providers.alphaxiv.AlphaXivProvider.get_overview", return_value=None):
            with patch.object(service, "read", return_value="pdf text") as read_mock:
                out = service.read_structured("1706.03762", save_dir=save_dir)

        assert out == "pdf text"
        read_mock.assert_called_once_with("1706.03762", save_dir)

    def test_read_structured_falls_back_when_alphaxiv_raises(self, tmp_path: Path) -> None:
        service = PaperService()
        save_dir = tmp_path / "pdfs"
        save_dir.mkdir(parents=True)

        with patch(
            "crane.providers.alphaxiv.AlphaXivProvider.get_overview",
            side_effect=RuntimeError("boom"),
        ):
            with patch.object(service, "read", return_value="pdf fallback") as read_mock:
                out = service.read_structured("1706.03762", save_dir=save_dir)

        assert out == "pdf fallback"
        read_mock.assert_called_once_with("1706.03762", save_dir)

    def test_read_structured_uses_sanitized_cache_filename(self, tmp_path: Path) -> None:
        service = PaperService()
        save_dir = tmp_path / "pdfs"
        save_dir.mkdir(parents=True)

        overview = AlphaXivOverview(
            arxiv_id="cs/1234",
            version_id="v1",
            title="Paper",
            abstract="Abs",
            overview="Overview",
            summary="Summary",
            citations_bibtex="",
        )
        with patch("crane.providers.alphaxiv.AlphaXivProvider.get_overview", return_value=overview):
            service.read_structured("cs/1234", save_dir=save_dir)

        assert (tmp_path / "overviews" / "cs_1234.md").exists()


class TestPDFChunkerStructured:
    def test_chunk_structured_splits_by_heading(self, tmp_path: Path) -> None:
        chunker = PDFChunker(refs_dir=tmp_path)
        markdown = "# Title\n\n## Abstract\nA text\n\n## Method\nM text"
        chunks = chunker.chunk_structured("p1", markdown)

        assert len(chunks) == 2
        assert chunks[0]["section_title"] == "Abstract"
        assert chunks[1]["section_title"] == "Method"
        assert all(chunk["page"] == 0 for chunk in chunks)

    def test_chunk_structured_skips_empty_and_heading_only_sections(self, tmp_path: Path) -> None:
        chunker = PDFChunker(refs_dir=tmp_path)
        markdown = "## Empty\n\n## Filled\ncontent\n\n## HeadingOnly"
        chunks = chunker.chunk_structured("p1", markdown)

        assert len(chunks) == 1
        assert chunks[0]["section_title"] == "Filled"

    def test_chunk_structured_handles_malformed_markdown(self, tmp_path: Path) -> None:
        chunker = PDFChunker(refs_dir=tmp_path)
        markdown = "Unheaded block\nwith two lines"
        chunks = chunker.chunk_structured("p1", markdown)

        assert len(chunks) == 1
        assert chunks[0]["section_title"] == "Unheaded block"
        assert chunks[0]["word_count"] == 3

    def test_chunk_structured_returns_empty_on_empty_input(self, tmp_path: Path) -> None:
        chunker = PDFChunker(refs_dir=tmp_path)
        assert chunker.chunk_structured("p1", "") == []

    def test_chunk_structured_word_count_excludes_heading(self, tmp_path: Path) -> None:
        chunker = PDFChunker(refs_dir=tmp_path)
        markdown = "## Results\none two three"
        chunks = chunker.chunk_structured("p1", markdown)

        assert len(chunks) == 1
        assert chunks[0]["word_count"] == 3
