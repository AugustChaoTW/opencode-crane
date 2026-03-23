# pyright: reportMissingImports=false

from __future__ import annotations

from pathlib import Path
from typing import Any

from crane.services.figure_generator import FigureGenerator
from crane.workspace import resolve_workspace

_figure_generator = FigureGenerator()


def _resolve_output_path(output_path: str, project_dir: str | None) -> Path:
    path = Path(output_path)
    if path.is_absolute():
        return path

    if project_dir is not None:
        base_dir = Path(project_dir)
    else:
        try:
            base_dir = Path(resolve_workspace().project_root)
        except ValueError:
            base_dir = Path.cwd()

    return base_dir / path


def _build_result(path: Path, figure_type: str) -> dict[str, Any]:
    return {
        "path": str(path),
        "figure_type": figure_type,
        "format": path.suffix.lstrip(".") or "pdf",
        "size_bytes": path.stat().st_size,
    }


def register_tools(mcp):
    @mcp.tool()
    def generate_figure(
        figure_type: str,
        data: Any,
        title: str,
        xlabel: str = "",
        ylabel: str = "",
        output_path: str = "figures/figure.pdf",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        resolved_output = _resolve_output_path(output_path, project_dir)
        normalized_type = figure_type.strip().lower()

        if normalized_type == "bar":
            path = _figure_generator.generate_bar_chart(
                data=data,
                title=title,
                xlabel=xlabel,
                ylabel=ylabel,
                output_path=resolved_output,
            )
        elif normalized_type == "line":
            path = _figure_generator.generate_line_plot(
                data=data,
                title=title,
                xlabel=xlabel,
                ylabel=ylabel,
                output_path=resolved_output,
            )
        elif normalized_type == "scatter":
            path = _figure_generator.generate_scatter_plot(
                data=data,
                title=title,
                xlabel=xlabel,
                ylabel=ylabel,
                output_path=resolved_output,
            )
        elif normalized_type == "heatmap":
            path = _figure_generator.generate_heatmap(
                data=data,
                title=title,
                output_path=resolved_output,
            )
        else:
            raise ValueError("Unsupported figure_type. Use one of: bar, line, scatter, heatmap")

        return _build_result(path, normalized_type)

    @mcp.tool()
    def generate_comparison(
        papers: list[str],
        metrics: dict[str, list[float]],
        output_path: str,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        path = _figure_generator.generate_comparison_chart(
            papers=papers,
            metrics=metrics,
            output_path=_resolve_output_path(output_path, project_dir),
        )
        return _build_result(path, "comparison")
