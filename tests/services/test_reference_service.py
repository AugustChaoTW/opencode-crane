"""
Unit tests for ReferenceService.
Tests reference CRUD operations with YAML + BibTeX persistence.
"""

from __future__ import annotations

import pytest

from crane.services.reference_service import ReferenceService


@pytest.fixture
def refs_dir(tmp_path):
    """Create a temporary references directory."""
    refs = tmp_path / "references"
    (refs / "papers").mkdir(parents=True)
    (refs / "pdfs").mkdir(parents=True)
    (refs / "bibliography.bib").write_text("", encoding="utf-8")
    return refs


@pytest.fixture
def reference_service(refs_dir):
    return ReferenceService(refs_dir)


@pytest.fixture
def sample_paper_data():
    return {
        "key": "vaswani2017-attention",
        "title": "Attention Is All You Need",
        "authors": ["Vaswani", "Shazeer"],
        "year": 2017,
        "doi": "10.48550/arXiv.1706.03762",
        "venue": "NeurIPS",
        "url": "https://arxiv.org/abs/1706.03762",
        "pdf_url": "https://arxiv.org/pdf/1706.03762.pdf",
        "abstract": "The dominant sequence transduction models.",
        "source": "arxiv",
        "paper_type": "conference",
        "categories": ["cs.CL"],
        "keywords": ["transformer", "attention"],
    }


class TestReferenceServiceAdd:
    """Test adding references."""

    def test_add_creates_yaml_file(self, reference_service, refs_dir, sample_paper_data):
        reference_service.add(**sample_paper_data)

        yaml_path = refs_dir / "papers" / "vaswani2017-attention.yaml"
        assert yaml_path.exists()

    def test_add_appends_to_bibtex(self, reference_service, refs_dir, sample_paper_data):
        reference_service.add(**sample_paper_data)

        bib_content = (refs_dir / "bibliography.bib").read_text()
        assert "vaswani2017-attention" in bib_content

    def test_add_returns_confirmation(self, reference_service, sample_paper_data):
        result = reference_service.add(**sample_paper_data)
        assert "vaswani2017-attention" in result


class TestReferenceServiceList:
    """Test listing references."""

    def test_list_empty_returns_empty(self, reference_service):
        result = reference_service.list()
        assert result == []

    def test_list_returns_added_references(self, reference_service, sample_paper_data):
        reference_service.add(**sample_paper_data)

        result = reference_service.list()
        assert len(result) == 1
        assert result[0]["key"] == "vaswani2017-attention"

    def test_list_filter_by_keyword(self, reference_service, sample_paper_data):
        reference_service.add(**sample_paper_data)

        result = reference_service.list(filter_keyword="attention")
        assert len(result) == 1

        result = reference_service.list(filter_keyword="nonexistent")
        assert len(result) == 0

    def test_list_respects_limit(self, reference_service, sample_paper_data):
        reference_service.add(**sample_paper_data)

        result = reference_service.list(limit=0)
        assert result == []


class TestReferenceServiceGet:
    """Test getting single reference."""

    def test_get_existing(self, reference_service, sample_paper_data):
        reference_service.add(**sample_paper_data)

        result = reference_service.get("vaswani2017-attention")
        assert result["title"] == "Attention Is All You Need"

    def test_get_nonexistent_raises(self, reference_service):
        with pytest.raises(ValueError, match="Reference not found"):
            reference_service.get("nonexistent2024")


class TestReferenceServiceSearch:
    """Test searching references."""

    def test_search_finds_by_title(self, reference_service, sample_paper_data):
        reference_service.add(**sample_paper_data)

        result = reference_service.search("attention")
        assert len(result) == 1

    def test_search_finds_by_author(self, reference_service, sample_paper_data):
        reference_service.add(**sample_paper_data)

        result = reference_service.search("Vaswani")
        assert len(result) == 1

    def test_search_empty_query_returns_empty(self, reference_service, sample_paper_data):
        reference_service.add(**sample_paper_data)

        result = reference_service.search("")
        assert result == []


class TestReferenceServiceRemove:
    """Test removing references."""

    def test_remove_existing(self, reference_service, sample_paper_data, refs_dir):
        reference_service.add(**sample_paper_data)

        result = reference_service.remove("vaswani2017-attention")

        yaml_path = refs_dir / "papers" / "vaswani2017-attention.yaml"
        assert not yaml_path.exists()
        assert "Removed" in result

    def test_remove_nonexistent(self, reference_service):
        result = reference_service.remove("nonexistent2024")
        assert "not found" in result

    def test_remove_with_pdf(self, reference_service, sample_paper_data, refs_dir):
        reference_service.add(**sample_paper_data)
        pdf_path = refs_dir / "pdfs" / "vaswani2017-attention.pdf"
        pdf_path.write_bytes(b"pdf")

        reference_service.remove("vaswani2017-attention", delete_pdf=True)

        assert not pdf_path.exists()


