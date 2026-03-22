"""
Unit tests for PaperService.
Tests paper search, download, and read operations.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crane.services.paper_service import PaperService


@pytest.fixture
def paper_service():
    return PaperService()


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
    <arxiv:primary_category term="cs.CL" xmlns:arxiv="http://arxiv.org/schemas/atom"/>
    <category term="cs.CL"/>
  </entry>
</feed>"""


class TestPaperServiceSearch:
    """Test paper search functionality."""

    def test_search_returns_list(self, paper_service, mock_arxiv_response):
        mock_response = MagicMock()
        mock_response.content = mock_arxiv_response.encode("utf-8")
        mock_response.raise_for_status.return_value = None

        with patch("crane.services.paper_service.requests.get", return_value=mock_response):
            results = paper_service.search("transformer")

        assert isinstance(results, list)
        assert len(results) > 0

    def test_search_result_has_required_fields(self, paper_service, mock_arxiv_response):
        mock_response = MagicMock()
        mock_response.content = mock_arxiv_response.encode("utf-8")
        mock_response.raise_for_status.return_value = None

        with patch("crane.services.paper_service.requests.get", return_value=mock_response):
            results = paper_service.search("transformer")

        result = results[0]
        assert "title" in result
        assert "authors" in result
        assert "abstract" in result
        assert "doi" in result
        assert "url" in result
        assert "pdf_url" in result
        assert "published_date" in result
        assert "categories" in result
        assert "paper_id" in result

    def test_search_respects_max_results(self, paper_service, mock_arxiv_response):
        mock_response = MagicMock()
        mock_response.content = mock_arxiv_response.encode("utf-8")
        mock_response.raise_for_status.return_value = None

        with patch(
            "crane.services.paper_service.requests.get", return_value=mock_response
        ) as mock_get:
            paper_service.search("transformer", max_results=5)

        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["params"]["max_results"] == 5

    def test_search_invalid_source_raises(self, paper_service):
        with pytest.raises(ValueError, match="Unsupported source"):
            paper_service.search("transformer", source="invalid")


class TestPaperServiceDownload:
    """Test paper download functionality."""

    def test_download_creates_pdf(self, paper_service, tmp_path):
        save_dir = tmp_path / "pdfs"
        mock_response = MagicMock()
        mock_response.content = b"fake pdf content"
        mock_response.raise_for_status.return_value = None

        with patch("crane.services.paper_service.requests.get", return_value=mock_response):
            result = paper_service.download("1706.03762", save_dir)

        assert result.exists()
        assert result.read_bytes() == b"fake pdf content"
        assert result.name == "1706.03762.pdf"

    def test_download_creates_directory(self, paper_service, tmp_path):
        save_dir = tmp_path / "new" / "nested" / "dir"
        mock_response = MagicMock()
        mock_response.content = b"pdf"
        mock_response.raise_for_status.return_value = None

        with patch("crane.services.paper_service.requests.get", return_value=mock_response):
            paper_service.download("1706.03762", save_dir)

        assert save_dir.exists()

    def test_download_returns_path(self, paper_service, tmp_path):
        save_dir = tmp_path / "pdfs"
        mock_response = MagicMock()
        mock_response.content = b"pdf"
        mock_response.raise_for_status.return_value = None

        with patch("crane.services.paper_service.requests.get", return_value=mock_response):
            result = paper_service.download("1706.03762", save_dir)

        assert isinstance(result, Path)
        assert str(result).endswith("1706.03762.pdf")


class TestPaperServiceRead:
    """Test paper read functionality."""

    def test_read_existing_pdf(self, paper_service, tmp_path):
        save_dir = tmp_path / "pdfs"
        save_dir.mkdir(parents=True)
        (save_dir / "1706.03762.pdf").write_bytes(b"fake pdf")

        mock_reader = MagicMock()
        page = MagicMock()
        page.extract_text.return_value = "Extracted text content"
        mock_reader.pages = [page]

        with patch("crane.services.paper_service.PyPDF2.PdfReader", return_value=mock_reader):
            text = paper_service.read("1706.03762", save_dir)

        assert text == "Extracted text content"

    def test_read_auto_downloads_if_missing(self, paper_service, tmp_path):
        save_dir = tmp_path / "pdfs"

        mock_response = MagicMock()
        mock_response.content = b"downloaded pdf"
        mock_response.raise_for_status.return_value = None

        mock_reader = MagicMock()
        page = MagicMock()
        page.extract_text.return_value = "Downloaded content"
        mock_reader.pages = [page]

        with patch("crane.services.paper_service.requests.get", return_value=mock_response):
            with patch("crane.services.paper_service.PyPDF2.PdfReader", return_value=mock_reader):
                text = paper_service.read("1706.03762", save_dir)

        assert text == "Downloaded content"
        assert (save_dir / "1706.03762.pdf").exists()

    def test_read_multiple_pages(self, paper_service, tmp_path):
        save_dir = tmp_path / "pdfs"
        save_dir.mkdir(parents=True)
        (save_dir / "1706.03762.pdf").write_bytes(b"pdf")

        mock_reader = MagicMock()
        page1 = MagicMock()
        page1.extract_text.return_value = "Page 1"
        page2 = MagicMock()
        page2.extract_text.return_value = "Page 2"
        mock_reader.pages = [page1, page2]

        with patch("crane.services.paper_service.PyPDF2.PdfReader", return_value=mock_reader):
            text = paper_service.read("1706.03762", save_dir)

        assert "Page 1" in text
        assert "Page 2" in text
