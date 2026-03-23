from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProtectedZoneKind(Enum):
    CITATION = "citation"
    TABLE = "table"
    FIGURE = "figure"
    FACTUAL = "factual"


@dataclass(slots=True)
class ProtectedZone:
    id: str
    kind: ProtectedZoneKind | str
    file: str
    anchor_start: str
    checksum: str
    reason: str
    source: str
    verified_at: str

    def __post_init__(self) -> None:
        if isinstance(self.kind, str):
            self.kind = ProtectedZoneKind(self.kind)

        for field_name in ("file", "anchor_start", "reason", "source"):
            if not getattr(self, field_name):
                raise ValueError(f"{field_name} cannot be empty")

    def to_yaml_dict(self) -> dict[str, str]:
        kind = (
            self.kind if isinstance(self.kind, ProtectedZoneKind) else ProtectedZoneKind(self.kind)
        )
        return {
            "id": self.id,
            "kind": kind.value,
            "file": self.file,
            "anchor_start": self.anchor_start,
            "checksum": self.checksum,
            "reason": self.reason,
            "source": self.source,
            "verified_at": self.verified_at,
        }

    @classmethod
    def from_yaml_dict(cls, data: dict[str, str]) -> "ProtectedZone":
        return cls(
            id=data.get("id", ""),
            kind=ProtectedZoneKind(data["kind"]),
            file=data["file"],
            anchor_start=data["anchor_start"],
            checksum=data.get("checksum", ""),
            reason=data["reason"],
            source=data["source"],
            verified_at=data.get("verified_at", ""),
        )
