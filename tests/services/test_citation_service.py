# pyright: reportMissingImports=false

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
    assert out["valid"] is False
    assert out["total_citations"] == 2
    assert out["found"] == ["k1"]
    assert out["missing"] == ["k4"]
    assert out["unused"] == ["k2", "k3"]
    assert "claims" in out
    assert "unverified_count" in out
    assert "contradictions" in out


def test_analyze_claims_classifies_evidence_levels(service: CitationService) -> None:
    service.ref_service.get_all_keys.return_value = ["k1", "k2"]
    service.ref_service.get.side_effect = [
        {"title": "T1", "authors": ["A"], "year": 2020},
        {"title": "", "authors": ["A"], "year": 2020},
    ]
    text = (
        r"Method A improves accuracy by 2% \cite{k1}. "
        r"Method B improves latency \cite{k2}. "
        "Therefore, Method A scales better. "
        "This might generalize to all domains."
    )

    claims = service.analyze_claims(text)
    levels = [claim["evidence_level"] for claim in claims]

    assert "VERIFIED" in levels
    assert "PROBABLE" in levels
    assert "INFERRED" in levels
    assert "SPECULATIVE" in levels


def test_scan_contradictions_detects_conflicting_claims(service: CitationService) -> None:
    claims = [
        {
            "text": "Method X improves model accuracy.",
            "evidence_level": "INFERRED",
            "citation_key": "",
            "confidence": 0.5,
        },
        {
            "text": "Method X degrades model accuracy.",
            "evidence_level": "INFERRED",
            "citation_key": "",
            "confidence": 0.5,
        },
    ]

    contradictions = service.scan_contradictions(claims)
    assert len(contradictions) == 1
    assert "Conflicting polarity" in contradictions[0]["reason"]


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


def test_analyze_claims_extracts_from_multi_paragraph_text(service: CitationService) -> None:
    service.ref_service.get.return_value = {"title": "T", "authors": ["A"], "year": 2020}
    text = (
        "Model A improves F1 by 3% \\cite{k1}.\n\n"
        "Therefore, this effect should hold in production.\n\n"
        "The gain might shrink on out-of-domain data."
    )

    claims = service.analyze_claims(text)
    assert len(claims) == 3
    assert claims[0]["text"].startswith("Model A improves F1")
    assert claims[1]["text"].startswith("Therefore")
    assert claims[2]["text"].startswith("The gain might")


def test_analyze_claims_cited_complete_metadata_is_verified(
    service: CitationService,
) -> None:
    service.ref_service.get.return_value = {"title": "Paper", "authors": ["A"], "year": 2022}
    claims = service.analyze_claims(r"Model A improves recall \cite{k1}.")

    assert len(claims) == 1
    assert claims[0]["evidence_level"] == "VERIFIED"
    assert claims[0]["citation_key"] == "k1"
    assert claims[0]["confidence"] == 0.95


def test_analyze_claims_cited_missing_title_is_probable(service: CitationService) -> None:
    service.ref_service.get.return_value = {"title": "", "authors": ["A"], "year": 2022}
    claims = service.analyze_claims(r"Model A increases throughput \cite{k2}.")

    assert len(claims) == 1
    assert claims[0]["evidence_level"] == "PROBABLE"
    assert claims[0]["citation_key"] == "k2"
    assert claims[0]["confidence"] == 0.75


@pytest.mark.parametrize("cue", ["Therefore", "Thus", "Hence"])
def test_analyze_claims_inference_cues_without_citation_are_inferred(
    service: CitationService, cue: str
) -> None:
    claims = service.analyze_claims(f"{cue}, the method generalizes across domains.")

    assert len(claims) == 1
    assert claims[0]["evidence_level"] == "INFERRED"
    assert claims[0]["citation_key"] == ""
    assert claims[0]["confidence"] == 0.6


@pytest.mark.parametrize("hedge", ["might", "may", "could", "potentially"])
def test_analyze_claims_speculation_cues_without_citation_are_speculative(
    service: CitationService, hedge: str
) -> None:
    claims = service.analyze_claims(f"This {hedge} improve robustness in deployment.")

    assert len(claims) == 1
    assert claims[0]["evidence_level"] == "SPECULATIVE"
    assert claims[0]["citation_key"] == ""
    assert claims[0]["confidence"] == 0.35


def test_analyze_claims_verified_confidence_higher_than_speculative(
    service: CitationService,
) -> None:
    service.ref_service.get.return_value = {"title": "Paper", "authors": ["A"], "year": 2020}
    claims = service.analyze_claims(
        r"Method A improves accuracy \cite{k1}. This might fail on unseen data."
    )

    verified = next(c for c in claims if c["evidence_level"] == "VERIFIED")
    speculative = next(c for c in claims if c["evidence_level"] == "SPECULATIVE")
    assert verified["confidence"] > speculative["confidence"]


