# pyright: reportMissingImports=false

from __future__ import annotations

from crane.models.protected_zone import ProtectedZone, ProtectedZoneKind
from crane.services.protected_zone_service import (
    add_protected_zone,
    load_protected_zones,
    merge_zones,
    save_protected_zones,
    validate_zone,
)


def _zone(
    *,
    zone_id: str = "",
    kind: ProtectedZoneKind = ProtectedZoneKind.CITATION,
    file: str = "NIPS-MAIN.tex",
    anchor_start: str = "Introduction, Para 2, Sentence 3",
    checksum: str = "",
    reason: str = "Verified citation-claim link",
    source: str = "vaswani2017-attention",
    verified_at: str = "",
) -> ProtectedZone:
    return ProtectedZone(
        id=zone_id,
        kind=kind,
        file=file,
        anchor_start=anchor_start,
        checksum=checksum,
        reason=reason,
        source=source,
        verified_at=verified_at,
    )


class TestLoadProtectedZones:
    def test_load_missing_file_returns_empty(self, tmp_path):
        yaml_path = tmp_path / "papers" / "NIPS" / "NIPS-protected-zones.yaml"

        assert load_protected_zones(yaml_path) == []

    def test_load_saved_zones_roundtrip(self, tmp_path):
        yaml_path = tmp_path / "papers" / "NIPS" / "NIPS-protected-zones.yaml"
        zones = [
            _zone(zone_id="pz_001", checksum="", verified_at="2026-03-23T01:00:00"),
            _zone(
                zone_id="pz_002",
                kind=ProtectedZoneKind.TABLE,
                anchor_start="Table 1",
                reason="Verified table values",
                source="table-audit",
                checksum="",
                verified_at="2026-03-23T01:01:00",
            ),
        ]

        save_protected_zones(yaml_path, zones)
        loaded = load_protected_zones(yaml_path)

        assert [zone.id for zone in loaded] == ["pz_001", "pz_002"]
        assert loaded[0].kind == ProtectedZoneKind.CITATION
        assert validate_zone(loaded[0]) is True


class TestSaveProtectedZones:
    def test_save_creates_yaml_with_metadata(self, tmp_path):
        yaml_path = tmp_path / "papers" / "NIPS" / "NIPS-protected-zones.yaml"

        save_protected_zones(yaml_path, [_zone(zone_id="pz_001")])

        content = yaml_path.read_text(encoding="utf-8")
        assert "metadata:" in content
        assert "protected_zones:" in content
        assert "paper_path:" in content


class TestAddProtectedZone:
    def test_add_assigns_next_zone_id_and_persists(self, tmp_path):
        yaml_path = tmp_path / "papers" / "NIPS" / "NIPS-protected-zones.yaml"

        first_id = add_protected_zone(yaml_path, _zone())
        second_id = add_protected_zone(
            yaml_path,
            _zone(kind=ProtectedZoneKind.FACTUAL, anchor_start="Results, Para 1"),
        )
        loaded = load_protected_zones(yaml_path)

        assert first_id == "pz_001"
        assert second_id == "pz_002"
        assert [zone.id for zone in loaded] == ["pz_001", "pz_002"]
        assert all(zone.verified_at for zone in loaded)
        assert all(validate_zone(zone) for zone in loaded)

    def test_add_replaces_duplicate_zone_id(self, tmp_path):
        yaml_path = tmp_path / "papers" / "NIPS" / "NIPS-protected-zones.yaml"

        add_protected_zone(yaml_path, _zone(zone_id="pz_001"))
        new_id = add_protected_zone(yaml_path, _zone(zone_id="pz_001", anchor_start="Discussion"))

        assert new_id == "pz_002"


class TestValidateZone:
    def test_returns_false_for_invalid_checksum(self):
        zone = _zone(zone_id="pz_001", checksum="invalid", verified_at="2026-03-23T01:00:00")

        assert validate_zone(zone) is False


class TestMergeZones:
    def test_merge_preserves_order_and_deduplicates(self):
        zone_a = _zone(zone_id="pz_001")
        zone_b = _zone(zone_id="pz_002", anchor_start="Table 1", kind=ProtectedZoneKind.TABLE)
        zone_c = _zone(zone_id="pz_002", anchor_start="Duplicate")
        merged = merge_zones([[zone_a, zone_b], [zone_c]])

        assert merged == [zone_a, zone_b]
