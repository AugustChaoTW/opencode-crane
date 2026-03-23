# pyright: reportMissingImports=false

from __future__ import annotations

import pytest

from crane.models.protected_zone import ProtectedZone, ProtectedZoneKind


class TestProtectedZoneKind:
    def test_enum_values(self):
        assert ProtectedZoneKind.CITATION.value == "citation"
        assert ProtectedZoneKind.TABLE.value == "table"
        assert ProtectedZoneKind.FIGURE.value == "figure"
        assert ProtectedZoneKind.FACTUAL.value == "factual"


class TestProtectedZone:
    def test_creation_with_all_fields(self):
        zone = ProtectedZone(
            id="pz_001",
            kind=ProtectedZoneKind.CITATION,
            file="NIPS-MAIN.tex",
            anchor_start="Introduction, Para 2, Sentence 3",
            checksum="abc123",
            reason="Verified citation-claim link",
            source="vaswani2017-attention",
            verified_at="2026-03-23T01:00:00",
        )

        assert zone.id == "pz_001"
        assert zone.kind == ProtectedZoneKind.CITATION
        assert zone.file == "NIPS-MAIN.tex"

    def test_creation_accepts_string_kind(self):
        zone = ProtectedZone(
            id="pz_001",
            kind="figure",
            file="NIPS-MAIN.tex",
            anchor_start="Figure 1 caption",
            checksum="abc123",
            reason="Verified figure values",
            source="manual-review",
            verified_at="2026-03-23T01:00:00",
        )

        assert zone.kind == ProtectedZoneKind.FIGURE

    def test_empty_file_raises(self):
        with pytest.raises(ValueError, match="file cannot be empty"):
            ProtectedZone(
                id="pz_001",
                kind=ProtectedZoneKind.CITATION,
                file="",
                anchor_start="Introduction",
                checksum="abc123",
                reason="Verified citation-claim link",
                source="vaswani2017-attention",
                verified_at="2026-03-23T01:00:00",
            )

    def test_yaml_roundtrip(self):
        zone = ProtectedZone(
            id="pz_001",
            kind=ProtectedZoneKind.FACTUAL,
            file="NIPS-MAIN.tex",
            anchor_start="Results, Para 1",
            checksum="abc123",
            reason="Verified factual statement",
            source="experiment-log",
            verified_at="2026-03-23T01:00:00",
        )

        data = zone.to_yaml_dict()
        restored = ProtectedZone.from_yaml_dict(data)

        assert restored == zone
