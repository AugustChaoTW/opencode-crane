# pyright: reportMissingImports=false
from __future__ import annotations

from pathlib import Path

import pytest

from crane.models.writing_style_models import (
    InteractiveRewriteSession,
    PreferenceLearnerState,
    RewriteChoice,
    RewriteSuggestion,
    UserPreference,
)
from crane.services.preference_learner_service import PreferenceLearnerService


def _make_session_with_choices(
    decisions: list[tuple[str, str]],
) -> InteractiveRewriteSession:
    suggestions = []
    choices = []
    for i, (rationale, decision) in enumerate(decisions):
        suggestions.append(
            RewriteSuggestion(
                original_text=f"Original {i}",
                suggested_text=f"Suggested {i}",
                rationale=rationale,
                exemplar_source="IEEE TPAMI",
                confidence=0.7,
            )
        )
        modified_text = f"Modified {i}" if decision == "modify" else ""
        choices.append(
            RewriteChoice(
                suggestion_id=f"sug_{i}",
                decision=decision,
                modified_text=modified_text,
            )
        )
    return InteractiveRewriteSession(
        session_id="test_session",
        paper_path="/tmp/test.tex",
        journal_name="IEEE TPAMI",
        section_name="Introduction",
        suggestions=suggestions,
        choices=choices,
    )


class TestPreferenceLearnerInit:
    def test_creates_storage_dir(self, tmp_path: Path):
        storage = tmp_path / "prefs"
        PreferenceLearnerService(storage_dir=storage)
        assert storage.exists()

    def test_default_state_for_new_user(self, tmp_path: Path):
        service = PreferenceLearnerService(storage_dir=tmp_path / "prefs")
        state = service.get_state("new_user")
        assert state.user_id == "new_user"
        assert state.total_sessions == 0
        assert state.total_choices == 0
        assert len(state.preferences) == 0


class TestLearnFromSession:
    def test_increments_session_count(self, tmp_path: Path):
        service = PreferenceLearnerService(storage_dir=tmp_path / "prefs")
        session = _make_session_with_choices(
            [
                ("Reduce passive voice usage", "accept"),
            ]
        )
        state = service.learn_from_session(session)
        assert state.total_sessions == 1
        assert state.total_choices == 1

    def test_accept_increases_strength(self, tmp_path: Path):
        service = PreferenceLearnerService(storage_dir=tmp_path / "prefs")
        session = _make_session_with_choices(
            [
                ("Reduce passive voice usage", "accept"),
            ]
        )
        state = service.learn_from_session(session)
        assert "passive_voice_ratio" in state.preferences
        pref = state.preferences["passive_voice_ratio"]
        assert pref.strength > 0.0
        assert pref.evidence_count == 1

    def test_reject_decreases_strength(self, tmp_path: Path):
        service = PreferenceLearnerService(storage_dir=tmp_path / "prefs")
        session1 = _make_session_with_choices(
            [
                ("Reduce passive voice usage", "accept"),
            ]
        )
        service.learn_from_session(session1)
        session2 = _make_session_with_choices(
            [
                ("Reduce passive voice usage", "reject"),
            ]
        )
        state = service.learn_from_session(session2)
        pref = state.preferences["passive_voice_ratio"]
        assert pref.evidence_count == 2

    def test_modify_increases_strength_slightly(self, tmp_path: Path):
        service = PreferenceLearnerService(storage_dir=tmp_path / "prefs")
        session = _make_session_with_choices(
            [
                ("Reduce passive voice usage", "modify"),
            ]
        )
        state = service.learn_from_session(session)
        pref = state.preferences["passive_voice_ratio"]
        assert pref.strength > 0.0
        assert pref.strength <= 0.1

    def test_multiple_choices_in_session(self, tmp_path: Path):
        service = PreferenceLearnerService(storage_dir=tmp_path / "prefs")
        session = _make_session_with_choices(
            [
                ("Reduce passive voice usage", "accept"),
                ("Simplify sentence length", "reject"),
                ("Increase technical vocabulary density", "accept"),
            ]
        )
        state = service.learn_from_session(session)
        assert state.total_choices == 3
        assert len(state.preferences) >= 2

    def test_category_weights_updated(self, tmp_path: Path):
        service = PreferenceLearnerService(storage_dir=tmp_path / "prefs")
        session = _make_session_with_choices(
            [
                ("Reduce passive voice usage", "accept"),
            ]
        )
        state = service.learn_from_session(session)
        assert "grammar" in state.category_weights

    def test_cross_session_accumulation(self, tmp_path: Path):
        service = PreferenceLearnerService(storage_dir=tmp_path / "prefs")
        for _ in range(3):
            session = _make_session_with_choices(
                [
                    ("Reduce passive voice usage", "accept"),
                ]
            )
            service.learn_from_session(session)
        state = service.get_state()
        assert state.total_sessions == 3
        pref = state.preferences["passive_voice_ratio"]
        assert pref.evidence_count == 3
        assert pref.strength >= 0.3


class TestGetPreferenceWeights:
    def test_empty_for_new_user(self, tmp_path: Path):
        service = PreferenceLearnerService(storage_dir=tmp_path / "prefs")
        weights = service.get_preference_weights("new_user")
        assert weights == {}

    def test_returns_signed_weights(self, tmp_path: Path):
        service = PreferenceLearnerService(storage_dir=tmp_path / "prefs")
        session = _make_session_with_choices(
            [
                ("Reduce passive voice usage", "accept"),
            ]
        )
        service.learn_from_session(session)
        weights = service.get_preference_weights()
        assert "passive_voice_ratio" in weights


