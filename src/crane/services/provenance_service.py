from __future__ import annotations

import re

from crane.models.provenance import AnnotatedClaim, Provenance, VerificationStatus


class ProvenanceService:
    _NEGATION_PATTERN = re.compile(
        r"\b(?:not|no|never|without|cannot|can't|isn't|aren't|wasn't|weren't|"
        r"doesn't|don't|didn't|won't|shouldn't|wouldn't|couldn't)\b",
        re.IGNORECASE,
    )
    _PUNCTUATION_PATTERN = re.compile(r"[^\w\s]")

    def create_provenance(
        self,
        source_id: str,
        source_type: str,
        quote: str,
        location: str,
        confidence: float,
    ) -> Provenance:
        return Provenance(
            source_id=source_id,
            source_type=source_type,
            quote=quote,
            location=location,
            confidence=confidence,
        )

    def verify_claim(self, claim: AnnotatedClaim) -> VerificationStatus:
        if claim.verification_status == VerificationStatus.CONFLICTING:
            return claim.verification_status

        if not claim.provenance:
            claim.verification_status = VerificationStatus.UNVERIFIED
            return claim.verification_status

        if all(self._is_valid_provenance_item(item) for item in claim.provenance):
            claim.verification_status = VerificationStatus.VERIFIED
        else:
            claim.verification_status = VerificationStatus.UNVERIFIED

        return claim.verification_status

    def detect_conflicts(
        self, claims: list[AnnotatedClaim]
    ) -> list[tuple[AnnotatedClaim, AnnotatedClaim]]:
        grouped_claims: dict[str, dict[bool, list[AnnotatedClaim]]] = {}
        conflicting_pairs: list[tuple[AnnotatedClaim, AnnotatedClaim]] = []

        for claim in claims:
            key = self._claim_key(claim.claim)
            is_negated = self._has_negation(claim.claim)
            grouped_claims.setdefault(key, {True: [], False: []})[is_negated].append(claim)

        for variants in grouped_claims.values():
            positive_claims = variants[False]
            negative_claims = variants[True]
            for positive_claim in positive_claims:
                for negative_claim in negative_claims:
                    positive_claim.verification_status = VerificationStatus.CONFLICTING
                    negative_claim.verification_status = VerificationStatus.CONFLICTING
                    conflicting_pairs.append((positive_claim, negative_claim))

        return conflicting_pairs

    def _is_valid_provenance_item(self, item: object) -> bool:
        if not isinstance(item, Provenance):
            return False

        return (
            bool(item.source_id)
            and bool(item.source_type)
            and bool(item.quote)
            and bool(item.location)
            and 0.0 <= item.confidence <= 1.0
        )

    def _claim_key(self, claim: str) -> str:
        normalized = self._NEGATION_PATTERN.sub(" ", claim.lower())
        normalized = self._PUNCTUATION_PATTERN.sub(" ", normalized)
        return " ".join(normalized.split())

    def _has_negation(self, claim: str) -> bool:
        return bool(self._NEGATION_PATTERN.search(claim))


_DEFAULT_SERVICE = ProvenanceService()


def create_provenance(
    source_id: str,
    source_type: str,
    quote: str,
    location: str,
    confidence: float,
) -> Provenance:
    return _DEFAULT_SERVICE.create_provenance(
        source_id=source_id,
        source_type=source_type,
        quote=quote,
        location=location,
        confidence=confidence,
    )


def verify_claim(claim: AnnotatedClaim) -> VerificationStatus:
    return _DEFAULT_SERVICE.verify_claim(claim)


def detect_conflicts(
    claims: list[AnnotatedClaim],
) -> list[tuple[AnnotatedClaim, AnnotatedClaim]]:
    return _DEFAULT_SERVICE.detect_conflicts(claims)
