from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from crane.tools.screening import register_tools


class _ToolCollector:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


def test_screening_tools_registered():
    collector = _ToolCollector()
    register_tools(collector)

    assert {"screen_reference", "list_screened_references", "compare_papers"} <= set(
        collector.tools
    )


def test_screen_reference_returns_serialized_result():
    collector = _ToolCollector()
    register_tools(collector)

    fake_result = SimpleNamespace(
        paper_key="paper-a",
        decision=SimpleNamespace(value="include"),
        reason="keep",
        criteria=["novelty"],
        timestamp="2026-04-01T00:00:00",
    )

    with patch("crane.tools.screening.ScreeningService.screen", return_value=fake_result):
        result = collector.tools["screen_reference"]("paper-a", "include", reason="keep")

    assert result == {
        "paper_key": "paper-a",
        "decision": "include",
        "reason": "keep",
        "criteria": ["novelty"],
        "timestamp": "2026-04-01T00:00:00",
    }


def test_list_screened_references_passes_optional_filter():
    collector = _ToolCollector()
    register_tools(collector)

    with patch(
        "crane.tools.screening.ScreeningService.list_screened",
        return_value=[{"key": "paper-a", "decision": "maybe"}],
    ) as mocked:
        result = collector.tools["list_screened_references"](decision="maybe")

    mocked.assert_called_once_with("maybe")
    assert result == [{"key": "paper-a", "decision": "maybe"}]


def test_compare_papers_returns_matrix_dict():
    collector = _ToolCollector()
    register_tools(collector)

    fake_matrix = SimpleNamespace(to_dict=lambda: {"papers": ["paper-a", "paper-b"]})
    with patch(
        "crane.tools.screening.ScreeningService.compare", return_value=fake_matrix
    ) as mocked:
        result = collector.tools["compare_papers"](["paper-a", "paper-b"], dimensions=["year"])

    mocked.assert_called_once_with(["paper-a", "paper-b"], ["year"])
    assert result == {"papers": ["paper-a", "paper-b"]}
