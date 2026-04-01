from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from crane.services.citation_service import CitationService


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> CitationService:
    fake_ref = MagicMock()
    fake_ref.get_all_keys.return_value = ["k1", "k2", "k3"]
    monkeypatch.setattr(
        "crane.services.citation_service.ReferenceService", lambda *_a, **_k: fake_ref
    )
    svc = CitationService(refs_dir="references")
    svc.ref_service = fake_ref
    return svc


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (r"No cite here", []),
        (r"Use \cite{k1}", ["k1"]),
        (r"Use \cite{k1,k2}", ["k1", "k2"]),
        (r"Use \cite{k1, k2, k1}", ["k1", "k2"]),
        (r"\cite{k1}\n\cite{k2,k3}", ["k1", "k2", "k3"]),
    ],
)
def test_extract_cite_keys_variants(
    service: CitationService, text: str, expected: list[str]
) -> None:
    assert service.extract_cite_keys(text) == expected


def test_check_local_consistency_uses_given_text(service: CitationService) -> None:
    out = service.check_local_consistency("ignored.tex", manuscript_text=r"\cite{k1,k4}")
    assert out == {
        "valid": False,
        "total_citations": 2,
        "found": ["k1"],
        "missing": ["k4"],
        "unused": ["k2", "k3"],
    }


def test_check_local_consistency_reads_file_when_text_missing(
    service: CitationService, tmp_path: Path
) -> None:
    manuscript = tmp_path / "m.tex"
    manuscript.write_text(r"text \cite{k2}", encoding="utf-8")

    out = service.check_local_consistency(manuscript)
    assert out["valid"] is True
    assert out["found"] == ["k2"]


def test_check_local_consistency_missing_file_raises(service: CitationService) -> None:
    with pytest.raises(FileNotFoundError):
        service.check_local_consistency("/tmp/nope-1234.tex")


def test_check_metadata_reference_not_found(service: CitationService) -> None:
    service.ref_service.get.side_effect = ValueError("Reference not found")
    out = service.check_metadata("missing")
    assert out["valid"] is False
    assert "error" in out
    assert out["checks"] == {}


@pytest.mark.parametrize(
    ("expected_doi", "expected_year", "expected_title", "valid"),
    [
        ("10.1000/x", 2022, "Great", True),
        ("10.1000/other", 2022, "Great", False),
        ("10.1000/x", 2024, "Great", False),
        ("10.1000/x", 2022, "Missing", False),
        ("", None, "", True),
    ],
)
def test_check_metadata_variants(
    service: CitationService,
    expected_doi: str,
    expected_year: int | None,
    expected_title: str,
    valid: bool,
) -> None:
    service.ref_service.get.return_value = {
        "doi": "10.1000/X",
        "year": 2022,
        "title": "Great Paper",
    }
    out = service.check_metadata(
        "k1",
        expected_doi=expected_doi,
        expected_year=expected_year,
        expected_title=expected_title,
    )
    assert out["valid"] is valid


@pytest.mark.parametrize(
    ("ref", "is_valid"),
    [
        ({"title": "T", "authors": ["A"], "year": 2020}, True),
        ({"title": "", "authors": ["A"], "year": 2020}, False),
        ({"title": "T", "authors": [], "year": 2020}, False),
        ({"title": "T", "authors": ["A"], "year": 0}, False),
    ],
)
def test_check_all_metadata_field_presence(
    service: CitationService, ref: dict[str, object], is_valid: bool
) -> None:
    service.ref_service.get_all_keys.return_value = ["k1"]
    service.ref_service.get.return_value = ref
    out = service.check_all_metadata()
    assert len(out) == 1
    assert out[0]["valid"] is is_valid


def test_check_all_metadata_from_manuscript_text(service: CitationService) -> None:
    service.ref_service.get.side_effect = [
        {"title": "A", "authors": ["1"], "year": 2020},
        ValueError("missing"),
    ]
    out = service.check_all_metadata(manuscript_text=r"\cite{k1,kx}")
    assert len(out) == 2
    assert out[0]["key"] == "k1"
    assert out[1]["key"] == "kx"
    assert out[1]["valid"] is False


def test_check_all_metadata_reads_from_file_if_exists(
    service: CitationService, tmp_path: Path
) -> None:
    path = tmp_path / "paper.tex"
    path.write_text(r"\cite{k2}", encoding="utf-8")
    service.ref_service.get.return_value = {"title": "T", "authors": ["a"], "year": 1}
    out = service.check_all_metadata(manuscript_path=path)
    assert [r["key"] for r in out] == ["k2"]


def test_check_all_metadata_missing_manuscript_path_falls_back_to_all_keys(
    service: CitationService,
) -> None:
    service.ref_service.get_all_keys.return_value = ["k1", "k2"]
    service.ref_service.get.return_value = {"title": "T", "authors": ["a"], "year": 1}
    out = service.check_all_metadata(manuscript_path="/tmp/does-not-exist.tex")
    assert [r["key"] for r in out] == ["k1", "k2"]
