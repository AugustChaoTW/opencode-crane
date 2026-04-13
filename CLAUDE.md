# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CRANE is an autonomous research assistant MCP (Model Context Protocol) server. It exposes 140+ tools that implement a 6-stage academic research lifecycle (literature review → paper writing → experiment design → idea generation → automated review → journal matching), drawing from Nature's "The AI Scientist" paper.

The server runs over `stdio` transport and is consumed by MCP clients (e.g., Claude Desktop, OpenCode).

## Development Commands

The project uses `uv` for dependency management (CI) but also supports `pip` locally.

```bash
# Setup
uv sync --dev          # preferred (matches CI)
pip install -e ".[dev]" # alternative

# Testing
uv run pytest -m "not integration"          # unit tests only
uv run pytest -m "integration"              # integration tests only
uv run pytest --cov=crane --cov-report=term-missing  # with coverage (≥80% required)
uv run pytest tests/path/to/test_file.py::TestClass::test_method  # single test

# Linting & formatting
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Run the server
crane   # via installed entrypoint
python -m crane.server
```

Makefile aliases (`make test`, `make lint`, `make fmt`, `make clean`) are also available.

## Architecture

### Layer structure

```
MCP Client
    │
    ▼
src/crane/server.py          ← FastMCP server; imports & registers all tool modules
    │
    ▼
src/crane/tools/             ← ~30 modules; each exports register_tools(mcp)
    │
    ▼
src/crane/services/          ← ~52 service classes; all business logic lives here
    │
    ▼
src/crane/providers/         ← paper source adapters (arXiv, OpenAlex, Semantic Scholar, …)
src/crane/models/            ← shared data structures (Paper, PaperProfile, Provenance, …)
src/crane/utils/             ← BibTeX/YAML I/O, git/gh CLI wrappers, retry helpers
src/crane/config/            ← domain packs, journal standards (IEEE TPAMI), LLM templates
```

### Adding a new tool

1. Create or extend a service in `src/crane/services/`.
2. Create (or extend) a tool module in `src/crane/tools/` that exports `register_tools(mcp)` and calls `@mcp.tool()` decorators.
3. Import and call `register_<name>_tools(mcp)` in `src/crane/server.py`.
4. CI validates that ≥20 tools are registered; ensure the count stays above this threshold.

### Key services

| Service | Lines | Responsibility |
|---|---|---|
| `AutomatedReviewerV2` | ~11 K | 5-reviewer ensemble + meta-review |
| `MCPToolOrchestrationService` | ~1 K | intelligent tool discovery |
| `TrustCalibrationService` | ~600 | AI autonomy levels (4 modes) |
| `ExperimentGenerationService` | ~570 | code synthesis, hyperparameter optimization |
| `ResearchPipelineBenchmarkService` | ~500 | 6-stage evaluation |
| `IdeationService` | ~385 | knowledge graph-based idea generation |
| `CausalReasoningEngine` | ~444 | 8 LeCun causal frameworks |

### Workspace & config

- `src/crane/workspace.py` — manages per-project working directories
- `src/crane/config/domain_packs/` — research domain specifications
- `src/crane/config/journal_standards/` — per-journal metadata
- `src/crane/config/templates/llm/` — LLM prompt templates (evidence extraction, Feynman sessions, revision planning, etc.)

## Testing Conventions

- Tests are under `tests/`; integration tests live in `tests/integration/` and are marked `@pytest.mark.integration`.
- Unit tests must not require network access or external credentials.
- `tests/conftest.py` provides fixtures for temp directories and mock `gh`/`git` responses.
- Coverage minimum is 80% (enforced by `pyproject.toml`).

## Code Style

- Ruff target: Python 3.10, line length 100.
- Ignored rules: `E501` (long lines), `F821`, `F841`, `E741`.
- Active rules: `E`, `F`, `I` (isort), `UP` (pyupgrade).

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `CRANE_CHECK_VERSION_ON_START` | `"true"` | Emit warning if a newer version is on PyPI |
| `GH_TOKEN` | — | Required for `gh` CLI calls (issues, PRs) |
