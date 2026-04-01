# pyright: reportMissingImports=false

from __future__ import annotations

from pathlib import Path

import pytest

from crane.models.paper_profile import DimensionScore
from crane.services.feynman_session_service import FeynmanQuestion
from crane.services.feynman_session_service import FeynmanSession
from crane.services.feynman_session_service import FeynmanSessionService


def _score(
    dimension: str,
    score: float,
    reason_codes: list[str] | None = None,
    evidence_spans: list[str] | None = None,
    missing_evidence: list[str] | None = None,
    suggestions: list[str] | None = None,
) -> DimensionScore:
    return DimensionScore(
        dimension=dimension,
        score=score,
        confidence=0.8,
        reason_codes=reason_codes or [],
        evidence_spans=evidence_spans or [],
        missing_evidence=missing_evidence or [],
        suggestions=suggestions or [],
    )


def _service() -> FeynmanSessionService:
    return FeynmanSessionService()


def test_feynman_question_rejects_empty_question() -> None:
    with pytest.raises(ValueError, match="question cannot be empty"):
        FeynmanQuestion(
            dimension="methodology",
            question="",
            section="Method",
            difficulty="basic",
            expected_insight="clarity",
        )


@pytest.mark.parametrize("difficulty", ["", "hard", "BASIC", "expert"])
def test_feynman_question_rejects_invalid_difficulty(difficulty: str) -> None:
    with pytest.raises(ValueError, match="difficulty must be basic/probing/challenging"):
        FeynmanQuestion(
            dimension="methodology",
            question="Why this method?",
            section="Method",
            difficulty=difficulty,
            expected_insight="clarity",
        )


def test_feynman_question_accepts_valid_values() -> None:
    q = FeynmanQuestion(
        dimension="methodology",
        question="Why this method?",
        section="Method",
        difficulty="probing",
        expected_insight="clarity",
    )
    assert q.question == "Why this method?"
    assert q.difficulty == "probing"


def test_feynman_session_filters_by_dimension_and_difficulty() -> None:
    session = FeynmanSession(
        paper_path="paper.tex",
        mode="post_evaluation",
        focus_dimensions=["methodology", "evaluation"],
        questions=[
            FeynmanQuestion("methodology", "Q1", "Method", "basic", "I1"),
            FeynmanQuestion("evaluation", "Q2", "Results", "probing", "I2"),
            FeynmanQuestion("methodology", "Q3", "Method", "challenging", "I3"),
        ],
        total_questions=3,
        weak_dimensions=["methodology"],
    )

    assert [q.question for q in session.by_dimension("methodology")] == ["Q1", "Q3"]
    assert [q.question for q in session.by_difficulty("probing")] == ["Q2"]


def test_generate_session_auto_selects_weak_dimensions() -> None:
    svc = _service()
    session = svc.generate_session(
        dimension_scores=[
            _score("methodology", 58),
            _score("novelty", 65),
            _score("evaluation", 83),
        ],
        mode="post_evaluation",
        focus_dimensions=None,
        num_questions=6,
    )

    assert session.focus_dimensions == ["methodology", "novelty"]
    assert session.weak_dimensions == ["methodology", "novelty"]
    assert all(q.dimension in {"methodology", "novelty"} for q in session.questions)


def test_generate_session_all_scores_high_returns_empty_for_post_evaluation() -> None:
    svc = _service()
    session = svc.generate_session(
        dimension_scores=[_score("methodology", 80), _score("novelty", 90)],
        mode="post_evaluation",
        num_questions=5,
    )

    assert session.questions == []
    assert session.total_questions == 0
    assert session.weak_dimensions == []


def test_generate_session_focus_dimensions_override_auto_selection() -> None:
    svc = _service()
    session = svc.generate_session(
        dimension_scores=[
            _score("methodology", 90),
            _score("evaluation", 55),
            _score("presentation", 50),
        ],
        focus_dimensions=["methodology"],
        num_questions=2,
    )
    assert session.focus_dimensions == ["methodology"]
    assert len(session.questions) == 2
    assert all(q.dimension == "methodology" for q in session.questions)


@pytest.mark.parametrize(
    "num_questions",
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12],
)
def test_generate_session_respects_num_questions_limit(num_questions: int) -> None:
    svc = _service()
    session = svc.generate_session(
        dimension_scores=[_score("evaluation", 55)],
        num_questions=num_questions,
        mode="post_evaluation",
    )
    assert session.total_questions <= num_questions
    if num_questions <= 5:
        assert session.total_questions == num_questions
    else:
        assert session.total_questions == 5


def test_generate_session_distributes_questions_across_dimensions() -> None:
    svc = _service()
    session = svc.generate_session(
        dimension_scores=[
            _score("methodology", 50),
            _score("novelty", 55),
            _score("evaluation", 60),
        ],
        num_questions=6,
        mode="post_evaluation",
    )

    by_dim = {dim: len(session.by_dimension(dim)) for dim in session.focus_dimensions}
    assert by_dim["methodology"] >= 2
    assert by_dim["novelty"] >= 2
    assert by_dim["evaluation"] >= 2


