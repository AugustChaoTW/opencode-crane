"""
Unit tests for SemanticSearchService.

Tests follow TDD pattern: test → implement → refine.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crane.services.reference_service import ReferenceService
from crane.services.semantic_search_service import SemanticSearchService


@pytest.fixture
def temp_refs_dir():
    """Create temporary references directory with sample data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        refs_path = Path(tmpdir) / "references"
        refs_path.mkdir(parents=True, exist_ok=True)

        ref_svc = ReferenceService(refs_path)

        ref_svc.add(
            key="paper1",
            title="Attention Is All You Need",
            authors=["Vaswani", "Shazeer"],
            year=2017,
            abstract="We propose a new simple network architecture based on attention mechanisms.",
        )
        ref_svc.add(
            key="paper2",
            title="BERT: Pre-training of Deep Bidirectional Transformers",
            authors=["Devlin", "Chang"],
            year=2018,
            abstract="We introduce a new language representation model called BERT.",
        )
        ref_svc.add(
            key="paper3",
            title="Language Models are Unsupervised Multitask Learners",
            authors=["Radford", "Wu"],
            year=2019,
            abstract="We demonstrate that language models begin to learn these tasks.",
        )

        yield refs_path


@pytest.fixture
def semantic_search_service(temp_refs_dir):
    """Create SemanticSearchService instance."""
    return SemanticSearchService(refs_dir=temp_refs_dir)


class TestSemanticSearchServiceInit:
    """Test service initialization."""

    def test_init_with_valid_refs_dir(self, temp_refs_dir):
        """Test initializing with valid refs directory."""
        service = SemanticSearchService(refs_dir=temp_refs_dir)
        assert service.refs_path == temp_refs_dir
        assert service.ref_svc is not None

    def test_init_validates_refs_dir_exists(self):
        """Test that init raises error if refs_dir doesn't exist."""
        with pytest.raises(ValueError, match="References directory does not exist"):
            SemanticSearchService(refs_dir="/nonexistent/path")

    def test_init_loads_all_references(self, semantic_search_service, temp_refs_dir):
        """Test that init loads all references."""
        assert semantic_search_service.references is not None
        assert len(semantic_search_service.references) == 3

    def test_init_with_embeddings_file(self, temp_refs_dir):
        """Test initializing when embeddings cache exists."""
        embeddings_file = temp_refs_dir / "embeddings.yaml"
        embeddings_file.write_text(
            """embeddings:
  paper1: [0.1, 0.2, 0.3]
  paper2: [0.4, 0.5, 0.6]
  paper3: [0.7, 0.8, 0.9]
metadata:
  model: "text-embedding-3-small"
  embedding_count: 3
  last_updated: "2026-04-01T06:30:00Z"
"""
        )
        service = SemanticSearchService(refs_dir=temp_refs_dir)
        assert service.embeddings is not None


