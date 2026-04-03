from __future__ import annotations

from datetime import datetime, timedelta

import yaml

from crane.services.session_service import SessionService


def test_create_and_load_session(tmp_path):
    service = SessionService(project_dir=str(tmp_path))
    session_id = service.create_session("Q1 Review", {"paper_path": "papers/main.tex"})

    loaded = service.load_session(session_id)
    assert loaded["session_id"] == session_id
    assert loaded["name"] == "Q1 Review"
    assert loaded["context"]["paper_path"] == "papers/main.tex"
    assert loaded["messages"] == []


def test_save_session_updates_messages_and_timestamp(tmp_path):
    service = SessionService(project_dir=str(tmp_path))
    session_id = service.create_session("Run")
    before = service.load_session(session_id)["updated_at"]

    result = service.save_session(
        session_id,
        [
            {
                "role": "user",
                "content": "Review this",
                "timestamp": "2026-04-03T10:00:00",
            }
        ],
    )
    after = service.load_session(session_id)

    assert result["status"] == "saved"
    assert result["message_count"] == 1
    assert after["updated_at"] >= before
    assert after["messages"][0]["role"] == "user"


def test_list_sessions_sorted_by_updated_at_desc(tmp_path):
    service = SessionService(project_dir=str(tmp_path))
    older = service.create_session("older")
    newer = service.create_session("newer")

    old_path = service.sessions_dir / f"{older}.yaml"
    old_data = yaml.safe_load(old_path.read_text(encoding="utf-8"))
    old_data["updated_at"] = "2020-01-01T00:00:00"
    old_path.write_text(yaml.safe_dump(old_data, sort_keys=False), encoding="utf-8")

    sessions = service.list_sessions(limit=10)
    assert sessions[0]["session_id"] == newer
    assert sessions[1]["session_id"] == older


def test_delete_session(tmp_path):
    service = SessionService(project_dir=str(tmp_path))
    session_id = service.create_session("delete me")

    deleted = service.delete_session(session_id)
    assert deleted["status"] == "deleted"

    missing = service.delete_session(session_id)
    assert missing["status"] == "not_found"


def test_cleanup_old_sessions(tmp_path):
    service = SessionService(project_dir=str(tmp_path))
    old_session = service.create_session("old")
    fresh_session = service.create_session("fresh")

    old_path = service.sessions_dir / f"{old_session}.yaml"
    old_data = yaml.safe_load(old_path.read_text(encoding="utf-8"))
    old_data["updated_at"] = (datetime.now() - timedelta(days=90)).isoformat(timespec="seconds")
    old_path.write_text(yaml.safe_dump(old_data, sort_keys=False), encoding="utf-8")

    deleted_count = service.cleanup_old_sessions(max_age_days=30)
    assert deleted_count == 1
    assert not (service.sessions_dir / f"{old_session}.yaml").exists()
    assert (service.sessions_dir / f"{fresh_session}.yaml").exists()
