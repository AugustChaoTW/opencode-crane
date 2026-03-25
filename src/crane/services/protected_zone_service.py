from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import replace
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import cast

import yaml

from crane.models.protected_zone import ProtectedZone, ProtectedZoneKind


def load_protected_zones(yaml_path: str | Path) -> list[ProtectedZone]:
    path = Path(yaml_path)
    if not path.exists():
        return []

    data = _read_yaml_document(path)
    raw_zones = data.get("protected_zones", [])
    if not isinstance(raw_zones, list):
        return []

    return [ProtectedZone.from_yaml_dict(item) for item in raw_zones if isinstance(item, dict)]


def save_protected_zones(yaml_path: str | Path, zones: list[ProtectedZone]) -> None:
    path = Path(yaml_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing = _read_yaml_document(path)
    metadata = existing.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    document = {
        "metadata": {
            "paper_path": str(metadata.get("paper_path") or _default_paper_path(path)),
            "generated_at": datetime.now().isoformat(),
            "version": int(metadata.get("version", 1) or 1),
        },
        "protected_zones": [_normalize_zone(zone).to_yaml_dict() for zone in zones],
    }

    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            document,
            handle,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )


def add_protected_zone(yaml_path: str | Path, zone: ProtectedZone) -> str:
    zones = load_protected_zones(yaml_path)
    zone_id = zone.id
    if not zone_id or any(existing.id == zone_id for existing in zones):
        zone_id = _next_zone_id(zones)

    stored_zone = replace(_normalize_zone(zone), id=zone_id)
    save_protected_zones(yaml_path, [*zones, stored_zone])
    return zone_id


def validate_zone(zone: ProtectedZone) -> bool:
    return bool(zone.checksum) and zone.checksum == _compute_checksum(zone)


def merge_zones(zone_lists: Iterable[Iterable[ProtectedZone]]) -> list[ProtectedZone]:
    merged: list[ProtectedZone] = []
    seen: set[str] = set()

    for zone_list in zone_lists:
        for zone in zone_list:
            key = zone.id or _compute_checksum(zone)
            if key in seen:
                continue
            seen.add(key)
            merged.append(zone)

    return merged


def _read_yaml_document(path: Path) -> dict:
    if not path.exists():
        return {}

    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    return data if isinstance(data, dict) else {}


def _default_paper_path(path: Path) -> Path:
    name = path.name
    if name.endswith("-protected-zones.yaml"):
        return path.with_name(name.replace("-protected-zones.yaml", "-MAIN.tex"))
    return path.with_suffix(".tex")


def _normalize_zone(zone: ProtectedZone) -> ProtectedZone:
    checksum = zone.checksum
    if not validate_zone(zone):
        checksum = _compute_checksum(zone)

    verified_at = zone.verified_at or datetime.now().isoformat()
    return replace(zone, checksum=checksum, verified_at=verified_at)


def _compute_checksum(zone: ProtectedZone) -> str:
    kind = zone.kind if isinstance(zone.kind, ProtectedZoneKind) else ProtectedZoneKind(zone.kind)
    kind = cast(ProtectedZoneKind, kind)
    payload = "\n".join([kind.value, zone.file, zone.anchor_start, zone.reason, zone.source])
    return sha256(payload.encode("utf-8")).hexdigest()


def _next_zone_id(zones: list[ProtectedZone]) -> str:
    next_index = 1
    pattern = re.compile(r"^pz_(\d+)$")

    for zone in zones:
        match = pattern.match(zone.id)
        if match:
            next_index = max(next_index, int(match.group(1)) + 1)

    return f"pz_{next_index:03d}"
