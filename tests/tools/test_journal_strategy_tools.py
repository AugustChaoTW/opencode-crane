from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from crane.tools.journal_strategy import register_tools


class _ToolCollector:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


def test_analyze_paper_for_journal_writes_yaml_report(tmp_path):
    collector = _ToolCollector()
    register_tools(collector)
    output_path = tmp_path / "reports" / "journal.yaml"

    with (
        patch(
            "crane.tools.journal_strategy.JournalRecommendationService.analyze_paper_attributes",
            return_value=SimpleNamespace(),
        ),
        patch(
            "crane.tools.journal_strategy.JournalRecommendationService.create_submission_strategy",
            return_value=SimpleNamespace(),
        ),
        patch(
            "crane.tools.journal_strategy.JournalRecommendationService.to_dict",
            return_value={"paper_type": "application_system"},
        ),
    ):
        result = collector.tools["analyze_paper_for_journal"](
            paper_path="paper.tex",
            output_path=str(output_path),
        )

    assert result == {"paper_type": "application_system"}
    assert output_path.exists()


def test_generate_submission_checklist_falls_back_for_invalid_type():
    collector = _ToolCollector()
    register_tools(collector)

    with patch(
        "crane.tools.journal_strategy.JournalRecommendationService._generate_submission_checklist",
        side_effect=lambda ptype: [ptype.value],
    ):
        result = collector.tools["generate_submission_checklist"]("unknown-type")

    assert result == ["application_system"]


def test_find_similar_papers_in_journal_delegates_to_recommender():
    collector = _ToolCollector()
    register_tools(collector)

    expected = {"match_count": 2, "journal": "TMLR"}
    with patch(
        "crane.tools.journal_strategy.JournalRecommender.find_similar_papers_in_journal",
        return_value=expected,
    ) as mocked:
        result = collector.tools["find_similar_papers_in_journal"](
            ["repair", "validation"],
            "TMLR",
            max_results=5,
        )

    mocked.assert_called_once_with(["repair", "validation"], "TMLR", 5)
    assert result == expected