def test_analyze_claims_detects_numeric_claims(service: CitationService) -> None:
    claims = service.analyze_claims("Latency is 12 ms and error rate is 4.5 percent.")

    assert len(claims) == 1
    assert "12" in claims[0]["text"]
    assert claims[0]["evidence_level"] == "INFERRED"
    assert claims[0]["confidence"] == 0.5


def test_analyze_claims_empty_text_returns_empty_list(service: CitationService) -> None:
    assert service.analyze_claims("") == []


def test_analyze_claims_text_with_no_claims_returns_empty_list(
    service: CitationService,
) -> None:
    text = "Introduction section. Background context only. No findings discussed."
    assert service.analyze_claims(text) == []


def test_scan_contradictions_increases_vs_decreases(service: CitationService) -> None:
    claims = [
        {"text": "Method A increases accuracy."},
        {"text": "Method A decreases accuracy."},
    ]
    contradictions = service.scan_contradictions(claims)

    assert len(contradictions) == 1
    assert contradictions[0]["claim_a"] == "Method A increases accuracy."
    assert contradictions[0]["claim_b"] == "Method A decreases accuracy."


def test_scan_contradictions_improves_vs_worsens(service: CitationService) -> None:
    claims = [
        {"text": "Method B improves robustness."},
        {"text": "Method B worsens robustness."},
    ]
    contradictions = service.scan_contradictions(claims)

    assert len(contradictions) == 1
    assert "Conflicting polarity" in contradictions[0]["reason"]


def test_scan_contradictions_higher_vs_lower(service: CitationService) -> None:
    claims = [
        {"text": "Method C is better than baseline."},
        {"text": "Method C is worse than baseline."},
    ]
    contradictions = service.scan_contradictions(claims)

    assert len(contradictions) == 1
    assert "method c" in contradictions[0]["reason"].lower()
    assert "baseline" in contradictions[0]["reason"].lower()


def test_scan_contradictions_no_conflict_for_compatible_claims(
    service: CitationService,
) -> None:
    claims = [
        {"text": "Method A improves accuracy."},
        {"text": "Method B improves accuracy."},
    ]
    assert service.scan_contradictions(claims) == []


def test_scan_contradictions_empty_input_returns_empty(service: CitationService) -> None:
    assert service.scan_contradictions([]) == []


def test_scan_contradictions_reason_includes_explanation(service: CitationService) -> None:
    claims = [
        {"text": "Method A improves calibration."},
        {"text": "Method A worsens calibration."},
    ]
    contradictions = service.scan_contradictions(claims)

    assert len(contradictions) == 1
    assert "Conflicting polarity for relationship" in contradictions[0]["reason"]
    assert "method a" in contradictions[0]["reason"].lower()
    assert "calibration" in contradictions[0]["reason"].lower()


def test_scan_contradictions_same_subject_same_polarity_not_flagged(
    service: CitationService,
) -> None:
    claims = [
        {"text": "Method A improves recall."},
        {"text": "Method A improves recall."},
    ]
    assert service.scan_contradictions(claims) == []


def test_check_local_consistency_populates_claims_for_citable_text(
    service: CitationService,
) -> None:
    service.ref_service.get.return_value = {"title": "T", "authors": ["A"], "year": 2020}
    out = service.check_local_consistency(
        "inline.tex",
        manuscript_text=r"Method A improves accuracy by 2% \cite{k1}.",
    )

    assert len(out["claims"]) == 1
    assert out["claims"][0]["citation_key"] == "k1"
    assert out["claims"][0]["evidence_level"] == "VERIFIED"


def test_check_local_consistency_unverified_count_increases_with_more_unverified_claims(
    service: CitationService,
) -> None:
    low_unverified = service.check_local_consistency(
        "inline.tex",
        manuscript_text=r"Method A improves score \cite{k1}.",
    )
    high_unverified = service.check_local_consistency(
        "inline.tex",
        manuscript_text=(
            r"Method A improves score \cite{k1}. "
            "Therefore the model is universally robust. "
            "This might transfer to every domain."
        ),
    )

    assert high_unverified["unverified_count"] > low_unverified["unverified_count"]
    assert high_unverified["unverified_count"] >= 2


def test_check_local_consistency_contradictions_present_when_empty(
    service: CitationService,
) -> None:
    out = service.check_local_consistency(
        "inline.tex",
        manuscript_text=r"Method A improves robustness \cite{k1}.",
    )

    assert "contradictions" in out
    assert out["contradictions"] == []


def test_check_local_consistency_backward_compatible_fields_preserved(
    service: CitationService,
) -> None:
    out = service.check_local_consistency(
        "inline.tex",
        manuscript_text=r"Use \cite{k1,kx} in the text.",
    )

    assert out["valid"] is False
    assert out["total_citations"] == 2
    assert out["found"] == ["k1"]
    assert out["missing"] == ["kx"]
    assert out["unused"] == ["k2", "k3"]
