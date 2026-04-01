# pyright: reportMissingImports=false

from __future__ import annotations

from datetime import datetime

import pytest

from crane.services.rubric_calibration_service import RubricCalibrationService, RubricVersion


def _weights(**overrides: float) -> dict[str, float]:
    base = {
        "writing_quality": 0.12,
        "methodology": 0.18,
        "novelty": 0.18,
        "evaluation": 0.20,
        "presentation": 0.08,
        "limitations": 0.10,
        "reproducibility": 0.14,
    }
    base.update(overrides)
    return base


def _version(version: str, accuracy: float, **weight_overrides: float) -> RubricVersion:
    return RubricVersion(
        version=version,
        created_at=datetime.now().isoformat(),
        dimension_weights=_weights(**weight_overrides),
        gate_dimensions=["methodology", "novelty", "evaluation"],
        gate_threshold=60.0,
        changelog=f"version {version}",
        benchmark_accuracy=accuracy,
    )


def test_get_current_version_without_file_returns_default(tmp_path) -> None:
    service = RubricCalibrationService(tmp_path / "rubrics")

    current = service.get_current_version()

    assert current.version == "1.0.0"
    assert current.benchmark_accuracy == 0.8
    assert abs(sum(current.dimension_weights.values()) - 1.0) < 1e-9


def test_get_current_version_with_existing_file(tmp_path) -> None:
    service = RubricCalibrationService(tmp_path / "rubrics")
    stored = _version("1.2.0", 0.91)
    service.save_version(stored)

    current = service.get_current_version()

    assert current.version == "1.2.0"
    assert current.benchmark_accuracy == 0.91


def test_get_current_version_invalid_yaml_falls_back_to_default(tmp_path) -> None:
    rubric_dir = tmp_path / "rubrics"
    rubric_dir.mkdir(parents=True, exist_ok=True)
    (rubric_dir / "current.yaml").write_text("[]", encoding="utf-8")
    service = RubricCalibrationService(rubric_dir)

    current = service.get_current_version()

    assert current.version == "1.0.0"


def test_save_version_creates_version_and_current_files(tmp_path) -> None:
    rubric_dir = tmp_path / "rubrics"
    service = RubricCalibrationService(rubric_dir)
    path = service.save_version(_version("2.0.0", 0.88))

    assert path.exists()
    assert (rubric_dir / "current.yaml").exists()


def test_save_and_load_roundtrip_keeps_weights(tmp_path) -> None:
    service = RubricCalibrationService(tmp_path / "rubrics")
    stored = _version("2.1.0", 0.87, evaluation=0.22, presentation=0.06)
    service.save_version(stored)

    loaded = service.get_current_version()

    assert loaded.dimension_weights["evaluation"] == 0.22
    assert loaded.dimension_weights["presentation"] == 0.06


def test_list_versions_empty_directory_returns_empty(tmp_path) -> None:
    service = RubricCalibrationService(tmp_path / "rubrics")

    assert service.list_versions() == []


def test_list_versions_excludes_current_yaml(tmp_path) -> None:
    rubric_dir = tmp_path / "rubrics"
    service = RubricCalibrationService(rubric_dir)
    service.save_version(_version("1.0.1", 0.81))
    service.save_version(_version("1.0.2", 0.82))

    listed = service.list_versions()

    assert [item.version for item in listed] == ["1.0.1", "1.0.2"]


def test_list_versions_skips_invalid_documents(tmp_path) -> None:
    rubric_dir = tmp_path / "rubrics"
    rubric_dir.mkdir(parents=True, exist_ok=True)
    (rubric_dir / "broken.yaml").write_text("{invalid: true}", encoding="utf-8")
    service = RubricCalibrationService(rubric_dir)

    assert service.list_versions() == []


def test_compare_versions_detects_changed_dimensions_and_accuracy(tmp_path) -> None:
    service = RubricCalibrationService(tmp_path / "rubrics")
    service.save_version(_version("1.0.0", 0.8))
    service.save_version(_version("1.0.1", 0.85, evaluation=0.24, presentation=0.04))

    result = service.compare_versions("1.0.0", "1.0.1")

    assert result.old_version == "1.0.0"
    assert result.new_version == "1.0.1"
    assert set(result.dimensions_changed) == {"evaluation", "presentation"}
    assert result.accuracy_delta == 0.05
    assert result.approved is True


