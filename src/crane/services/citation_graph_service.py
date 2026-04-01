"""Citation graph service for building and analyzing citation relationships."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from crane.providers.openalex import OpenAlexProvider
from crane.providers.semantic_scholar import SemanticScholarProvider
from crane.services.reference_service import ReferenceService
from crane.utils.yaml_io import list_paper_keys, read_paper_yaml, write_paper_yaml


class CitationGraphService:
    """Service for citation graph operations and gap detection."""

    def __init__(self, refs_dir: str | Path = "references"):
        self.refs_path = Path(refs_dir)
        self.papers_dir = self.refs_path / "papers"
        self.ref_svc = ReferenceService(refs_dir=self.refs_path)

        self.semantic_scholar = SemanticScholarProvider()
        self.openalex = OpenAlexProvider()

        self._references: dict[str, dict[str, Any]] = {}
        self._load_references()

    def _load_references(self) -> None:
        """Load all references into memory."""
        for key in list_paper_keys(str(self.papers_dir)):
            data = read_paper_yaml(str(self.papers_dir), key)
            if data:
                self._references[key] = data

    def _get_provider(self, source: str = "semantic_scholar"):
        """Get paper provider by source name."""
        if source == "semantic_scholar":
            return self.semantic_scholar
        elif source == "openalex":
            return self.openalex
        raise ValueError(f"Unknown provider: {source}")

    def build_citation_graph(
        self,
        source: str = "semantic_scholar",
        limit_per_paper: int = 10,
    ) -> dict[str, list[str]]:
        """Build citation graph for all references.

        Returns:
            Dict mapping paper_key -> list of cited reference keys
        """
        provider = self._get_provider(source)
        graph: dict[str, list[str]] = {}

        for key, ref_data in self._references.items():
            doi = ref_data.get("doi", "")
            if not doi:
                graph[key] = []
                continue

            try:
                paper = provider.get_by_doi(doi)
                if paper and paper.references:
                    graph[key] = paper.references[:limit_per_paper]
                    self._update_citations(key, paper.references)
                else:
                    graph[key] = []
            except Exception:
                graph[key] = []

        return graph

    def _update_citations(self, key: str, cited_ids: list[str]) -> None:
        """Update paper YAML with citation data."""
        if key not in self._references:
            return

        ref_data = self._references[key]
        ref_data["cites"] = cited_ids

        write_paper_yaml(str(self.papers_dir), key, ref_data)

    def find_citation_gaps(
        self,
        min_citation_count: int = 2,
        top_k: int = 20,
    ) -> list[dict[str, Any]]:
        """Find papers cited by multiple references but not in library.

        Args:
            min_citation_count: Minimum times a paper must be cited to be a gap
            top_k: Maximum number of gaps to return

        Returns:
            List of missing papers with citation frequency and metadata
        """
        citation_freq: dict[str, int] = {}
        citation_sources: dict[str, list[str]] = {}

        for key, ref_data in self._references.items():
            for cited_id in ref_data.get("cites", []):
                citation_freq[cited_id] = citation_freq.get(cited_id, 0) + 1
                if cited_id not in citation_sources:
                    citation_sources[cited_id] = []
                citation_sources[cited_id].append(key)

        gaps: list[dict[str, Any]] = []
        for cited_id, count in citation_freq.items():
            if count < min_citation_count:
                continue

            if cited_id in self._references:
                continue

            gaps.append(
                {
                    "paper_id": cited_id,
                    "citation_count": count,
                    "cited_by": citation_sources[cited_id],
                }
            )

        gaps.sort(key=lambda x: x["citation_count"], reverse=True)
        return gaps[:top_k]

    def find_semantic_gaps(
        self,
        k_clusters: int = 5,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Find sparse regions in embedding space.

        Uses k-means clustering on paper embeddings to find
        under-explored topic intersections.

        Returns:
            List of sparse regions with centroid papers
        """
        import numpy as np

        embeddings_file = self.refs_path / "embeddings.yaml"
        if not embeddings_file.exists():
            return []

        with open(embeddings_file) as f:
            data = yaml.safe_load(f)

        if not data or "embeddings" not in data:
            return []

        embeddings = data["embeddings"]
        if len(embeddings) < k_clusters:
            return []

        keys = list(embeddings.keys())
        vectors = np.array([embeddings[k] for k in keys], dtype=np.float32)

        labels, centroids = self._kmeans(vectors, k_clusters)

        cluster_sizes = [np.sum(labels == i) for i in range(k_clusters)]
        min_cluster = int(np.argmin(cluster_sizes))

        sparse_regions = []
        for i in range(k_clusters):
            if cluster_sizes[i] <= min_cluster + 1:
                centroid = centroids[i]
                dists = np.linalg.norm(vectors - centroid, axis=1)
                nearest_idx = np.argsort(dists)[:3]

                cluster_papers = [keys[idx] for idx in nearest_idx]
                sparse_regions.append(
                    {
                        "cluster_id": i,
                        "size": int(cluster_sizes[i]),
                        "representative_papers": cluster_papers,
                        "sparse": True,
                    }
                )

        return sparse_regions[:top_k]

    def _kmeans(
        self,
        vectors: np.ndarray,
        k: int,
        max_iter: int = 100,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Run k-means clustering.

        Returns:
            Tuple of (labels, centroids)
        """
        import numpy as np

        n = len(vectors)
        if n < k:
            k = n

        idx = np.random.choice(n, k, replace=False)
        centroids = vectors[idx].copy()

        for _ in range(max_iter):
            dists = np.linalg.norm(vectors[:, None] - centroids[None, :], axis=2)
            labels = np.argmin(dists, axis=1)

            new_centroids = np.zeros_like(centroids)
            for i in range(k):
                mask = labels == i
                if np.any(mask):
                    new_centroids[i] = vectors[mask].mean(axis=0)
                else:
                    new_centroids[i] = centroids[i]

            if np.allclose(centroids, new_centroids):
                break
            centroids = new_centroids

        return labels, centroids

    def get_research_clusters(
        self,
        k_clusters: int = 5,
    ) -> list[dict[str, Any]]:
        """Group references into topic clusters.

        Returns:
            List of clusters with paper keys and summaries
        """
        import numpy as np

        embeddings_file = self.refs_path / "embeddings.yaml"
        if not embeddings_file.exists():
            return []

        with open(embeddings_file) as f:
            data = yaml.safe_load(f)

        if not data or "embeddings" not in data:
            return []

        embeddings = data["embeddings"]
        if len(embeddings) < k_clusters:
            return []

        keys = list(embeddings.keys())
        vectors = np.array([embeddings[k] for k in keys], dtype=np.float32)

        labels, _ = self._kmeans(vectors, k_clusters)

        clusters: list[dict[str, Any]] = []
        for i in range(k_clusters):
            cluster_keys = [keys[j] for j, label in enumerate(labels) if label == i]

            cluster_refs = []
            for key in cluster_keys:
                ref = self._references.get(key, {})
                cluster_refs.append(
                    {
                        "key": key,
                        "title": ref.get("title", ""),
                        "year": ref.get("year", 0),
                        "cites": ref.get("cites", []),
                    }
                )

            clusters.append(
                {
                    "cluster_id": i,
                    "size": len(cluster_keys),
                    "papers": cluster_refs,
                }
            )

        clusters.sort(key=lambda x: x["size"], reverse=True)
        return clusters