class TestReferenceServiceAnnotate:
    """Test annotating references."""

    def test_annotate_adds_summary(self, reference_service, sample_paper_data):
        reference_service.add(**sample_paper_data)

        reference_service.annotate(
            key="vaswani2017-attention",
            summary="A groundbreaking paper on transformers.",
        )

        result = reference_service.get("vaswani2017-attention")
        assert result["ai_annotations"]["summary"] == "A groundbreaking paper on transformers."

    def test_annotate_nonexistent_raises(self, reference_service):
        with pytest.raises(ValueError, match="Reference not found"):
            reference_service.annotate(key="nonexistent2024", summary="test")

    def test_annotate_appends_key_contributions(self, reference_service, sample_paper_data):
        reference_service.add(**sample_paper_data)

        reference_service.annotate(
            key="vaswani2017-attention",
            key_contributions=["Self-attention", "Parallel training"],
        )
        reference_service.annotate(
            key="vaswani2017-attention",
            key_contributions=["Long-range dependency modeling"],
        )

        result = reference_service.get("vaswani2017-attention")
        assert result["ai_annotations"]["key_contributions"] == [
            "Self-attention",
            "Parallel training",
            "Long-range dependency modeling",
        ]

    def test_annotate_appends_tags_and_related_issues(self, reference_service, sample_paper_data):
        reference_service.add(**sample_paper_data)

        reference_service.annotate(
            key="vaswani2017-attention",
            tags=["transformer", "nlp"],
            related_issues=[11, 12],
        )
        reference_service.annotate(
            key="vaswani2017-attention",
            tags=["architecture"],
            related_issues=[13],
        )

        result = reference_service.get("vaswani2017-attention")
        assert result["ai_annotations"]["tags"] == ["transformer", "nlp", "architecture"]
        assert result["ai_annotations"]["related_issues"] == [11, 12, 13]

    def test_annotate_rejects_unknown_tag(self, reference_service, sample_paper_data):
        reference_service.add(**sample_paper_data)

        with pytest.raises(ValueError, match="Invalid tags"):
            reference_service.annotate(
                key="vaswani2017-attention",
                tags=["unknown-tag"],
            )

    def test_annotate_rejects_overlong_summary(self, reference_service, sample_paper_data):
        reference_service.add(**sample_paper_data)

        with pytest.raises(ValueError, match="summary exceeds"):
            reference_service.annotate(
                key="vaswani2017-attention",
                summary="x" * 2001,
            )

    def test_annotate_rejects_non_positive_related_issue(
        self, reference_service, sample_paper_data
    ):
        reference_service.add(**sample_paper_data)

        with pytest.raises(ValueError, match="related_issues must contain positive integers"):
            reference_service.annotate(
                key="vaswani2017-attention",
                related_issues=[0, 2],
            )

    def test_annotate_clears_summary_with_empty_string(self, reference_service, sample_paper_data):
        reference_service.add(**sample_paper_data)
        reference_service.annotate(
            key="vaswani2017-attention",
            summary="Initial summary",
        )

        reference_service.annotate(
            key="vaswani2017-attention",
            summary="",
        )

        result = reference_service.get("vaswani2017-attention")
        assert result["ai_annotations"]["summary"] == ""

    def test_annotate_clears_methodology_with_none(self, reference_service, sample_paper_data):
        reference_service.add(**sample_paper_data)
        reference_service.annotate(
            key="vaswani2017-attention",
            methodology="Transformer encoder-decoder",
        )

        reference_service.annotate(
            key="vaswani2017-attention",
            methodology=None,
        )

        result = reference_service.get("vaswani2017-attention")
        assert result["ai_annotations"]["methodology"] == ""


class TestReferenceServiceGetAllKeys:
    """Test getting all reference keys."""

    def test_get_all_keys_empty(self, reference_service):
        result = reference_service.get_all_keys()
        assert result == []

    def test_get_all_keys_returns_sorted(self, reference_service, sample_paper_data):
        reference_service.add(**sample_paper_data)
        reference_service.add(
            key="brown2020-gpt3",
            title="GPT-3",
            authors=["Brown"],
            year=2020,
        )

        result = reference_service.get_all_keys()
        assert len(result) == 2
        assert result == sorted(result)
