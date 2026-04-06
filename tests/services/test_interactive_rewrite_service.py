# pyright: reportMissingImports=false
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from crane.models.writing_style_models import (
    InteractiveRewriteSession,
    RewriteChoice,
    RewriteSuggestion,
)
from crane.services.interactive_rewrite_service import InteractiveRewriteService


def _make_session(
    tmp_path: Path,
    n_suggestions: int = 3,
    session_id: str = "rw_test_001",
) -> tuple[InteractiveRewriteService, InteractiveRewriteSession]:
    service = InteractiveRewriteService(storage_dir=tmp_path / "sessions")
    suggestions = [
        RewriteSuggestion(
            original_text=f"Original text {i}",
            suggested_text=f"Suggested text {i}",
            rationale=f"Reduce passive voice in sentence {i}",
            exemplar_source="IEEE TPAMI",
            confidence=0.8 - i * 0.1,
        )
        for i in range(n_suggestions)
    ]
    session = InteractiveRewriteSession(
        session_id=session_id,
        paper_path="/tmp/test.tex",
        journal_name="IEEE TPAMI",
        section_name="Introduction",
        suggestions=suggestions,
        choices=[],
        applied_rewrites=[],
        status="active",
    )
    service._save_session(session)
    return service, session


class TestInteractiveRewriteServiceInit:
    def test_creates_storage_dir(self, tmp_path: Path):
        storage = tmp_path / "new_sessions"
        InteractiveRewriteService(storage_dir=storage)
        assert storage.exists()

    def test_default_storage_dir(self):
        service = InteractiveRewriteService()
        assert service._storage_dir.exists()


class TestSubmitChoice:
    def test_accept_adds_to_applied(self, tmp_path: Path):
        service, session = _make_session(tmp_path)
        updated = service.submit_choice(session, 0, "accept")
        assert len(updated.applied_rewrites) == 1
        assert updated.applied_rewrites[0].original_text == "Original text 0"

    def test_reject_does_not_add_to_applied(self, tmp_path: Path):
        service, session = _make_session(tmp_path)
        updated = service.submit_choice(session, 0, "reject")
        assert len(updated.applied_rewrites) == 0

    def test_modify_adds_modified_text(self, tmp_path: Path):
        service, session = _make_session(tmp_path)
        updated = service.submit_choice(session, 0, "modify", modified_text="My custom text")
        assert len(updated.applied_rewrites) == 1
        assert updated.applied_rewrites[0].suggested_text == "My custom text"

    def test_modify_without_text_raises(self, tmp_path: Path):
        service, session = _make_session(tmp_path)
        with pytest.raises(ValueError, match="modified_text is required"):
            service.submit_choice(session, 0, "modify")

    def test_invalid_decision_raises(self, tmp_path: Path):
        service, session = _make_session(tmp_path)
        with pytest.raises(ValueError, match="Invalid decision"):
            service.submit_choice(session, 0, "maybe")

    def test_out_of_range_index_raises(self, tmp_path: Path):
        service, session = _make_session(tmp_path)
        with pytest.raises(IndexError):
            service.submit_choice(session, 99, "accept")

    def test_negative_index_raises(self, tmp_path: Path):
        service, session = _make_session(tmp_path)
        with pytest.raises(IndexError):
            service.submit_choice(session, -1, "accept")

    def test_choice_recorded_in_session(self, tmp_path: Path):
        service, session = _make_session(tmp_path)
        updated = service.submit_choice(session, 0, "accept", reason="Looks good")
        assert len(updated.choices) == 1
        assert updated.choices[0].decision == "accept"
        assert updated.choices[0].reason == "Looks good"
        assert updated.choices[0].suggestion_id == "sug_0"

    def test_session_completes_when_all_decided(self, tmp_path: Path):
        service, session = _make_session(tmp_path, n_suggestions=2)
        session = service.submit_choice(session, 0, "accept")
        assert session.status == "active"
        session = service.submit_choice(session, 1, "reject")
        assert session.status == "completed"

    def test_updated_at_changes(self, tmp_path: Path):
        service, session = _make_session(tmp_path)
        original_updated = session.updated_at
        updated = service.submit_choice(session, 0, "accept")
        assert updated.updated_at >= original_updated


