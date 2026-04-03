"""Agent management service with grouping and override resolution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from crane.workspace import resolve_workspace


class AgentService:
    """Manage CRANE agents with grouping, override resolution, and display."""

    AGENT_SOURCE_GROUPS = [
        ("Built-in", "builtin"),
        ("Custom", "custom"),
        ("Project", "project"),
    ]

    _SOURCE_PRIORITY = {
        "builtin": 0,
        "custom": 1,
        "project": 2,
    }

    def __init__(self, project_dir: str | None = None):
        workspace = resolve_workspace(project_dir)
        self.project_root = Path(workspace.project_root)

    def list_agents(self) -> dict[str, Any]:
        """List all agents grouped by source, with override resolution."""
        all_agents = [
            *self._load_builtin_agents(),
            *self._load_custom_agents(),
            *self._load_project_agents(),
        ]
        resolved = self.resolve_overrides(all_agents)

        groups: list[dict[str, Any]] = []
        for label, source in self.AGENT_SOURCE_GROUPS:
            source_agents = [
                self._to_agent_summary(agent) for agent in resolved if agent.get("source") == source
            ]
            source_agents.sort(key=lambda item: str(item.get("name", "")).lower())
            groups.append(
                {
                    "label": label,
                    "source": source,
                    "agents": source_agents,
                }
            )

        total_active = sum(1 for agent in resolved if agent.get("is_active", False))
        return {
            "total_active": total_active,
            "groups": groups,
        }

    def get_agent(self, name: str) -> dict[str, Any] | None:
        """Get a single agent by name (after override resolution)."""
        target = name.strip().lower()
        if not target:
            return None

        all_agents = [
            *self._load_builtin_agents(),
            *self._load_custom_agents(),
            *self._load_project_agents(),
        ]
        resolved = self.resolve_overrides(all_agents)
        for agent in resolved:
            if str(agent.get("name", "")).strip().lower() == target and agent.get(
                "is_active", False
            ):
                return dict(agent)
        return None

    def resolve_overrides(self, all_agents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Resolve agent overrides by source priority.

        Higher-priority sources shadow lower-priority sources for the same name.
        """
        indexed: list[tuple[int, dict[str, Any]]] = []
        for idx, raw in enumerate(all_agents):
            agent = dict(raw)
            agent.setdefault("source", "builtin")
            indexed.append((idx, agent))

        by_name: dict[str, list[tuple[int, dict[str, Any]]]] = {}
        for idx, agent in indexed:
            name = str(agent.get("name", "")).strip()
            if not name:
                continue
            key = name.lower()
            by_name.setdefault(key, []).append((idx, agent))

        active_by_name: dict[str, tuple[int, dict[str, Any]]] = {}
        for key, candidates in by_name.items():
            active_by_name[key] = max(
                candidates,
                key=lambda item: (
                    self._SOURCE_PRIORITY.get(str(item[1].get("source", "builtin")), -1),
                    item[0],
                ),
            )

        resolved: list[dict[str, Any]] = []
        for idx, agent in indexed:
            name = str(agent.get("name", "")).strip()
            if not name:
                continue

            key = name.lower()
            active_idx, active_agent = active_by_name[key]
            if idx == active_idx:
                agent["is_active"] = True
                agent["overridden_by"] = None
            else:
                agent["is_active"] = False
                agent["overridden_by"] = str(active_agent.get("source", "unknown"))

            resolved.append(agent)

        return resolved

    def _load_builtin_agents(self) -> list[dict[str, Any]]:
        """Load built-in agent definitions."""
        return [
            {
                "name": "researcher",
                "agent_type": "autonomous",
                "model": None,
                "memory": "research-memory",
                "source": "builtin",
                "system_prompt": "You are a research assistant...",
                "tools": ["search_papers", "read_paper", "ask_library"],
            },
            {
                "name": "reviewer",
                "agent_type": "reviewer",
                "model": None,
                "memory": None,
                "source": "builtin",
                "system_prompt": "You are a paper reviewer...",
                "tools": ["review_paper_sections"],
            },
            {
                "name": "evaluator",
                "agent_type": "assisted",
                "model": None,
                "memory": None,
                "source": "builtin",
                "system_prompt": "You evaluate paper quality...",
                "tools": ["evaluate_paper_v2"],
            },
        ]

    def _load_custom_agents(self) -> list[dict[str, Any]]:
        """Load custom agents from ~/.crane/agents/*.yaml."""
        return self._load_agents_from_dir(Path.home() / ".crane" / "agents", source="custom")

    def _load_project_agents(self) -> list[dict[str, Any]]:
        """Load project agents from .crane/agents/*.yaml."""
        return self._load_agents_from_dir(self.project_root / ".crane" / "agents", source="project")

    def _load_agents_from_dir(self, agents_dir: Path, source: str) -> list[dict[str, Any]]:
        """Load and normalize agent definitions from a directory."""
        if not agents_dir.exists() or not agents_dir.is_dir():
            return []

        files = sorted(
            [*agents_dir.glob("*.yaml"), *agents_dir.glob("*.yml")],
            key=lambda path: path.name.lower(),
        )

        agents: list[dict[str, Any]] = []
        for file_path in files:
            loaded = self._parse_agent_file(file_path, source)
            agents.extend(loaded)

        return agents

    def _parse_agent_file(self, file_path: Path, source: str) -> list[dict[str, Any]]:
        """Parse one YAML file that may contain one or multiple agents."""
        try:
            raw = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        except Exception:
            return []

        if raw is None:
            return []

        candidates: list[dict[str, Any]] = []
        if isinstance(raw, dict):
            nested = raw.get("agents")
            if isinstance(nested, list):
                for item in nested:
                    if isinstance(item, dict):
                        normalized = self._normalize_agent(item, source)
                        if normalized is not None:
                            candidates.append(normalized)
            else:
                normalized = self._normalize_agent(raw, source)
                if normalized is not None:
                    candidates.append(normalized)
        elif isinstance(raw, list):
            for item in raw:
                if not isinstance(item, dict):
                    continue
                normalized = self._normalize_agent(item, source)
                if normalized is not None:
                    candidates.append(normalized)

        return candidates

    def _normalize_agent(self, raw: dict[str, Any], source: str) -> dict[str, Any] | None:
        """Normalize loosely structured YAML data into canonical agent shape."""
        name = str(raw.get("name", "")).strip()
        if not name:
            return None

        tools = raw.get("tools", [])
        if not isinstance(tools, list):
            tools = []

        return {
            "name": name,
            "agent_type": str(raw.get("agent_type", "autonomous")),
            "model": raw.get("model"),
            "memory": raw.get("memory"),
            "source": source,
            "system_prompt": str(raw.get("system_prompt", "")),
            "tools": [str(tool) for tool in tools],
        }

    def _to_agent_summary(self, agent: dict[str, Any]) -> dict[str, Any]:
        """Return the agent fields exposed by list_agents."""
        return {
            "name": str(agent.get("name", "")),
            "agent_type": str(agent.get("agent_type", "autonomous")),
            "model": agent.get("model"),
            "memory": agent.get("memory"),
            "overridden_by": agent.get("overridden_by"),
            "is_active": bool(agent.get("is_active", False)),
        }
