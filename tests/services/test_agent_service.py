# pyright: reportMissingImports=false

from __future__ import annotations

from pathlib import Path

import pytest

from crane.services.agent_service import AgentService


class _Workspace:
    def __init__(self, project_root: str):
        self.project_root = project_root


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> AgentService:
    home_dir = tmp_path / "home"
    home_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "crane.services.agent_service.resolve_workspace",
        lambda _project_dir=None: _Workspace(str(tmp_path)),
    )
    monkeypatch.setattr("crane.services.agent_service.Path.home", lambda: home_dir)
    return AgentService(project_dir=str(tmp_path))


def test_list_agents_returns_expected_groups_with_builtin_agents(service: AgentService) -> None:
    result = service.list_agents()

    assert result["total_active"] == 3
    assert [group["source"] for group in result["groups"]] == ["builtin", "custom", "project"]

    builtin = next(group for group in result["groups"] if group["source"] == "builtin")
    names = {agent["name"] for agent in builtin["agents"]}
    assert names == {"researcher", "reviewer", "evaluator"}
    assert all(agent["is_active"] for agent in builtin["agents"])


def test_project_agent_overrides_global_agents(
    service: AgentService,
    tmp_path: Path,
) -> None:
    custom_dir = tmp_path / "home" / ".crane" / "agents"
    custom_dir.mkdir(parents=True, exist_ok=True)
    (custom_dir / "custom-researcher.yaml").write_text(
        """
name: researcher
agent_type: assisted
model: gpt-5-mini
memory: custom-memory
tools:
  - custom_tool
""".strip(),
        encoding="utf-8",
    )

    project_dir = tmp_path / ".crane" / "agents"
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "project-researcher.yaml").write_text(
        """
name: researcher
agent_type: reviewer
memory: project-memory
tools:
  - project_tool
""".strip(),
        encoding="utf-8",
    )

    result = service.list_agents()
    assert result["total_active"] == 3

    grouped = {
        group["source"]: {agent["name"]: agent for agent in group["agents"]}
        for group in result["groups"]
    }

    assert grouped["builtin"]["researcher"]["is_active"] is False
    assert grouped["builtin"]["researcher"]["overridden_by"] == "project"
    assert grouped["custom"]["researcher"]["is_active"] is False
    assert grouped["custom"]["researcher"]["overridden_by"] == "project"
    assert grouped["project"]["researcher"]["is_active"] is True
    assert grouped["project"]["researcher"]["overridden_by"] is None


def test_get_agent_returns_active_agent_after_override(
    service: AgentService, tmp_path: Path
) -> None:
    project_dir = tmp_path / ".crane" / "agents"
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "override.yaml").write_text(
        """
name: reviewer
agent_type: autonomous
model: claude-sonnet
memory: reviewer-memory
system_prompt: Custom project reviewer
tools:
  - review_paper_sections
  - evaluate_paper_v2
""".strip(),
        encoding="utf-8",
    )

    reviewer = service.get_agent("reviewer")
    assert reviewer is not None
    assert reviewer["source"] == "project"
    assert reviewer["agent_type"] == "autonomous"
    assert reviewer["is_active"] is True


def test_resolve_overrides_marks_shadowed_agents(service: AgentService) -> None:
    resolved = service.resolve_overrides(
        [
            {"name": "x", "source": "builtin", "agent_type": "autonomous"},
            {"name": "x", "source": "custom", "agent_type": "assisted"},
            {"name": "x", "source": "project", "agent_type": "reviewer"},
            {"name": "y", "source": "builtin", "agent_type": "autonomous"},
        ]
    )

    by_source = {item["source"]: item for item in resolved if item["name"] == "x"}
    assert by_source["builtin"]["is_active"] is False
    assert by_source["builtin"]["overridden_by"] == "project"
    assert by_source["custom"]["is_active"] is False
    assert by_source["custom"]["overridden_by"] == "project"
    assert by_source["project"]["is_active"] is True
    assert by_source["project"]["overridden_by"] is None
