# pyright: reportMissingImports=false

"""
TDD tests for citation verification tools.
Tests both the service layer and MCP tool layer.
"""

from __future__ import annotations

import pytest

from crane.services.citation_service import CitationService
from crane.tools.citations import register_tools


class _ToolCollector:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


@pytest.fixture
def citation_tools():
    collector = _ToolCollector()
    register_tools(collector)
    return collector.tools


@pytest.fixture
def sample_refs_dir(tmp_path):
    """Create a sample references directory with test papers."""
    refs_dir = tmp_path / "references"
    papers_dir = refs_dir / "papers"
    papers_dir.mkdir(parents=True)

    # Create test reference files
    (papers_dir / "vaswani2017-attention.yaml").write_text(
        """key: vaswani2017-attention
title: Attention Is All You Need
authors:
  - Vaswani
  - Shazeer
year: 2017
doi: 10.48550/arXiv.1706.03762
url: https://arxiv.org/abs/1706.03762
venue: NeurIPS
source: arxiv
paper_type: conference
""",
        encoding="utf-8",
    )

    (papers_dir / "brown2020-gpt3.yaml").write_text(
        """key: brown2020-gpt3
title: Language Models are Few-Shot Learners
authors:
  - Brown
  - Mann
year: 2020
doi: 10.48550/arXiv.2005.14165
url: https://arxiv.org/abs/2005.14165
venue: NeurIPS
source: arxiv
paper_type: conference
""",
        encoding="utf-8",
    )

    # Create bibliography.bib
    (refs_dir / "bibliography.bib").write_text("", encoding="utf-8")

    return refs_dir


class TestCitationServiceExtractCiteKeys:
    """Test citation key extraction from LaTeX text."""

    def test_single_citation(self, sample_refs_dir):
        service = CitationService(sample_refs_dir)
        text = r"This is a citation \cite{vaswani2017-attention} in text."
        keys = service.extract_cite_keys(text)
        assert keys == ["vaswani2017-attention"]

    def test_multiple_citations_in_one_cite(self, sample_refs_dir):
        service = CitationService(sample_refs_dir)
        text = r"Multiple citations \cite{vaswani2017-attention,brown2020-gpt3}."
        keys = service.extract_cite_keys(text)
        assert set(keys) == {"vaswani2017-attention", "brown2020-gpt3"}

    def test_multiple_cite_commands(self, sample_refs_dir):
        service = CitationService(sample_refs_dir)
        text = r"First \cite{vaswani2017-attention} and second \cite{brown2020-gpt3}."
        keys = service.extract_cite_keys(text)
        assert set(keys) == {"vaswani2017-attention", "brown2020-gpt3"}

    def test_no_duplicates(self, sample_refs_dir):
        service = CitationService(sample_refs_dir)
        text = r"Same cite \cite{vaswani2017-attention} twice \cite{vaswani2017-attention}."
        keys = service.extract_cite_keys(text)
        assert keys == ["vaswani2017-attention"]

    def test_empty_text(self, sample_refs_dir):
        service = CitationService(sample_refs_dir)
        keys = service.extract_cite_keys("")
        assert keys == []

    def test_no_citations(self, sample_refs_dir):
        service = CitationService(sample_refs_dir)
        text = "This text has no citations."
        keys = service.extract_cite_keys(text)
        assert keys == []


class TestCitationServiceCheckLocalConsistency:
    """Test local consistency checking."""

    def test_all_citations_exist(self, sample_refs_dir):
        service = CitationService(sample_refs_dir)
        text = r"Citations \cite{vaswani2017-attention,brown2020-gpt3}."
        result = service.check_local_consistency("<inline>", text)

        assert result["valid"] is True
        assert result["total_citations"] == 2
        assert set(result["found"]) == {"vaswani2017-attention", "brown2020-gpt3"}
        assert result["missing"] == []

    def test_missing_citation(self, sample_refs_dir):
        service = CitationService(sample_refs_dir)
        text = r"Citation \cite{nonexistent2024-paper}."
        result = service.check_local_consistency("<inline>", text)

        assert result["valid"] is False
        assert result["total_citations"] == 1
        assert result["found"] == []
        assert result["missing"] == ["nonexistent2024-paper"]

    def test_mixed_found_and_missing(self, sample_refs_dir):
        service = CitationService(sample_refs_dir)
        text = r"Found \cite{vaswani2017-attention} and missing \cite{nonexistent2024}."
        result = service.check_local_consistency("<inline>", text)

        assert result["valid"] is False
        assert result["total_citations"] == 2
        assert result["found"] == ["vaswani2017-attention"]
        assert result["missing"] == ["nonexistent2024"]

    def test_unused_references(self, sample_refs_dir):
        service = CitationService(sample_refs_dir)
        text = r"Only cite one \cite{vaswani2017-attention}."
        result = service.check_local_consistency("<inline>", text)

        assert result["valid"] is True
        assert "brown2020-gpt3" in result["unused"]


