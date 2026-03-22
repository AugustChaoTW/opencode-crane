from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class VerificationStatus(Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    CONFLICTING = "conflicting"


@dataclass
class Provenance:
    source_id: str
    source_type: str
    quote: str
    location: str
    confidence: float

    def __post_init__(self):
        if not self.source_id:
            raise ValueError("source_id cannot be empty")
        if not self.source_type:
            raise ValueError("source_type cannot be empty")
        if not self.quote:
            raise ValueError("quote cannot be empty")
        if not self.location:
            raise ValueError("location cannot be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass
class AnnotatedClaim:
    claim: str
    provenance: list[Provenance] = field(default_factory=list)
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED

    def __post_init__(self):
        if not self.claim:
            raise ValueError("claim cannot be empty")
