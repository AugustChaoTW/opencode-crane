"""Tests for screening service."""

from __future__ import annotations

import importlib

import pytest


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
