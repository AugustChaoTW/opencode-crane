"""
TDD tests for paper search tools (arXiv API).
RED phase: define expected behavior before implementation.

arXiv API calls are mocked — no real network requests.
"""

from unittest.mock import MagicMock, patch

import pytest

from crane.tools.papers import register_tools


class _ToolCollector:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


@pytest.fixture
def paper_tools():
    collector = _ToolCollector()
    register_tools(collector)
    return collector.tools


class TestSearchPapers:
    def test_registered(self, paper_tools):
        assert "search_papers" in paper_tools

    def test_returns_list_of_dicts(self, paper_tools, mock_arxiv_response):
        mock_response = MagicMock()
        mock_response.content = mock_arxiv_response.encode("utf-8")
        mock_response.raise_for_status.return_value = None

        with patch("crane.services.paper_service.requests.get", return_value=mock_response):
            results = paper_tools["search_papers"]("transformer")

        assert isinstance(results, list)
        assert len(results) > 0
        assert isinstance(results[0], dict)

    def test_each_result_has_required_fields(self, paper_tools, mock_arxiv_response):
        """Each result must have: title, authors, abstract, doi, url, pdf_url, published_date."""
        mock_response = MagicMock()
        mock_response.content = mock_arxiv_response.encode("utf-8")
        mock_response.raise_for_status.return_value = None

        with patch("crane.services.paper_service.requests.get", return_value=mock_response):
            results = paper_tools["search_papers"]("transformer")

        required_fields = {
            "title",
            "authors",
            "abstract",
            "doi",
            "url",
            "pdf_url",
            "published_date",
            "categories",
            "paper_id",
        }
        assert required_fields.issubset(set(results[0].keys()))

    def test_respects_max_results(self, paper_tools, mock_arxiv_response):
        mock_response = MagicMock()
        mock_response.content = mock_arxiv_response.encode("utf-8")
        mock_response.raise_for_status.return_value = None

        with patch(
            "crane.services.paper_service.requests.get", return_value=mock_response
        ) as mock_get:
            paper_tools["search_papers"]("transformer", max_results=3)

        assert mock_get.call_args.kwargs["params"]["max_results"] == 3

    def test_invalid_source_raises(self, paper_tools):
        with pytest.raises(ValueError):
            paper_tools["search_papers"]("transformer", source="semantic_scholar")


class TestDownloadPaper:
    def test_registered(self, paper_tools):
        assert "download_paper" in paper_tools

    def test_returns_file_path(self, paper_tools, tmp_project):
        save_dir = tmp_project / "references" / "pdfs"
        mock_response = MagicMock()
        mock_response.content = b"fake pdf"
        mock_response.raise_for_status.return_value = None

        with patch("crane.services.paper_service.requests.get", return_value=mock_response):
            output_path = paper_tools["download_paper"]("1706.03762", save_dir=str(save_dir))

        assert isinstance(output_path, str)
        assert output_path.endswith("1706.03762.pdf")

    def test_creates_pdf_file(self, paper_tools, tmp_project):
        save_dir = tmp_project / "references" / "pdfs"
        mock_response = MagicMock()
        mock_response.content = b"fake pdf"
        mock_response.raise_for_status.return_value = None

        with patch("crane.services.paper_service.requests.get", return_value=mock_response):
            output_path = paper_tools["download_paper"]("1706.03762", save_dir=str(save_dir))

        assert (save_dir / "1706.03762.pdf").exists()
        assert (save_dir / "1706.03762.pdf").read_bytes() == b"fake pdf"
        assert output_path == str(save_dir / "1706.03762.pdf")

    def test_creates_save_dir_if_missing(self, paper_tools, tmp_path):
        save_dir = tmp_path / "new" / "pdfs"
        mock_response = MagicMock()
        mock_response.content = b"fake pdf"
        mock_response.raise_for_status.return_value = None

        with patch("crane.services.paper_service.requests.get", return_value=mock_response):
            output_path = paper_tools["download_paper"]("1706.03762", save_dir=str(save_dir))

        assert save_dir.exists()
        assert (save_dir / "1706.03762.pdf").exists()
        assert output_path == str(save_dir / "1706.03762.pdf")


class TestReadPaper:
    def test_registered(self, paper_tools):
        assert "read_paper" in paper_tools

    def test_returns_text_string(self, paper_tools, tmp_project):
        save_dir = tmp_project / "references" / "pdfs"
        (save_dir / "1706.03762.pdf").write_bytes(b"fake pdf")

        mock_reader = MagicMock()
        page_1 = MagicMock()
        page_1.extract_text.return_value = "page one"
        page_2 = MagicMock()
        page_2.extract_text.return_value = "page two"
        mock_reader.pages = [page_1, page_2]

        with patch("crane.services.paper_service.PyPDF2.PdfReader", return_value=mock_reader):
            text = paper_tools["read_paper"]("1706.03762", save_dir=str(save_dir))

        assert isinstance(text, str)
        assert "page one" in text
        assert "page two" in text

    def test_auto_downloads_if_missing(self, paper_tools, tmp_project):
        save_dir = tmp_project / "references" / "pdfs"

        mock_response = MagicMock()
        mock_response.content = b"fake pdf"
        mock_response.raise_for_status.return_value = None

        mock_reader = MagicMock()
        page = MagicMock()
        page.extract_text.return_value = "downloaded paper text"
        mock_reader.pages = [page]

        with patch(
            "crane.services.paper_service.requests.get", return_value=mock_response
        ) as mock_get:
            with patch("crane.services.paper_service.PyPDF2.PdfReader", return_value=mock_reader):
                text = paper_tools["read_paper"]("1706.03762", save_dir=str(save_dir))

        assert (save_dir / "1706.03762.pdf").exists()
        assert "downloaded paper text" in text
        assert mock_get.call_count == 1
