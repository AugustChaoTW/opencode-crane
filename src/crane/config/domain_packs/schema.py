from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

REQUIRED_DIMENSIONS = {
    "writing_quality",
    "methodology",
    "novelty",
    "evaluation",
    "presentation",
    "limitations",
    "reproducibility",
}


@dataclass
class DomainPack:
    name: str
    display_name: str
    version: str
    description: str
    dimension_weights: dict[str, float]
    gate_dimensions: list[str]
    gate_threshold: float
    scoring_signals: dict[str, list[str]]
    recommended_journals: list[str]
    detection_keywords: list[str]
    detection_threshold: float


class DomainPackLoader:
    def __init__(self, packs_dir: str | Path | None = None):
        self.packs_dir = (
            Path(packs_dir) if packs_dir is not None else Path(__file__).resolve().parent
        )

    def load(self, pack_name: str) -> DomainPack:
        filename = pack_name if pack_name.endswith(".yaml") else f"{pack_name}.yaml"
        pack_path = self.packs_dir / filename

        if not pack_path.exists():
            raise FileNotFoundError(f"Domain pack not found: {pack_path}")

        raw_data = yaml.safe_load(pack_path.read_text(encoding="utf-8"))
        if not isinstance(raw_data, dict):
            raise ValueError(f"Invalid domain pack YAML: {pack_path}")

        missing = {
            "name",
            "display_name",
            "version",
            "description",
            "dimension_weights",
            "gate_dimensions",
            "gate_threshold",
            "scoring_signals",
            "recommended_journals",
            "detection_keywords",
            "detection_threshold",
        }.difference(raw_data)
        if missing:
            raise ValueError(
                f"Domain pack '{pack_path.stem}' missing required fields: {sorted(missing)}"
            )

        pack = DomainPack(
            name=str(raw_data["name"]),
            display_name=str(raw_data["display_name"]),
            version=str(raw_data["version"]),
            description=str(raw_data["description"]),
            dimension_weights={
                str(key): float(value) for key, value in dict(raw_data["dimension_weights"]).items()
            },
            gate_dimensions=[str(value) for value in list(raw_data["gate_dimensions"])],
            gate_threshold=float(raw_data["gate_threshold"]),
            scoring_signals={
                str(key): [str(signal) for signal in list(value)]
                for key, value in dict(raw_data["scoring_signals"]).items()
            },
            recommended_journals=[str(value) for value in list(raw_data["recommended_journals"])],
            detection_keywords=[str(value) for value in list(raw_data["detection_keywords"])],
            detection_threshold=float(raw_data["detection_threshold"]),
        )

        errors = self.validate_pack(pack)
        if errors:
            raise ValueError(f"Invalid domain pack '{pack.name}': " + "; ".join(errors))

        return pack

    def load_all(self) -> list[DomainPack]:
        packs: list[DomainPack] = []
        for path in sorted(self.packs_dir.glob("*.yaml")):
            packs.append(self.load(path.stem))
        return packs

    def detect_domain(self, text: str) -> str | None:
        lowered = text.lower()
        best_pack: str | None = None
        best_ratio = 0.0

        for pack in self.load_all():
            keywords = [keyword for keyword in pack.detection_keywords if keyword.strip()]
            if not keywords:
                continue

            matches = sum(1 for keyword in keywords if keyword.lower() in lowered)
            ratio = matches / len(keywords)

            if ratio >= pack.detection_threshold and ratio > best_ratio:
                best_pack = pack.name
                best_ratio = ratio

        return best_pack

    def validate_pack(self, pack: DomainPack) -> list[str]:
        errors: list[str] = []

        if not pack.name.strip():
            errors.append("name must be non-empty")
        if not pack.display_name.strip():
            errors.append("display_name must be non-empty")
        if not pack.version.strip():
            errors.append("version must be non-empty")
        if not pack.description.strip():
            errors.append("description must be non-empty")

        if set(pack.dimension_weights) != REQUIRED_DIMENSIONS:
            missing = sorted(REQUIRED_DIMENSIONS.difference(pack.dimension_weights))
            extra = sorted(set(pack.dimension_weights).difference(REQUIRED_DIMENSIONS))
            if missing:
                errors.append(f"dimension_weights missing dimensions: {missing}")
            if extra:
                errors.append(f"dimension_weights has unknown dimensions: {extra}")

        total_weight = sum(pack.dimension_weights.values())
        if abs(total_weight - 1.0) > 1e-6:
            errors.append(f"dimension_weights must sum to 1.0, got {total_weight:.6f}")

        for dimension, weight in pack.dimension_weights.items():
            if weight < 0.0:
                errors.append(f"dimension weight cannot be negative: {dimension}")

        invalid_gates = sorted(set(pack.gate_dimensions).difference(pack.dimension_weights))
        if invalid_gates:
            errors.append(f"gate_dimensions not in dimension_weights: {invalid_gates}")

        if not 0.0 <= pack.gate_threshold <= 100.0:
            errors.append("gate_threshold must be between 0 and 100")

        for dimension, patterns in pack.scoring_signals.items():
            if dimension not in pack.dimension_weights:
                errors.append(f"scoring_signals has unknown dimension: {dimension}")
            if not isinstance(patterns, list):
                errors.append(f"scoring_signals[{dimension}] must be a list")
                continue
            if any(not pattern.strip() for pattern in patterns):
                errors.append(f"scoring_signals[{dimension}] contains empty pattern")

        if not pack.recommended_journals:
            errors.append("recommended_journals must be non-empty")

        if not pack.detection_keywords:
            errors.append("detection_keywords must be non-empty")

        if not 0.0 <= pack.detection_threshold <= 1.0:
            errors.append("detection_threshold must be between 0.0 and 1.0")

        return errors
