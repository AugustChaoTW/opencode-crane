"""Integration tests for Ollama embedding support (v0.14.4).

Requires:
    - Ollama running at http://localhost:11434
    - nomic-embed-text model pulled: ollama pull nomic-embed-text

Run with:
    uv run pytest tests/integration/test_ollama_embeddings.py -v -m integration
"""

from __future__ import annotations

import pytest
import yaml

from crane.services.reference_service import ReferenceService
from crane.services.semantic_search_service import SemanticSearchService


OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
EMBED_DIM = 768  # nomic-embed-text outputs 768-dim vectors


def _ollama_available() -> bool:
    """Return True if Ollama server and nomic-embed-text are available."""
    try:
        import requests
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        if resp.status_code != 200:
            return False
        models = [m["name"].split(":")[0] for m in resp.json().get("models", [])]
        return EMBED_MODEL in models
    except Exception:
        return False


skip_if_no_ollama = pytest.mark.skipif(
    not _ollama_available(),
    reason=f"Ollama not available or '{EMBED_MODEL}' not installed",
)


@pytest.fixture
def refs_dir(tmp_path):
    """Create a temporary references directory with 3 papers."""
    refs = tmp_path / "references"
    refs.mkdir(parents=True)
    svc = ReferenceService(refs)
    svc.add(
        key="attention",
        title="Attention Is All You Need",
        authors=["Vaswani", "Shazeer"],
        year=2017,
        abstract="We propose a new architecture based purely on attention mechanisms.",
    )
    svc.add(
        key="bert",
        title="BERT: Pre-training of Deep Bidirectional Transformers",
        authors=["Devlin", "Chang"],
        year=2018,
        abstract="We introduce a new language representation model called BERT.",
    )
    svc.add(
        key="gpt2",
        title="Language Models are Unsupervised Multitask Learners",
        authors=["Radford", "Wu"],
        year=2019,
        abstract="Language models begin to learn NLP tasks without explicit supervision.",
    )
    return refs


# ===========================================================================
# A. Real Ollama embedding calls
# ===========================================================================


@pytest.mark.integration
@skip_if_no_ollama
class TestOllamaEmbedTextLive:
    def test_embed_single_text_returns_vector(self, refs_dir):
        svc = SemanticSearchService(refs_dir=refs_dir)
        vec = svc._embed_text_ollama("attention mechanisms in NLP", model=EMBED_MODEL)
        assert isinstance(vec, list)
        assert len(vec) == EMBED_DIM

    def test_embed_returns_floats(self, refs_dir):
        svc = SemanticSearchService(refs_dir=refs_dir)
        vec = svc._embed_text_ollama("test", model=EMBED_MODEL)
        assert all(isinstance(v, float) for v in vec)

    def test_different_texts_produce_different_vectors(self, refs_dir):
        svc = SemanticSearchService(refs_dir=refs_dir)
        v1 = svc._embed_text_ollama("attention in transformers", model=EMBED_MODEL)
        v2 = svc._embed_text_ollama("convolutional neural networks for images", model=EMBED_MODEL)
        assert v1 != v2

    def test_same_text_cached(self, refs_dir):
        import requests
        svc = SemanticSearchService(refs_dir=refs_dir)
        text = "cache test sentence"
        with pytest.MonkeyPatch().context() as mp:
            call_count = [0]
            original_post = requests.post

            def counting_post(*args, **kwargs):
                call_count[0] += 1
                return original_post(*args, **kwargs)

            mp.setattr("crane.services.semantic_search_service.requests.post", counting_post)
            svc._embed_text_ollama(text, model=EMBED_MODEL)
            svc._embed_text_ollama(text, model=EMBED_MODEL)

        assert call_count[0] == 1  # second call was cached


# ===========================================================================
# B. build_embeddings with Ollama provider
# ===========================================================================


