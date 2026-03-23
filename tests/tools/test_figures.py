# pyright: reportMissingImports=false

from pathlib import Path

import pytest

from crane.tools.figures import register_tools


class _ToolCollector:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


@pytest.fixture
def figure_tools():
    collector = _ToolCollector()
    register_tools(collector)
    return collector.tools


def _assert_pdf_result(result: dict[str, object], expected_path: Path) -> None:
    assert result["path"] == str(expected_path)
    assert result["format"] == "pdf"
    assert isinstance(result["size_bytes"], int)
    assert 0 < result["size_bytes"] < 10 * 1024 * 1024
    assert expected_path.exists()
    assert expected_path.read_bytes().startswith(b"%PDF")


class TestGenerateFigure:
    def test_registered(self, figure_tools):
        assert "generate_figure" in figure_tools

    @pytest.mark.parametrize(
        ("figure_type", "data"),
        [
            (
                "bar",
                {"labels": ["baseline", "ours"], "values": [0.72, 0.84]},
            ),
            (
                "line",
                {"x": [1, 2, 3, 4], "y": [0.31, 0.48, 0.62, 0.74]},
            ),
            (
                "scatter",
                [{"x": 32, "y": 0.71}, {"x": 64, "y": 0.81}, {"x": 128, "y": 0.89}],
            ),
            (
                "heatmap",
                {
                    "values": [[0.91, 0.83], [0.77, 0.88]],
                    "x_labels": ["precision", "recall"],
                    "y_labels": ["paper_a", "paper_b"],
                },
            ),
        ],
    )
    def test_generates_publication_pdf(self, figure_tools, tmp_project, figure_type, data):
        output_path = tmp_project / "figures" / f"{figure_type}.pdf"

        result = figure_tools["generate_figure"](
            figure_type=figure_type,
            data=data,
            title="Evaluation Results",
            xlabel="Condition",
            ylabel="Score",
            output_path=str(output_path),
        )

        _assert_pdf_result(result, output_path)
        assert result["figure_type"] == figure_type

    def test_rejects_raster_extension(self, figure_tools, tmp_project):
        with pytest.raises(ValueError, match="Only PDF output is supported"):
            figure_tools["generate_figure"](
                figure_type="bar",
                data={"baseline": 0.72, "ours": 0.84},
                title="Scores",
                xlabel="Model",
                ylabel="Accuracy",
                output_path=str(tmp_project / "figures" / "scores.png"),
            )


class TestGenerateComparison:
    def test_registered(self, figure_tools):
        assert "generate_comparison" in figure_tools

    def test_generates_grouped_comparison_pdf(self, figure_tools, tmp_project):
        output_path = tmp_project / "figures" / "comparison.pdf"

        result = figure_tools["generate_comparison"](
            papers=["Transformer", "GPT-3", "T5"],
            metrics={
                "accuracy": [0.82, 0.88, 0.86],
                "f1": [0.79, 0.85, 0.84],
            },
            output_path=str(output_path),
        )

        _assert_pdf_result(result, output_path)
        assert result["figure_type"] == "comparison"

    def test_validates_metric_lengths(self, figure_tools, tmp_project):
        with pytest.raises(ValueError, match="length must match expected length"):
            figure_tools["generate_comparison"](
                papers=["Transformer", "GPT-3"],
                metrics={"accuracy": [0.82]},
                output_path=str(tmp_project / "figures" / "invalid.pdf"),
            )
