"""
TDD tests for Paper and AiAnnotations data models.
RED phase: define expected behavior before implementation.
"""

import pytest

from crane.models.paper import AiAnnotations, Paper


class TestPaperCreation:
    """Paper instantiation and validation."""

    def test_create_minimal_paper(self):
        p = Paper(key="doe2024-test", title="Test Paper", authors=["John Doe"], year=2024)
        assert p.key == "doe2024-test"
        assert p.title == "Test Paper"
        assert p.authors == ["John Doe"]
        assert p.year == 2024

    def test_create_full_paper(self, sample_paper_dict):
        p = Paper(**sample_paper_dict)
        assert p.key == "vaswani2017-attention"
        assert p.doi == "10.48550/arXiv.1706.03762"
        assert p.venue == "NeurIPS"
        assert "cs.CL" in p.categories

    def test_empty_key_raises(self):
        with pytest.raises(ValueError, match="key cannot be empty"):
            Paper(key="", title="T", authors=["A"], year=2024)

    def test_empty_title_raises(self):
        with pytest.raises(ValueError, match="title cannot be empty"):
            Paper(key="k", title="", authors=["A"], year=2024)

    def test_default_fields(self):
        p = Paper(key="k", title="T", authors=["A"], year=2024)
        assert p.doi == ""
        assert p.source == "manual"
        assert p.paper_type == "unknown"
        assert p.categories == []
        assert p.keywords == []
        assert p.ai_annotations is None


class TestPaperEquality:
    """Paper identity is based on key."""

    def test_same_key_equal(self):
        a = Paper(key="x", title="A", authors=["A"], year=2024)
        b = Paper(key="x", title="B", authors=["B"], year=2025)
        assert a == b

    def test_different_key_not_equal(self):
        a = Paper(key="x", title="A", authors=["A"], year=2024)
        b = Paper(key="y", title="A", authors=["A"], year=2024)
        assert a != b

    def test_hashable_for_sets(self):
        a = Paper(key="x", title="A", authors=["A"], year=2024)
        b = Paper(key="x", title="B", authors=["B"], year=2025)
        assert len({a, b}) == 1


class TestPaperStr:
    """Paper string representation."""

    def test_str_format(self):
        p = Paper(key="doe2024-test", title="Test Paper", authors=["John Doe"], year=2024)
        s = str(p)
        assert "John Doe" in s
        assert "2024" in s
        assert "Test Paper" in s
        assert "doe2024-test" in s


class TestPaperYamlSerialization:
    """Paper ↔ YAML dict round-trip."""

    def test_to_yaml_dict_has_all_fields(self, sample_paper_dict):
        p = Paper(**sample_paper_dict)
        d = p.to_yaml_dict()
        assert d["key"] == "vaswani2017-attention"
        assert d["title"] == "Attention Is All You Need"
        assert d["year"] == 2017
        assert isinstance(d["authors"], list)
        assert isinstance(d["categories"], list)

    def test_to_yaml_dict_excludes_empty_optional(self):
        p = Paper(key="k", title="T", authors=["A"], year=2024)
        d = p.to_yaml_dict()
        # Empty strings should be omitted or empty, not None
        assert d.get("doi", "") == ""

    def test_from_yaml_dict_roundtrip(self, sample_paper_dict):
        p1 = Paper(**sample_paper_dict)
        d = p1.to_yaml_dict()
        p2 = Paper.from_yaml_dict(d)
        assert p1.key == p2.key
        assert p1.title == p2.title
        assert p1.authors == p2.authors
        assert p1.year == p2.year
        assert p1.doi == p2.doi

    def test_from_yaml_dict_with_annotations(self):
        d = {
            "key": "k",
            "title": "T",
            "authors": ["A"],
            "year": 2024,
            "ai_annotations": {
                "summary": "test summary",
                "key_contributions": ["c1"],
                "contribution_types": ["method"],
                "tags": ["t1"],
            },
        }
        p = Paper.from_yaml_dict(d)
        assert p.ai_annotations is not None
        assert p.ai_annotations.summary == "test summary"
        assert p.ai_annotations.key_contributions == ["c1"]
        assert p.ai_annotations.contribution_types == ["method"]


class TestPaperBibtex:
    """Paper → BibTeX generation."""

    def test_to_bibtex_contains_key(self, sample_paper_dict):
        p = Paper(**sample_paper_dict)
        bib = p.to_bibtex()
        assert "vaswani2017-attention" in bib

    def test_to_bibtex_contains_title(self, sample_paper_dict):
        p = Paper(**sample_paper_dict)
        bib = p.to_bibtex()
        assert "Attention Is All You Need" in bib

    def test_to_bibtex_contains_year(self, sample_paper_dict):
        p = Paper(**sample_paper_dict)
        bib = p.to_bibtex()
        assert "2017" in bib

    def test_to_bibtex_entry_type(self, sample_paper_dict):
        p = Paper(**sample_paper_dict)
        bib = p.to_bibtex()
        assert bib.startswith("@")


class TestAiAnnotations:
    """AiAnnotations dataclass."""

    def test_create_empty(self):
        a = AiAnnotations()
        assert a.summary == ""
        assert a.key_contributions == []
        assert a.tags == []
        assert a.related_issues == []

    def test_create_full(self):
        a = AiAnnotations(
            summary="test",
            key_contributions=["c1", "c2"],
            contribution_types=["method"],
            methodology="method",
            relevance_notes="relevant",
            tags=["t1"],
            related_issues=[1, 2],
            added_date="2026-03-14",
        )
        assert a.summary == "test"
        assert len(a.key_contributions) == 2
        assert a.contribution_types == ["method"]
        assert a.added_date == "2026-03-14"
