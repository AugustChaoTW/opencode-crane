# pyright: reportMissingImports=false, reportMissingModuleSource=false

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import matplotlib  # pyright: ignore[reportMissingImports]

matplotlib.use("Agg")

import seaborn as sns  # pyright: ignore[reportMissingImports, reportMissingModuleSource]
from matplotlib import pyplot as plt  # pyright: ignore[reportMissingImports]
from matplotlib.figure import Figure  # pyright: ignore[reportMissingImports]

PUB_SETTINGS = {
    "dpi": 300,
    "font_family": "serif",
    "font_size": 10,
    "fig_width_single": 3.5,
    "fig_width_double": 7.0,
    "save_format": "pdf",
}

MAX_FIGURE_SIZE_BYTES = 10 * 1024 * 1024


class FigureGenerator:
    def __init__(self, settings: dict[str, Any] | None = None):
        self.settings = {**PUB_SETTINGS, **(settings or {})}
        font_size = self.settings["font_size"]
        self._rc_params = {
            "figure.dpi": self.settings["dpi"],
            "savefig.dpi": self.settings["dpi"],
            "font.family": self.settings["font_family"],
            "font.serif": [
                "Times New Roman",
                "Computer Modern Roman",
                "CMU Serif",
                "Nimbus Roman",
            ],
            "font.size": font_size,
            "axes.titlesize": font_size + 1,
            "axes.labelsize": font_size,
            "xtick.labelsize": font_size - 1,
            "ytick.labelsize": font_size - 1,
            "legend.fontsize": font_size - 1,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "mathtext.fontset": "cm",
            "axes.edgecolor": "#333333",
            "axes.linewidth": 0.8,
            "grid.color": "#d9d9d9",
            "grid.linestyle": "--",
            "grid.linewidth": 0.4,
            "grid.alpha": 0.7,
        }

    def generate_bar_chart(
        self,
        data: Any,
        title: str,
        xlabel: str,
        ylabel: str,
        output_path: str | Path,
    ) -> Path:
        labels, values = self._normalize_category_data(data)
        prefer_double = len(labels) > 5 or self._longest_label(labels) > 12

        with plt.rc_context(self._rc_params):
            fig, ax = self._create_axes(prefer_double=prefer_double)
            palette = sns.color_palette("deep", n_colors=max(len(labels), 1))
            positions = list(range(len(labels)))
            ax.bar(
                positions,
                values,
                width=0.65,
                color=palette[: len(labels)],
                edgecolor="#333333",
                linewidth=0.4,
            )
            ax.set_xticks(positions)
            ax.set_xticklabels(labels)
            self._style_axis(ax, title=title, xlabel=xlabel, ylabel=ylabel, rotate_x=prefer_double)
            return self._save_figure(fig, output_path)

    def generate_line_plot(
        self,
        data: Any,
        title: str,
        xlabel: str,
        ylabel: str,
        output_path: str | Path,
    ) -> Path:
        x_values, y_values = self._normalize_xy_data(data)
        prefer_double = len(x_values) > 8

        with plt.rc_context(self._rc_params):
            fig, ax = self._create_axes(prefer_double=prefer_double)
            ax.plot(
                x_values,
                y_values,
                marker="o",
                markersize=3.8,
                linewidth=1.4,
                color=sns.color_palette("deep", n_colors=1)[0],
            )
            self._style_axis(ax, title=title, xlabel=xlabel, ylabel=ylabel, rotate_x=prefer_double)
            return self._save_figure(fig, output_path)

    def generate_scatter_plot(
        self,
        data: Any,
        title: str,
        xlabel: str,
        ylabel: str,
        output_path: str | Path,
    ) -> Path:
        x_values, y_values = self._normalize_xy_data(data)
        x_numeric = self._normalize_numeric_series(x_values, len(x_values), "x")
        y_numeric = self._normalize_numeric_series(y_values, len(y_values), "y")
        marker_size = 18 if len(x_numeric) > 100 else 24
        alpha = 0.7 if len(x_numeric) > 100 else 0.85

        with plt.rc_context(self._rc_params):
            fig, ax = self._create_axes(prefer_double=len(x_numeric) > 150)
            ax.scatter(
                x_numeric,
                y_numeric,
                s=marker_size,
                alpha=alpha,
                color=sns.color_palette("deep", n_colors=1)[0],
                edgecolors="white",
                linewidths=0.3,
            )
            self._style_axis(ax, title=title, xlabel=xlabel, ylabel=ylabel, rotate_x=False)
            return self._save_figure(fig, output_path)

    def generate_heatmap(
        self,
        data: Any,
        title: str,
        output_path: str | Path,
    ) -> Path:
        matrix, x_labels, y_labels = self._normalize_heatmap_data(data)
        row_count = len(matrix)
        column_count = len(matrix[0])
        prefer_double = column_count > 5 or row_count > 5
        width = self._figure_width(prefer_double)
        height = max(2.6, min(5.2, 1.8 + 0.38 * row_count))
        annotate = row_count * column_count <= 36

        with plt.rc_context(self._rc_params):
            fig, ax = plt.subplots(figsize=(width, height), constrained_layout=True)
            sns.heatmap(
                matrix,
                ax=ax,
                cmap="crest",
                annot=annotate,
                fmt=".2g",
                linewidths=0.3,
                linecolor="white",
                cbar_kws={"shrink": 0.85, "pad": 0.02},
                xticklabels=x_labels,
                yticklabels=y_labels,
            )
            ax.set_title(title, pad=8)
            ax.set_xlabel("")
            ax.set_ylabel("")
            ax.tick_params(axis="x", rotation=30)
            ax.tick_params(axis="y", rotation=0)
            return self._save_figure(fig, output_path)

    def generate_comparison_chart(
        self,
        papers: list[str],
        metrics: dict[str, list[float]],
        output_path: str | Path,
    ) -> Path:
        if len(papers) < 2:
            raise ValueError("Need at least 2 papers for a comparison chart")
        if not metrics:
            raise ValueError("metrics must not be empty")

        metric_names = list(metrics.keys())
        normalized_metrics = {
            name: self._normalize_numeric_series(values, len(papers), name)
            for name, values in metrics.items()
        }
        prefer_double = len(papers) > 4 or len(metric_names) > 2
        positions = list(range(len(papers)))
        bar_width = min(0.8 / max(len(metric_names), 1), 0.3)

        with plt.rc_context(self._rc_params):
            fig, ax = self._create_axes(prefer_double=prefer_double)
            palette = sns.color_palette("colorblind", n_colors=len(metric_names))

            for index, metric_name in enumerate(metric_names):
                offset = (index - (len(metric_names) - 1) / 2) * bar_width
                x_positions = [position + offset for position in positions]
                ax.bar(
                    x_positions,
                    normalized_metrics[metric_name],
                    width=bar_width * 0.95,
                    label=metric_name.replace("_", " ").title(),
                    color=palette[index],
                    edgecolor="#333333",
                    linewidth=0.4,
                )

            ax.set_xticks(positions)
            ax.set_xticklabels(papers)
            self._style_axis(
                ax,
                title="Paper Comparison Across Metrics",
                xlabel="Papers",
                ylabel="Metric Value",
                rotate_x=prefer_double,
            )
            ax.legend(frameon=False, ncol=min(len(metric_names), 3), loc="best")
            return self._save_figure(fig, output_path)

    def _create_axes(self, prefer_double: bool = False) -> tuple[Figure, Any]:
        width = self._figure_width(prefer_double)
        height = max(2.4, width * 0.62)
        fig, ax = plt.subplots(figsize=(width, height), constrained_layout=True)
        return fig, ax

    def _figure_width(self, prefer_double: bool) -> float:
        return (
            self.settings["fig_width_double"]
            if prefer_double
            else self.settings["fig_width_single"]
        )

    def _style_axis(
        self,
        ax: Any,
        title: str,
        xlabel: str,
        ylabel: str,
        rotate_x: bool,
    ) -> None:
        ax.set_title(title, pad=8)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", visible=True)
        ax.grid(axis="x", visible=False)
        ax.set_axisbelow(True)
        ax.tick_params(axis="x", rotation=30 if rotate_x else 0)
        sns.despine(ax=ax)

    def _save_figure(self, figure: Figure, output_path: str | Path) -> Path:
        path = self._prepare_output_path(output_path)
        try:
            figure.savefig(
                path,
                format=self.settings["save_format"],
                bbox_inches="tight",
                transparent=False,
            )
        finally:
            plt.close(figure)

        size_bytes = path.stat().st_size
        if size_bytes > MAX_FIGURE_SIZE_BYTES:
            path.unlink(missing_ok=True)
            raise ValueError(f"Generated figure exceeds 10MB limit: {size_bytes} bytes")
        return path

    def _prepare_output_path(self, output_path: str | Path) -> Path:
        path = Path(output_path)
        if path.suffix and path.suffix.lower() != f".{self.settings['save_format']}":
            raise ValueError("Only PDF output is supported for figure generation")
        if not path.suffix:
            path = path.with_suffix(f".{self.settings['save_format']}")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _normalize_category_data(self, data: Any) -> tuple[list[str], list[float]]:
        if isinstance(data, Mapping):
            if "labels" in data and "values" in data:
                labels = [str(item) for item in self._as_list(data["labels"], "labels")]
                values = self._normalize_numeric_series(data["values"], len(labels), "values")
                return labels, values

            labels = [str(key) for key in data.keys()]
            values = self._normalize_numeric_series(list(data.values()), len(labels), "values")
            return labels, values

        items = self._as_list(data, "data")
        if items and all(isinstance(item, Mapping) for item in items):
            labels = [
                str(item.get("label", item.get("category", item.get("x", "")))) for item in items
            ]
            values = [item.get("value", item.get("y")) for item in items]
            if any(value is None for value in values):
                raise ValueError("Each data point must include a value or y field")
            return labels, self._normalize_numeric_series(values, len(labels), "values")

        if items and all(self._is_non_string_sequence(item) and len(item) >= 2 for item in items):
            labels = [str(item[0]) for item in items]
            values = [item[1] for item in items]
            return labels, self._normalize_numeric_series(values, len(labels), "values")

        raise ValueError("Unsupported bar chart data format")

    def _normalize_xy_data(self, data: Any) -> tuple[list[Any], list[float]]:
        if isinstance(data, Mapping):
            if "x" in data and "y" in data:
                x_values = self._as_list(data["x"], "x")
                y_values = self._normalize_numeric_series(data["y"], len(x_values), "y")
                return x_values, y_values

            labels, values = self._normalize_category_data(data)
            return labels, values

        items = self._as_list(data, "data")
        if items and all(isinstance(item, Mapping) for item in items):
            x_values = [item.get("x") for item in items]
            y_values = [item.get("y") for item in items]
            if any(value is None for value in x_values + y_values):
                raise ValueError("Each data point must include x and y fields")
            return x_values, self._normalize_numeric_series(y_values, len(x_values), "y")

        if items and all(self._is_non_string_sequence(item) and len(item) >= 2 for item in items):
            x_values = [item[0] for item in items]
            y_values = [item[1] for item in items]
            return x_values, self._normalize_numeric_series(y_values, len(x_values), "y")

        raise ValueError("Unsupported x/y data format")

    def _normalize_heatmap_data(self, data: Any) -> tuple[list[list[float]], list[str], list[str]]:
        x_labels: list[str] = []
        y_labels: list[str] = []

        if isinstance(data, Mapping):
            if "values" not in data:
                raise ValueError("Heatmap data must include a values field")
            matrix_input = data["values"]
            if "x_labels" in data:
                x_labels = [str(item) for item in self._as_list(data["x_labels"], "x_labels")]
            if "y_labels" in data:
                y_labels = [str(item) for item in self._as_list(data["y_labels"], "y_labels")]
        else:
            matrix_input = data

        rows = self._as_list(matrix_input, "values")
        if not rows:
            raise ValueError("Heatmap values must not be empty")

        matrix: list[list[float]] = []
        expected_columns: int | None = None
        for row_index, row in enumerate(rows):
            row_values = self._normalize_numeric_series(row, None, f"row_{row_index}")
            if expected_columns is None:
                expected_columns = len(row_values)
            elif len(row_values) != expected_columns:
                raise ValueError("Heatmap rows must all have the same length")
            matrix.append(row_values)

        if expected_columns is None or expected_columns == 0:
            raise ValueError("Heatmap values must include at least one column")

        if not x_labels:
            x_labels = [str(index + 1) for index in range(expected_columns)]
        if not y_labels:
            y_labels = [str(index + 1) for index in range(len(matrix))]
        if len(x_labels) != expected_columns:
            raise ValueError("x_labels length must match heatmap column count")
        if len(y_labels) != len(matrix):
            raise ValueError("y_labels length must match heatmap row count")

        return matrix, x_labels, y_labels

    def _normalize_numeric_series(
        self,
        values: Any,
        expected_length: int | None,
        field_name: str,
    ) -> list[float]:
        items = self._as_list(values, field_name)
        if not items:
            raise ValueError(f"{field_name} must not be empty")
        if expected_length is not None and len(items) != expected_length:
            raise ValueError(f"{field_name} length must match expected length {expected_length}")

        normalized: list[float] = []
        for value in items:
            try:
                normalized.append(float(value))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{field_name} contains non-numeric value: {value}") from exc
        return normalized

    def _as_list(self, values: Any, field_name: str) -> list[Any]:
        if isinstance(values, Mapping):
            raise ValueError(f"{field_name} must be a sequence, not a mapping")
        if not self._is_non_string_sequence(values):
            raise ValueError(f"{field_name} must be a sequence")
        return list(values)

    def _is_non_string_sequence(self, value: Any) -> bool:
        return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))

    def _longest_label(self, labels: list[str]) -> int:
        return max((len(label) for label in labels), default=0)