@pytest.mark.parametrize("count", [1, 2, 3, 4, 5, 6, 7, 8])
def test_select_questions_for_dimension_mixes_difficulties(count: int) -> None:
    svc = _service()
    selected = svc._select_questions_for_dimension(
        dimension="methodology",
        score=_score(
            "methodology",
            58,
            reason_codes=["deep learning"],
            evidence_spans=["Method: Transformer block"],
            missing_evidence=["ablation details"],
            suggestions=["report seed stability"],
        ),
        count=count,
    )
    difficulties = [q.difficulty for q in selected]
    assert len(selected) == count
    assert difficulties[0] == "basic"
    if count >= 3:
        assert "challenging" in difficulties
    if count >= 2:
        assert "probing" in difficulties


def test_select_questions_fills_template_placeholders() -> None:
    svc = _service()
    selected = svc._select_questions_for_dimension(
        dimension="novelty",
        score=_score(
            "novelty",
            52,
            evidence_spans=["Related Work: Model-A"],
            missing_evidence=["formal novelty claim"],
            suggestions=["show 7.5% gain"],
        ),
        count=3,
    )
    rendered = "\n".join(q.question for q in selected)
    assert "{" not in rendered
    assert "}" not in rendered


def test_generate_session_report_markdown_structure() -> None:
    svc = _service()
    session = svc.generate_session(
        dimension_scores=[_score("methodology", 58), _score("evaluation", 62)],
        num_questions=4,
        mode="post_evaluation",
        paper_path="paper.tex",
    )

    report = svc.generate_session_report(session)

    assert report.startswith("# Feynman Session: Test Your Understanding")
    assert "**Mode**: post_evaluation" in report
    assert "## methodology" in report
    assert "### Question 1" in report
    assert "*What a good answer covers*" in report


def test_generate_session_report_for_empty_session() -> None:
    svc = _service()
    session = FeynmanSession(
        paper_path="paper.tex",
        mode="post_evaluation",
        focus_dimensions=[],
        questions=[],
        total_questions=0,
        weak_dimensions=[],
    )
    report = svc.generate_session_report(session)
    assert "No questions generated" in report


def test_mode_specific_behavior_post_evaluation_vs_pre_submission() -> None:
    svc = _service()
    scores = [
        _score("methodology", 75),
        _score("evaluation", 72),
        _score("reproducibility", 85),
        _score("limitations", 88),
    ]

    post_session = svc.generate_session(scores, mode="post_evaluation", num_questions=6)
    pre_session = svc.generate_session(scores, mode="pre_submission", num_questions=6)

    assert post_session.total_questions == 0
    assert "reproducibility" in pre_session.focus_dimensions
    assert "limitations" in pre_session.focus_dimensions
    assert pre_session.total_questions > 0


@pytest.mark.parametrize(
    ("mode", "expected_focus"),
    [
        ("methodology", ["methodology"]),
        ("writing", ["writing_quality", "presentation"]),
    ],
)
def test_mode_specific_dimension_defaults(mode: str, expected_focus: list[str]) -> None:
    svc = _service()
    session = svc.generate_session(
        dimension_scores=[
            _score("methodology", 95),
            _score("writing_quality", 92),
            _score("presentation", 89),
        ],
        mode=mode,
        num_questions=3,
    )
    assert session.focus_dimensions == expected_focus


def test_generate_session_single_dimension_edge_case() -> None:
    svc = _service()
    session = svc.generate_session(
        dimension_scores=[_score("presentation", 50)],
        num_questions=3,
    )
    assert session.focus_dimensions == ["presentation"]
    assert len(session.questions) == 2


def test_generate_session_zero_questions_edge_case() -> None:
    svc = _service()
    session = svc.generate_session(
        dimension_scores=[_score("evaluation", 40)],
        num_questions=0,
    )
    assert session.questions == []
    assert session.total_questions == 0


def test_generate_session_rejects_negative_num_questions() -> None:
    svc = _service()
    with pytest.raises(ValueError, match="num_questions must be >= 0"):
        svc.generate_session(
            dimension_scores=[_score("evaluation", 40)],
            num_questions=-1,
        )


def test_generate_session_rejects_invalid_mode() -> None:
    svc = _service()
    with pytest.raises(ValueError, match="mode must be one of"):
        svc.generate_session(
            dimension_scores=[_score("evaluation", 40)],
            mode="unknown",
            num_questions=2,
        )


@pytest.mark.parametrize(
    "template_file,placeholders",
    [
        (
            "feynman_student.txt",
            [
                "{section_name}",
                "{section_text}",
                "{dimension}",
                "{score}",
                "{missing_evidence}",
                "{num_questions}",
            ],
        ),
        (
            "feynman_sifu.txt",
            [
                "{question}",
                "{section_text}",
                "{dimension}",
                "{score}",
                "{missing_evidence}",
            ],
        ),
    ],
)
def test_prompt_templates_exist_and_contain_placeholders(
    template_file: str,
    placeholders: list[str],
) -> None:
    path = Path("src/crane/templates/llm") / template_file
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    for placeholder in placeholders:
        assert placeholder in content
