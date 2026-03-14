"""
TDD tests for reference management tools.
RED phase: define expected behavior before implementation.

These tests verify the MCP tool functions directly,
mocking the filesystem via tmp_project fixture.
"""

import pytest

from crane.models.paper import AiAnnotations, Paper
from crane.tools.references import register_tools
from crane.utils.bibtex import append_entry, read_entries
from crane.utils.yaml_io import read_paper_yaml, write_paper_yaml

# To test the tool functions, we register them on a mock MCP and extract them.
# This pattern allows testing tool logic without a running MCP server.


class _ToolCollector:
    """Minimal mock MCP server that collects registered tools."""

    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


@pytest.fixture
def ref_tools():
    collector = _ToolCollector()
    register_tools(collector)
    return collector.tools


class TestAddReference:
    def test_registered(self, ref_tools):
        assert "add_reference" in ref_tools

    def test_creates_yaml_file(self, ref_tools, tmp_project):
        refs_dir = str(tmp_project / "references")
        result = ref_tools["add_reference"](
            key="vaswani2017-attention",
            title="Attention Is All You Need",
            authors=["Ashish Vaswani", "Noam Shazeer"],
            year=2017,
            venue="NeurIPS",
            refs_dir=refs_dir,
        )

        assert "Added reference" in result
        paper_data = read_paper_yaml(
            str(tmp_project / "references" / "papers"), "vaswani2017-attention"
        )
        assert paper_data is not None
        assert paper_data["title"] == "Attention Is All You Need"

    def test_appends_to_bibtex(self, ref_tools, tmp_project):
        refs_dir = str(tmp_project / "references")
        ref_tools["add_reference"](
            key="vaswani2017-attention",
            title="Attention Is All You Need",
            authors=["Ashish Vaswani"],
            year=2017,
            doi="10.48550/arXiv.1706.03762",
            venue="NeurIPS",
            paper_type="conference",
            refs_dir=refs_dir,
        )

        entries = read_entries(str(tmp_project / "references" / "bibliography.bib"))
        assert len(entries) == 1
        assert entries[0]["key"] == "vaswani2017-attention"


class TestListReferences:
    def test_registered(self, ref_tools):
        assert "list_references" in ref_tools

    def test_empty_returns_empty_list(self, ref_tools, tmp_project):
        refs_dir = str(tmp_project / "references")
        results = ref_tools["list_references"](refs_dir=refs_dir)
        assert results == []

    def test_returns_summary_fields(
        self, ref_tools, tmp_project, sample_paper_dict, sample_paper_dict_2
    ):
        papers_dir = str(tmp_project / "references" / "papers")
        write_paper_yaml(papers_dir, sample_paper_dict["key"], sample_paper_dict)
        write_paper_yaml(papers_dir, sample_paper_dict_2["key"], sample_paper_dict_2)

        results = ref_tools["list_references"](refs_dir=str(tmp_project / "references"))

        assert len(results) == 2
        assert set(results[0].keys()) == {"key", "title", "authors", "year", "venue"}

    def test_filter_by_keyword(
        self, ref_tools, tmp_project, sample_paper_dict, sample_paper_dict_2
    ):
        papers_dir = str(tmp_project / "references" / "papers")
        write_paper_yaml(papers_dir, sample_paper_dict["key"], sample_paper_dict)
        write_paper_yaml(papers_dir, sample_paper_dict_2["key"], sample_paper_dict_2)

        results = ref_tools["list_references"](
            filter_keyword="few-shot",
            refs_dir=str(tmp_project / "references"),
        )

        assert len(results) == 1
        assert results[0]["key"] == "brown2020-gpt3"

    def test_filter_by_tag(self, ref_tools, tmp_project, sample_paper_dict, sample_paper_dict_2):
        p1 = Paper.from_yaml_dict(sample_paper_dict)
        p1.ai_annotations = AiAnnotations(tags=["transformers", "foundational"])
        p2 = Paper.from_yaml_dict(sample_paper_dict_2)
        p2.ai_annotations = AiAnnotations(tags=["llm"])

        papers_dir = str(tmp_project / "references" / "papers")
        write_paper_yaml(papers_dir, p1.key, p1.to_yaml_dict())
        write_paper_yaml(papers_dir, p2.key, p2.to_yaml_dict())

        results = ref_tools["list_references"](
            filter_tag="llm",
            refs_dir=str(tmp_project / "references"),
        )

        assert len(results) == 1
        assert results[0]["key"] == "brown2020-gpt3"


class TestGetReference:
    def test_registered(self, ref_tools):
        assert "get_reference" in ref_tools

    def test_returns_full_data(self, ref_tools, tmp_project, sample_paper_dict):
        p = Paper.from_yaml_dict(sample_paper_dict)
        p.ai_annotations = AiAnnotations(summary="A landmark NLP paper")
        papers_dir = str(tmp_project / "references" / "papers")
        write_paper_yaml(papers_dir, p.key, p.to_yaml_dict())

        result = ref_tools["get_reference"](p.key, refs_dir=str(tmp_project / "references"))

        assert result["key"] == "vaswani2017-attention"
        assert result["abstract"]
        assert result["ai_annotations"]["summary"] == "A landmark NLP paper"

    def test_nonexistent_key(self, ref_tools, tmp_project):
        with pytest.raises(ValueError, match="Reference not found"):
            ref_tools["get_reference"]("missing-key", refs_dir=str(tmp_project / "references"))


