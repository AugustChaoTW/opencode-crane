# pyright: reportMissingImports=false

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from collections.abc import Mapping

import yaml

from crane.services.citation_graph_service import CitationGraphService


def _build_service(
    service_refs_dir: Path,
    sample_reference_map: Mapping[str, Mapping[str, object]],
    monkeypatch,
) -> CitationGraphService:
    monkeypatch.setattr(
        "crane.services.citation_graph_service.list_paper_keys",
        lambda *_a, **_k: list(sample_reference_map.keys()),
    )
    monkeypatch.setattr(
        "crane.services.citation_graph_service.read_paper_yaml",
        lambda _papers_dir, key: sample_reference_map.get(key),
    )
    return CitationGraphService(refs_dir=service_refs_dir)


def test_get_provider_returns_expected_instances(
    service_refs_dir: Path,
    sample_reference_map: dict[str, dict[str, object]],
    monkeypatch,
) -> None:
    svc = _build_service(service_refs_dir, sample_reference_map, monkeypatch)
    assert svc._get_provider("semantic_scholar") is svc.semantic_scholar
    assert svc._get_provider("openalex") is svc.openalex


def test_get_provider_unknown_raises(
    service_refs_dir: Path,
    sample_reference_map: dict[str, dict[str, object]],
    monkeypatch,
) -> None:
    svc = _build_service(service_refs_dir, sample_reference_map, monkeypatch)
    try:
        svc._get_provider("bad")
    except ValueError as exc:
        assert "Unknown provider" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_build_citation_graph_handles_success_empty_and_exception(
    service_refs_dir: Path,
    sample_reference_map: dict[str, dict[str, object]],
    monkeypatch,
) -> None:
    svc = _build_service(service_refs_dir, sample_reference_map, monkeypatch)
    provider = MagicMock()
    provider.get_by_doi.side_effect = [
        SimpleNamespace(references=["x1", "x2", "x3"]),
        RuntimeError("api fail"),
    ]
    monkeypatch.setattr(svc, "_get_provider", lambda *_a, **_k: provider)
    update = MagicMock()
    monkeypatch.setattr(svc, "_update_citations", update)

    graph = svc.build_citation_graph(limit_per_paper=2)
    assert graph["paper-a"] == ["x1", "x2"]
    assert graph["paper-b"] == []
    update.assert_called_once_with("paper-a", ["x1", "x2", "x3"])


def test_build_citation_graph_without_doi_returns_empty_list(
    service_refs_dir: Path, monkeypatch
) -> None:
    refs = {"paper-a": {"title": "A", "doi": ""}}
    svc = _build_service(service_refs_dir, refs, monkeypatch)
    graph = svc.build_citation_graph()
    assert graph == {"paper-a": []}


def test_update_citations_writes_yaml(
    service_refs_dir: Path,
    sample_reference_map: dict[str, dict[str, object]],
    monkeypatch,
) -> None:
    svc = _build_service(service_refs_dir, sample_reference_map, monkeypatch)
    writer = MagicMock()
    monkeypatch.setattr("crane.services.citation_graph_service.write_paper_yaml", writer)

    svc._update_citations("paper-a", ["c1", "c2"])
    assert svc._references["paper-a"]["cites"] == ["c1", "c2"]
    writer.assert_called_once_with(str(svc.papers_dir), "paper-a", svc._references["paper-a"])


def test_update_citations_missing_key_no_write(
    service_refs_dir: Path,
    sample_reference_map: dict[str, dict[str, object]],
    monkeypatch,
) -> None:
    svc = _build_service(service_refs_dir, sample_reference_map, monkeypatch)
    writer = MagicMock()
    monkeypatch.setattr("crane.services.citation_graph_service.write_paper_yaml", writer)
    svc._update_citations("missing", ["x"])
    writer.assert_not_called()


def test_find_citation_gaps_filters_counts_existing_and_topk(
    service_refs_dir: Path,
    sample_reference_map: dict[str, dict[str, object]],
    monkeypatch,
) -> None:
    svc = _build_service(service_refs_dir, sample_reference_map, monkeypatch)
    gaps = svc.find_citation_gaps(min_citation_count=2, top_k=1)
    assert len(gaps) == 1
    assert gaps[0]["paper_id"] == "ext-1"
    assert gaps[0]["citation_count"] == 2


def test_find_semantic_gaps_no_embedding_file_returns_empty(
    service_refs_dir: Path,
    sample_reference_map: dict[str, dict[str, object]],
    monkeypatch,
) -> None:
    svc = _build_service(service_refs_dir, sample_reference_map, monkeypatch)
    assert svc.find_semantic_gaps() == []


def test_find_semantic_gaps_invalid_embedding_payload_returns_empty(
    service_refs_dir: Path,
    sample_reference_map: dict[str, dict[str, object]],
    monkeypatch,
) -> None:
    svc = _build_service(service_refs_dir, sample_reference_map, monkeypatch)
    (service_refs_dir / "embeddings.yaml").write_text("foo: bar", encoding="utf-8")
    assert svc.find_semantic_gaps() == []


