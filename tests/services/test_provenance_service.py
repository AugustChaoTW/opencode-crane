from __future__ import annotations

from typing import cast

import pytest

from crane.models.provenance import AnnotatedClaim, Provenance, VerificationStatus
from crane.services import provenance_service
from crane.services.provenance_service import ProvenanceService


@pytest.fixture
def svc() -> ProvenanceService:
    return ProvenanceService()


@pytest.mark.parametrize(
    ("source_id", "source_type", "quote", "location", "confidence"),
    [
        ("p1", "pdf", "q", "p1", 0.0),
        ("p2", "web", "quote", "sec2", 1.0),
        ("p3", "yaml", "another", "l3", 0.45),
    ],
)
def test_create_provenance_happy_path(
    svc: ProvenanceService,
    source_id: str,
    source_type: str,
    quote: str,
    location: str,
    confidence: float,
) -> None:
    item = svc.create_provenance(source_id, source_type, quote, location, confidence)
    assert isinstance(item, Provenance)
    assert item.source_id == source_id
    assert item.confidence == confidence


@pytest.mark.parametrize(
    ("source_id", "source_type", "quote", "location", "confidence"),
    [
        ("", "pdf", "q", "p1", 0.1),
        ("p1", "", "q", "p1", 0.1),
        ("p1", "pdf", "", "p1", 0.1),
        ("p1", "pdf", "q", "", 0.1),
        ("p1", "pdf", "q", "p1", -0.1),
        ("p1", "pdf", "q", "p1", 1.1),
    ],
)
def test_create_provenance_validation_errors(
    svc: ProvenanceService,
    source_id: str,
    source_type: str,
    quote: str,
    location: str,
    confidence: float,
) -> None:
    with pytest.raises(ValueError):
        svc.create_provenance(source_id, source_type, quote, location, confidence)


def test_verify_claim_returns_conflicting_without_mutation(svc: ProvenanceService) -> None:
    claim = AnnotatedClaim("X", verification_status=VerificationStatus.CONFLICTING)
    assert svc.verify_claim(claim) == VerificationStatus.CONFLICTING


def test_verify_claim_no_provenance_is_unverified(svc: ProvenanceService) -> None:
    claim = AnnotatedClaim("X")
    assert svc.verify_claim(claim) == VerificationStatus.UNVERIFIED


def test_verify_claim_with_valid_provenance_is_verified(svc: ProvenanceService) -> None:
    claim = AnnotatedClaim(
        "X",
        provenance=[Provenance("s1", "pdf", "quote", "p1", 0.9)],
    )
    assert svc.verify_claim(claim) == VerificationStatus.VERIFIED


@pytest.mark.parametrize(
    "item",
    [
        "not-a-provenance",
        123,
        object(),
    ],
)
def test_verify_claim_invalid_provenance_item_type_unverified(
    svc: ProvenanceService, item: object
) -> None:
    claim = AnnotatedClaim("x", provenance=cast(list[Provenance], [item]))
    assert svc.verify_claim(claim) == VerificationStatus.UNVERIFIED


@pytest.mark.parametrize(
    ("text", "has_negation"),
    [
        ("Model improves robustness", False),
        ("Model does not improve robustness", True),
        ("This cannot work", True),
        ("We NEVER observed failure", True),
        ("No issue reported", True),
        ("Evidence supports claim", False),
    ],
)
def test_has_negation_pattern(svc: ProvenanceService, text: str, has_negation: bool) -> None:
    assert svc._has_negation(text) is has_negation


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ("Model improves accuracy.", "model improves accuracy"),
        ("Model does not improve accuracy!", "model does improve accuracy"),
        ("No evidence, no claim.", "evidence claim"),
        ("This, perhaps, works?", "this perhaps works"),
        ("can't verify this", "verify this"),
    ],
)
def test_claim_key_normalization(svc: ProvenanceService, raw: str, normalized: str) -> None:
    assert svc._claim_key(raw) == normalized


def test_detect_conflicts_marks_pairs_conflicting(svc: ProvenanceService) -> None:
    positive = AnnotatedClaim("Model works")
    negative = AnnotatedClaim("Model not works")
    unrelated = AnnotatedClaim("Different claim entirely")

    conflicts = svc.detect_conflicts([positive, negative, unrelated])

    assert len(conflicts) == 1
    assert conflicts[0] == (positive, negative)
    assert positive.verification_status == VerificationStatus.CONFLICTING
    assert negative.verification_status == VerificationStatus.CONFLICTING
    assert unrelated.verification_status == VerificationStatus.UNVERIFIED


def test_detect_conflicts_cartesian_pairing_for_multiple_variants(svc: ProvenanceService) -> None:
    positives = [AnnotatedClaim("Claim works"), AnnotatedClaim("Claim works.")]
    negatives = [AnnotatedClaim("Claim not works"), AnnotatedClaim("Claim never works")]

    conflicts = svc.detect_conflicts([*positives, *negatives])
    assert len(conflicts) == len(positives) * len(negatives)


def test_detect_conflicts_no_pairs_when_only_single_polarity(svc: ProvenanceService) -> None:
    claims = [AnnotatedClaim("A is good"), AnnotatedClaim("A is also good")]
    assert svc.detect_conflicts(claims) == []


def test_module_level_wrappers_delegate_to_default_service(monkeypatch: pytest.MonkeyPatch) -> None:
    class StubService:
        def create_provenance(self, **kwargs):
            return kwargs

        def verify_claim(self, claim):
            return "verified-out"

        def detect_conflicts(self, claims):
            return [(claims[0], claims[0])]

    monkeypatch.setattr(provenance_service, "_DEFAULT_SERVICE", StubService())
    claim = AnnotatedClaim("x")

    created = provenance_service.create_provenance("s", "pdf", "q", "l", 0.5)
    verified = provenance_service.verify_claim(claim)
    conflicts = provenance_service.detect_conflicts([claim])

    assert created["source_id"] == "s"
    assert verified == "verified-out"
    assert len(conflicts) == 1
