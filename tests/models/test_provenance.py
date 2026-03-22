"""Tests for Provenance models."""

from __future__ import annotations

import importlib

import pytest


def _load_provenance():
    return importlib.import_module("crane.models.provenance")


def _load_service():
    return importlib.import_module("crane.services.provenance_service")


class TestVerificationStatus:
    def test_enum_values(self):
        prov = _load_provenance()
        assert prov.VerificationStatus.VERIFIED.value == "verified"
        assert prov.VerificationStatus.UNVERIFIED.value == "unverified"
        assert prov.VerificationStatus.CONFLICTING.value == "conflicting"


class TestProvenance:
    def test_creation_with_all_fields(self):
        prov = _load_provenance()
        p = prov.Provenance(
            source_id="1706.03762",
            source_type="abstract",
            quote="Transformers replace recurrence with attention.",
            location="Abstract",
            confidence=0.95,
        )
        assert p.source_id == "1706.03762"
        assert p.confidence == 0.95

    def test_empty_source_id_raises(self):
        prov = _load_provenance()
        with pytest.raises(ValueError, match="source_id"):
            prov.Provenance(
                source_id="",
                source_type="abstract",
                quote="test",
                location="test",
                confidence=0.5,
            )

    def test_confidence_out_of_range_raises(self):
        prov = _load_provenance()
        with pytest.raises(ValueError, match="confidence"):
            prov.Provenance(
                source_id="test",
                source_type="abstract",
                quote="test",
                location="test",
                confidence=1.5,
            )


class TestAnnotatedClaim:
    def test_creation_with_defaults(self):
        prov = _load_provenance()
        claim = prov.AnnotatedClaim(claim="Transformers are effective.")
        assert claim.verification_status == prov.VerificationStatus.UNVERIFIED
        assert claim.provenance == []

    def test_empty_claim_raises(self):
        prov = _load_provenance()
        with pytest.raises(ValueError, match="claim"):
            prov.AnnotatedClaim(claim="")


class TestProvenanceService:
    def test_create_provenance(self):
        svc_mod = _load_service()
        prov_mod = _load_provenance()
        svc = svc_mod.ProvenanceService()
        p = svc.create_provenance(
            source_id="1706.03762",
            source_type="abstract",
            quote="Test quote",
            location="Abstract",
            confidence=0.9,
        )
        assert isinstance(p, prov_mod.Provenance)

    def test_verify_claim(self):
        svc_mod = _load_service()
        prov_mod = _load_provenance()
        svc = svc_mod.ProvenanceService()
        p = prov_mod.Provenance(
            source_id="test",
            source_type="abstract",
            quote="test",
            location="test",
            confidence=0.9,
        )
        claim = prov_mod.AnnotatedClaim(claim="Test claim", provenance=[p])
        status = svc.verify_claim(claim)
        assert status == prov_mod.VerificationStatus.VERIFIED

    def test_detect_conflicts(self):
        svc_mod = _load_service()
        prov_mod = _load_provenance()
        svc = svc_mod.ProvenanceService()
        p1 = prov_mod.Provenance(
            source_id="test",
            source_type="abstract",
            quote="test",
            location="test",
            confidence=0.9,
        )
        p2 = prov_mod.Provenance(
            source_id="test2",
            source_type="abstract",
            quote="test",
            location="test",
            confidence=0.9,
        )
        claim1 = prov_mod.AnnotatedClaim(claim="Attention is effective.", provenance=[p1])
        claim2 = prov_mod.AnnotatedClaim(claim="Attention is not effective.", provenance=[p2])
        conflicts = svc.detect_conflicts([claim1, claim2])
        assert len(conflicts) > 0
