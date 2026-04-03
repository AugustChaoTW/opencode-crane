# pyright: reportMissingImports=false

from __future__ import annotations

from pathlib import Path

import pytest

from crane.services.agent_memory_service import AgentMemoryService


class _Workspace:
    def __init__(self, project_root: str):
        self.project_root = project_root


@pytest.fixture
def memory_service(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> AgentMemoryService:
    monkeypatch.setattr(
        "crane.services.agent_memory_service.resolve_workspace",
        lambda _project_dir=None: _Workspace(str(tmp_path)),
    )
    return AgentMemoryService(project_dir=str(tmp_path))


def test_get_agent_memory_empty_when_file_missing(memory_service: AgentMemoryService) -> None:
    assert memory_service.get_agent_memory("researcher") == []


def test_add_and_get_agent_memory(memory_service: AgentMemoryService, tmp_path: Path) -> None:
    out = memory_service.add_agent_memory(
        agent_name="researcher",
        content="User prefers IEEE TPAMI for submissions",
        source="manual",
    )

    assert out["agent_name"] == "researcher"
    assert out["entry"]["content"] == "User prefers IEEE TPAMI for submissions"
    assert out["entry"]["source"] == "manual"
    assert out["total_entries"] == 1

    entries = memory_service.get_agent_memory("researcher")
    assert len(entries) == 1
    assert entries[0]["content"] == "User prefers IEEE TPAMI for submissions"

    memory_file = tmp_path / ".crane" / "memory" / "researcher.yaml"
    assert memory_file.exists()


def test_remove_agent_memory_by_index(memory_service: AgentMemoryService) -> None:
    memory_service.add_agent_memory("researcher", "first", "manual")
    memory_service.add_agent_memory("researcher", "second", "manual")

    result = memory_service.remove_agent_memory("researcher", 0)
    assert result["total_entries"] == 1
    assert result["removed"]["content"] == "first"

    remaining = memory_service.get_agent_memory("researcher")
    assert len(remaining) == 1
    assert remaining[0]["content"] == "second"


def test_remove_agent_memory_invalid_index_raises(memory_service: AgentMemoryService) -> None:
    memory_service.add_agent_memory("researcher", "first", "manual")

    with pytest.raises(ValueError, match="index out of range"):
        memory_service.remove_agent_memory("researcher", 5)


def test_clear_agent_memory(memory_service: AgentMemoryService) -> None:
    memory_service.add_agent_memory("reviewer", "one", "manual")
    memory_service.add_agent_memory("reviewer", "two", "manual")

    result = memory_service.clear_agent_memory("reviewer")
    assert result["agent_name"] == "reviewer"
    assert result["cleared"] == 2
    assert memory_service.get_agent_memory("reviewer") == []


def test_search_agent_memory(memory_service: AgentMemoryService) -> None:
    memory_service.add_agent_memory("evaluator", "Focus on ablation quality", "manual")
    memory_service.add_agent_memory("evaluator", "Use TPAMI framing for intro", "manual")
    memory_service.add_agent_memory("evaluator", "Check baseline fairness", "review")

    matches = memory_service.search_agent_memory("evaluator", "tpami")
    assert len(matches) == 1
    assert matches[0]["content"] == "Use TPAMI framing for intro"
    assert matches[0]["index"] == 1

    source_matches = memory_service.search_agent_memory("evaluator", "review")
    assert len(source_matches) == 1
    assert source_matches[0]["source"] == "review"