class TestCitationServiceCheckMetadata:
    """Test metadata verification."""

    def test_correct_doi(self, sample_refs_dir):
        service = CitationService(sample_refs_dir)
        result = service.check_metadata(
            "vaswani2017-attention",
            expected_doi="10.48550/arXiv.1706.03762",
        )

        assert result["valid"] is True
        assert result["checks"]["doi"]["match"] is True

    def test_wrong_doi(self, sample_refs_dir):
        service = CitationService(sample_refs_dir)
        result = service.check_metadata(
            "vaswani2017-attention",
            expected_doi="10.1234/wrong-doi",
        )

        assert result["valid"] is False
        assert result["checks"]["doi"]["match"] is False

    def test_correct_year(self, sample_refs_dir):
        service = CitationService(sample_refs_dir)
        result = service.check_metadata(
            "vaswani2017-attention",
            expected_year=2017,
        )

        assert result["valid"] is True
        assert result["checks"]["year"]["match"] is True

    def test_wrong_year(self, sample_refs_dir):
        service = CitationService(sample_refs_dir)
        result = service.check_metadata(
            "vaswani2017-attention",
            expected_year=2020,
        )

        assert result["valid"] is False
        assert result["checks"]["year"]["match"] is False

    def test_title_substring_match(self, sample_refs_dir):
        service = CitationService(sample_refs_dir)
        result = service.check_metadata(
            "vaswani2017-attention",
            expected_title="Attention",
        )

        assert result["valid"] is True
        assert result["checks"]["title"]["match"] is True

    def test_nonexistent_reference(self, sample_refs_dir):
        service = CitationService(sample_refs_dir)
        result = service.check_metadata(
            "nonexistent2024",
            expected_doi="10.1234/test",
        )

        assert result["valid"] is False
        assert "error" in result


class TestCitationToolsRegistered:
    """Test MCP tool registration."""

    def test_check_citations_registered(self, citation_tools):
        assert "check_citations" in citation_tools

    def test_verify_reference_registered(self, citation_tools):
        assert "verify_reference" in citation_tools

    def test_check_all_references_registered(self, citation_tools):
        assert "check_all_references" in citation_tools


class TestCheckCitationsTool:
    """Test check_citations MCP tool."""

    def test_valid_citations(self, citation_tools, sample_refs_dir):
        text = r"Citations \cite{vaswani2017-attention,brown2020-gpt3}."
        result = citation_tools["check_citations"](
            manuscript_text=text,
            refs_dir=str(sample_refs_dir),
        )

        assert result["valid"] is True
        assert result["total_citations"] == 2

    def test_missing_citation(self, citation_tools, sample_refs_dir):
        text = r"Citation \cite{nonexistent2024}."
        result = citation_tools["check_citations"](
            manuscript_text=text,
            refs_dir=str(sample_refs_dir),
        )

        assert result["valid"] is False
        assert "nonexistent2024" in result["missing"]

    def test_claim_analysis_excluded_by_default(self, citation_tools, sample_refs_dir):
        text = r"Model A improves robustness \cite{vaswani2017-attention}."
        result = citation_tools["check_citations"](
            manuscript_text=text,
            refs_dir=str(sample_refs_dir),
        )

        assert "claims" not in result
        assert "unverified_count" not in result
        assert "contradictions" not in result

    def test_claim_analysis_included_when_requested(self, citation_tools, sample_refs_dir):
        text = r"Model A improves robustness \cite{vaswani2017-attention}."
        result = citation_tools["check_citations"](
            manuscript_text=text,
            include_claim_analysis=True,
            refs_dir=str(sample_refs_dir),
        )

        assert "claims" in result
        assert "unverified_count" in result
        assert "contradictions" in result

    def test_no_input_raises(self, citation_tools, sample_refs_dir):
        with pytest.raises(ValueError):
            citation_tools["check_citations"](refs_dir=str(sample_refs_dir))