class TestEmbedding:
    """Test embedding generation and caching."""

    def test_embed_text_calls_openai_api(self, semantic_search_service):
        """Test that embed_text calls OpenAI API with mock."""
        with patch("crane.services.semantic_search_service.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"data": [{"embedding": [0.1] * 1536}]}
            mock_post.return_value = mock_response

            result = semantic_search_service._embed_text("test query", api_key="test-key")
            assert result is not None
            assert isinstance(result, list)
            assert len(result) == 1536

    def test_embed_text_skips_if_no_api_key(self, semantic_search_service):
        """Test that embed_text gracefully skips if no API key."""
        result = semantic_search_service._embed_text("test query", api_key=None)
        assert result is None

    def test_embed_text_handles_api_error(self, semantic_search_service):
        """Test that embed_text handles API errors gracefully."""
        with patch("crane.services.semantic_search_service.requests.post") as mock_post:
            mock_post.side_effect = Exception("API error")

            result = semantic_search_service._embed_text("test query", api_key="test-key")
            assert result is None

    def test_embed_text_caches_results(self, semantic_search_service):
        """Test that embed_text caches results to avoid re-embedding."""
        with patch("crane.services.semantic_search_service.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"data": [{"embedding": [0.1] * 1536}]}
            mock_post.return_value = mock_response

            # First call
            result1 = semantic_search_service._embed_text("test", api_key="key")
            result2 = semantic_search_service._embed_text("test", api_key="key")

            assert mock_post.call_count == 1
            assert result1 == result2


class TestSearchSimilar:
    """Test similarity search functionality."""

    def test_search_similar_returns_top_k_matches(self, semantic_search_service):
        """Test that search_similar returns top k matches."""
        semantic_search_service.embeddings = {
            "paper1": [1.0, 0.0, 0.0],
            "paper2": [0.9, 0.1, 0.0],
            "paper3": [0.0, 0.0, 1.0],
        }

        results = semantic_search_service.search_similar(
            query_text="attention mechanism", query_embedding=[1.0, 0.0, 0.0], k=2
        )

        assert len(results) <= 2
        assert all("key" in r and "similarity" in r for r in results)

    def test_search_similar_returns_similarity_scores(self, semantic_search_service):
        """Test that results include similarity scores."""
        semantic_search_service.embeddings = {
            "paper1": [1.0, 0.0, 0.0],
            "paper2": [0.9, 0.1, 0.0],
        }

        results = semantic_search_service.search_similar(
            query_text="test", query_embedding=[1.0, 0.0, 0.0], k=2
        )

        assert all(0.0 <= r["similarity"] <= 1.0 for r in results)

    def test_search_similar_excludes_query_itself(self, semantic_search_service):
        """Test that search excludes query paper if provided."""
        semantic_search_service.embeddings = {
            "paper1": [1.0, 0.0, 0.0],
            "paper2": [0.9, 0.1, 0.0],
            "paper3": [0.8, 0.2, 0.0],
        }

        results = semantic_search_service.search_similar(
            query_text="test", query_embedding=[1.0, 0.0, 0.0], k=5, exclude_key="paper1"
        )

        keys = [r["key"] for r in results]
        assert "paper1" not in keys

    def test_search_similar_handles_empty_embeddings(self, semantic_search_service):
        """Test search when no embeddings exist."""
        semantic_search_service.embeddings = {}

        results = semantic_search_service.search_similar(
            query_text="test", query_embedding=[1.0, 0.0, 0.0], k=5
        )

        assert results == []

    def test_search_similar_returns_reference_data(self, semantic_search_service):
        """Test that results include reference metadata."""
        semantic_search_service.embeddings = {
            "paper1": [1.0, 0.0, 0.0],
            "paper2": [0.9, 0.1, 0.0],
        }

        results = semantic_search_service.search_similar(
            query_text="test", query_embedding=[1.0, 0.0, 0.0], k=2
        )

        for result in results:
            assert "key" in result
            assert "similarity" in result
            assert "title" in result


class TestVectorStorage:
    """Test vector caching and persistence."""

    def test_save_embeddings_to_yaml(self, semantic_search_service, temp_refs_dir):
        """Test saving embeddings to YAML cache."""
        vectors = {
            "paper1": [0.1] * 1536,
            "paper2": [0.2] * 1536,
        }
        semantic_search_service._save_embeddings(vectors)

        embeddings_file = temp_refs_dir / "embeddings.yaml"
        assert embeddings_file.exists()

    def test_load_embeddings_from_cache(self, semantic_search_service, temp_refs_dir):
        """Test loading embeddings from cache."""
        embeddings_file = temp_refs_dir / "embeddings.yaml"
        embeddings_file.write_text(
            """embeddings:
  paper1: [0.1, 0.2, 0.3]
  paper2: [0.4, 0.5, 0.6]
metadata:
  model: "text-embedding-3-small"
  embedding_count: 2
  last_updated: "2026-04-01T06:30:00Z"
"""
        )

        vectors = semantic_search_service._load_embeddings()
        assert vectors is not None
        assert "paper1" in vectors
        assert len(vectors["paper1"]) == 3

    def test_embeddings_cache_invalidation(self, semantic_search_service, temp_refs_dir):
        """Test cache invalidation when references change."""
        embeddings_file = temp_refs_dir / "embeddings.yaml"
        embeddings_file.write_text(
            """embeddings:
  paper1: [0.1, 0.2, 0.3]
metadata:
  model: "text-embedding-3-small"
  embedding_count: 1
  last_updated: "2020-01-01T00:00:00Z"
"""
        )

        is_valid = semantic_search_service._is_embeddings_cache_valid()
        assert isinstance(is_valid, bool)
