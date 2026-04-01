from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from crane.tools.q1_evaluation import register_tools


class _ToolCollector:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


def test_evaluate_q1_standards_returns_result_and_writes_yaml(tmp_path):
    collector = _ToolCollector()
    register_tools(collector)
    output_path = tmp_path / "reports" / "q1.yaml"

    with (
        patch(
            "crane.tools.q1_evaluation.Q1EvaluationService.evaluate",
            return_value=SimpleNamespace(),
        ) as evaluate_mock,
        patch(
            "crane.tools.q1_evaluation.Q1EvaluationService.to_dict",
            return_value={"overall_score": 91.5, "readiness": "ready"},
        ),
    ):
        result = collector.tools["evaluate_q1_standards"](
            paper_path="paper.tex",
            output_path=str(output_path),
        )

    evaluate_mock.assert_called_once_with("paper.tex")
    assert result["overall_score"] == 91.5
    assert output_path.exists()
