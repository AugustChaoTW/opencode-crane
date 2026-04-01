"""Semantic search service using embeddings and vector similarity."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import yaml

from crane.services.reference_service import ReferenceService
from crane.utils.yaml_io import list_paper_keys, read_paper_yaml


class SemanticSearchService:
    """Service for semantic search using embeddings and vector similarity."""

    def __init__(self, refs_dir: str | Path = "references", embedding_api_key: str | None = None):
        self.refs_path = Path(refs_dir)

        if not self.refs_path.exists():
            raise ValueError(f"References directory does not exist: {self.refs_path}")

        self.ref_svc = ReferenceService(refs_dir=self.refs_path)
        self.embeddings_file = self.refs_path / "embeddings.yaml"
        self.embedding_api_key = embedding_api_key
        self.embedding_model = "text-embedding-3-small"
        self.embedding_dim = 1536

        self.references = self._load_references()
        self.embeddings = self._load_embeddings()
        self._embedding_cache: dict[str, list[float]] = {}

    def _load_references(self) -> dict[str, dict[str, Any]]:
        """Load all references from disk."""
        refs = {}
        for key in list_paper_keys(str(self.refs_path / "papers")):
            data = read_paper_yaml(str(self.refs_path / "papers"), key)
            if data:
                refs[key] = data
        return refs

    def _load_embeddings(self) -> dict[str, list[float]] | None:
        """Load embeddings from cache if valid."""
        if not self.embeddings_file.exists():
            return None

        try:
            with open(self.embeddings_file, "r") as f:
                data = yaml.safe_load(f)

            if data and "embeddings" in data:
                embeddings = data["embeddings"]
                if isinstance(embeddings, dict):
                    return embeddings
        except Exception:
            pass

        return None

    def _is_embeddings_cache_valid(self) -> bool:
        """Check if embeddings cache is still valid."""
        if not self.embeddings_file.exists():
            return False

        try:
            with open(self.embeddings_file, "r") as f:
                data = yaml.safe_load(f)

            if not data or "metadata" not in data:
                return False

            metadata = data["metadata"]
            expected_count = len(self.references)
            actual_count = metadata.get("embedding_count", 0)

            return actual_count == expected_count
        except Exception:
            return False

    def _embed_text(self, text: str, api_key: str | None = None) -> list[float] | None:
        """Embed text using OpenAI API."""
        if not api_key:
            return None

        cache_key = f"{text}:{self.embedding_model}"
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        try:
            response = requests.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": self.embedding_model, "input": text},
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            embedding = data["data"][0]["embedding"]

            self._embedding_cache[cache_key] = embedding
            return embedding
        except Exception:
            return None

    def _get_reference_text(self, ref_key: str) -> str:
        """Extract embeddable text from reference."""
        ref = self.references.get(ref_key, {})

        title = str(ref.get("title", ""))
        abstract = str(ref.get("abstract", ""))

        ai_annotations = ref.get("ai_annotations") or {}
        summary = str(ai_annotations.get("summary", ""))
        key_contributions = ai_annotations.get("key_contributions", [])
        contributions_text = " ".join(str(c) for c in key_contributions)

        return f"{title}. {abstract}. {summary}. {contributions_text}".strip()

    def build_embeddings(self, api_key: str | None = None) -> dict[str, list[float]]:
        """Build and cache embeddings for all references."""
        api_key = api_key or self.embedding_api_key

        if not api_key:
            return {}

        embeddings = {}
        for ref_key in self.references:
            text = self._get_reference_text(ref_key)
            embedding = self._embed_text(text, api_key=api_key)
            if embedding:
                embeddings[ref_key] = embedding

        if embeddings:
            self._save_embeddings(embeddings)
            self.embeddings = embeddings

        return embeddings

    def _save_embeddings(self, vectors: dict[str, list[float]]) -> None:
        """Save embeddings to YAML cache."""
        data = {
            "embeddings": vectors,
            "metadata": {
                "model": self.embedding_model,
                "embedding_count": len(vectors),
                "last_updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            },
        }

        with open(self.embeddings_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def search_similar(
        self,
        query_text: str,
        query_embedding: list[float],
        k: int = 5,
        exclude_key: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find similar papers using cosine similarity."""
        if not self.embeddings or not query_embedding:
            return []

        import numpy as np

        query_vec = np.array(query_embedding, dtype=np.float32)

        similarities: list[tuple[str, float]] = []
        for ref_key, ref_embedding in self.embeddings.items():
            if exclude_key and ref_key == exclude_key:
                continue

            ref_vec = np.array(ref_embedding, dtype=np.float32)
            similarity = float(
                np.dot(query_vec, ref_vec)
                / (np.linalg.norm(query_vec) * np.linalg.norm(ref_vec) + 1e-8)
            )
            similarities.append((ref_key, similarity))

        similarities.sort(key=lambda x: x[1], reverse=True)

        results = []
        for ref_key, similarity in similarities[:k]:
            ref = self.references.get(ref_key, {})
            results.append(
                {
                    "key": ref_key,
                    "similarity": similarity,
                    "title": ref.get("title", ""),
                    "authors": ref.get("authors", []),
                    "year": ref.get("year"),
                    "abstract": ref.get("abstract", "")[:200] if ref.get("abstract") else "",
                }
            )

        return results

    def find_similar_by_paper(
        self,
        paper_key: str,
        k: int = 5,
    ) -> list[dict[str, Any]]:
        """Find papers similar to a given reference."""
        if paper_key not in self.embeddings:
            return []

        query_embedding = self.embeddings[paper_key]
        ref = self.references.get(paper_key, {})
        query_text = ref.get("title", "")

        return self.search_similar(
            query_text=query_text,
            query_embedding=query_embedding,
            k=k,
            exclude_key=paper_key,
        )
