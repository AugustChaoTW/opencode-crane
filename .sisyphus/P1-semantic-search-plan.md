# P1: Semantic Search Implementation Plan

## 1. Architecture Design

### Current State
- ReferenceService: YAML + BibTeX (34 references)
- PaperService: Multi-source search (arXiv, OpenAlex, S2, Crossref)
- Reference structure: title, abstract, ai_annotations (summary, key_contributions, methodology)

### Design: SemanticSearchService

```
SemanticSearchService
├── __init__(refs_dir)
│   └── Load all references + vectors from cache
├── build_embeddings()
│   ├── Fetch text: title + abstract + summary
│   ├── Call embedding API (OpenAI text-embedding-3-small)
│   └── Save vectors to references/embeddings.yaml + .npy
├── search_similar(query_text, k=5)
│   ├── Embed query
│   ├── Cosine similarity against all references
│   └── Return top-k (key, similarity_score, reference)
└── find_similar_by_paper(paper_key, k=5)
    ├── Use paper's abstract + summary as query
    └── Return top-k similar papers
```

### Integration Points
- Extends ReferenceService (does NOT modify it)
- New MCP tool: `semantic_search`
- Cache vectors in `references/embeddings.yaml` (local-first)
- Fallback: Re-embed if cache outdated

---

## 2. Sub-task Breakdown (TDD-Oriented)

### Phase 1: MVP (Week 1)
**Goal**: Find similar papers by query text

1. **Create SemanticSearchService skeleton**
   - File: `src/crane/services/semantic_search_service.py`
   - Tests: `tests/services/test_semantic_search_service.py`
   
   TDD Steps:
   ```
   test: test_init_loads_references → fails (no service)
   feat: SemanticSearchService.__init__ (loads refs from ReferenceService)
   test: test_init_validates_refs_dir → add validation
   
   test: test_build_embeddings_requires_api_key → fails
   feat: Add embedding_api parameter
   test: test_build_embeddings_creates_vectors → mock API
   
   test: test_search_similar_returns_top_k → mock vectors
   feat: search_similar(query_text, k=5) implementation
   test: test_search_similar_excludes_query_paper → edge case
   ```