class TestSearchReferences:
    def test_registered(self, ref_tools):
        assert "search_references" in ref_tools

    def test_matches_title(self, ref_tools, tmp_project, sample_paper_dict, sample_paper_dict_2):
        papers_dir = str(tmp_project / "references" / "papers")
        write_paper_yaml(papers_dir, sample_paper_dict["key"], sample_paper_dict)
        write_paper_yaml(papers_dir, sample_paper_dict_2["key"], sample_paper_dict_2)

        results = ref_tools["search_references"](
            "few-shot learners",
            refs_dir=str(tmp_project / "references"),
        )

        assert len(results) == 1
        assert results[0]["key"] == "brown2020-gpt3"

    def test_matches_abstract(self, ref_tools, tmp_project, sample_paper_dict, sample_paper_dict_2):
        papers_dir = str(tmp_project / "references" / "papers")
        write_paper_yaml(papers_dir, sample_paper_dict["key"], sample_paper_dict)
        write_paper_yaml(papers_dir, sample_paper_dict_2["key"], sample_paper_dict_2)

        results = ref_tools["search_references"](
            "complex recurrent",
            refs_dir=str(tmp_project / "references"),
        )

        assert len(results) == 1
        assert results[0]["key"] == "vaswani2017-attention"

    def test_no_match_returns_empty(self, ref_tools, tmp_project, sample_paper_dict):
        papers_dir = str(tmp_project / "references" / "papers")
        write_paper_yaml(papers_dir, sample_paper_dict["key"], sample_paper_dict)

        results = ref_tools["search_references"](
            "graph neural tangent kernel",
            refs_dir=str(tmp_project / "references"),
        )
        assert results == []


class TestRemoveReference:
    def test_registered(self, ref_tools):
        assert "remove_reference" in ref_tools

    def test_removes_yaml(self, ref_tools, tmp_project, sample_paper_dict):
        papers_dir = str(tmp_project / "references" / "papers")
        write_paper_yaml(papers_dir, sample_paper_dict["key"], sample_paper_dict)

        ref_tools["remove_reference"](
            sample_paper_dict["key"],
            refs_dir=str(tmp_project / "references"),
        )
        assert read_paper_yaml(papers_dir, sample_paper_dict["key"]) is None

    def test_removes_bibtex_entry(self, ref_tools, tmp_project, sample_paper_dict):
        papers_dir = str(tmp_project / "references" / "papers")
        write_paper_yaml(papers_dir, sample_paper_dict["key"], sample_paper_dict)
        append_entry(
            str(tmp_project / "references" / "bibliography.bib"),
            Paper.from_yaml_dict(sample_paper_dict).to_bibtex(),
        )

        ref_tools["remove_reference"](
            sample_paper_dict["key"],
            refs_dir=str(tmp_project / "references"),
        )
        entries = read_entries(str(tmp_project / "references" / "bibliography.bib"))
        assert entries == []

    def test_optionally_removes_pdf(self, ref_tools, tmp_project, sample_paper_dict):
        pdf_path = tmp_project / "references" / "pdfs" / "vaswani2017-attention.pdf"
        pdf_path.write_text("dummy", encoding="utf-8")

        data = sample_paper_dict.copy()
        data["pdf_path"] = str(pdf_path)
        papers_dir = str(tmp_project / "references" / "papers")
        write_paper_yaml(papers_dir, data["key"], data)

        ref_tools["remove_reference"](
            data["key"],
            delete_pdf=True,
            refs_dir=str(tmp_project / "references"),
        )
        assert not pdf_path.exists()


class TestAnnotateReference:
    def test_registered(self, ref_tools):
        assert "annotate_reference" in ref_tools

    def test_writes_annotations(self, ref_tools, tmp_project, sample_paper_dict):
        papers_dir = str(tmp_project / "references" / "papers")
        write_paper_yaml(papers_dir, sample_paper_dict["key"], sample_paper_dict)

        ref_tools["annotate_reference"](
            key=sample_paper_dict["key"],
            summary="Foundational transformer architecture paper",
            key_contributions=["Self-attention", "Parallelizable training"],
            methodology="Encoder-decoder transformer",
            relevance_notes="Core baseline for modern LLMs",
            tags=["transformer", "nlp"],
            related_issues=[12],
            refs_dir=str(tmp_project / "references"),
        )

        data = read_paper_yaml(papers_dir, sample_paper_dict["key"])
        assert data is not None
        assert data["ai_annotations"]["summary"] == "Foundational transformer architecture paper"
        assert data["ai_annotations"]["tags"] == ["transformer", "nlp"]
        assert data["ai_annotations"]["related_issues"] == [12]

    def test_updates_existing_annotations(self, ref_tools, tmp_project, sample_paper_dict):
        p = Paper.from_yaml_dict(sample_paper_dict)
        p.ai_annotations = AiAnnotations(
            summary="Old summary",
            methodology="Original method",
            tags=["old-tag"],
            related_issues=[1],
        )
        papers_dir = str(tmp_project / "references" / "papers")
        write_paper_yaml(papers_dir, p.key, p.to_yaml_dict())

        ref_tools["annotate_reference"](
            key=p.key,
            summary="Updated summary",
            tags=["updated-tag"],
            related_issues=[2, 3],
            refs_dir=str(tmp_project / "references"),
        )

        data = read_paper_yaml(papers_dir, p.key)
        assert data is not None
        assert data["ai_annotations"]["summary"] == "Updated summary"
        assert data["ai_annotations"]["tags"] == ["updated-tag"]
        assert data["ai_annotations"]["related_issues"] == [2, 3]
        assert data["ai_annotations"]["methodology"] == "Original method"