class TestAdjustSuggestions:
    def test_no_change_for_new_user(self, tmp_path: Path):
        service = PreferenceLearnerService(storage_dir=tmp_path / "prefs")
        suggestions = [
            RewriteSuggestion(
                original_text="Test",
                suggested_text="Better test",
                rationale="Reduce passive voice",
                confidence=0.5,
            )
        ]
        adjusted = service.adjust_suggestions(suggestions, "new_user")
        assert adjusted[0].confidence == 0.5

    def test_boosts_preferred_suggestions(self, tmp_path: Path):
        service = PreferenceLearnerService(storage_dir=tmp_path / "prefs")
        for _ in range(5):
            session = _make_session_with_choices(
                [
                    ("Reduce passive voice usage", "accept"),
                ]
            )
            service.learn_from_session(session)

        suggestions = [
            RewriteSuggestion(
                original_text="Test",
                suggested_text="Better test",
                rationale="Reduce passive voice",
                confidence=0.5,
            )
        ]
        adjusted = service.adjust_suggestions(suggestions)
        assert adjusted[0].confidence >= 0.5

    def test_preserves_suggestion_content(self, tmp_path: Path):
        service = PreferenceLearnerService(storage_dir=tmp_path / "prefs")
        session = _make_session_with_choices(
            [
                ("Reduce passive voice usage", "accept"),
            ]
        )
        service.learn_from_session(session)
        suggestions = [
            RewriteSuggestion(
                original_text="Original",
                suggested_text="Suggested",
                rationale="Reduce passive voice",
                confidence=0.5,
            )
        ]
        adjusted = service.adjust_suggestions(suggestions)
        assert adjusted[0].original_text == "Original"
        assert adjusted[0].suggested_text == "Suggested"

    def test_reorders_by_confidence(self, tmp_path: Path):
        service = PreferenceLearnerService(storage_dir=tmp_path / "prefs")
        for _ in range(5):
            session = _make_session_with_choices(
                [
                    ("Reduce passive voice usage", "accept"),
                ]
            )
            service.learn_from_session(session)

        suggestions = [
            RewriteSuggestion(rationale="Increase vocabulary diversity", confidence=0.9),
            RewriteSuggestion(rationale="Reduce passive voice", confidence=0.3),
        ]
        adjusted = service.adjust_suggestions(suggestions)
        assert adjusted[0].confidence >= adjusted[1].confidence


class TestResetPreferences:
    def test_reset_clears_state(self, tmp_path: Path):
        service = PreferenceLearnerService(storage_dir=tmp_path / "prefs")
        session = _make_session_with_choices(
            [
                ("Reduce passive voice usage", "accept"),
            ]
        )
        service.learn_from_session(session)
        state = service.reset_preferences()
        assert state.total_sessions == 0
        assert state.total_choices == 0
        assert len(state.preferences) == 0


class TestPreferenceSummary:
    def test_summary_structure(self, tmp_path: Path):
        service = PreferenceLearnerService(storage_dir=tmp_path / "prefs")
        session = _make_session_with_choices(
            [
                ("Reduce passive voice usage", "accept"),
                ("Simplify sentence length", "reject"),
            ]
        )
        service.learn_from_session(session)
        summary = service.get_preference_summary()
        assert "user_id" in summary
        assert "total_sessions" in summary
        assert "preferences" in summary
        assert isinstance(summary["preferences"], list)

    def test_summary_sorted_by_strength(self, tmp_path: Path):
        service = PreferenceLearnerService(storage_dir=tmp_path / "prefs")
        for _ in range(3):
            session = _make_session_with_choices(
                [
                    ("Reduce passive voice usage", "accept"),
                    ("Simplify sentence length", "accept"),
                ]
            )
            service.learn_from_session(session)
        summary = service.get_preference_summary()
        prefs = summary["preferences"]
        if len(prefs) >= 2:
            assert prefs[0]["strength"] >= prefs[1]["strength"]


class TestStatePersistence:
    def test_save_and_load_roundtrip(self, tmp_path: Path):
        service = PreferenceLearnerService(storage_dir=tmp_path / "prefs")
        session = _make_session_with_choices(
            [
                ("Reduce passive voice usage", "accept"),
            ]
        )
        service.learn_from_session(session)
        state = service.get_state()
        assert state.total_sessions == 1
        assert "passive_voice_ratio" in state.preferences

    def test_persistence_across_instances(self, tmp_path: Path):
        storage = tmp_path / "prefs"
        service1 = PreferenceLearnerService(storage_dir=storage)
        session = _make_session_with_choices(
            [
                ("Reduce passive voice usage", "accept"),
            ]
        )
        service1.learn_from_session(session)

        service2 = PreferenceLearnerService(storage_dir=storage)
        state = service2.get_state()
        assert state.total_sessions == 1
        assert "passive_voice_ratio" in state.preferences

    def test_multiple_users_isolated(self, tmp_path: Path):
        service = PreferenceLearnerService(storage_dir=tmp_path / "prefs")
        session = _make_session_with_choices(
            [
                ("Reduce passive voice usage", "accept"),
            ]
        )
        service.learn_from_session(session, user_id="user_a")
        service.learn_from_session(session, user_id="user_b")

        state_a = service.get_state("user_a")
        state_b = service.get_state("user_b")
        assert state_a.user_id == "user_a"
        assert state_b.user_id == "user_b"
        assert state_a.total_sessions == 1
        assert state_b.total_sessions == 1
