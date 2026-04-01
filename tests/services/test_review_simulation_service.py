# pyright: reportMissingImports=false

from __future__ import annotations

from pathlib import Path

from crane.models.paper_profile import (
    DimensionScore,
    EvidencePattern,
    NoveltyShape,
    PaperProfile,
)
from crane.services.review_simulation_service import ReviewSimulationService


def _score(dimension: str, score: float, confidence: float = 0.8) -> DimensionScore:
    return DimensionScore(dimension=dimension, score=score, confidence=confidence)


def _profile(*, keywords: list[str] | None = None, has_code: bool = True) -> PaperProfile:
    return PaperProfile(
        problem_domain="machine learning",
        method_family="transformer",
        validation_scale="multi-dataset",
        novelty_shape=NoveltyShape.NEW_METHOD,
        evidence_pattern=EvidencePattern.MIXED,
        keywords=keywords or [],
        has_code=has_code,
        has_appendix=True,
        word_count=7000,
    )


def _write_patterns(path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    data = (root / "data" / "review_patterns.yaml").read_text(encoding="utf-8")
    path.write_text(data, encoding="utf-8")


def test_load_patterns_from_yaml_reads_all_ten(tmp_path) -> None:
    patterns_path = tmp_path / "review_patterns.yaml"
    _write_patterns(patterns_path)

    service = ReviewSimulationService(patterns_path)

    assert len(service.patterns) == 10


def test_load_patterns_contains_required_pattern_names(tmp_path) -> None:
    patterns_path = tmp_path / "review_patterns.yaml"
    _write_patterns(patterns_path)

    service = ReviewSimulationService(patterns_path)
    names = {item.name for item in service.patterns}

    assert {
        "novelty_concerns",
        "weak_baselines",
        "methodology_unclear",
        "insufficient_experiments",
        "reproducibility_concerns",
        "overclaiming",
        "poor_writing_quality",
        "missing_limitations",
        "statistical_rigor",
        "presentation_issues",
    }.issubset(names)


def test_load_patterns_missing_file_returns_empty() -> None:
    service = ReviewSimulationService("/tmp/does-not-exist-patterns.yaml")

    assert service.patterns == []


def test_load_patterns_invalid_document_returns_empty(tmp_path) -> None:
    path = tmp_path / "invalid.yaml"
    path.write_text("[]", encoding="utf-8")

    service = ReviewSimulationService(path)

    assert service.patterns == []


def test_load_patterns_skips_non_dict_entries(tmp_path) -> None:
    path = tmp_path / "patterns.yaml"
    path.write_text("patterns:\n  - abc\n  - 1\n", encoding="utf-8")

    service = ReviewSimulationService(path)

    assert service.patterns == []


def test_load_patterns_skips_invalid_trigger_signal_shape(tmp_path) -> None:
    path = tmp_path / "patterns.yaml"
    path.write_text(
        "patterns:\n"
        "  - name: p\n"
        "    description: d\n"
        "    severity: major\n"
        "    dimension: novelty\n"
        "    trigger_signals: text\n"
        "    example_critique: c\n",
        encoding="utf-8",
    )

    service = ReviewSimulationService(path)

    assert service.patterns == []


def test_predict_criticisms_high_scores_yield_accept(tmp_path) -> None:
    patterns_path = tmp_path / "review_patterns.yaml"
    _write_patterns(patterns_path)
    service = ReviewSimulationService(patterns_path)

    prediction = service.predict_criticisms(
        dimension_scores=[
            _score("methodology", 90),
            _score("novelty", 92),
            _score("evaluation", 91),
            _score("writing_quality", 93),
            _score("reproducibility", 88),
            _score("limitations", 86),
            _score("presentation", 90),
        ],
        profile=_profile(keywords=["robustness", "benchmarking"]),
    )

    assert prediction.predicted_decision == "accept"
    assert prediction.overall_sentiment == "encouraging"


def test_predict_criticisms_low_scores_without_gate_failure_major_revisions(tmp_path) -> None:
    patterns_path = tmp_path / "review_patterns.yaml"
    _write_patterns(patterns_path)
    service = ReviewSimulationService(patterns_path)

    prediction = service.predict_criticisms(
        dimension_scores=[
            _score("methodology", 65),
            _score("novelty", 66),
            _score("evaluation", 65),
            _score("writing_quality", 64),
            _score("reproducibility", 63),
            _score("limitations", 68),
            _score("presentation", 67),
        ],
        profile=_profile(
            keywords=[
                "incremental improvement",
                "missing sota comparison",
                "single run results",
                "no ablation",
                "code unavailable",
                "state of the art everywhere",
            ],
            has_code=False,
        ),
    )

    assert prediction.predicted_decision == "major_revisions"
    assert len(prediction.criticisms) >= 3


def test_predict_criticisms_gate_failure_yields_reject(tmp_path) -> None:
    patterns_path = tmp_path / "review_patterns.yaml"
    _write_patterns(patterns_path)
    service = ReviewSimulationService(patterns_path)

    prediction = service.predict_criticisms(
        dimension_scores=[
            _score("methodology", 40),
            _score("novelty", 50),
            _score("evaluation", 55),
            _score("writing_quality", 85),
        ],
        profile=_profile(keywords=["unclear method"]),
    )

    assert prediction.predicted_decision == "reject"
    assert prediction.overall_sentiment == "harsh"


def test_predict_criticisms_empty_scores_still_returns_prediction(tmp_path) -> None:
    patterns_path = tmp_path / "review_patterns.yaml"
    _write_patterns(patterns_path)
    service = ReviewSimulationService(patterns_path)

    prediction = service.predict_criticisms([], _profile())

    assert prediction.predicted_decision in {
        "accept",
        "minor_revisions",
        "major_revisions",
        "reject",
    }
    assert 0.0 <= prediction.confidence <= 1.0


def test_predict_criticisms_unknown_dimensions_are_ignored(tmp_path) -> None:
    patterns_path = tmp_path / "review_patterns.yaml"
    _write_patterns(patterns_path)
    service = ReviewSimulationService(patterns_path)

    prediction = service.predict_criticisms(
        [_score("new_dimension", 20), _score("another", 50)],
        _profile(),
    )

    assert prediction.predicted_decision != "reject"


def test_predict_criticisms_matches_trigger_signals(tmp_path) -> None:
    patterns_path = tmp_path / "review_patterns.yaml"
    _write_patterns(patterns_path)
    service = ReviewSimulationService(patterns_path)

    prediction = service.predict_criticisms(
        [_score("novelty", 60), _score("methodology", 75), _score("evaluation", 75)],
        _profile(keywords=["incremental improvement", "similar to prior work"]),
    )

    novelty_items = [
        item for item in prediction.criticisms if item.pattern.name == "novelty_concerns"
    ]
    assert novelty_items
    assert len(novelty_items[0].matched_signals) >= 1


def test_predict_criticisms_sorted_by_likelihood_desc(tmp_path) -> None:
    patterns_path = tmp_path / "review_patterns.yaml"
    _write_patterns(patterns_path)
    service = ReviewSimulationService(patterns_path)

    prediction = service.predict_criticisms(
        [_score("evaluation", 50), _score("novelty", 68), _score("methodology", 68)],
        _profile(keywords=["missing sota comparison", "single run results"]),
    )
    values = [item.likelihood for item in prediction.criticisms]

    assert values == sorted(values, reverse=True)


def test_predict_criticisms_confidence_within_bounds(tmp_path) -> None:
    patterns_path = tmp_path / "review_patterns.yaml"
    _write_patterns(patterns_path)
    service = ReviewSimulationService(patterns_path)

    prediction = service.predict_criticisms(
        [_score("evaluation", 75, 0.3), _score("novelty", 78, 0.4), _score("methodology", 80, 0.5)],
        _profile(),
    )

    assert 0.0 <= prediction.confidence <= 1.0


def test_predict_criticisms_with_no_patterns_returns_accept_like_signal() -> None:
    service = ReviewSimulationService("/tmp/missing-patterns.yaml")

    prediction = service.predict_criticisms(
        [_score("methodology", 85), _score("novelty", 86), _score("evaluation", 88)],
        _profile(),
    )

    assert prediction.criticisms == []
    assert prediction.predicted_decision == "accept"


def test_generate_mock_review_produces_structured_text(tmp_path) -> None:
    patterns_path = tmp_path / "review_patterns.yaml"
    _write_patterns(patterns_path)
    service = ReviewSimulationService(patterns_path)
    prediction = service.predict_criticisms(
        [_score("methodology", 62), _score("novelty", 61), _score("evaluation", 60)],
        _profile(keywords=["unclear method", "incremental improvement", "no baseline comparison"]),
    )

    review = service.generate_mock_review(prediction)

    assert "Summary" in review
    assert "Major Points" in review
    assert "Minor Notes" in review


def test_generate_mock_review_without_criticisms_has_positive_line() -> None:
    service = ReviewSimulationService("/tmp/missing-patterns.yaml")
    prediction = service.predict_criticisms(
        [_score("methodology", 90), _score("novelty", 91), _score("evaluation", 90)],
        _profile(),
    )

    review = service.generate_mock_review(prediction)

    assert "generally solid" in review


def test_generate_mock_review_includes_suggested_fix_when_high_likelihood(tmp_path) -> None:
    patterns_path = tmp_path / "review_patterns.yaml"
    _write_patterns(patterns_path)
    service = ReviewSimulationService(patterns_path)
    prediction = service.predict_criticisms(
        [_score("evaluation", 55), _score("novelty", 70), _score("methodology", 70)],
        _profile(keywords=["missing sota comparison", "single run results"]),
    )

    review = service.generate_mock_review(prediction)

    assert "Suggested fix:" in review


def test_predict_criticisms_produces_minor_revisions_for_one_major_issue(tmp_path) -> None:
    patterns_path = tmp_path / "review_patterns.yaml"
    _write_patterns(patterns_path)
    service = ReviewSimulationService(patterns_path)
    prediction = service.predict_criticisms(
        [
            _score("methodology", 78),
            _score("novelty", 80),
            _score("evaluation", 64),
            _score("writing_quality", 90),
        ],
        _profile(keywords=["missing sota comparison"]),
    )

    assert prediction.predicted_decision == "minor_revisions"


def test_predict_criticisms_sentiment_balanced_for_minor_revisions(tmp_path) -> None:
    patterns_path = tmp_path / "review_patterns.yaml"
    _write_patterns(patterns_path)
    service = ReviewSimulationService(patterns_path)
    prediction = service.predict_criticisms(
        [_score("methodology", 78), _score("novelty", 80), _score("evaluation", 64)],
        _profile(keywords=["missing sota comparison"]),
    )

    assert prediction.overall_sentiment == "balanced"