2. **Embedding API Integration**
   - Support: OpenAI text-embedding-3-small (cheap, good quality)
   - Fallback: Lazy embedding (don't embed if no API key)
   
   TDD:
   ```
   test: test_embedding_api_openai_call → mock requests
   feat: _embed_text(text) → calls OpenAI API
   test: test_embedding_caching → avoid re-embedding
   test: test_embedding_batch_processing → efficiency
   ```

3. **Vector Storage (Local-First)**
   - Store in: `references/embeddings.yaml`
   - Format:
   ```yaml
   embeddings:
     paper_key_1: [0.123, -0.456, ...]  # 1536-dim embedding
     paper_key_2: [...]
   metadata:
     model: "text-embedding-3-small"
     embedding_count: 34
     last_updated: "2026-04-01T06:30:00Z"
   ```
   
   TDD:
   ```
   test: test_save_embeddings_to_yaml → verify format
   feat: _save_embeddings(vectors_dict)
   test: test_load_embeddings_from_cache → verify load
   feat: _load_embeddings() → checks cache validity
   ```

4. **MCP Tool: semantic_search**
   - File: `src/crane/tools/semantic_search.py`
   - Tests: `tests/tools/test_semantic_search_tools.py`
   
   Tool signature:
   ```python
   def semantic_search(
       query: str,
       k: int = 5,
       project_dir: str | None = None,
   ) -> dict:
       """
       Find similar papers by query text.
       Returns: {
           "query": "...",
           "matches": [
               {"key": "...", "similarity": 0.85, "title": "..."},
               ...
           ]
       }
       """
   ```
   
   TDD:
   ```
   test: test_semantic_search_tool_finds_matches → mock service
   test: test_semantic_search_tool_returns_correct_format → verify output
   test: test_semantic_search_tool_respects_k_parameter → boundary
   ```

---

## 3. Tech Stack Decisions

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Embedding Model** | OpenAI text-embedding-3-small | Industry standard, cheap ($0.02/M tokens), 1536-dim |
| **Vector Storage** | YAML + .npy cache | Local-first, human-readable, numpy-compatible |
| **Similarity Metric** | Cosine similarity | Standard, O(k) for k-NN search |
| **Dependencies** | numpy (new) | Lightweight, already used by matplotlib |
| **API Key Management** | Optional env var `OPENAI_API_KEY` | Graceful degradation if not set |
| **Caching Strategy** | File mtime-based invalidation | Re-embed if references modified > cache time |

**No new dependencies** required beyond numpy (which is lightweight and standard).

---

## 4. Implementation Priority

### MVP (Must-Have)
1. ✅ SemanticSearchService with basic similarity search
2. ✅ OpenAI embedding integration
3. ✅ Vector caching (local YAML)
4. ✅ MCP tool registration
5. ✅ TDD test coverage (>85%)

### Phase 2 (Nice-to-Have)
- [ ] Graph visualization (research map)
- [ ] Batch API calls optimization
- [ ] Alternative embedding models (Sentence Transformers for offline)
- [ ] Query expansion (expand query with related terms)

### Defer to Phase 3
- [ ] Multi-modal search (text + figures)
- [ ] Cross-paper citation network visualization
- [ ] Domain insight generation (AI summary of research gaps)

---

## 5. Test Strategy

### Unit Tests (tests/services/test_semantic_search_service.py)
```python
class TestSemanticSearchServiceInit:
    def test_init_with_valid_refs_dir → setUp
    def test_init_validates_refs_dir_exists
    def test_init_loads_all_references

class TestEmbedding:
    def test_embed_text_calls_openai_api (mock)
    def test_embed_text_caches_results
    def test_embed_text_handles_api_error_gracefully
    def test_embed_text_skips_if_no_api_key

class TestSearchSimilar:
    def test_search_similar_returns_top_k_matches
    def test_search_similar_returns_similarity_scores
    def test_search_similar_excludes_query_itself
    def test_search_similar_handles_empty_query
    def test_search_similar_handles_new_references_not_yet_embedded

class TestVectorStorage:
    def test_save_embeddings_to_yaml
    def test_load_embeddings_from_cache
    def test_embeddings_cache_invalidation_on_refs_change
```

### Integration Tests (tests/tools/test_semantic_search_tools.py)
```python
class TestSemanticSearchTool:
    def test_tool_end_to_end_with_query (integration)
    def test_tool_with_missing_api_key (fallback)
    def test_tool_respects_k_parameter
    def test_tool_returns_correct_schema
```

### Quality Metrics
- **Coverage**: >85% for services/semantic_search_service.py
- **Latency**: <2s for search_similar (across 34 papers)
- **API Cost**: <$1 for embedding 34 papers (batch mode)

---

## 6. Effort Estimate

| Task | Effort | Notes |
|------|--------|-------|
| Service skeleton + basic search | 1–2d | TDD cycle: test → impl → refine |
| Embedding API integration | 1d | OpenAI API calls, error handling |
| Vector storage (YAML + cache) | 0.5d | Straightforward YAML I/O |
| MCP tool registration | 0.5d | Wrapper around service |
| Test suite (unit + integration) | 1–1.5d | TDD means tests are concurrent |
| Edge case handling + optimization | 0.5d | Rate limiting, batch API calls |
| **Total MVP** | **4–5 days** | Realistic single-person sprint |
| Phase 2 (graph viz, expansion) | 3–4d | Separate sprint |
| Phase 3 (multimodal, insights) | 5–7d | Requires LLM integration |

---

## 7. Atomic Commit Strategy

```bash
# Phase 1: Service Layer
feat: add SemanticSearchService skeleton
test: add unit tests for semantic search init
feat: implement search_similar with mock embeddings
test: add similarity search tests
feat: integrate OpenAI embedding API
test: add embedding API integration tests
feat: add vector caching (YAML + .npy)
test: add caching tests

# Phase 1: Tool Layer
feat: add semantic_search MCP tool
test: add semantic search tool tests
refactor: register semantic_search in server.py

# Phase 1: Polish
test: add edge case tests for empty query, missing refs
fix: handle API errors gracefully
docs: add docstrings and examples
perf: optimize cosine_similarity for k-NN search

# Final
test: verify coverage >85% for semantic_search module
ci: add semantic_search to test matrix
```

---

## 8. Success Criteria

- [ ] 433 tests passing (including new semantic search tests)
- [ ] Coverage: >85% on `services/semantic_search_service.py`
- [ ] `semantic_search` MCP tool registered and callable
- [ ] Embedding 34 papers: <5 API calls (batch optimized)
- [ ] Query latency: <2s for finding 5 similar papers
- [ ] Vector cache working (references/embeddings.yaml)
- [ ] Graceful fallback if no OpenAI API key
- [ ] Example workflow documented in docs/tutorials/04-semantic-search.md

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| **OpenAI API cost** | Start with small batch, use mock in tests |
| **Embedding quality too low** | Use text-embedding-3-small (proven), add summary + keywords |
| **Cache invalidation bugs** | Implement mtime-based validation, add cache reset command |
| **Slow search on large dataset** | Pre-optimize cosine_similarity with numpy, cache for re-use |
| **API rate limiting** | Implement exponential backoff + batch API calls |

---

## Ready to Execute
This plan is TDD-ready. Start with `test: test_init_loads_references` and iterate.
