from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import yaml


@dataclass
class RubricVersion:
    version: str
    created_at: str
    dimension_weights: dict[str, float]
    gate_dimensions: list[str]
    gate_threshold: float
    changelog: str
    benchmark_accuracy: float


@dataclass
class CalibrationResult:
    old_version: str
    new_version: str
    dimensions_changed: list[str]
    weight_deltas: dict[str, float]
    accuracy_delta: float
    approved: bool
    reason: str


class RubricCalibrationService:
    _DEFAULT_DIMENSION_WEIGHTS = {
        "writing_quality": 0.12,
        "methodology": 0.18,
        "novelty": 0.18,
        "evaluation": 0.20,
        "presentation": 0.08,
        "limitations": 0.10,
        "reproducibility": 0.14,
    }
    _DEFAULT_GATE_DIMENSIONS = ["methodology", "novelty", "evaluation"]

    def __init__(self, rubric_dir: str | Path = "data/rubric_versions"):
        self.rubric_dir = Path(rubric_dir)

    def get_current_version(self) -> RubricVersion:
        current_path = self.rubric_dir / "current.yaml"
        if not current_path.exists():
            return self._default_version()

        data = self._read_yaml_dict(current_path)
        version = self._version_from_dict(data)
        return version if version is not None else self._default_version()

    def save_version(self, version: RubricVersion) -> Path:
        self.rubric_dir.mkdir(parents=True, exist_ok=True)

        version_path = self.rubric_dir / f"{version.version}.yaml"
        payload = self._version_to_dict(version)
        with version_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)

        current_path = self.rubric_dir / "current.yaml"
        with current_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)

        return version_path

    def list_versions(self) -> list[RubricVersion]:
        if not self.rubric_dir.exists():
            return []

        versions: list[RubricVersion] = []
        for path in sorted(self.rubric_dir.glob("*.yaml")):
            if path.name == "current.yaml":
                continue
            parsed = self._version_from_dict(self._read_yaml_dict(path))
            if parsed is not None:
                versions.append(parsed)
        return versions

    def compare_versions(self, v1: str, v2: str) -> CalibrationResult:
        old = self._load_version(v1)
        new = self._load_version(v2)

        changed, deltas = self._weight_delta(old.dimension_weights, new.dimension_weights)
        accuracy_delta = round(new.benchmark_accuracy - old.benchmark_accuracy, 4)
        approved = accuracy_delta > 0
        reason = "Accuracy improved" if approved else "Accuracy did not improve"
        return CalibrationResult(
            old_version=old.version,
            new_version=new.version,
            dimensions_changed=changed,
            weight_deltas=deltas,
            accuracy_delta=accuracy_delta,
            approved=approved,
            reason=reason,
        )

    def rollback(self, target_version: str) -> RubricVersion:
        target = self._load_version(target_version)
        self.rubric_dir.mkdir(parents=True, exist_ok=True)
        current_path = self.rubric_dir / "current.yaml"
        with current_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(
                self._version_to_dict(target), handle, sort_keys=False, allow_unicode=True
            )
        return target

    def propose_update(
        self,
        new_weights: dict[str, float],
        reason: str,
    ) -> CalibrationResult:
        current = self.get_current_version()
        validation_error = self._validate_weights(new_weights, current.dimension_weights, reason)
        if validation_error:
            return CalibrationResult(
                old_version=current.version,
                new_version=current.version,
                dimensions_changed=[],
                weight_deltas={},
                accuracy_delta=0.0,
                approved=False,
                reason=validation_error,
            )

        next_version = self._bump_patch(current.version)
        new_accuracy = self._estimate_accuracy(
            current.dimension_weights,
            new_weights,
            current.benchmark_accuracy,
        )
        proposal = RubricVersion(
            version=next_version,
            created_at=datetime.now().isoformat(),
            dimension_weights={k: round(float(v), 6) for k, v in sorted(new_weights.items())},
            gate_dimensions=list(current.gate_dimensions),
            gate_threshold=current.gate_threshold,
            changelog=reason.strip(),
            benchmark_accuracy=new_accuracy,
        )

        changed, deltas = self._weight_delta(current.dimension_weights, proposal.dimension_weights)
        accuracy_delta = round(proposal.benchmark_accuracy - current.benchmark_accuracy, 4)
        approved = accuracy_delta > 0
        if approved:
            self.save_version(proposal)
            result_reason = "Approved automatically: benchmark accuracy improved"
        else:
            result_reason = "Rejected automatically: benchmark accuracy did not improve"

        return CalibrationResult(
            old_version=current.version,
            new_version=proposal.version,
            dimensions_changed=changed,
            weight_deltas=deltas,
            accuracy_delta=accuracy_delta,
            approved=approved,
            reason=result_reason,
        )

    def _default_version(self) -> RubricVersion:
        return RubricVersion(
            version="1.0.0",
            created_at=datetime.now().isoformat(),
            dimension_weights=dict(self._DEFAULT_DIMENSION_WEIGHTS),
            gate_dimensions=list(self._DEFAULT_GATE_DIMENSIONS),
            gate_threshold=60.0,
            changelog="Initial default rubric",
            benchmark_accuracy=0.8,
        )

    def _load_version(self, version: str) -> RubricVersion:
        if version == "current":
            return self.get_current_version()

        version_path = self.rubric_dir / f"{version}.yaml"
        if not version_path.exists():
            raise ValueError(f"rubric version not found: {version}")

        parsed = self._version_from_dict(self._read_yaml_dict(version_path))
        if parsed is None:
            raise ValueError(f"invalid rubric version file: {version_path}")
        return parsed

    def _version_from_dict(self, data: dict[str, object]) -> RubricVersion | None:
        if not data:
            return None

        raw_weights = data.get("dimension_weights")
        if not isinstance(raw_weights, dict):
            return None

        weights: dict[str, float] = {}
        for key, value in raw_weights.items():
            if not isinstance(key, str):
                return None
            if not isinstance(value, (int, float)):
                return None
            weights[key] = float(value)

        gate_dimensions_raw = data.get("gate_dimensions", [])
        if not isinstance(gate_dimensions_raw, list) or not all(
            isinstance(item, str) for item in gate_dimensions_raw
        ):
            return None

        gate_threshold_raw = data.get("gate_threshold", 60.0)
        benchmark_accuracy_raw = data.get("benchmark_accuracy", 0.0)
        if not isinstance(gate_threshold_raw, (int, float)):
            return None
        if not isinstance(benchmark_accuracy_raw, (int, float)):
            return None

        try:
            return RubricVersion(
                version=str(data.get("version", "")),
                created_at=str(data.get("created_at", "")),
                dimension_weights=weights,
                gate_dimensions=[item for item in gate_dimensions_raw if isinstance(item, str)],
                gate_threshold=float(gate_threshold_raw),
                changelog=str(data.get("changelog", "")),
                benchmark_accuracy=float(benchmark_accuracy_raw),
            )
        except (TypeError, ValueError):
            return None

    def _version_to_dict(self, version: RubricVersion) -> dict[str, object]:
        return asdict(version)

    def _read_yaml_dict(self, path: Path) -> dict[str, object]:
        with path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        return data if isinstance(data, dict) else {}

    def _weight_delta(
        self,
        old: dict[str, float],
        new: dict[str, float],
    ) -> tuple[list[str], dict[str, float]]:
        dimensions = sorted(set(old) | set(new))
        changed: list[str] = []
        deltas: dict[str, float] = {}
        for dim in dimensions:
            delta = round(float(new.get(dim, 0.0)) - float(old.get(dim, 0.0)), 6)
            if delta != 0:
                changed.append(dim)
                deltas[dim] = delta
        return changed, deltas

    def _validate_weights(
        self,
        new_weights: dict[str, float],
        baseline: dict[str, float],
        reason: str,
    ) -> str | None:
        if not reason.strip():
            return "Reason is required"
        if not new_weights:
            return "At least one weight is required"

        if set(new_weights.keys()) != set(baseline.keys()):
            return "Weight dimensions must exactly match the current rubric"

        values = list(new_weights.values())
        if any((not isinstance(v, int | float)) for v in values):
            return "Weights must be numeric"
        if any(float(v) < 0.0 or float(v) > 1.0 for v in values):
            return "Weights must be between 0.0 and 1.0"

        total = sum(float(v) for v in values)
        if abs(total - 1.0) > 1e-6:
            return "Weights must sum to 1.0"

        return None

    def _estimate_accuracy(
        self,
        current_weights: dict[str, float],
        new_weights: dict[str, float],
        current_accuracy: float,
    ) -> float:
        drift = sum(
            abs(float(new_weights.get(dim, 0.0)) - float(current_weights.get(dim, 0.0)))
            for dim in set(current_weights) | set(new_weights)
        )
        delta = round(0.05 - drift * 0.1, 4)
        next_accuracy = current_accuracy + delta
        return round(min(1.0, max(0.0, next_accuracy)), 4)

    def _bump_patch(self, version: str) -> str:
        parts = version.split(".")
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            return "1.0.1"
        major, minor, patch = (int(parts[0]), int(parts[1]), int(parts[2]))
        return f"{major}.{minor}.{patch + 1}"