@pytest.mark.integration
@skip_if_no_ollama
class TestBuildEmbeddingsOllamaLive:
    def test_build_embeds_all_three_papers(self, refs_dir):
        svc = SemanticSearchService(refs_dir=refs_dir)
        result = svc.build_embeddings(provider="ollama", model=EMBED_MODEL, ollama_url=OLLAMA_URL)

        assert len(result) == 3
        assert "attention" in result
        assert "bert" in result
        assert "gpt2" in result

    def test_embedding_dimension_is_768(self, refs_dir):
        svc = SemanticSearchService(refs_dir=refs_dir)
        result = svc.build_embeddings(provider="ollama", model=EMBED_MODEL, ollama_url=OLLAMA_URL)

        for key, vec in result.items():
            assert len(vec) == EMBED_DIM, f"{key}: expected {EMBED_DIM} dims, got {len(vec)}"

    def test_provider_stored_in_service(self, refs_dir):
        svc = SemanticSearchService(refs_dir=refs_dir)
        svc.build_embeddings(provider="ollama", model=EMBED_MODEL, ollama_url=OLLAMA_URL)
        assert svc.embedding_provider == "ollama"
        assert svc.embedding_model == EMBED_MODEL
        assert svc.embedding_dim == EMBED_DIM

    def test_cache_file_created(self, refs_dir):
        svc = SemanticSearchService(refs_dir=refs_dir)
        svc.build_embeddings(provider="ollama", model=EMBED_MODEL, ollama_url=OLLAMA_URL)
        assert svc.embeddings_file.exists()

    def test_cache_has_provider_metadata(self, refs_dir):
        svc = SemanticSearchService(refs_dir=refs_dir)
        svc.build_embeddings(provider="ollama", model=EMBED_MODEL, ollama_url=OLLAMA_URL)

        with open(svc.embeddings_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        meta = data["metadata"]
        assert meta["provider"] == "ollama"
        assert meta["model"] == EMBED_MODEL
        assert meta["embedding_dim"] == EMBED_DIM
        assert meta["embedding_count"] == 3

    def test_second_build_skips_existing(self, refs_dir):
        """build_embeddings is idempotent: second call with same provider skips already-embedded."""
        svc = SemanticSearchService(refs_dir=refs_dir)
        svc.build_embeddings(provider="ollama", model=EMBED_MODEL, ollama_url=OLLAMA_URL)

        # Second service instance loads from cache
        svc2 = SemanticSearchService(refs_dir=refs_dir)
        assert svc2.get_unembedded_keys() == []

        # build again — should make 0 Ollama calls
        import requests
        call_count = [0]
        original_post = requests.post

        def counting_post(*args, **kwargs):
            call_count[0] += 1
            return original_post(*args, **kwargs)

        import unittest.mock as mock
        with mock.patch("crane.services.semantic_search_service.requests.post", side_effect=counting_post):
            svc2.build_embeddings(provider="ollama", model=EMBED_MODEL, ollama_url=OLLAMA_URL)

        assert call_count[0] == 0


# ===========================================================================
# C. Provider restored from cache → semantic search works
# ===========================================================================


@pytest.mark.integration
@skip_if_no_ollama
class TestOllamaSemanticSearchLive:
    def test_search_after_ollama_build(self, refs_dir):
        # Build
        svc = SemanticSearchService(refs_dir=refs_dir)
        svc.build_embeddings(provider="ollama", model=EMBED_MODEL, ollama_url=OLLAMA_URL)

        # New instance loads from cache
        svc2 = SemanticSearchService(refs_dir=refs_dir)
        assert svc2.embedding_provider == "ollama"

        results = svc2.search_similar(query_text="transformer attention mechanism", k=2)
        assert len(results) == 2
        for r in results:
            assert "key" in r
            assert "similarity" in r
            assert -1.0 <= r["similarity"] <= 1.0

    def test_attention_paper_is_top_result(self, refs_dir):
        svc = SemanticSearchService(refs_dir=refs_dir)
        svc.build_embeddings(provider="ollama", model=EMBED_MODEL, ollama_url=OLLAMA_URL)

        results = svc.search_similar(query_text="self-attention transformer architecture", k=3)
        top_key = results[0]["key"]
        # "attention" paper should be most similar to this query
        assert top_key == "attention", f"Expected 'attention' paper on top, got '{top_key}'"

    def test_find_similar_by_paper(self, refs_dir):
        svc = SemanticSearchService(refs_dir=refs_dir)
        svc.build_embeddings(provider="ollama", model=EMBED_MODEL, ollama_url=OLLAMA_URL)

        results = svc.find_similar_by_paper("bert", k=2)
        keys = [r["key"] for r in results]
        assert "bert" not in keys  # excluded
        assert len(keys) == 2


# ===========================================================================
# D. MCP tool layer (build_embeddings tool with provider="ollama")
# ===========================================================================


@pytest.mark.integration
@skip_if_no_ollama
class TestBuildEmbeddingsToolOllama:
    def test_tool_succeeds_with_ollama_provider(self, refs_dir, tmp_path):
        """Smoke-test the MCP tool wrapper end-to-end."""

        class _Col:
            def __init__(self):
                self.tools: dict = {}

            def tool(self):
                def decorator(fn):
                    self.tools[fn.__name__] = fn
                    return fn
                return decorator

        from crane.tools.semantic_search import register_tools
        col = _Col()
        register_tools(col)

        build_fn = col.tools["build_embeddings"]
        result = build_fn(
            refs_dir=str(refs_dir),
            provider="ollama",
            model=EMBED_MODEL,
            ollama_url=OLLAMA_URL,
        )

        assert result["status"] == "success"
        assert result["provider"] == "ollama"
        assert result["model"] == EMBED_MODEL
        assert result["embedding_count"] == 3
        assert result["embedding_dim"] == EMBED_DIM

    def test_semantic_search_tool_after_ollama_build(self, refs_dir):
        """semantic_search tool uses provider read from embeddings.yaml."""

        class _Col:
            def __init__(self):
                self.tools: dict = {}

            def tool(self):
                def decorator(fn):
                    self.tools[fn.__name__] = fn
                    return fn
                return decorator

        from crane.tools.semantic_search import register_tools
        col = _Col()
        register_tools(col)

        build_fn = col.tools["build_embeddings"]
        build_fn(refs_dir=str(refs_dir), provider="ollama", model=EMBED_MODEL, ollama_url=OLLAMA_URL)

        search_fn = col.tools["semantic_search"]
        result = search_fn(query="language model pre-training", refs_dir=str(refs_dir))

        assert result["status"] == "success"
        assert result["match_count"] > 0
