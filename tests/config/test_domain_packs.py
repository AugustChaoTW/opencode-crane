from __future__ import annotations

from copy import deepcopy

import pytest
import yaml

from crane.config.domain_packs.schema import DomainPack, DomainPackLoader


def _valid_pack() -> DomainPack:
    return DomainPack(
        name="ai_ml",
        display_name="AI & Machine Learning",
        version="1.0.0",
        description="AI/ML evaluation pack",
        dimension_weights={
            "writing_quality": 0.12,
            "methodology": 0.18,
            "novelty": 0.18,
            "evaluation": 0.20,
            "presentation": 0.08,
            "limitations": 0.10,
            "reproducibility": 0.14,
        },
        gate_dimensions=["methodology", "novelty", "evaluation"],
        gate_threshold=60.0,
        scoring_signals={
            "methodology": [r"\\section\{.*[Mm]ethod.*\}"],
            "novelty": [r"\bnovel\b"],
            "evaluation": [r"\bbaseline\b"],
        },
        recommended_journals=["IEEE TPAMI", "JMLR"],
        detection_keywords=["deep learning", "transformer", "machine learning"],
        detection_threshold=0.15,
    )


def _write_pack(tmp_path, pack_name: str, payload: dict) -> None:
    pack_dir = tmp_path / "packs"
    pack_dir.mkdir(parents=True, exist_ok=True)
    (pack_dir / f"{pack_name}.yaml").write_text(yaml.safe_dump(payload), encoding="utf-8")


def test_load_ai_ml_yaml_success() -> None:
    loader = DomainPackLoader()
    pack = loader.load("ai_ml")

    assert pack.name == "ai_ml"
    assert pack.display_name == "AI & Machine Learning"
    assert abs(sum(pack.dimension_weights.values()) - 1.0) < 1e-6
    assert set(pack.gate_dimensions) == {"methodology", "novelty", "evaluation"}


def test_load_all_returns_at_least_one_pack() -> None:
    loader = DomainPackLoader()
    packs = loader.load_all()

    assert len(packs) >= 1
    assert "ai_ml" in {pack.name for pack in packs}


def test_detect_domain_for_ai_ml_text_returns_ai_ml() -> None:
    loader = DomainPackLoader()
    text = """
    We propose a transformer deep learning architecture for machine learning tasks.
    The neural network uses an attention mechanism for natural language processing.
    """

    assert loader.detect_domain(text) == "ai_ml"


def test_detect_domain_for_non_ai_text_returns_none() -> None:
    loader = DomainPackLoader()
    text = """
    This manuscript studies stratigraphic sedimentation and marine isotope ratios
    in paleoceanography, with no machine intelligence terminology.
    """

    assert loader.detect_domain(text) is None


def test_load_missing_pack_raises_file_not_found(tmp_path) -> None:
    loader = DomainPackLoader(tmp_path / "packs")

    with pytest.raises(FileNotFoundError):
        loader.load("does_not_exist")


def test_load_missing_required_fields_raises(tmp_path) -> None:
    payload = {
        "name": "broken",
        "display_name": "Broken",
    }
    _write_pack(tmp_path, "broken", payload)
    loader = DomainPackLoader(tmp_path / "packs")

    with pytest.raises(ValueError, match="missing required fields"):
        loader.load("broken")


def test_validate_pack_valid_pack_no_errors() -> None:
    loader = DomainPackLoader()
    errors = loader.validate_pack(_valid_pack())

    assert errors == []


def test_detect_domain_uses_highest_ratio_above_threshold(tmp_path) -> None:
    base = {
        "name": "pack_a",
        "display_name": "Pack A",
        "version": "1.0.0",
        "description": "A",
        "dimension_weights": _valid_pack().dimension_weights,
        "gate_dimensions": ["methodology"],
        "gate_threshold": 60.0,
        "scoring_signals": {"methodology": ["method"]},
        "recommended_journals": ["J1"],
        "detection_keywords": ["alpha", "beta", "gamma", "delta"],
        "detection_threshold": 0.10,
    }
    payload_b = deepcopy(base)
    payload_b["name"] = "pack_b"
    payload_b["display_name"] = "Pack B"
    payload_b["detection_keywords"] = ["alpha", "beta"]

    _write_pack(tmp_path, "pack_a", base)
    _write_pack(tmp_path, "pack_b", payload_b)

    loader = DomainPackLoader(tmp_path / "packs")
    assert loader.detect_domain("alpha beta") == "pack_b"


