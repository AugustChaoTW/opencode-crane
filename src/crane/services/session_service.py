from __future__ import annotations

import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml


class SessionService:
    def __init__(self, project_dir: str | None = None):
        root = Path(project_dir or Path.cwd())
        self.sessions_dir = root / ".crane" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.yaml"

    def _read_session(self, session_id: str) -> dict[str, Any]:
        path = self._session_path(session_id)
        if not path.exists():
            raise ValueError(f"Session not found: {session_id}")
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"Invalid session file: {session_id}")
        return loaded

    def _write_session(self, session_id: str, data: dict[str, Any]) -> None:
        path = self._session_path(session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    def create_session(self, name: str, context: dict | None = None) -> str:
        session_id = f"sess_{int(time.time())}_{secrets.token_hex(4)}"
        now = datetime.now().isoformat(timespec="seconds")
        payload = {
            "session_id": session_id,
            "name": name,
            "created_at": now,
            "updated_at": now,
            "messages": [],
            "context": context or {},
        }
        self._write_session(session_id, payload)
        return session_id

    def save_session(self, session_id: str, messages: list[dict]) -> dict:
        session = self._read_session(session_id)
        session["messages"] = messages
        session["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self._write_session(session_id, session)
        return {
            "status": "saved",
            "session_id": session_id,
            "message_count": len(messages),
        }

    def load_session(self, session_id: str) -> dict:
        session = self._read_session(session_id)
        return {
            "session_id": session.get("session_id", session_id),
            "name": session.get("name", ""),
            "created_at": session.get("created_at", ""),
            "updated_at": session.get("updated_at", ""),
            "messages": session.get("messages", []),
            "context": session.get("context", {}),
        }

    def list_sessions(self, limit: int = 20) -> list[dict]:
        if limit <= 0:
            return []

        sessions: list[dict[str, Any]] = []
        for file_path in self.sessions_dir.glob("*.yaml"):
            loaded = yaml.safe_load(file_path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                continue
            sessions.append(
                {
                    "session_id": loaded.get("session_id", file_path.stem),
                    "name": loaded.get("name", ""),
                    "created_at": loaded.get("created_at", ""),
                    "updated_at": loaded.get("updated_at", ""),
                    "message_count": len(loaded.get("messages", [])),
                }
            )

        sessions.sort(key=lambda item: str(item.get("updated_at", "")), reverse=True)
        return sessions[:limit]

    def delete_session(self, session_id: str) -> dict:
        path = self._session_path(session_id)
        if not path.exists():
            return {"status": "not_found", "session_id": session_id}
        path.unlink()
        return {"status": "deleted", "session_id": session_id}

    def cleanup_old_sessions(self, max_age_days: int = 30) -> int:
        cutoff = datetime.now() - timedelta(days=max_age_days)
        deleted = 0

        for file_path in self.sessions_dir.glob("*.yaml"):
            loaded = yaml.safe_load(file_path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                continue

            updated_at_raw = str(loaded.get("updated_at") or loaded.get("created_at") or "")
            if not updated_at_raw:
                continue

            try:
                updated_at = datetime.fromisoformat(updated_at_raw)
            except ValueError:
                continue

            if updated_at < cutoff:
                file_path.unlink(missing_ok=True)
                deleted += 1

        return deleted
