"""Tests for JudgeReliabilityService."""

import pytest
from crane.services.judge_reliability_service import (
    JudgeReliabilityService,
    TransitivityResult,
    ConformalResult,
    ReliabilityReport,
)


def test_transitivity_no_violations():
    """Test when all preferences are consistent (no cycles)."""
    service = JudgeReliabilityService()
    preferences = [
        ("A", "B", "A"),  # A > B
        ("B", "C", "B"),  # B > C
        ("A", "C", "A"),  # A > C (consistent)
    ]
    result = service.check_transitivity(preferences)
    assert result.has_cycles is False
    assert result.violation_rate == 0.0


def test_transitivity_with_cycle():
    service = JudgeReliabilityService()
    preferences = [
        ("A", "B", "A"),
        ("B", "C", "A"),
        ("C", "A", "A"),
    ]
    result = service.check_transitivity(preferences)
    assert result.has_cycles is True


def test_conformal_prediction_set():
    """Test conformal prediction set generation."""
    service = JudgeReliabilityService(alpha=0.10)
    calibration = [3, 4, 3, 5, 4, 3, 4, 5]

    result = service.generate_conformal_set(score=4, calibration_scores=calibration)

    assert 1 <= result.set_width <= 5
    assert 1.0 <= result.reliability_score <= 10.0
    assert result.coverage_guarantee == 0.90


def test_reliability_analysis():
    """Test overall reliability analysis."""
    service = JudgeReliabilityService()
    scores = {
        "coherence": 4,
        "relevance": 5,
        "fluency": 3,
        "consistency": 3,
    }

    report = service.analyze_reliability(scores, criterion="coherence")

    assert 1.0 <= report.overall_reliability <= 10.0
    assert report.difficulty_class in ["easy", "medium", "hard"]


def test_trust_signals():
    """Test trust signal generation."""
    service = JudgeReliabilityService()

    assert "HIGH" in service.get_trust_signal(9.0)
    assert "MEDIUM" in service.get_trust_signal(5.5)
    assert "LOW" in service.get_trust_signal(2.0)


def test_calibration_data():
    """Test calibration data accumulation."""
    service = JudgeReliabilityService()

    service.add_calibration_score("coherence", 4)
    service.add_calibration_score("coherence", 5)

    assert len(service._calibration_scores["coherence"]) == 2