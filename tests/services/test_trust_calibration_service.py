# pyright: reportMissingImports=false

from __future__ import annotations

import pytest

from crane.services.trust_calibration_service import TrustCalibrationService


class _StubPermissionRuleService:
    def __init__(self, project_dir: str | None = None):
        self.project_dir = project_dir

    def evaluate_action(self, action: str, context: dict | None = None) -> str:
        _ = context
        lowered = action.lower()
        if "danger" in lowered or "delete" in lowered:
            return "deny"
        if "read" in lowered or "analyze" in lowered:
            return "allow"
        return "ask"


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> TrustCalibrationService:
    monkeypatch.setattr(
        "crane.services.trust_calibration_service.PermissionRuleService",
        _StubPermissionRuleService,
    )
    return TrustCalibrationService()


def test_quantify_uncertainty_low_for_high_confidence_evidence(
    service: TrustCalibrationService,
) -> None:
    output = {
        "confidence": 0.93,
        "evidence_spans": ["a", "b", "c"],
        "missing_evidence": [],
        "contradictions": [],
    }

    uncertainty = service.quantify_uncertainty(output, "analyze paper quality")
    assert 0.0 <= uncertainty < 0.25


def test_quantify_uncertainty_high_for_low_confidence_hallucination(
    service: TrustCalibrationService,
) -> None:
    output = {
        "confidence": 0.1,
        "evidence_spans": [],
        "missing_evidence": ["m1", "m2", "m3"],
        "contradictions": ["c1", "c2"],
        "hallucination_detected": True,
    }

    uncertainty = service.quantify_uncertainty(output, "open-ended novel hypothesis generation")
    assert uncertainty > 0.85


def test_quantify_uncertainty_clamps_invalid_confidence(service: TrustCalibrationService) -> None:
    output = {"confidence": 9.0, "evidence_spans": ["e1", "e2", "e3"]}
    uncertainty = service.quantify_uncertainty(output, "analyze")
    assert 0.0 <= uncertainty <= 0.2


def test_get_autonomy_level_human_approval_override(service: TrustCalibrationService) -> None:
    level = service.get_autonomy_level(
        "analyze references",
        {"require_human_approval": True, "preferred_autonomy_level": 3},
    )
    assert level == 0


def test_get_autonomy_level_preference_downshifted_by_high_risk_task(
    service: TrustCalibrationService,
) -> None:
    level = service.get_autonomy_level(
        "submit camera-ready paper to venue",
        {"preferred_autonomy_level": 3},
    )
    assert level == 2


def test_get_autonomy_level_infers_from_trust_and_risk_tolerance(
    service: TrustCalibrationService,
) -> None:
    level = service.get_autonomy_level(
        "analyze benchmark results",
        {"trust_score": 0.88, "risk_tolerance": 0.85},
    )
    assert level == 3


def test_adjust_autonomy_reduces_on_high_risk_or_uncertainty(
    service: TrustCalibrationService,
) -> None:
    assert service.adjust_autonomy(3, uncertainty=0.9, risk_score=0.2) == 1
    assert service.adjust_autonomy(3, uncertainty=0.2, risk_score=0.95) == 1


def test_adjust_autonomy_increases_when_safe_and_trusted(service: TrustCalibrationService) -> None:
    service.trust_score = 0.9
    next_level = service.adjust_autonomy(1, uncertainty=0.1, risk_score=0.1)
    assert next_level == 3


def test_adjust_autonomy_stays_same_for_mid_conditions(service: TrustCalibrationService) -> None:
    assert service.adjust_autonomy(2, uncertainty=0.45, risk_score=0.45) == 2


def test_generate_responsibility_report_empty_defaults_balanced(
    service: TrustCalibrationService,
) -> None:
    report = service.generate_responsibility_report([])
    assert report["human_pct"] == 50.0
    assert report["ai_pct"] == 50.0
    assert report["total_decisions"] == 0


