from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import random


@dataclass
class ShortestPathResult:
    success: bool
    path_length: int
    expected_length: int
    path: list[str]


@dataclass
class GeneralizationReport:
    spatial_transfer_score: float
    length_scaling_score: float
    failure_mode: str | None


class GeneralizationBenchmarkService:
    def generate_grid_map(
        self, width: int, height: int, sparsity: float = 0.3
    ) -> dict[str, list[str]]:
        nodes = {}
        for y in range(height):
            for x in range(width):
                node_id = f"N{x}_{y}"
                neighbors = []
                if x > 0 and random.random() > sparsity:
                    neighbors.append(f"N{x-1}_{y}")
                if x < width - 1 and random.random() > sparsity:
                    neighbors.append(f"N{x+1}_{y}")
                if y > 0 and random.random() > sparsity:
                    neighbors.append(f"N{x}_{y-1}")
                if y < height - 1 and random.random() > sparsity:
                    neighbors.append(f"N{x}_{y+1}")
                if neighbors:
                    nodes[node_id] = neighbors
        return nodes

    def find_shortest_path_bfs(
        self, start: str, end: str, graph: dict[str, list[str]]
    ) -> list[str]:
        if start not in graph and end not in graph:
            return []
        visited = {start}
        queue = [(start, [start])]
        while queue:
            node, path = queue.pop(0)
            if node == end:
                return path
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return []

    def evaluate_spatial_transfer(
        self, train_graph: dict, test_graph: dict
    ) -> float:
        test_pairs = [
            (start, end)
            for start in test_graph
            for end in test_graph
            if start != end
        ][:20]
        successes = 0
        for start, end in test_pairs:
            path = self.find_shortest_path_bfs(start, end, test_graph)
            if path:
                successes += 1
        return successes / len(test_pairs) if test_pairs else 0.0

    def evaluate_length_scaling(
        self, graph: dict, max_train_length: int
    ) -> dict[int, float]:
        results = {}
        for length in [max_train_length + 5, max_train_length + 10]:
            nodes = list(graph.keys())
            test_pairs = [(n1, n2) for n1 in nodes for n2 in nodes if n1 != n2]
            successes = 0
            for start, end in test_pairs:
                path = self.find_shortest_path_bfs(start, end, graph)
                if path and len(path) > max_train_length:
                    successes += 1
            results[length] = successes / len(test_pairs) if test_pairs else 0.0
        return results

    def run_benchmark(self, width: int = 10, height: int = 10) -> GeneralizationReport:
        train_graph = self.generate_grid_map(width, height)
        test_graph = self.generate_grid_map(width, height)

        spatial = self.evaluate_spatial_transfer(train_graph, test_graph)
        length_results = self.evaluate_length_scaling(train_graph, max_train_length=8)

        avg_length = sum(length_results.values()) / len(length_results) if length_results else 0.0

        failure_mode = None
        if avg_length < 0.5:
            failure_mode = "recursive_instability"
        elif spatial < 0.7:
            failure_mode = "spatial_transfer_failure"

        return GeneralizationReport(
            spatial_transfer_score=spatial,
            length_scaling_score=avg_length,
            failure_mode=failure_mode,
        )