"""
Unit tests for SemanticSearchService.
Tests follow TDD pattern: test -> implement -> refine.
All OpenAI API calls are mocked.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import yaml

from crane.services.reference_service import ReferenceService
from crane.services.semantic_search_service import SemanticSearchService


def _fake_embedding(dim: int = 1536, seed: int = 42) -> list[float]:
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(dim)
    vec = vec / np.linalg.norm(vec)
    return vec.tolist()


@pytest.fixture
def refs_dir(tmp_path):
    refs = tmp_path / "references"
    refs.mkdir(parents=True)
    ref_svc = ReferenceService(refs)
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
    return refs


@pytest.fixture
def service(refs_dir):
    return SemanticSearchService(refs_dir=refs_dir)


@pytest.fixture
def fake_vectors():
    return {
        "paper1": _fake_embedding(seed=1),
        "paper2": _fake_embedding(seed=2),
        "paper3": _fake_embedding(seed=3),
    }


@pytest.fixture
def service_with_embeddings(service, fake_vectors):
    service.embeddings = dict(fake_vectors)
    return service


class TestSemanticSearchServiceInit:
    def test_init_with_valid_refs_dir(self, refs_dir):
        svc = SemanticSearchService(refs_dir=refs_dir)
        assert svc.refs_path == refs_dir

    def test_init_validates_refs_dir_exists(self):
        with pytest.raises(ValueError, match="References directory does not exist"):
            SemanticSearchService(refs_dir="/nonexistent/path")

    def test_init_loads_all_references(self, service):
        assert len(service.references) == 3
        assert "paper1" in service.references
        assert "paper2" in service.references
        assert "paper3" in service.references

    def test_init_creates_papers_dir(self, tmp_path):
        refs = tmp_path / "new_refs"
        refs.mkdir()
        svc = SemanticSearchService(refs_dir=refs)
        assert svc.papers_dir.exists()

    def test_init_accepts_string_path(self, refs_dir):
        svc = SemanticSearchService(refs_dir=str(refs_dir))
        assert isinstance(svc.refs_path, Path)

    def test_init_with_embeddings_cache(self, refs_dir, fake_vectors):
        cache_data = {
            "metadata": {
                "model": "text-embedding-3-small",
                "embedding_count": 3,
                "last_updated": "2026-04-01T00:00:00Z",
            },
            "embeddings": fake_vectors,
        }
        with open(refs_dir / "embeddings.yaml", "w", encoding="utf-8") as f:
            yaml.dump(cache_data, f, sort_keys=False)

        svc = SemanticSearchService(refs_dir=refs_dir)
        assert len(svc.embeddings) == 3
        assert "paper1" in svc.embeddings

    def test_init_empty_refs_dir(self, tmp_path):
        refs = tmp_path / "empty_refs"
        refs.mkdir()
        svc = SemanticSearchService(refs_dir=refs)
        assert len(svc.references) == 0

    def test_init_stores_api_key(self, refs_dir):
        svc = SemanticSearchService(refs_dir=refs_dir, embedding_api_key="sk-test")
        assert svc.embedding_api_key == "sk-test"


class TestProperties:
    def test_has_embeddings_false_initially(self, service):
        assert service.has_embeddings is False

    def test_has_embeddings_true_with_data(self, service_with_embeddings):
        assert service_with_embeddings.has_embeddings is True

    def test_embedding_count_zero(self, service):
        assert service.embedding_count == 0

    def test_embedding_count_matches(self, service_with_embeddings):
        assert service_with_embeddings.embedding_count == 3


class TestReferenceLoading:
    def test_get_reference_data_existing(self, service):
        data = service.get_reference_data("paper1")
        assert data["title"] == "Attention Is All You Need"

    def test_get_reference_data_missing_raises(self, service):
        with pytest.raises(ValueError, match="not found"):
            service.get_reference_data("nonexistent")

    def test_get_reference_text_includes_title(self, service):
        text = service.get_reference_text("paper1")
        assert "Attention Is All You Need" in text

    def test_get_reference_text_includes_abstract(self, service):
        text = service.get_reference_text("paper1")
        assert "attention mechanisms" in text

    def test_get_reference_text_missing_abstract(self, refs_dir):
        papers_dir = refs_dir / "papers"
        paper = {"key": "no-abstract", "title": "Title Only", "authors": ["A"], "year": 2024}
        with open(papers_dir / "no-abstract.yaml", "w", encoding="utf-8") as f:
            yaml.dump(paper, f, sort_keys=False)
        svc = SemanticSearchService(refs_dir=refs_dir)
        text = svc.get_reference_text("no-abstract")
        assert "Title Only" in text

    def test_get_reference_text_with_annotations(self, refs_dir):
        papers_dir = refs_dir / "papers"
        paper = {
            "key": "annotated",
            "title": "Annotated Paper",
            "authors": ["A"],
            "year": 2024,
            "abstract": "Some abstract.",
            "ai_annotations": {
                "summary": "AI summary text",
                "key_contributions": ["contrib1", "contrib2"],
            },
        }
        with open(papers_dir / "annotated.yaml", "w", encoding="utf-8") as f:
            yaml.dump(paper, f, sort_keys=False)
        svc = SemanticSearchService(refs_dir=refs_dir)
        text = svc.get_reference_text("annotated")
        assert "AI summary text" in text
        assert "contrib1" in text

    def test_get_unembedded_keys_all_missing(self, service):
        assert set(service.get_unembedded_keys()) == {"paper1", "paper2", "paper3"}

    def test_get_unembedded_keys_none_missing(self, service_with_embeddings):
        assert service_with_embeddings.get_unembedded_keys() == []

    def test_get_unembedded_keys_partial(self, service):
        service.embeddings = {"paper1": [0.1] * 10}
        missing = service.get_unembedded_keys()
        assert "paper1" not in missing
        assert "paper2" in missing
        assert "paper3" in missing

    def test_reload_references_detects_new_paper(self, service_with_embeddings, refs_dir):
        papers_dir = refs_dir / "papers"
        new = {"key": "new-paper", "title": "New", "authors": ["X"], "year": 2026}
        with open(papers_dir / "new-paper.yaml", "w", encoding="utf-8") as f:
            yaml.dump(new, f, sort_keys=False)
        service_with_embeddings._load_references()
        assert "new-paper" in service_with_embeddings.get_unembedded_keys()


class TestEmbedText:
    def _mock_api_response(self, embedding=None):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [{"embedding": embedding or [0.1] * 1536}],
            "usage": {"total_tokens": 10},
        }
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    def test_embed_text_calls_api(self, service):
        with patch("crane.services.semantic_search_service.requests.post") as mock_post:
            mock_post.return_value = self._mock_api_response()
            result = service._embed_text("test query", api_key="sk-test")

        assert result is not None
        assert len(result) == 1536
        mock_post.assert_called_once()

    def test_embed_text_returns_none_without_key(self, service):
        result = service._embed_text("test query", api_key=None)
        assert result is None

    def test_embed_text_uses_instance_key(self, refs_dir):
        svc = SemanticSearchService(refs_dir=refs_dir, embedding_api_key="sk-instance")
        with patch("crane.services.semantic_search_service.requests.post") as mock_post:
            mock_post.return_value = self._mock_api_response()
            result = svc._embed_text("test query")

        assert result is not None
        call_kwargs = mock_post.call_args
        assert "sk-instance" in call_kwargs.kwargs["headers"]["Authorization"]

    def test_embed_text_uses_env_key(self, service):
        with patch("crane.services.semantic_search_service.requests.post") as mock_post:
            mock_post.return_value = self._mock_api_response()
            with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-env"}):
                result = service._embed_text("test query")

        assert result is not None

    def test_embed_text_raises_on_http_error(self, service):
        with patch("crane.services.semantic_search_service.requests.post") as mock_post:
            mock_post.return_value.raise_for_status.side_effect = Exception("429")
            with pytest.raises(Exception, match="429"):
                service._embed_text("test", api_key="sk-test")

    def test_embed_text_caches_results(self, service):
        with patch("crane.services.semantic_search_service.requests.post") as mock_post:
            mock_post.return_value = self._mock_api_response()
            r1 = service._embed_text("same text", api_key="sk-test")
            r2 = service._embed_text("same text", api_key="sk-test")

        assert mock_post.call_count == 1
        assert r1 == r2

    def test_embed_text_sends_correct_model(self, service):
        with patch("crane.services.semantic_search_service.requests.post") as mock_post:
            mock_post.return_value = self._mock_api_response()
            service._embed_text("hello", api_key="sk-test")

        body = mock_post.call_args.kwargs["json"]
        assert body["model"] == "text-embedding-3-small"
        assert body["input"] == "hello"

    def test_embed_text_sends_correct_url(self, service):
        with patch("crane.services.semantic_search_service.requests.post") as mock_post:
            mock_post.return_value = self._mock_api_response()
            service._embed_text("hello", api_key="sk-test")

        url = mock_post.call_args.args[0]
        assert url == "https://api.openai.com/v1/embeddings"


class TestBuildEmbeddings:
    def test_build_embeds_all_papers(self, service):
        call_count = 0

        def mock_embed(text, api_key=None):
            nonlocal call_count
            call_count += 1
            return _fake_embedding(seed=call_count)

        with patch.object(service, "_embed_text", side_effect=mock_embed):
            result = service.build_embeddings(api_key="sk-test")

        assert call_count == 3
        assert len(result) == 3

    def test_build_skips_already_embedded(self, service_with_embeddings):
        call_count = 0

        def mock_embed(text, api_key=None):
            nonlocal call_count
            call_count += 1
            return _fake_embedding(seed=call_count + 10)

        with patch.object(service_with_embeddings, "_embed_text", side_effect=mock_embed):
            service_with_embeddings.build_embeddings(api_key="sk-test")

        assert call_count == 0

    def test_build_embeds_only_new_papers(self, service, fake_vectors):
        service.embeddings = {
            "paper1": fake_vectors["paper1"],
            "paper2": fake_vectors["paper2"],
        }
        call_count = 0

        def mock_embed(text, api_key=None):
            nonlocal call_count
            call_count += 1
            return _fake_embedding(seed=call_count + 20)

        with patch.object(service, "_embed_text", side_effect=mock_embed):
            service.build_embeddings(api_key="sk-test")

        assert call_count == 1
        assert len(service.embeddings) == 3

    def test_build_saves_cache(self, service):
        def mock_embed(text, api_key=None):
            return _fake_embedding(seed=42)

        with patch.object(service, "_embed_text", side_effect=mock_embed):
            service.build_embeddings(api_key="sk-test")

        assert service.embeddings_file.exists()

    def test_build_returns_empty_without_key(self, service):
        result = service.build_embeddings(api_key=None)
        assert result == {}

    def test_build_returns_existing_without_key(self, service_with_embeddings):
        result = service_with_embeddings.build_embeddings(api_key=None)
        assert len(result) == 3


class TestSearchSimilar:
    def test_returns_results(self, service_with_embeddings):
        query_vec = _fake_embedding(seed=1)
        results = service_with_embeddings.search_similar(
            query_text="attention", query_embedding=query_vec
        )
        assert len(results) > 0

    def test_respects_k(self, service_with_embeddings):
        query_vec = _fake_embedding(seed=1)
        results = service_with_embeddings.search_similar(
            query_text="attention", query_embedding=query_vec, k=2
        )
        assert len(results) == 2

    def test_result_format(self, service_with_embeddings):
        query_vec = _fake_embedding(seed=1)
        results = service_with_embeddings.search_similar(
            query_text="test", query_embedding=query_vec, k=3
        )
        for r in results:
            assert "key" in r
            assert "similarity" in r
            assert "title" in r
            assert "authors" in r
            assert "year" in r
            assert isinstance(r["similarity"], float)

    def test_sorted_by_similarity(self, service_with_embeddings):
        query_vec = _fake_embedding(seed=1)
        results = service_with_embeddings.search_similar(
            query_text="test", query_embedding=query_vec, k=3
        )
        sims = [r["similarity"] for r in results]
        assert sims == sorted(sims, reverse=True)

    def test_most_similar_first(self, service_with_embeddings):
        query_vec = _fake_embedding(seed=1)
        results = service_with_embeddings.search_similar(
            query_text="test", query_embedding=query_vec, k=3
        )
        assert results[0]["key"] == "paper1"
        assert results[0]["similarity"] > 0.99

    def test_excludes_key(self, service_with_embeddings):
        query_vec = _fake_embedding(seed=1)
        results = service_with_embeddings.search_similar(
            query_text="test", query_embedding=query_vec, k=5, exclude_key="paper1"
        )
        keys = [r["key"] for r in results]
        assert "paper1" not in keys

    def test_k_larger_than_refs(self, service_with_embeddings):
        query_vec = _fake_embedding(seed=1)
        results = service_with_embeddings.search_similar(
            query_text="test", query_embedding=query_vec, k=100
        )
        assert len(results) == 3

    def test_empty_embeddings_with_query_vec(self, service):
        service.embeddings = {}
        results = service.search_similar(query_text="test", query_embedding=[1.0, 0.0, 0.0], k=5)
        assert results == []

    def test_empty_embeddings_without_query_vec_raises(self, service):
        service.embeddings = {}
        with pytest.raises(ValueError, match="No embeddings"):
            service.search_similar(query_text="test", k=5)

    def test_similarity_bounded(self, service_with_embeddings):
        query_vec = _fake_embedding(seed=1)
        results = service_with_embeddings.search_similar(
            query_text="test", query_embedding=query_vec, k=3
        )
        for r in results:
            assert -1.0 <= r["similarity"] <= 1.0

    def test_abstract_truncated(self, service_with_embeddings):
        long_abstract = "x" * 500
        service_with_embeddings.references["paper1"]["abstract"] = long_abstract
        query_vec = _fake_embedding(seed=1)
        results = service_with_embeddings.search_similar(
            query_text="test", query_embedding=query_vec, k=1
        )
        assert len(results[0]["abstract"]) == 200

    def test_search_with_api_embedding(self, service_with_embeddings):
        query_vec = _fake_embedding(seed=1)
        with patch.object(service_with_embeddings, "_embed_text", return_value=query_vec):
            results = service_with_embeddings.search_similar(query_text="attention")
        assert len(results) > 0
        assert results[0]["key"] == "paper1"

    def test_search_raises_when_no_key_and_no_embedding(self, service_with_embeddings):
        with patch.object(service_with_embeddings, "_embed_text", return_value=None):
            with pytest.raises(ValueError, match="Cannot embed query"):
                service_with_embeddings.search_similar(query_text="test")


class TestFindSimilarByPaper:
    def test_finds_similar(self, service_with_embeddings):
        results = service_with_embeddings.find_similar_by_paper("paper1", k=2)
        assert len(results) == 2
        keys = [r["key"] for r in results]
        assert "paper1" not in keys

    def test_raises_for_unembedded_paper(self, service):
        with pytest.raises(ValueError, match="No embedding"):
            service.find_similar_by_paper("paper1")


class TestEdgeCases:
    def test_empty_query_raises(self, service_with_embeddings):
        with pytest.raises(ValueError, match="empty"):
            service_with_embeddings.search_similar(query_text="")

    def test_whitespace_query_raises(self, service_with_embeddings):
        with pytest.raises(ValueError, match="empty"):
            service_with_embeddings.search_similar(query_text="   ")

    def test_k_zero_returns_empty(self, service_with_embeddings):
        results = service_with_embeddings.search_similar(
            query_text="test", query_embedding=[1.0] * 1536, k=0
        )
        assert results == []

    def test_negative_k_returns_empty(self, service_with_embeddings):
        results = service_with_embeddings.search_similar(
            query_text="test", query_embedding=[1.0] * 1536, k=-1
        )
        assert results == []

    def test_zero_norm_query_returns_empty(self, service_with_embeddings):
        results = service_with_embeddings.search_similar(
            query_text="test", query_embedding=[0.0] * 1536, k=5
        )
        assert results == []

    def test_zero_norm_ref_skipped(self, service):
        service.embeddings = {
            "paper1": [0.0] * 3,
            "paper2": [1.0, 0.0, 0.0],
        }
        results = service.search_similar(query_text="test", query_embedding=[1.0, 0.0, 0.0], k=5)
        keys = [r["key"] for r in results]
        assert "paper1" not in keys
        assert "paper2" in keys

    def test_paper_without_annotations_embeddable(self, refs_dir):
        papers_dir = refs_dir / "papers"
        paper = {
            "key": "plain",
            "title": "Plain Paper",
            "authors": ["Author"],
            "year": 2024,
            "abstract": "Some abstract.",
        }
        with open(papers_dir / "plain.yaml", "w", encoding="utf-8") as f:
            yaml.dump(paper, f, sort_keys=False)
        svc = SemanticSearchService(refs_dir=refs_dir)
        text = svc.get_reference_text("plain")
        assert "Plain Paper" in text
        assert "Some abstract" in text


class TestVectorStorage:
    def test_save_creates_file(self, service_with_embeddings):
        service_with_embeddings._save_embeddings(service_with_embeddings.embeddings)
        assert service_with_embeddings.embeddings_file.exists()

    def test_save_format(self, service_with_embeddings):
        service_with_embeddings._save_embeddings(service_with_embeddings.embeddings)
        with open(service_with_embeddings.embeddings_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "metadata" in data
        assert "embeddings" in data
        assert data["metadata"]["model"] == "text-embedding-3-small"
        assert data["metadata"]["embedding_count"] == 3
        assert "last_updated" in data["metadata"]
        # v0.14.4: provider and embedding_dim are also stored
        assert "provider" in data["metadata"]
        assert "embedding_dim" in data["metadata"]

    def test_save_vector_dimensions(self, service_with_embeddings):
        service_with_embeddings._save_embeddings(service_with_embeddings.embeddings)
        with open(service_with_embeddings.embeddings_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for vec in data["embeddings"].values():
            assert len(vec) == 1536

    def test_load_from_file(self, service, fake_vectors):
        cache_data = {
            "metadata": {
                "model": "text-embedding-3-small",
                "embedding_count": 3,
                "last_updated": "2026-04-01T00:00:00Z",
            },
            "embeddings": fake_vectors,
        }
        with open(service.embeddings_file, "w", encoding="utf-8") as f:
            yaml.dump(cache_data, f, sort_keys=False)

        service._load_embeddings()
        assert len(service.embeddings) == 3

    def test_load_leaves_empty_if_missing(self, service):
        service._load_embeddings()
        assert service.embeddings == {}

    def test_load_leaves_empty_if_corrupt(self, service):
        service.embeddings_file.write_text("not: valid: yaml: [[[", encoding="utf-8")
        service._load_embeddings()
        assert service.embeddings == {}

    def test_load_leaves_empty_if_no_embeddings_key(self, service):
        service.embeddings_file.write_text("metadata: {}", encoding="utf-8")
        service._load_embeddings()
        assert service.embeddings == {}

    def test_save_load_roundtrip(self, service_with_embeddings):
        original = dict(service_with_embeddings.embeddings)
        service_with_embeddings._save_embeddings(original)

        svc2 = SemanticSearchService(refs_dir=service_with_embeddings.refs_path)
        assert len(svc2.embeddings) == len(original)
        for key in original:
            np.testing.assert_allclose(svc2.embeddings[key], original[key], rtol=1e-5)

    def test_cache_valid_when_counts_match(self, service_with_embeddings):
        service_with_embeddings._save_embeddings(service_with_embeddings.embeddings)
        assert service_with_embeddings._is_embeddings_cache_valid() is True

    def test_cache_invalid_when_no_file(self, service):
        assert service._is_embeddings_cache_valid() is False

    def test_cache_invalid_when_count_mismatch(self, service):
        cache_data = {
            "metadata": {
                "model": "text-embedding-3-small",
                "embedding_count": 1,
                "last_updated": "2026-04-01T00:00:00Z",
            },
            "embeddings": {"paper1": [0.1] * 3},
        }
        with open(service.embeddings_file, "w", encoding="utf-8") as f:
            yaml.dump(cache_data, f, sort_keys=False)
        assert service._is_embeddings_cache_valid() is False

    def test_cache_invalid_when_corrupt(self, service):
        service.embeddings_file.write_text("garbage[[[", encoding="utf-8")
        assert service._is_embeddings_cache_valid() is False

    def test_cache_invalid_when_no_metadata(self, service):
        service.embeddings_file.write_text("embeddings: {}", encoding="utf-8")
        assert service._is_embeddings_cache_valid() is False


# ===========================================================================
# Ollama support (v0.14.4)
# ===========================================================================


def _ollama_embed_response(dim: int = 768) -> MagicMock:
    """Fake Ollama /api/embeddings response."""
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {"embedding": [0.1] * dim}
    return mock


class TestEmbedTextOllama:
    def test_calls_ollama_endpoint(self, service):
        with patch("crane.services.semantic_search_service.requests.post") as mock_post:
            mock_post.return_value = _ollama_embed_response()
            result = service._embed_text_ollama("test text", model="nomic-embed-text")

        url = mock_post.call_args.args[0]
        assert "11434" in url
        assert "embeddings" in url
        assert result is not None
        assert len(result) == 768

    def test_sends_correct_json(self, service):
        with patch("crane.services.semantic_search_service.requests.post") as mock_post:
            mock_post.return_value = _ollama_embed_response()
            service._embed_text_ollama("hello world", model="nomic-embed-text")

        body = mock_post.call_args.kwargs["json"]
        assert body["model"] == "nomic-embed-text"
        assert body["prompt"] == "hello world"

    def test_custom_base_url(self, service):
        with patch("crane.services.semantic_search_service.requests.post") as mock_post:
            mock_post.return_value = _ollama_embed_response()
            service._embed_text_ollama("text", model="nomic-embed-text", base_url="http://myserver:11434")

        url = mock_post.call_args.args[0]
        assert "myserver:11434" in url

    def test_caches_result(self, service):
        with patch("crane.services.semantic_search_service.requests.post") as mock_post:
            mock_post.return_value = _ollama_embed_response()
            r1 = service._embed_text_ollama("same", model="nomic-embed-text")
            r2 = service._embed_text_ollama("same", model="nomic-embed-text")

        assert mock_post.call_count == 1
        assert r1 == r2

    def test_different_models_not_confused(self, service):
        responses = iter([_ollama_embed_response(768), _ollama_embed_response(1024)])
        with patch("crane.services.semantic_search_service.requests.post", side_effect=responses):
            r1 = service._embed_text_ollama("same", model="nomic-embed-text")
            r2 = service._embed_text_ollama("same", model="mxbai-embed-large")

        assert len(r1) == 768
        assert len(r2) == 1024

    def test_raises_on_http_error(self, service):
        with patch("crane.services.semantic_search_service.requests.post") as mock_post:
            mock_post.return_value.raise_for_status.side_effect = Exception("connection refused")
            with pytest.raises(Exception, match="connection refused"):
                service._embed_text_ollama("text", model="nomic-embed-text")


class TestBuildEmbeddingsOllama:
    def test_ollama_provider_sets_provider_attr(self, service):
        with patch.object(service, "_embed_text_ollama", return_value=[0.1] * 768):
            service.build_embeddings(provider="ollama")

        assert service.embedding_provider == "ollama"

    def test_ollama_provider_sets_model(self, service):
        with patch.object(service, "_embed_text_ollama", return_value=[0.1] * 768):
            service.build_embeddings(provider="ollama", model="mxbai-embed-large")

        assert service.embedding_model == "mxbai-embed-large"

    def test_ollama_default_model_is_nomic(self, service):
        with patch.object(service, "_embed_text_ollama", return_value=[0.1] * 768) as mock_embed:
            service.build_embeddings(provider="ollama")

        # First call uses nomic-embed-text
        model_used = mock_embed.call_args_list[0].args[1]
        assert model_used == "nomic-embed-text"

    def test_ollama_embeds_all_papers(self, service):
        call_count = 0

        def fake_ollama(text, model, base_url="http://localhost:11434"):
            nonlocal call_count
            call_count += 1
            return [0.1] * 768

        with patch.object(service, "_embed_text_ollama", side_effect=fake_ollama):
            result = service.build_embeddings(provider="ollama")

        assert call_count == 3
        assert len(result) == 3

    def test_ollama_saves_provider_in_cache(self, service):
        with patch.object(service, "_embed_text_ollama", return_value=[0.1] * 768):
            service.build_embeddings(provider="ollama")

        with open(service.embeddings_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert data["metadata"]["provider"] == "ollama"
        assert data["metadata"]["model"] == "nomic-embed-text"
        assert data["metadata"]["embedding_dim"] == 768

    def test_ollama_embedding_dim_inferred_from_vector(self, service):
        with patch.object(service, "_embed_text_ollama", return_value=[0.1] * 1024):
            service.build_embeddings(provider="ollama", model="mxbai-embed-large")

        assert service.embedding_dim == 1024

    def test_ollama_skip_failed_papers(self, service):
        """Papers that fail to embed are skipped; others succeed."""
        call_count = 0

        def selective_fail(text, model, base_url="http://localhost:11434"):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("timeout")
            return [0.1] * 768

        with patch.object(service, "_embed_text_ollama", side_effect=selective_fail):
            result = service.build_embeddings(provider="ollama")

        # 2 out of 3 succeeded
        assert len(result) == 2


class TestEmbedQueryRouting:
    def test_openai_routes_to_embed_text(self, service):
        service.embedding_provider = "openai"
        with patch.object(service, "_embed_text", return_value=[0.1] * 1536) as mock_ot:
            result = service._embed_query("test")

        mock_ot.assert_called_once_with("test")
        assert result == [0.1] * 1536

    def test_ollama_routes_to_embed_text_ollama(self, service):
        service.embedding_provider = "ollama"
        service.embedding_model = "nomic-embed-text"
        with patch.object(service, "_embed_text_ollama", return_value=[0.1] * 768) as mock_ot:
            result = service._embed_query("test")

        mock_ot.assert_called_once()
        assert result == [0.1] * 768

    def test_ollama_exception_returns_none(self, service):
        service.embedding_provider = "ollama"
        with patch.object(service, "_embed_text_ollama", side_effect=Exception("down")):
            result = service._embed_query("test")

        assert result is None

    def test_openai_no_key_returns_none(self, service):
        service.embedding_provider = "openai"
        service.embedding_api_key = None
        with patch.dict("os.environ", {}, clear=True):
            import os
            os.environ.pop("OPENAI_API_KEY", None)
            result = service._embed_query("test")

        assert result is None


class TestMetadataRoundtrip:
    def test_ollama_provider_restored_from_cache(self, service, fake_vectors):
        """Provider loaded from embeddings.yaml so query uses same backend."""
        cache_data = {
            "metadata": {
                "provider": "ollama",
                "model": "nomic-embed-text",
                "embedding_dim": 768,
                "embedding_count": 3,
                "last_updated": "2026-04-01T00:00:00Z",
            },
            "embeddings": {k: [0.1] * 768 for k in fake_vectors},
        }
        with open(service.embeddings_file, "w", encoding="utf-8") as f:
            yaml.dump(cache_data, f, sort_keys=False)

        svc2 = SemanticSearchService(refs_dir=service.refs_path)
        assert svc2.embedding_provider == "ollama"
        assert svc2.embedding_model == "nomic-embed-text"
        assert svc2.embedding_dim == 768

    def test_legacy_cache_without_provider_defaults_openai(self, service, fake_vectors):
        """Old embeddings.yaml (no provider field) keeps openai as default."""
        cache_data = {
            "metadata": {
                "model": "text-embedding-3-small",
                "embedding_count": 3,
                "last_updated": "2026-04-01T00:00:00Z",
            },
            "embeddings": fake_vectors,
        }
        with open(service.embeddings_file, "w", encoding="utf-8") as f:
            yaml.dump(cache_data, f, sort_keys=False)

        svc2 = SemanticSearchService(refs_dir=service.refs_path)
        # No provider in old cache → stays at default "openai"
        assert svc2.embedding_provider == "openai"


class TestResolveApiKey:
    def test_explicit_key_wins(self, service):
        service.embedding_api_key = "sk-instance"
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-env"}):
            assert service._resolve_api_key("sk-explicit") == "sk-explicit"

    def test_instance_key_fallback(self, service):
        service.embedding_api_key = "sk-instance"
        with patch.dict("os.environ", {}, clear=True):
            import os

            os.environ.pop("OPENAI_API_KEY", None)
            assert service._resolve_api_key() == "sk-instance"

    def test_env_key_fallback(self, service):
        service.embedding_api_key = None
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-env"}):
            assert service._resolve_api_key() == "sk-env"

    def test_none_when_no_key(self, service):
        service.embedding_api_key = None
        with patch.dict("os.environ", {}, clear=True):
            import os

            os.environ.pop("OPENAI_API_KEY", None)
            assert service._resolve_api_key() is None