def test_compare_versions_no_improvement_not_approved(tmp_path) -> None:
    service = RubricCalibrationService(tmp_path / "rubrics")
    service.save_version(_version("1.0.0", 0.9))
    service.save_version(_version("1.0.1", 0.85, evaluation=0.21, presentation=0.07))

    result = service.compare_versions("1.0.0", "1.0.1")

    assert result.approved is False
    assert result.reason == "Accuracy did not improve"


def test_compare_versions_missing_raises_value_error(tmp_path) -> None:
    service = RubricCalibrationService(tmp_path / "rubrics")

    with pytest.raises(ValueError, match="rubric version not found"):
        service.compare_versions("1.0.0", "9.9.9")


def test_propose_update_valid_weights_auto_approves_and_saves(tmp_path) -> None:
    service = RubricCalibrationService(tmp_path / "rubrics")

    result = service.propose_update(
        new_weights=_weights(evaluation=0.21, presentation=0.07),
        reason="Increase evaluation emphasis",
    )

    assert result.approved is True
    assert result.new_version == "1.0.1"
    assert (tmp_path / "rubrics" / "1.0.1.yaml").exists()
    assert service.get_current_version().version == "1.0.1"


def test_propose_update_rejects_empty_reason(tmp_path) -> None:
    service = RubricCalibrationService(tmp_path / "rubrics")

    result = service.propose_update(new_weights=_weights(), reason="   ")

    assert result.approved is False
    assert result.reason == "Reason is required"


def test_propose_update_rejects_empty_weights(tmp_path) -> None:
    service = RubricCalibrationService(tmp_path / "rubrics")

    result = service.propose_update(new_weights={}, reason="test")

    assert result.approved is False
    assert result.reason == "At least one weight is required"


def test_propose_update_rejects_dimension_mismatch(tmp_path) -> None:
    service = RubricCalibrationService(tmp_path / "rubrics")

    result = service.propose_update(
        new_weights={"methodology": 1.0},
        reason="bad keys",
    )

    assert result.approved is False
    assert "exactly match" in result.reason


def test_propose_update_rejects_weights_out_of_range(tmp_path) -> None:
    service = RubricCalibrationService(tmp_path / "rubrics")
    invalid = _weights(evaluation=1.2, presentation=-0.1)

    result = service.propose_update(new_weights=invalid, reason="invalid")

    assert result.approved is False
    assert result.reason == "Weights must be between 0.0 and 1.0"


def test_propose_update_rejects_weights_not_summing_to_one(tmp_path) -> None:
    service = RubricCalibrationService(tmp_path / "rubrics")
    invalid = _weights(evaluation=0.5)

    result = service.propose_update(new_weights=invalid, reason="invalid")

    assert result.approved is False
    assert result.reason == "Weights must sum to 1.0"


def test_propose_update_rejects_when_accuracy_not_improved(tmp_path) -> None:
    service = RubricCalibrationService(tmp_path / "rubrics")
    bad_shift = {
        "writing_quality": 1.0,
        "methodology": 0.0,
        "novelty": 0.0,
        "evaluation": 0.0,
        "presentation": 0.0,
        "limitations": 0.0,
        "reproducibility": 0.0,
    }

    result = service.propose_update(new_weights=bad_shift, reason="large shift")

    assert result.approved is False
    assert result.accuracy_delta < 0
    assert not (tmp_path / "rubrics" / "1.0.1.yaml").exists()


def test_rollback_sets_current_to_target_version(tmp_path) -> None:
    service = RubricCalibrationService(tmp_path / "rubrics")
    service.save_version(_version("1.0.1", 0.81))
    service.save_version(_version("1.0.2", 0.83))

    rolled = service.rollback("1.0.1")

    assert rolled.version == "1.0.1"
    assert service.get_current_version().version == "1.0.1"


def test_rollback_missing_version_raises(tmp_path) -> None:
    service = RubricCalibrationService(tmp_path / "rubrics")

    with pytest.raises(ValueError, match="rubric version not found"):
        service.rollback("3.0.0")


def test_propose_update_bumps_from_non_semver_to_default_patch(tmp_path) -> None:
    service = RubricCalibrationService(tmp_path / "rubrics")
    service.save_version(_version("custom", 0.9))

    result = service.propose_update(_weights(), "keep stable")

    assert result.new_version == "1.0.1"