@pytest.mark.parametrize(
    "field_name",
    ["name", "display_name", "version", "description"],
)
def test_validate_pack_empty_required_strings(field_name: str) -> None:
    pack = _valid_pack()
    setattr(pack, field_name, "")
    loader = DomainPackLoader()

    errors = loader.validate_pack(pack)

    assert any(field_name in error for error in errors)


@pytest.mark.parametrize("new_total", [0.99, 1.01, 0.8, 1.2])
def test_validate_pack_weights_must_sum_to_one(new_total: float) -> None:
    pack = _valid_pack()
    scale = new_total / sum(pack.dimension_weights.values())
    pack.dimension_weights = {
        dimension: round(weight * scale, 6) for dimension, weight in pack.dimension_weights.items()
    }
    loader = DomainPackLoader()

    errors = loader.validate_pack(pack)

    assert any("must sum to 1.0" in error for error in errors)


def test_validate_pack_gate_dimensions_must_be_subset() -> None:
    pack = _valid_pack()
    pack.gate_dimensions.append("unknown_dimension")
    loader = DomainPackLoader()

    errors = loader.validate_pack(pack)

    assert any("gate_dimensions not in dimension_weights" in error for error in errors)


def test_validate_pack_missing_dimension_detected() -> None:
    pack = _valid_pack()
    del pack.dimension_weights["novelty"]
    loader = DomainPackLoader()

    errors = loader.validate_pack(pack)

    assert any("missing dimensions" in error for error in errors)


def test_validate_pack_unknown_dimension_detected() -> None:
    pack = _valid_pack()
    pack.dimension_weights["other_dimension"] = 0.0
    loader = DomainPackLoader()

    errors = loader.validate_pack(pack)

    assert any("unknown dimensions" in error for error in errors)


@pytest.mark.parametrize("dimension", ["methodology", "evaluation"])
def test_validate_pack_negative_weight_rejected(dimension: str) -> None:
    pack = _valid_pack()
    pack.dimension_weights[dimension] = -0.01
    loader = DomainPackLoader()

    errors = loader.validate_pack(pack)

    assert any("cannot be negative" in error for error in errors)


@pytest.mark.parametrize("threshold", [-1.0, 101.0])
def test_validate_pack_gate_threshold_range(threshold: float) -> None:
    pack = _valid_pack()
    pack.gate_threshold = threshold
    loader = DomainPackLoader()

    errors = loader.validate_pack(pack)

    assert any("gate_threshold" in error for error in errors)


@pytest.mark.parametrize("threshold", [-0.1, 1.1])
def test_validate_pack_detection_threshold_range(threshold: float) -> None:
    pack = _valid_pack()
    pack.detection_threshold = threshold
    loader = DomainPackLoader()

    errors = loader.validate_pack(pack)

    assert any("detection_threshold" in error for error in errors)


def test_validate_pack_unknown_scoring_signal_dimension_rejected() -> None:
    pack = _valid_pack()
    pack.scoring_signals["unknown_dim"] = [r"x"]
    loader = DomainPackLoader()

    errors = loader.validate_pack(pack)

    assert any("scoring_signals has unknown dimension" in error for error in errors)


def test_validate_pack_empty_scoring_signal_pattern_rejected() -> None:
    pack = _valid_pack()
    pack.scoring_signals["methodology"] = [" "]
    loader = DomainPackLoader()

    errors = loader.validate_pack(pack)

    assert any("contains empty pattern" in error for error in errors)


def test_validate_pack_requires_recommended_journals() -> None:
    pack = _valid_pack()
    pack.recommended_journals = []
    loader = DomainPackLoader()

    errors = loader.validate_pack(pack)

    assert any("recommended_journals" in error for error in errors)


def test_validate_pack_requires_detection_keywords() -> None:
    pack = _valid_pack()
    pack.detection_keywords = []
    loader = DomainPackLoader()

    errors = loader.validate_pack(pack)

    assert any("detection_keywords" in error for error in errors)
