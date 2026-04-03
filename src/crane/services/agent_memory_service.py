"""Per-agent persistent memory service."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from crane.workspace import resolve_workspace


class AgentMemoryService:
    """Manage per-agent persistent memory."""

    def __init__(self, project_dir: str | None = None):
        workspace = resolve_workspace(project_dir)
        self.project_root = Path(workspace.project_root)
        self.memory_dir = self.project_root / ".crane" / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def get_agent_memory(self, agent_name: str) -> list[dict[str, Any]]:
        """Get all memory entries for an agent."""
        payload = self._read_memory_file(agent_name)
        entries = payload.get("entries", [])
        if not isinstance(entries, list):
            return []
        return [entry for entry in entries if isinstance(entry, dict)]

    def add_agent_memory(
        self,
        agent_name: str,
        content: str,
        source: str = "manual",
    ) -> dict[str, Any]:
        """Add a memory entry for an agent."""
        clean_content = content.strip()
        if not clean_content:
            raise ValueError("content must not be empty")

        payload = self._read_memory_file(agent_name)
        entries = payload.get("entries", [])
        if not isinstance(entries, list):
            entries = []

        entry = {
            "timestamp": datetime.now().replace(microsecond=0).isoformat(),
            "content": clean_content,
            "source": source,
        }
        entries.append(entry)

        payload["entries"] = entries
        self._write_memory_file(agent_name, payload)
        return {
            "agent_name": self._normalize_agent_name(agent_name),
            "entry": entry,
            "total_entries": len(entries),
        }

    def remove_agent_memory(self, agent_name: str, index: int) -> dict[str, Any]:
        """Remove a memory entry by index."""
        payload = self._read_memory_file(agent_name)
        entries = payload.get("entries", [])
        if not isinstance(entries, list):
            entries = []

        if index < 0 or index >= len(entries):
            raise ValueError(f"index out of range: {index}")

        removed = entries.pop(index)
        payload["entries"] = entries
        self._write_memory_file(agent_name, payload)
        return {
            "agent_name": self._normalize_agent_name(agent_name),
            "removed": removed,
            "total_entries": len(entries),
        }

    def clear_agent_memory(self, agent_name: str) -> dict[str, Any]:
        """Clear all memory for an agent."""
        existing = self.get_agent_memory(agent_name)
        payload = {"entries": []}
        self._write_memory_file(agent_name, payload)
        return {
            "agent_name": self._normalize_agent_name(agent_name),
            "cleared": len(existing),
        }

    def search_agent_memory(self, agent_name: str, query: str) -> list[dict[str, Any]]:
        """Search memory entries by keyword."""
        keyword = query.strip().lower()
        if not keyword:
            return []

        matches: list[dict[str, Any]] = []
        for idx, entry in enumerate(self.get_agent_memory(agent_name)):
            content = str(entry.get("content", "")).lower()
            source = str(entry.get("source", "")).lower()
            if keyword in content or keyword in source:
                result = dict(entry)
                result["index"] = idx
                matches.append(result)

        return matches

    def _memory_file(self, agent_name: str) -> Path:
        safe_name = self._normalize_agent_name(agent_name)
        return self.memory_dir / f"{safe_name}.yaml"

    def _read_memory_file(self, agent_name: str) -> dict[str, Any]:
        path = self._memory_file(agent_name)
        if not path.exists():
            return {"entries": []}

        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception:
            return {"entries": []}

        if not isinstance(data, dict):
            return {"entries": []}

        entries = data.get("entries")
        if not isinstance(entries, list):
            data["entries"] = []
        return data

    def _write_memory_file(self, agent_name: str, payload: dict[str, Any]) -> None:
        path = self._memory_file(agent_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    def _normalize_agent_name(self, agent_name: str) -> str:
        normalized = agent_name.strip()
        if not normalized:
            raise ValueError("agent_name must not be empty")

        safe = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in normalized)
        safe = safe.strip("._")
        if not safe:
            raise ValueError("agent_name must contain valid characters")
        return safe
