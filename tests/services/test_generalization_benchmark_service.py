import pytest
from crane.services.generalization_benchmark_service import (
    GeneralizationBenchmarkService,
    ShortestPathResult,
    GeneralizationReport,
)


def test_generate_grid_map():
    service = GeneralizationBenchmarkService()
    graph = service.generate_grid_map(5, 5, sparsity=0.3)
    assert len(graph) > 0


def test_find_shortest_path_bfs():
    service = GeneralizationBenchmarkService()
    graph = {"A": ["B"], "B": ["C"], "C": []}
    path = service.find_shortest_path_bfs("A", "C", graph)
    assert path == ["A", "B", "C"]


def test_evaluate_spatial_transfer():
    service = GeneralizationBenchmarkService()
    train = {"A": ["B"], "B": ["C"], "C": []}
    test = {"X": ["Y"], "Y": ["Z"], "Z": []}
    score = service.evaluate_spatial_transfer(train, test)
    assert 0.0 <= score <= 1.0


def test_evaluate_length_scaling():
    service = GeneralizationBenchmarkService()
    graph = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
    results = service.evaluate_length_scaling(graph, max_train_length=2)
    assert isinstance(results, dict)


def test_run_benchmark():
    service = GeneralizationBenchmarkService()
    report = service.run_benchmark(width=5, height=5)
    assert isinstance(report, GeneralizationReport)
    assert 0.0 <= report.spatial_transfer_score <= 1.0
    assert 0.0 <= report.length_scaling_score <= 1.0