"""
Semantic search service using OpenAI embeddings and cosine similarity.

Provides vector-based similarity search across the reference library.
Uses text-embedding-3-small model (1536 dimensions) with local YAML caching.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import requests
import yaml

from crane.utils.yaml_io import list_paper_keys, read_paper_yaml


class SemanticSearchService:
    """Service for semantic search over references using vector embeddings.

    Embeds reference texts (title + abstract + summary) via OpenAI API,
    caches vectors locally in ``references/embeddings.yaml``, and performs
    cosine-similarity k-NN search.

    Args:
        refs_dir: Path to the references directory (contains ``papers/``).
        embedding_api_key: Optional OpenAI API key. Falls back to
            ``OPENAI_API_KEY`` environment variable.

    Raises:
        ValueError: If *refs_dir* does not exist.
    """

    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIM = 1536
    API_URL = "https://api.openai.com/v1/embeddings"

    def __init__(
        self,
        refs_dir: str | Path = "references",
        embedding_api_key: str | None = None,
    ) -> None:
        self.refs_path = Path(refs_dir)

        if not self.refs_path.exists():
            raise ValueError(f"References directory does not exist: {self.refs_path}")

        self.papers_dir = self.refs_path / "papers"
        self.papers_dir.mkdir(parents=True, exist_ok=True)

        self.embeddings_file = self.refs_path / "embeddings.yaml"
        self.embedding_api_key = embedding_api_key
        self.embedding_model = self.EMBEDDING_MODEL
        self.embedding_dim = self.EMBEDDING_DIM

        # Internal state
        self.references: dict[str, dict[str, Any]] = {}
        self.embeddings: dict[str, list[float]] = {}
        self._embedding_cache: dict[str, list[float]] = {}

        # Load data
        self._load_references()
        cached = self._load_embeddings()
        if cached is not None:
            self.embeddings = cached

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def has_embeddings(self) -> bool:
        """Return ``True`` if at least one embedding is loaded."""
        return len(self.embeddings) > 0

    @property
    def embedding_count(self) -> int:
        """Return the number of embedded references."""
        return len(self.embeddings)

    # ------------------------------------------------------------------
    # Reference loading
    # ------------------------------------------------------------------

    def _load_references(self) -> None:
        """Load all reference metadata from YAML files on disk."""
        self.references = {}
        for key in list_paper_keys(str(self.papers_dir)):
            data = read_paper_yaml(str(self.papers_dir), key)
            if data is not None:
                self.references[key] = data

    def get_reference_data(self, key: str) -> dict[str, Any]:
        """Return full metadata for a single reference.

        Args:
            key: Citation key.

        Returns:
            Reference dict.

        Raises:
            ValueError: If *key* is not found.
        """
        if key not in self.references:
            raise ValueError(f"Reference not found: {key}")
        return self.references[key]

    def get_reference_text(self, key: str) -> str:
        """Build the embeddable text for a reference.

        Concatenates title, abstract, and AI-annotation summary.

        Args:
            key: Citation key.

        Returns:
            Combined text string.
        """
        ref = self.references.get(key, {})
        title = str(ref.get("title", ""))
        abstract = str(ref.get("abstract", ""))
        ai = ref.get("ai_annotations") or {}
        summary = str(ai.get("summary", ""))
        contributions = ai.get("key_contributions", [])
        contrib_text = " ".join(str(c) for c in contributions)
        return f"{title}. {abstract}. {summary}. {contrib_text}".strip()

    def get_unembedded_keys(self) -> list[str]:
        """Return reference keys that do not yet have embeddings.

        Returns:
            List of keys missing from ``self.embeddings``.
        """
        return [k for k in self.references if k not in self.embeddings]

    # ------------------------------------------------------------------
    # Embedding API
    # ------------------------------------------------------------------

    def _resolve_api_key(self, api_key: str | None = None) -> str | None:
        """Return the first available API key (explicit > instance > env)."""
        return api_key or self.embedding_api_key or os.environ.get("OPENAI_API_KEY")

    def _embed_text(self, text: str, api_key: str | None = None) -> list[float] | None:
        """Embed *text* via the OpenAI embeddings API.

        Args:
            text: Input text to embed.
            api_key: Optional override for the API key.

        Returns:
            1536-dim float list, or ``None`` if no API key is available.

        Raises:
            requests.HTTPError: On non-2xx API response.
        """
        resolved_key = self._resolve_api_key(api_key)
        if not resolved_key:
            return None

        # In-memory cache (avoids duplicate API calls within a session)
        cache_key = text
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        response = requests.post(
            self.API_URL,
            headers={
                "Authorization": f"Bearer {resolved_key}",
                "Content-Type": "application/json",
            },
            json={"model": self.EMBEDDING_MODEL, "input": text},
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        embedding: list[float] = data["data"][0]["embedding"]
        self._embedding_cache[cache_key] = embedding
        return embedding

    # ------------------------------------------------------------------
    # Build embeddings
    # ------------------------------------------------------------------

    def build_embeddings(self, api_key: str | None = None) -> dict[str, list[float]]:
        """Embed all references that are not yet cached.

        Only calls the API for references missing from ``self.embeddings``.
        Saves the updated cache to disk afterwards.

        Args:
            api_key: Optional API key override.

        Returns:
            The full embeddings dict (including previously cached ones).
        """
        resolved_key = self._resolve_api_key(api_key)
        if not resolved_key:
            return dict(self.embeddings)

        missing = self.get_unembedded_keys()
        for key in missing:
            text = self.get_reference_text(key)
            vec = self._embed_text(text, api_key=resolved_key)
            if vec is not None:
                self.embeddings[key] = vec

        if self.embeddings:
            self._save_embeddings(self.embeddings)

        return dict(self.embeddings)

    # ------------------------------------------------------------------
    # Similarity search
    # ------------------------------------------------------------------

    def search_similar(
        self,
        query_text: str,
        query_embedding: list[float] | None = None,
        k: int = 5,
        exclude_key: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find the *k* most similar references to a query.

        If *query_embedding* is provided it is used directly; otherwise
        the query text is embedded via the API.

        Args:
            query_text: Natural-language query.
            query_embedding: Pre-computed query vector (optional).
            k: Number of results to return.
            exclude_key: Reference key to exclude (e.g. the query paper).

        Returns:
            List of dicts with ``key``, ``similarity``, ``title``,
            ``authors``, ``year``, and truncated ``abstract``.

        Raises:
            ValueError: If *query_text* is empty/whitespace or no
                embeddings are loaded.
        """
        if not query_text or not query_text.strip():
            raise ValueError("Query text must not be empty")

        if k <= 0:
            return []

        if not self.embeddings:
            if query_embedding is None:
                raise ValueError("No embeddings loaded. Call build_embeddings() first.")
            return []

        # Use provided embedding or compute one
        if query_embedding is None:
            computed = self._embed_text(query_text)
            if computed is None:
                raise ValueError(
                    "Cannot embed query: no API key available. "
                    "Set OPENAI_API_KEY or pass query_embedding."
                )
            query_embedding = computed

        query_vec = np.asarray(query_embedding, dtype=np.float64)
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return []

        similarities: list[tuple[str, float]] = []
        for ref_key, ref_emb in self.embeddings.items():
            if exclude_key and ref_key == exclude_key:
                continue
            ref_vec = np.asarray(ref_emb, dtype=np.float64)
            ref_norm = np.linalg.norm(ref_vec)
            if ref_norm == 0:
                continue
            sim = float(np.dot(query_vec, ref_vec) / (query_norm * ref_norm))
            similarities.append((ref_key, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)

        results: list[dict[str, Any]] = []
        for ref_key, sim in similarities[:k]:
            ref = self.references.get(ref_key, {})
            abstract = ref.get("abstract", "") or ""
            results.append(
                {
                    "key": ref_key,
                    "similarity": round(sim, 6),
                    "title": ref.get("title", ""),
                    "authors": ref.get("authors", []),
                    "year": ref.get("year"),
                    "abstract": abstract[:200],
                }
            )
        return results

    def find_similar_by_paper(
        self,
        paper_key: str,
        k: int = 5,
    ) -> list[dict[str, Any]]:
        """Find papers similar to an existing reference.

        Args:
            paper_key: Citation key of the query paper.
            k: Number of results.

        Returns:
            List of similar-paper dicts (excludes the query paper itself).

        Raises:
            ValueError: If *paper_key* has no embedding.
        """
        if paper_key not in self.embeddings:
            raise ValueError(f"No embedding for '{paper_key}'. Call build_embeddings() first.")

        query_embedding = self.embeddings[paper_key]
        ref = self.references.get(paper_key, {})
        query_text = ref.get("title", paper_key)

        return self.search_similar(
            query_text=query_text,
            query_embedding=query_embedding,
            k=k,
            exclude_key=paper_key,
        )

    # ------------------------------------------------------------------
    # Vector persistence
    # ------------------------------------------------------------------

    def _save_embeddings(self, vectors: dict[str, list[float]]) -> None:
        """Save embeddings to ``references/embeddings.yaml``.

        Format::

            metadata:
              model: text-embedding-3-small
              embedding_count: 34
              last_updated: "2026-04-01T06:30:00+00:00"
            embeddings:
              paper_key: [0.123, -0.456, ...]
        """
        data = {
            "metadata": {
                "model": self.EMBEDDING_MODEL,
                "embedding_count": len(vectors),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            },
            "embeddings": vectors,
        }
        with open(self.embeddings_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def _load_embeddings(self) -> dict[str, list[float]] | None:
        """Load embeddings from the YAML cache file.

        Returns:
            Embeddings dict, or ``None`` if the file is missing or corrupt.
        """
        if not self.embeddings_file.exists():
            return None

        try:
            with open(self.embeddings_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data and isinstance(data.get("embeddings"), dict):
                return data["embeddings"]
        except (yaml.YAMLError, OSError):
            return None

        return None

    def _is_embeddings_cache_valid(self) -> bool:
        """Check whether the cache covers all current references.

        Returns:
            ``True`` if the cached embedding count matches the reference count.
        """
        if not self.embeddings_file.exists():
            return False

        try:
            with open(self.embeddings_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not data or "metadata" not in data:
                return False
            return data["metadata"].get("embedding_count", 0) == len(self.references)
        except (yaml.YAMLError, OSError):
            return False
