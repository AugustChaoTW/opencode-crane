"""Tests for screening service."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from crane.services.reference_service import ReferenceService


def _load():
    return importlib.import_module("crane.services.screening_service")


class TestScreeningDecision:
    def test_enum_values(self):
        mod = _load()
        assert mod.ScreeningDecision.INCLUDE.value == "include"
        assert mod.ScreeningDecision.EXCLUDE.value == "exclude"
        assert mod.ScreeningDecision.MAYBE.value == "maybe"


class TestComparisonMatrix:
    def test_to_dict(self):
        mod = _load()
        dim = mod.ComparisonDimension(name="year", values={"p1": "2024", "p2": "2023"})
        matrix = mod.ComparisonMatrix(papers=["p1", "p2"], dimensions=[dim])
        result = matrix.to_dict()
        assert result["papers"] == ["p1", "p2"]
        assert result["dimensions"][0]["name"] == "year"


class TestScreeningService:
    @pytest.fixture
    def populated_refs(self, tmp_path):
        refs_dir = tmp_path / "references"
        service = ReferenceService(refs_dir)
        service.add(
            key="paper-a",
            title="Paper A",
            authors=["Alice", "Bob", "Carol", "Dave"],
            year=2024,
            venue="NeurIPS",
            doi="10.1000/a",
            abstract="Benchmarks on dataset A.",
        )
        service.add(
            key="paper-b",
            title="Paper B",
            authors=["Beatrice"],
            year=2023,
            venue="ICML",
            doi="10.1000/b",
            abstract="Benchmarks on dataset B.",
        )
        service.annotate(
            "paper-a",
            methodology="Transformer with retrieval",
            key_contributions=["better accuracy", "lower latency"],
        )
        return refs_dir

    def test_screen_invalid_decision(self, tmp_path):
        mod = _load()
        refs_dir = tmp_path / "references"
        (refs_dir / "papers").mkdir(parents=True)
        (refs_dir / "bibliography.bib").touch()

        svc = mod.ScreeningService(refs_dir)
        with pytest.raises(ValueError, match="Invalid decision"):
            svc.screen("test", "invalid")

    def test_compare_min_papers(self, tmp_path):
        mod = _load()
        refs_dir = tmp_path / "references"
        (refs_dir / "papers").mkdir(parents=True)
        (refs_dir / "bibliography.bib").touch()

        svc = mod.ScreeningService(refs_dir)
        with pytest.raises(ValueError, match="Need at least 2 papers"):
            svc.compare(["p1"])

    def test_screen_persists_decision_and_metadata(self, populated_refs):
        mod = _load()
        svc = mod.ScreeningService(populated_refs)

        result = svc.screen(
            "paper-a",
            "include",
            reason="Matches inclusion criteria",
            criteria=["novelty", "evaluation"],
        )

        stored = ReferenceService(populated_refs).get("paper-a")
        assert result.paper_key == "paper-a"
        assert result.decision == mod.ScreeningDecision.INCLUDE
        assert stored["screening"]["decision"] == "include"
        assert stored["screening"]["reason"] == "Matches inclusion criteria"
        assert stored["screening"]["criteria"] == ["novelty", "evaluation"]

    def test_list_screened_skips_unscreened_and_filters(self, populated_refs):
        mod = _load()
        svc = mod.ScreeningService(populated_refs)
        svc.screen("paper-a", "include", reason="keep")
        svc.screen("paper-b", "exclude", reason="wrong domain")

        all_results = svc.list_screened()
        excluded = svc.list_screened("exclude")

        assert [item["key"] for item in all_results] == ["paper-a", "paper-b"]
        assert excluded == [
            {
                "key": "paper-b",
                "title": "Paper B",
                "decision": "exclude",
                "reason": "wrong domain",
                "criteria": [],
            }
        ]

    def test_compare_builds_default_dimensions(self, populated_refs):
        mod = _load()
        svc = mod.ScreeningService(populated_refs)

        matrix = svc.compare(["paper-a", "paper-b"])
        as_dict = matrix.to_dict()

        dim_names = [dim["name"] for dim in as_dict["dimensions"]]
        assert dim_names == [
            "year",
            "authors",
            "venue",
            "methodology",
            "dataset",
            "metric",
            "result",
        ]
        authors_dim = next(dim for dim in as_dict["dimensions"] if dim["name"] == "authors")
        methodology_dim = next(dim for dim in as_dict["dimensions"] if dim["name"] == "methodology")
        assert authors_dim["values"]["paper-a"] == "Alice, Bob, Carol"
        assert methodology_dim["values"]["paper-a"] == "Transformer with retrieval"

    def test_compare_raises_for_missing_paper(self, populated_refs):
        mod = _load()
        svc = mod.ScreeningService(populated_refs)

        with pytest.raises(ValueError, match="Paper not found: missing-paper"):
            svc.compare(["paper-a", "missing-paper"])

    @pytest.mark.parametrize(
        ("dimension", "expected"),
        [
            ("year", "2025"),
            ("authors", "Alice, Bob, Carol"),
            ("venue", "TMLR"),
            ("doi", "10.1234/example"),
            ("methodology", "Prompting"),
            ("key_contributions", "one; two; three; four"),
            ("dataset", "MTEB"),
        ],
    )
    def test_extract_dimension_handles_core_fields(self, dimension, expected):
        mod = _load()
        svc = mod.ScreeningService(Path("references"))
        data = {
            "year": 2025,
            "authors": ["Alice", "Bob", "Carol", "Dave"],
            "venue": "TMLR",
            "doi": "10.1234/example",
            "dataset": "MTEB",
            "ai_annotations": {
                "methodology": "Prompting",
                "key_contributions": ["one", "two", "three", "four"],
            },
        }

        assert svc._extract_dimension(data, dimension) == expected

    def test_extract_dimension_handles_string_authors_and_missing_annotations(self):
        mod = _load()
        svc = mod.ScreeningService(Path("references"))

        assert svc._extract_dimension({"authors": "Solo Author"}, "authors") == "Solo Author"
        assert svc._extract_dimension({"ai_annotations": {}}, "key_contributions") == ""

    def test_extract_dimension_returns_all_key_contributions(self):
        mod = _load()
        svc = mod.ScreeningService(Path("references"))
        data = {
            "ai_annotations": {
                "key_contributions": ["one", "two", "three", "four", "five"],
            }
        }

        assert svc._extract_dimension(data, "key_contributions") == "one; two; three; four; five"
