# pyright: reportMissingImports=false

from __future__ import annotations

from pathlib import Path

import pytest

from crane.services.figure_generator import FigureGenerator


@pytest.fixture
def gen() -> FigureGenerator:
    return FigureGenerator(settings={"dpi": 80})


def test_prepare_output_path_adds_pdf_suffix(gen: FigureGenerator, tmp_path: Path) -> None:
    path = gen._prepare_output_path(tmp_path / "fig")
    assert path.suffix == ".pdf"
    assert path.parent.exists()


def test_prepare_output_path_rejects_non_pdf_suffix(gen: FigureGenerator, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Only PDF output"):
        gen._prepare_output_path(tmp_path / "fig.png")


@pytest.mark.parametrize(
    ("data", "expected_labels", "expected_values"),
    [
        ({"a": 1, "b": 2}, ["a", "b"], [1.0, 2.0]),
        ({"labels": ["x", "y"], "values": [3, 4]}, ["x", "y"], [3.0, 4.0]),
        ([{"label": "a", "value": 1}], ["a"], [1.0]),
        ([("a", 1), ("b", 2)], ["a", "b"], [1.0, 2.0]),
    ],
)
def test_normalize_category_data_supported_formats(
    gen: FigureGenerator, data, expected_labels, expected_values
) -> None:
    labels, values = gen._normalize_category_data(data)
    assert labels == expected_labels
    assert values == expected_values


@pytest.mark.parametrize(
    "data",
    [
        [{"label": "a"}],
        "not-sequence",
        [1, 2, 3],
    ],
)
def test_normalize_category_data_invalid_formats_raise(gen: FigureGenerator, data) -> None:
    with pytest.raises(ValueError):
        gen._normalize_category_data(data)


@pytest.mark.parametrize(
    ("data", "x", "y"),
    [
        ({"x": [1, 2], "y": [3, 4]}, [1, 2], [3.0, 4.0]),
        ({"a": 1, "b": 2}, ["a", "b"], [1.0, 2.0]),
        ([{"x": 1, "y": 2}, {"x": 3, "y": 4}], [1, 3], [2.0, 4.0]),
        ([(1, 2), (3, 4)], [1, 3], [2.0, 4.0]),
    ],
)
def test_normalize_xy_data_supported_formats(gen: FigureGenerator, data, x, y) -> None:
    x_values, y_values = gen._normalize_xy_data(data)
    assert x_values == x
    assert y_values == y


@pytest.mark.parametrize("data", [[{"x": 1}], "bad", [{"y": 2}]])
def test_normalize_xy_data_invalid_formats_raise(gen: FigureGenerator, data) -> None:
    with pytest.raises(ValueError):
        gen._normalize_xy_data(data)


def test_normalize_heatmap_data_defaults_labels(gen: FigureGenerator) -> None:
    matrix, x_labels, y_labels = gen._normalize_heatmap_data([[1, 2], [3, 4]])
    assert matrix == [[1.0, 2.0], [3.0, 4.0]]
    assert x_labels == ["1", "2"]
    assert y_labels == ["1", "2"]


@pytest.mark.parametrize(
    "data",
    [
        {"x_labels": ["a"]},
        [],
        [[1, 2], [3]],
        {"values": [[1]], "x_labels": ["a", "b"]},
        {"values": [[1]], "y_labels": ["a", "b"]},
    ],
)
def test_normalize_heatmap_data_invalid_cases_raise(gen: FigureGenerator, data) -> None:
    with pytest.raises(ValueError):
        gen._normalize_heatmap_data(data)


@pytest.mark.parametrize(
    ("values", "expected_len", "field", "valid"),
    [
        ([1, 2, 3], 3, "v", True),
        ([1, "2"], 2, "v", True),
        ([], None, "v", False),
        ([1], 2, "v", False),
        (["x"], 1, "v", False),
    ],
)
def test_normalize_numeric_series_variants(
    gen: FigureGenerator, values, expected_len, field: str, valid: bool
) -> None:
    if valid:
        out = gen._normalize_numeric_series(values, expected_len, field)
        assert len(out) == len(values)
    else:
        with pytest.raises(ValueError):
            gen._normalize_numeric_series(values, expected_len, field)


@pytest.mark.parametrize(
    ("value", "field", "raises"),
    [
        ([1, 2], "ok", False),
        ({"a": 1}, "bad", True),
        ("abc", "bad", True),
    ],
)
def test_as_list_validation(gen: FigureGenerator, value, field: str, raises: bool) -> None:
    if raises:
        with pytest.raises(ValueError):
            gen._as_list(value, field)
    else:
        assert gen._as_list(value, field) == [1, 2]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ([1, 2], True),
        ((1, 2), True),
        ("abc", False),
        (b"abc", False),
        ({"a": 1}, False),
    ],
)
def test_is_non_string_sequence(gen: FigureGenerator, value, expected: bool) -> None:
    assert gen._is_non_string_sequence(value) is expected


def test_longest_label(gen: FigureGenerator) -> None:
    assert gen._longest_label(["a", "abcd", "abc"]) == 4
    assert gen._longest_label([]) == 0


def test_generate_bar_chart_creates_file(gen: FigureGenerator, tmp_path: Path) -> None:
    out = gen.generate_bar_chart({"A": 1, "B": 2}, "T", "X", "Y", tmp_path / "bar")
    assert out.exists()


def test_generate_line_plot_creates_file(gen: FigureGenerator, tmp_path: Path) -> None:
    out = gen.generate_line_plot({"x": [1, 2], "y": [3, 4]}, "T", "X", "Y", tmp_path / "line")
    assert out.exists()


def test_generate_scatter_plot_creates_file(gen: FigureGenerator, tmp_path: Path) -> None:
    out = gen.generate_scatter_plot([(1, 2), (2, 3)], "T", "X", "Y", tmp_path / "scatter")
    assert out.exists()


def test_generate_heatmap_creates_file(gen: FigureGenerator, tmp_path: Path) -> None:
    out = gen.generate_heatmap([[1, 2], [3, 4]], "Heat", tmp_path / "heat")
    assert out.exists()


def test_generate_comparison_chart_validations(gen: FigureGenerator, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Need at least 2 papers"):
        gen.generate_comparison_chart(["p1"], {"acc": [1]}, tmp_path / "cmp")
    with pytest.raises(ValueError, match="metrics must not be empty"):
        gen.generate_comparison_chart(["p1", "p2"], {}, tmp_path / "cmp")


def test_generate_comparison_chart_creates_file(gen: FigureGenerator, tmp_path: Path) -> None:
    out = gen.generate_comparison_chart(
        ["p1", "p2"],
        {"acc": [0.8, 0.9], "f1": [0.7, 0.8]},
        tmp_path / "cmp",
    )
    assert out.exists()


def test_save_figure_raises_when_too_large(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    big = FigureGenerator()
    monkeypatch.setattr("crane.services.figure_generator.MAX_FIGURE_SIZE_BYTES", 1)
    with pytest.raises(ValueError, match="exceeds 10MB"):
        big.generate_bar_chart({"A": 1}, "t", "x", "y", tmp_path / "oversize")