def test_find_semantic_gaps_with_sparse_clusters(
    service_refs_dir: Path,
    sample_reference_map: dict[str, dict[str, object]],
    monkeypatch,
) -> None:
    svc = _build_service(service_refs_dir, sample_reference_map, monkeypatch)
    embeddings = {
        "embeddings": {
            "paper-a": [0.0, 0.0],
            "paper-b": [0.1, 0.1],
            "paper-c": [10.0, 10.0],
            "paper-d": [10.2, 10.1],
        }
    }
    (service_refs_dir / "embeddings.yaml").write_text(yaml.dump(embeddings), encoding="utf-8")
    monkeypatch.setattr(svc, "_kmeans", lambda _v, _k: ([0, 0, 1, 1], [[0, 0], [10, 10]]))

    gaps = svc.find_semantic_gaps(k_clusters=2)
    assert len(gaps) == 2
    assert all(item["sparse"] is True for item in gaps)


def test_kmeans_reduces_k_when_vectors_fewer_than_clusters(
    service_refs_dir: Path,
    sample_reference_map: dict[str, dict[str, object]],
    monkeypatch,
) -> None:
    import numpy as np

    svc = _build_service(service_refs_dir, sample_reference_map, monkeypatch)
    vectors = np.array([[0.0, 0.0], [1.0, 1.0]], dtype=np.float32)
    labels, centroids = svc._kmeans(vectors, k=5)
    assert len(labels) == 2
    assert centroids.shape[0] == 2


def test_get_research_clusters_empty_when_no_embedding_file(
    service_refs_dir: Path,
    sample_reference_map: dict[str, dict[str, object]],
    monkeypatch,
) -> None:
    svc = _build_service(service_refs_dir, sample_reference_map, monkeypatch)
    assert svc.get_research_clusters() == []


def test_get_research_clusters_success_sorted(
    service_refs_dir: Path,
    sample_reference_map: dict[str, dict[str, object]],
    monkeypatch,
) -> None:
    svc = _build_service(service_refs_dir, sample_reference_map, monkeypatch)
    embeddings = {"embeddings": {"paper-a": [0.1], "paper-b": [0.2], "paper-c": [0.3]}}
    (service_refs_dir / "embeddings.yaml").write_text(yaml.dump(embeddings), encoding="utf-8")
    monkeypatch.setattr(svc, "_kmeans", lambda _v, _k: ([0, 1, 1], [[0.1], [0.2]]))
    svc._references["paper-c"] = {"title": "C", "year": 2020, "cites": ["x"]}

    clusters = svc.get_research_clusters(k_clusters=2)
    assert clusters[0]["size"] >= clusters[1]["size"]
    assert all("papers" in c for c in clusters)


def test_generate_citation_mermaid_uses_stored_graph_when_none(
    service_refs_dir: Path,
    sample_reference_map: dict[str, dict[str, object]],
    monkeypatch,
) -> None:
    svc = _build_service(service_refs_dir, sample_reference_map, monkeypatch)
    mmd = svc.generate_citation_mermaid()
    assert "graph TD" in mmd
    assert "paper-a" in mmd
    assert "MISSING" in mmd


def test_generate_citation_mermaid_empty_graph_placeholder(
    service_refs_dir: Path,
    monkeypatch,
) -> None:
    svc = _build_service(service_refs_dir, {}, monkeypatch)
    mmd = svc.generate_citation_mermaid(graph={})
    assert "No citation data" in mmd


def test_generate_cluster_mermaid_no_clusters_message(
    service_refs_dir: Path,
    sample_reference_map: dict[str, dict[str, object]],
    monkeypatch,
) -> None:
    svc = _build_service(service_refs_dir, sample_reference_map, monkeypatch)
    monkeypatch.setattr(svc, "get_research_clusters", lambda **_k: [])
    out = svc.generate_cluster_mermaid(clusters=None)
    assert "No clusters available" in out


def test_generate_cluster_mermaid_success(
    service_refs_dir: Path,
    sample_reference_map: dict[str, dict[str, object]],
    monkeypatch,
) -> None:
    svc = _build_service(service_refs_dir, sample_reference_map, monkeypatch)
    clusters = [
        {"cluster_id": 1, "size": 1, "papers": [{"key": "p1", "title": "A very long title"}]}
    ]
    out = svc.generate_cluster_mermaid(clusters=clusters)
    assert "subgraph C1" in out
    assert "p1" in out


def test_generate_citation_figure_no_data(
    service_refs_dir: Path,
    monkeypatch,
) -> None:
    svc = _build_service(service_refs_dir, {}, monkeypatch)
    out = svc.generate_citation_figure(str(service_refs_dir / "figs" / "a.pdf"))
    assert out["status"] == "no_data"


def test_generate_citation_figure_success_creates_file(
    service_refs_dir: Path,
    sample_reference_map: dict[str, dict[str, object]],
    monkeypatch,
) -> None:
    svc = _build_service(service_refs_dir, sample_reference_map, monkeypatch)
    out_file = service_refs_dir / "figures" / "graph.pdf"
    out = svc.generate_citation_figure(str(out_file))
    assert out["status"] == "success"
    assert out_file.exists()
    assert out["paper_count"] == 2