def test_generate_responsibility_report_weights_human_overrides(
    service: TrustCalibrationService,
) -> None:
    decisions = [
        {"actor": "ai", "autonomy_level": 2},
        {"actor": "ai", "autonomy_level": 2, "overridden_by_human": True},
        {"actor": "human", "autonomy_level": 0, "requires_human": True},
    ]

    report = service.generate_responsibility_report(decisions)
    assert report["human_pct"] > report["ai_pct"]
    assert report["total_decisions"] == 3


def test_calibrate_trust_increases_with_positive_feedback(service: TrustCalibrationService) -> None:
    before = service.trust_score
    result = service.calibrate_trust(
        {
            "satisfaction": 0.95,
            "accepted_recommendations": 12,
            "rejected_recommendations": 1,
            "override_rate": 0.1,
            "error_reports": 0,
        }
    )
    assert result["trust_score"] > before
    assert result["trend"] in {"increasing", "stable"}


def test_calibrate_trust_decreases_with_negative_feedback(service: TrustCalibrationService) -> None:
    baseline = service.trust_score
    result = service.calibrate_trust(
        {
            "satisfaction": 0.1,
            "accepted_recommendations": 1,
            "rejected_recommendations": 10,
            "override_rate": 0.9,
            "error_reports": 3,
        }
    )
    assert result["trust_score"] < baseline
    assert result["recommended_autonomy_cap"] <= 2


def test_permission_decision_level_zero_always_asks(service: TrustCalibrationService) -> None:
    decision = service.permission_decision_for_level(
        task="read local files",
        autonomy_level=0,
        uncertainty=0.1,
        risk_score=0.1,
    )
    assert decision["decision"] == "ask"


def test_permission_decision_level_one_allows_only_high_confidence(
    service: TrustCalibrationService,
) -> None:
    allow = service.permission_decision_for_level(
        task="analyze notes",
        autonomy_level=1,
        uncertainty=0.2,
        risk_score=0.2,
    )
    ask = service.permission_decision_for_level(
        task="analyze notes",
        autonomy_level=1,
        uncertainty=0.6,
        risk_score=0.2,
    )
    assert allow["decision"] == "allow"
    assert ask["decision"] == "ask"


def test_permission_decision_level_two_routes_high_risk_to_ask(
    service: TrustCalibrationService,
) -> None:
    decision = service.permission_decision_for_level(
        task="analyze experimental output",
        autonomy_level=2,
        uncertainty=0.2,
        risk_score=0.9,
    )
    assert decision["decision"] == "ask"


def test_permission_decision_level_three_allows_with_logging(
    service: TrustCalibrationService,
) -> None:
    decision = service.permission_decision_for_level(
        task="dangerous delete operation",
        autonomy_level=3,
        uncertainty=0.9,
        risk_score=0.9,
    )
    assert decision["decision"] == "allow"
    assert decision["requires_logging"] is True


def test_evaluate_calibration_returns_required_structure(service: TrustCalibrationService) -> None:
    result = service.evaluate_calibration(
        task="analyze citation consistency",
        output={"confidence": 0.8, "evidence_spans": ["x", "y"]},
        autonomy_level=2,
        user_preferences={
            "trust_score": 0.7,
            "risk_tolerance": 0.6,
            "feedback": {"satisfaction": 0.7, "accepted_recommendations": 4},
            "decisions": [{"actor": "ai", "autonomy_level": 2}],
        },
    )

    assert set(result.keys()) >= {
        "autonomy_level",
        "uncertainty",
        "recommended_action",
        "responsibility",
        "trust_score",
    }
    assert 0 <= result["autonomy_level"] <= 3
    assert 0.0 <= result["uncertainty"] <= 1.0
    assert 0.0 <= result["trust_score"] <= 1.0
    assert set(result["responsibility"].keys()) == {"human_pct", "ai_pct"}
