"""Tests for Issue #107: Feynman interactive mode."""

from __future__ import annotations

import pytest

from crane.models.paper_profile import DimensionScore
from crane.services.feynman_session_service import (
    FeynmanInteractiveSession,
    FeynmanQuestion,
    FeynmanSessionService,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_score(dimension: str, score: float = 55.0) -> DimensionScore:
    return DimensionScore(
        dimension=dimension,
        score=score,
        confidence=0.8,
        reason_codes=["test"],
        evidence_spans=["Section: example"],
        missing_evidence=["baseline"],
        suggestions=["Add more experiments"],
    )


def _make_question(expected_insight: str = "core concept understanding") -> FeynmanQuestion:
    return FeynmanQuestion(
        dimension="methodology",
        question="Explain your method.",
        section="General",
        difficulty="basic",
        expected_insight=expected_insight,
    )


# ---------------------------------------------------------------------------
# start_interactive
# ---------------------------------------------------------------------------


class TestStartInteractive:
    def test_returns_session_with_first_question(self):
        svc = FeynmanSessionService()
        scores = [_make_score("methodology"), _make_score("novelty")]
        session = svc.start_interactive(scores, paper_path="paper.tex", num_questions=3)

        assert isinstance(session, FeynmanInteractiveSession)
        assert session.current_index == 0
        assert session.completed is False
        q = session.current_question()
        assert q is not None
        assert isinstance(q.question, str) and len(q.question) > 0

    def test_session_id_has_feynman_prefix(self):
        svc = FeynmanSessionService()
        scores = [_make_score("evaluation")]
        session = svc.start_interactive(scores)
        assert session.session_id.startswith("feynman_")

    def test_num_questions_respected(self):
        svc = FeynmanSessionService()
        scores = [_make_score("methodology"), _make_score("evaluation")]
        session = svc.start_interactive(scores, num_questions=2)
        assert len(session.questions) <= 2


# ---------------------------------------------------------------------------
# evaluate_answer — pass path
# ---------------------------------------------------------------------------


class TestEvaluateAnswerPass:
    def test_good_answer_advances_index(self):
        svc = FeynmanSessionService()
        q = _make_question("core concept understanding")
        session = FeynmanInteractiveSession(
            session_id="feynman_test",
            paper_path="p.tex",
            questions=[q, q],
            current_index=0,
            answers=[],
            scores=[],
            completed=False,
        )
        # Answer contains 2+ keywords from expected_insight and is long enough
        answer = "The core concept understanding here is that we optimize the method by iterating."
        result = svc.evaluate_answer(session, answer, confidence=4)

        assert result["result"] == "pass"
        assert "score" in result
        assert session.current_index == 1
        assert len(session.answers) == 1

    def test_good_answer_on_last_question_completes(self):
        svc = FeynmanSessionService()
        q = _make_question("core concept understanding")
        session = FeynmanInteractiveSession(
            session_id="feynman_test2",
            paper_path="p.tex",
            questions=[q],
            current_index=0,
            answers=[],
            scores=[],
            completed=False,
        )
        # answer >= 10 words and contains 2+ keywords from expected_insight → score 0.8
        answer = "The core concept understanding drives everything in this method and is essential."
        result = svc.evaluate_answer(session, answer, confidence=4)

        assert result["result"] == "completed"
        assert "summary" in result
        assert session.completed is True


# ---------------------------------------------------------------------------
# evaluate_answer — retry path
# ---------------------------------------------------------------------------


class TestEvaluateAnswerRetry:
    def test_short_answer_returns_retry(self):
        svc = FeynmanSessionService()
        q = _make_question()
        session = FeynmanInteractiveSession(
            session_id="feynman_retry",
            paper_path="p.tex",
            questions=[q],
            current_index=0,
            answers=[],
            scores=[],
            completed=False,
        )
        result = svc.evaluate_answer(session, "IDK", confidence=5)

        assert result["result"] == "retry"
        assert result["score"] < 0.6
        # index must NOT advance
        assert session.current_index == 0

    def test_low_confidence_causes_retry_even_with_ok_answer(self):
        svc = FeynmanSessionService()
        q = _make_question("core concept understanding")
        session = FeynmanInteractiveSession(
            session_id="feynman_conf",
            paper_path="p.tex",
            questions=[q],
            current_index=0,
            answers=[],
            scores=[],
            completed=False,
        )
        answer = "The core concept understanding drives everything in this method."
        result = svc.evaluate_answer(session, answer, confidence=2)  # < 3

        assert result["result"] == "retry"
        assert session.current_index == 0


# ---------------------------------------------------------------------------
# Jargon detection
# ---------------------------------------------------------------------------


class TestJargonDetection:
    def test_three_acronyms_flagged(self):
        svc = FeynmanSessionService()
        q = _make_question()
        answer = "BERT LSTM GPT are used in this NLP pipeline."
        score, jargon, unclear = svc._score_answer(q, answer)
        assert jargon is True
        assert unclear in {"BERT", "LSTM", "GPT", "NLP"}

    def test_no_acronyms_not_flagged(self):
        svc = FeynmanSessionService()
        q = _make_question()
        answer = "The model learns representations from data using gradient descent iteratively."
        score, jargon, unclear = svc._score_answer(q, answer)
        assert jargon is False
        assert unclear == ""

    def test_jargon_hint_mentions_acronym(self):
        svc = FeynmanSessionService()
        q = _make_question()
        hint = svc._build_retry_hint(q, jargon=True, unclear="BERT")
        assert "BERT" in hint

    def test_no_jargon_hint_mentions_expected_insight(self):
        svc = FeynmanSessionService()
        q = _make_question("core concept understanding")
        hint = svc._build_retry_hint(q, jargon=False, unclear="")
        assert "core concept understanding" in hint


# ---------------------------------------------------------------------------
# to_dict / from_dict round-trip
# ---------------------------------------------------------------------------


class TestSerialization:
    def _make_session(self) -> FeynmanInteractiveSession:
        q = _make_question()
        return FeynmanInteractiveSession(
            session_id="feynman_42",
            paper_path="my_paper.tex",
            questions=[q, q],
            current_index=1,
            answers=["Some answer"],
            scores=[0.75],
            completed=False,
        )

    def test_round_trip_preserves_fields(self):
        session = self._make_session()
        data = session.to_dict()
        restored = FeynmanInteractiveSession.from_dict(data)

        assert restored.session_id == session.session_id
        assert restored.paper_path == session.paper_path
        assert restored.current_index == session.current_index
        assert restored.answers == session.answers
        assert restored.scores == session.scores
        assert restored.completed == session.completed
        assert len(restored.questions) == len(session.questions)

    def test_round_trip_preserves_question_fields(self):
        session = self._make_session()
        data = session.to_dict()
        restored = FeynmanInteractiveSession.from_dict(data)

        orig_q = session.questions[0]
        rest_q = restored.questions[0]
        assert rest_q.dimension == orig_q.dimension
        assert rest_q.question == orig_q.question
        assert rest_q.difficulty == orig_q.difficulty
        assert rest_q.expected_insight == orig_q.expected_insight

    def test_to_dict_is_json_serializable(self):
        import json

        session = self._make_session()
        payload = json.dumps(session.to_dict())
        assert isinstance(payload, str)

    def test_completed_session_round_trip(self):
        q = _make_question()
        session = FeynmanInteractiveSession(
            session_id="feynman_done",
            paper_path="p.tex",
            questions=[q],
            current_index=1,
            answers=["answer"],
            scores=[0.8],
            completed=True,
        )
        restored = FeynmanInteractiveSession.from_dict(session.to_dict())
        assert restored.completed is True


# ---------------------------------------------------------------------------
# build_summary
# ---------------------------------------------------------------------------


class TestBuildSummary:
    def test_summary_after_all_answered(self):
        svc = FeynmanSessionService()
        q1 = _make_question("methodology insight")
        q2 = FeynmanQuestion(
            dimension="evaluation",
            question="Explain your metrics.",
            section="Results",
            difficulty="probing",
            expected_insight="metric rationale",
        )
        session = FeynmanInteractiveSession(
            session_id="feynman_sum",
            paper_path="p.tex",
            questions=[q1, q2],
            current_index=2,
            answers=["ans1", "ans2"],
            scores=[0.9, 0.4],
            completed=True,
        )
        summary = svc._build_summary(session)

        assert summary["average_score"] == pytest.approx(0.65, abs=0.01)
        assert summary["weakest_dimension"] == "evaluation"
        assert summary["strongest_dimension"] == "methodology"
        assert summary["total_questions"] == 2
        assert summary["answers_given"] == 2