class TestVerifyReferenceTool:
    """Test verify_reference MCP tool."""

    def test_correct_metadata(self, citation_tools, sample_refs_dir):
        result = citation_tools["verify_reference"](
            key="vaswani2017-attention",
            expected_doi="10.48550/arXiv.1706.03762",
            expected_year=2017,
            refs_dir=str(sample_refs_dir),
        )

        assert result["valid"] is True
        assert result["checks"]["doi"]["match"] is True
        assert result["checks"]["year"]["match"] is True

    def test_wrong_metadata(self, citation_tools, sample_refs_dir):
        result = citation_tools["verify_reference"](
            key="vaswani2017-attention",
            expected_doi="wrong-doi",
            expected_year=2020,
            refs_dir=str(sample_refs_dir),
        )

        assert result["valid"] is False
        assert result["checks"]["doi"]["match"] is False
        assert result["checks"]["year"]["match"] is False


class TestCheckAllReferencesTool:
    """Test check_all_references MCP tool."""

    def test_all_references_complete(self, citation_tools, sample_refs_dir):
        result = citation_tools["check_all_references"](
            refs_dir=str(sample_refs_dir),
        )

        assert len(result) == 2
        for ref_check in result:
            assert ref_check["valid"] is True

    def test_with_manuscript_filters_refs(self, citation_tools, sample_refs_dir):
        text = r"Only cite one \cite{vaswani2017-attention}."
        result = citation_tools["check_all_references"](
            manuscript_text=text,
            refs_dir=str(sample_refs_dir),
        )

        assert len(result) == 1
        assert result[0]["key"] == "vaswani2017-attention"


class TestCheckCitationsToolClaimAnalysisToggle:
    def test_include_claim_analysis_false_strips_enhanced_fields(
        self, citation_tools, sample_refs_dir
    ):
        text = (
            r"Model A improves robustness \cite{vaswani2017-attention}. "
            r"Model A worsens robustness \cite{brown2020-gpt3}."
        )
        result = citation_tools["check_citations"](
            manuscript_text=text,
            include_claim_analysis=False,
            refs_dir=str(sample_refs_dir),
        )

        assert result["valid"] is True
        assert result["total_citations"] == 2
        assert "claims" not in result
        assert "unverified_count" not in result
        assert "contradictions" not in result

    def test_include_claim_analysis_true_includes_values(self, citation_tools, sample_refs_dir):
        text = (
            r"Model A improves robustness \cite{vaswani2017-attention}. "
            "Therefore, the model generalizes broadly. "
            "This might fail on long-tail domains."
        )
        result = citation_tools["check_citations"](
            manuscript_text=text,
            include_claim_analysis=True,
            refs_dir=str(sample_refs_dir),
        )

        assert result["valid"] is True
        assert len(result["claims"]) == 3
        assert result["claims"][0]["evidence_level"] == "VERIFIED"
        assert result["unverified_count"] == 2
        assert result["contradictions"] == []

    def test_include_claim_analysis_false_preserves_legacy_field_values(
        self, citation_tools, sample_refs_dir
    ):
        text = r"Use known \cite{vaswani2017-attention} and unknown \cite{missing-key}."
        result = citation_tools["check_citations"](
            manuscript_text=text,
            include_claim_analysis=False,
            refs_dir=str(sample_refs_dir),
        )

        assert result == {
            "valid": False,
            "total_citations": 2,
            "found": ["vaswani2017-attention"],
            "missing": ["missing-key"],
            "unused": ["brown2020-gpt3"],
        }

    def test_include_claim_analysis_true_includes_empty_claim_collections(
        self, citation_tools, sample_refs_dir
    ):
        text = "Pure narrative introduction without any factual claim markers."
        result = citation_tools["check_citations"](
            manuscript_text=text,
            include_claim_analysis=True,
            refs_dir=str(sample_refs_dir),
        )

        assert result["claims"] == []
        assert result["unverified_count"] == 0
        assert result["contradictions"] == []