class TestGetPendingSuggestions:
    def test_all_pending_initially(self, tmp_path: Path):
        service, session = _make_session(tmp_path, n_suggestions=3)
        pending = service.get_pending_suggestions(session)
        assert len(pending) == 3

    def test_pending_decreases_after_choice(self, tmp_path: Path):
        service, session = _make_session(tmp_path, n_suggestions=3)
        session = service.submit_choice(session, 0, "accept")
        pending = service.get_pending_suggestions(session)
        assert len(pending) == 2

    def test_no_pending_when_all_decided(self, tmp_path: Path):
        service, session = _make_session(tmp_path, n_suggestions=2)
        session = service.submit_choice(session, 0, "accept")
        session = service.submit_choice(session, 1, "reject")
        pending = service.get_pending_suggestions(session)
        assert len(pending) == 0


class TestSessionSummary:
    def test_summary_counts(self, tmp_path: Path):
        service, session = _make_session(tmp_path, n_suggestions=3)
        session = service.submit_choice(session, 0, "accept")
        session = service.submit_choice(session, 1, "reject")
        session = service.submit_choice(session, 2, "modify", modified_text="Custom")
        summary = service.get_session_summary(session)
        assert summary["accepted"] == 1
        assert summary["rejected"] == 1
        assert summary["modified"] == 1
        assert summary["decisions_made"] == 3
        assert summary["applied_count"] == 2

    def test_acceptance_rate(self, tmp_path: Path):
        service, session = _make_session(tmp_path, n_suggestions=2)
        session = service.submit_choice(session, 0, "accept")
        session = service.submit_choice(session, 1, "accept")
        summary = service.get_session_summary(session)
        assert summary["acceptance_rate"] == 1.0

    def test_summary_metadata(self, tmp_path: Path):
        service, session = _make_session(tmp_path)
        summary = service.get_session_summary(session)
        assert summary["session_id"] == "rw_test_001"
        assert summary["journal_name"] == "IEEE TPAMI"
        assert summary["section_name"] == "Introduction"


class TestPauseResume:
    def test_pause_sets_status(self, tmp_path: Path):
        service, session = _make_session(tmp_path)
        paused = service.pause_session(session)
        assert paused.status == "paused"

    def test_resume_sets_active(self, tmp_path: Path):
        service, session = _make_session(tmp_path)
        service.pause_session(session)
        resumed = service.resume_session(session.session_id)
        assert resumed.status == "active"

    def test_resume_completed_raises(self, tmp_path: Path):
        service, session = _make_session(tmp_path, n_suggestions=1)
        session = service.submit_choice(session, 0, "accept")
        assert session.status == "completed"
        with pytest.raises(ValueError, match="already completed"):
            service.resume_session(session.session_id)

    def test_resume_nonexistent_raises(self, tmp_path: Path):
        service = InteractiveRewriteService(storage_dir=tmp_path / "sessions")
        with pytest.raises(FileNotFoundError):
            service.resume_session("nonexistent_id")


class TestSessionPersistence:
    def test_save_and_load_roundtrip(self, tmp_path: Path):
        service, session = _make_session(tmp_path)
        session = service.submit_choice(session, 0, "accept")
        loaded = service._load_session(session.session_id)
        assert loaded.session_id == session.session_id
        assert loaded.journal_name == "IEEE TPAMI"
        assert len(loaded.choices) == 1
        assert loaded.choices[0].decision == "accept"
        assert len(loaded.applied_rewrites) == 1

    def test_load_preserves_suggestions(self, tmp_path: Path):
        service, session = _make_session(tmp_path, n_suggestions=3)
        loaded = service._load_session(session.session_id)
        assert len(loaded.suggestions) == 3
        assert loaded.suggestions[0].original_text == "Original text 0"
        assert loaded.suggestions[0].confidence == 0.8

    def test_load_nonexistent_raises(self, tmp_path: Path):
        service = InteractiveRewriteService(storage_dir=tmp_path / "sessions")
        with pytest.raises(FileNotFoundError):
            service._load_session("does_not_exist")


class TestListSessions:
    def test_list_empty(self, tmp_path: Path):
        service = InteractiveRewriteService(storage_dir=tmp_path / "sessions")
        assert service.list_sessions() == []

    def test_list_returns_sessions(self, tmp_path: Path):
        service, _ = _make_session(tmp_path, session_id="rw_001")
        _make_session(tmp_path, session_id="rw_002")
        sessions = service.list_sessions()
        assert len(sessions) == 2

    def test_list_filter_by_status(self, tmp_path: Path):
        service, session = _make_session(tmp_path, n_suggestions=1, session_id="rw_active")
        _, session2 = _make_session(tmp_path, n_suggestions=1, session_id="rw_done")
        service.submit_choice(session2, 0, "accept")
        active = service.list_sessions(status="active")
        completed = service.list_sessions(status="completed")
        assert len(active) == 1
        assert len(completed) == 1
        assert active[0]["session_id"] == "rw_active"
        assert completed[0]["session_id"] == "rw_done"
