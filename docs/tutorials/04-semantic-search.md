# Tutorial 4: Semantic Search - Find Related Work Automatically

Semantic search helps you discover papers related to your research topic without manual keyword matching. CRANE uses OpenAI embeddings and vector similarity to find conceptually related papers.

## Overview

CRANE provides three semantic search tools:
- **`semantic_search`** - Find papers by query text
- **`semantic_search_by_paper`** - Find papers similar to one you already have
- **`build_embeddings`** - Generate embeddings for all papers (required first step)

## Quick Start

### 1. Build Embeddings for Your Library

First, generate embeddings for all papers in your reference library:

```bash
crane build_embeddings
```

Expected output:
```
Status: success
Embedding count: 34
Cache file: references/embeddings.yaml
Model: text-embedding-3-small
```

Requirements:
- `OPENAI_API_KEY` environment variable must be set
- API key must have access to `text-embedding-3-small` model

### 2. Search by Query Text

Find papers related to a research topic:

```bash
crane semantic_search query="attention mechanisms in neural networks" k=5
```

Expected output:
```
Query: attention mechanisms in neural networks
Status: success
Match count: 5
Matches:
  - Key: vaswani2017-attention
    Similarity: 0.92
    Title: Attention Is All You Need
    Authors: [Vaswani, Shazeer, ...]
    Year: 2017
    Abstract: We propose a new simple network architecture...

  - Key: devlin2018-bert
    Similarity: 0.88
    Title: BERT: Pre-training of Deep Bidirectional Transformers
    Authors: [Devlin, Chang, ...]
    Year: 2018
    Abstract: We introduce a new language representation model...
```

Parameters:
- `query` (required): Your search text
- `k` (optional, default 5): Number of results to return

### 3. Find Similar Papers

Given a paper you like, find similar ones:

```bash
crane semantic_search_by_paper paper_key="vaswani2017-attention" k=3
```

Expected output:
```
Paper key: vaswani2017-attention
Status: success
Match count: 3
Matches:
  - Key: devlin2018-bert
    Similarity: 0.91
    ...
  - Key: radford2019-gpt2
    Similarity: 0.87
    ...
```

## Real-World Workflow

### Scenario: Discovering Related Work for Your Paper

1. **Initialize your research project**
   ```bash
   cd my-research-repo
   bash ~/.opencode-crane/scripts/setup-project.sh
   ```

2. **Add your core papers to the library**
   ```bash
   crane add_reference \
     key="mybased2024-mywork" \
     title="My Novel Approach to Problem X" \
     authors='["Me"]' \
     year=2024 \
     abstract="We propose a new method for..."
   ```

3. **Search for related work**
   ```bash
   crane semantic_search query="novel approach to problem X" k=10
   ```

4. **Add promising results to your library**
   ```bash
   crane add_reference \
     key="related2023-work" \
     title="Related Work on Problem X" \
     authors='["Authors"]' \
     year=2023 \
     abstract="This paper addresses..." \
     source="semantic_search"
   ```

5. **Find papers similar to your core work**
   ```bash
   crane semantic_search_by_paper paper_key="mybased2024-mywork" k=5
   ```

## How It Works

### Embeddings

CRANE uses OpenAI's `text-embedding-3-small` model to convert paper text into 1536-dimensional vectors:

```
Paper Title + Abstract + Summary → Embedding (1536-dim vector)
```

Each embedding captures semantic meaning independent of keyword matching.

### Vector Similarity

When you search, CRANE:
1. Embeds your query text
2. Computes cosine similarity against all cached embeddings
3. Returns the top-k most similar papers

Similarity scores range from 0.0 (unrelated) to 1.0 (identical).

### Caching

Embeddings are cached in `references/embeddings.yaml`:

```yaml
embeddings:
  paper_key_1: [0.123, -0.456, ..., 0.789]  # 1536-dim vector
  paper_key_2: [...]
metadata:
  model: "text-embedding-3-small"
  embedding_count: 34
  last_updated: "2026-04-01T06:30:00Z"
```

Cache is automatically refreshed when:
- References directory is modified
- Embeddings file is deleted
- You explicitly call `build_embeddings`

## Cost and Performance

### API Cost

- **Model**: `text-embedding-3-small` ($0.02 per 1M tokens)
- **Cost for 34 papers**: ~$0.01 (one-time)
- **Cost per search**: ~$0.00001 (negligible)

### Latency

- **First search**: ~1-2 seconds (includes embedding query)
- **Subsequent searches**: <100ms (uses cached vectors)

### Scaling

- **100 papers**: 0.01 seconds per search
- **1000 papers**: 0.1 seconds per search
- **10000 papers**: 1 second per search (can optimize with approximate nearest neighbor if needed)

## Troubleshooting

### "OPENAI_API_KEY environment variable not set"

Set your API key:
```bash
export OPENAI_API_KEY="sk-..."
crane build_embeddings
```

### "Could not embed query text"

Network issue or API error. Check:
- API key is valid
- Network connection is active
- OpenAI API status: https://status.openai.com/

### "No embeddings found"

Run `build_embeddings` first:
```bash
crane build_embeddings
```

### "No embedding found for paper_key"

The paper doesn't have an embedding yet. Two options:

**Option 1**: Rebuild all embeddings
```bash
rm references/embeddings.yaml
crane build_embeddings
```

**Option 2**: Paper was added after embeddings were built. Rebuild to include it.

## Advanced: Custom Embeddings

Currently, CRANE uses OpenAI embeddings. For offline use or cost savings, you can:

1. **Use Sentence Transformers** (local, no API key)
   ```bash
   pip install sentence-transformers
   ```
   (Phase 2 feature: planned)

2. **Use alternative models** (Phase 2: Cohere, Hugging Face)

## Next Steps

- Create a research task to systematically review discovered papers
- Use `check_citations` to verify related work is properly cited
- Use `review_paper_sections` to audit your related work section
- Run `run_submission_check` before submission

## Examples

### Example 1: Literature Review on Transformers

```bash
crane semantic_search \
  query="transformer architectures attention mechanisms scaling" \
  k=20
```

### Example 2: Find Papers Using Specific Methods

```bash
crane semantic_search \
  query="reinforcement learning with human feedback RLHF alignment" \
  k=10
```

### Example 3: Competitor Analysis

Add a competitor's paper:
```bash
crane add_reference \
  key="competitor2024" \
  title="Competitor Product Release" \
  authors='["Competitor"]' \
  year=2024 \
  abstract="Their approach to..."
```

Then find similar work:
```bash
crane semantic_search_by_paper paper_key="competitor2024" k=10
```

## See Also

- `Tutorial 1: Literature Review` - Full workflow for systematic reviews
- `Tutorial 2: Submission Readiness` - Pre-submission checklist
- `check_citations` - Verify citations and references
- `review_paper_sections` - AI audit of your paper
