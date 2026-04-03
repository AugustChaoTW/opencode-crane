# CRANE: Autonomous AI Research Assistant

**Your AI-powered researcher that handles literature, tasks, and paper verification.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Server-orange.svg)](https://modelcontextprotocol.io/)

---

## 30-Second Elevator Pitch

CRANE is an **Autonomous Research Assistant MCP Server** that transforms how you conduct academic research. Built for [OpenCode](https://github.com/anomalyco/opencode), it bridges the gap between AI agents and research workflows. It doesn't just "summarize papers"—it manages your entire pipeline: from searching multi-source databases (arXiv, OpenAlex) and tracking tasks via GitHub Issues, to performing **evidence-first 7-dimension Q1 evaluation**, **profile-based journal matching**, and **interactive revision planning**. CRANE keeps your research structured, traceable, and publication-ready.

---

## 5 Key Differentiators

1.  **Evidence-First Q1 Evaluation**: 7-dimension hybrid scoring engine with gate mechanisms — not just keyword matching, but structured evidence extraction from your LaTeX manuscript.
2.  **Profile-Based Journal Matching**: Weighted fit scoring (Scope 35%, Contribution 20%, Evaluation 20%, Citation 15%, Operational 10%) across 18 Q1 journals with desk-reject risk assessment.
3.  **Interactive Revision Workflow**: 3-layer reports (Scorecard + Evidence View + Revision Backlog) with prioritized action items, before/after tracking, and projected score estimation.
4.  **PICOS Systematic Screening**: Automated Population/Intervention/Comparison/Outcome/Study Design extraction and matching for systematic literature reviews.
5.  **Domain-Aware Evaluation**: Pluggable domain packs (AI/ML included) with auto-detection, custom rubrics, and reviewer simulation for predicting likely criticisms.

---

## Feature Matrix (Workflow Phases)

CRANE provides **83 MCP Tools** organized across research phases:

| Phase | Core Tools | Purpose |
|-------|------------|---------|
| **Initialization** | `init_research`, `get_project_info` | Set up GitHub milestones, labels, and local file structure. |
| **Literature Review** | `search_papers`, `add_reference`, `read_paper` | Multi-source search, BibTeX sync, and AI-powered summarization. |
| **PICOS Screening** | `screen_papers_by_picos`, `screen_reference` | Systematic screening with Population/Intervention/Comparison/Outcome/Study Design criteria. |
| **Semantic Search** | `semantic_search`, `semantic_search_by_paper`, `build_embeddings` | Vector-based similarity search and embedding management for finding related work. |
| **Citation Graph** | `build_citation_graph`, `find_citation_gaps`, `get_research_clusters`, `visualize_citation_graph` | Citation relationship analysis, research gap detection, and visualization. |
| **Ask My Library** | `ask_library`, `chunk_papers`, `get_chunk_stats` | Conversational Q&A over your references with page-level citations. |
| **Task Management** | `create_task`, `list_tasks`, `report_progress` | Track research goals using GitHub Issues with phase-specific labels. |
| **Verification** | `check_citations`, `verify_reference` | Ensure every claim is cited and metadata (DOI/Year) is accurate. |
| **Writing & Audit** | `review_paper_sections`, `verify_paper` | Automated checks for logic, framing, and AI writing traces. |
| **Q1 Evaluation v2** | `evaluate_paper_v2`, `match_journal_v2`, `generate_revision_report` | Evidence-first 7-dimension scoring, profile-based journal matching, and 3-layer revision reports. |
| **Submission** | `run_submission_check`, `recommend_journals` | Final Q1-standard readiness evaluation and journal strategy. |
| **Version Management** | `check_crane_version`, `upgrade_crane`, `rollback_crane` | Check for updates, upgrade with backup, and rollback on failure. |

---

## Quick Start (5 Commands to Run Your First Pipeline)

Get CRANE running and perform a complete literature review in minutes:

1.  **Install CRANE**:
    ```bash
    curl -fsSL https://raw.githubusercontent.com/AugustChaoTW/opencode-crane/main/scripts/install.sh | bash
    ```
2.  **Initialize Project**:
    ```bash
    cd your-research-repo && bash ~/.opencode-crane/scripts/setup-project.sh
    ```
3.  **Run Pipeline (via OpenCode)**:
    Ask: *"Initialize this repo as a research project"*
4.  **Search & Add**:
    Ask: *"Search for papers about 'Transformer Scaling Laws' and add the top 3 to my library"*
5.  **Automated Review**:
    Ask: *"Perform a literature review pipeline for the topic 'Agentic Workflows'"*

---

## Installation

### Prerequisites
- **Python**: 3.10+
- **Tools**: [uv](https://astral.sh/uv/install.sh) (fast package manager), [bun](https://bun.sh/install)
- **OS**: Linux (Ubuntu 20.04+, Rocky Linux 8+, Fedora 36+)

### Simplified Setup
```bash
# 1. Install CRANE core
git clone https://github.com/AugustChaoTW/opencode-crane.git ~/.opencode-crane
cd ~/.opencode-crane && uv sync

# 2. Add to OpenCode configuration
# Add CRANE to your ~/.config/opencode/opencode.json under "mcp"
```
*For detailed plugin and skill installation, see the [Full Installation Guide](#full-installation-guide).*

---

## Architecture Diagram

```text
+-----------------------------------------------------------+
|                      OpenCode Agent                       |
|           (Natural Language Command Interface)             |
+--------------------------+--------------------------------+
                           |
            +--------------v--------------+
            |      CRANE MCP Server       |
            |    (FastMCP / 56 Tools)     |
            +--------------+--------------+
                           |
    +----------+-----------+-----------+-----------+----------+
    |          |           |           |           |          |
+---v---+ +---v---+  +----v----+ +----v----+ +----v----+ +---v---+
|GitHub | |LocalFS|  |Academic | |Eval v2  | |Domain   |Version|
|API(gh)| |(YAML) |  |APIs     | |Engine   | |Packs    |Manager|
+---+---+ +---+---+  +----+----+ +----+----+ +----v----+ +---v---+
    |         |            |           |           |         |
    |Tasks    |Meta/BibTeX |arXiv      |7-dim Q1   |AI/ML    |Upgrade
    |Issues   |PDFs        |OpenAlex   |Journal    |Medical  |Rollback
    |Progress |Rubric Vers |alphaXiv   |Revision   |Custom   |Migrate
    +---------+------------+-----------+-----------+---------+------+
```

---

## Key Features (Detail)

### Q1 Evaluation Engine (New)
- **7-Dimension Hybrid Scoring**: Writing Quality (12%), Methodology (18%), Novelty (18%), Evaluation (20%), Presentation (8%), Limitations (10%), Reproducibility (14%) — each scored 0-100 with evidence spans and reason codes.
- **Gate Mechanism**: Methodology, Novelty, or Evaluation scoring below 60 blocks Q1 readiness — prevents false positives.
- **Paper Profiling**: Automatic classification of paper type (empirical/system/theoretical/survey), method family, evidence pattern, novelty shape, and reproducibility maturity.
- **Backward Compatible**: `mode="heuristic"` preserves the original regex-based evaluation; `mode="hybrid"` activates the evidence-first engine.

### Journal Matching (New)
- **18 Q1 Journal Profiles**: Real impact factors, acceptance rates, scope keywords, desk-reject signals for IEEE TPAMI, TNNLS, ACM Computing Surveys, Nature MI, JMLR, and more.
- **Weighted Fit Scoring**: Scope (35%) + Contribution-style (20%) + Evaluation-style (20%) + Citation-neighborhood (15%) + Operational (10%).
- **Target/Backup/Safe Recommendations**: Not just "best match" — a 3-tier strategy with desk-reject risk assessment.

### Revision Planning (New)
- **3-Layer Reports**: Scorecard (scores + gates + readiness), Evidence View (per-dimension evidence spans), Revision Backlog (prioritized checkboxes).
- **ROI-Sorted Actions**: Impact x Effort matrix ranks what to fix first for maximum score improvement.
- **Before/After Tracking**: Snapshot scores, re-evaluate after changes, see delta per dimension.

### Domain Packs (New)
- **Pluggable Rubrics**: Each domain (AI/ML, medical, etc.) gets its own weight configuration, gate rules, and scoring signals.
- **Auto-Detection**: Paper domain detected from keywords — automatically selects the right rubric pack.

### Reviewer Simulation (New)
- **10 Criticism Patterns**: Novelty concerns, weak baselines, methodology unclear, insufficient experiments, reproducibility concerns, overclaiming, poor writing, missing limitations, statistical rigor, presentation issues.
- **Predicted Decision**: accept / minor_revisions / major_revisions / reject with confidence scoring.
- **Mock Review Generation**: Structured review text from predicted criticisms.

### Rubric Calibration (New)
- **Version Management**: Save, compare, and rollback rubric versions as YAML.
- **Proposal Workflow**: Propose weight updates with validation (weights sum to 1.0, reason required).

### APC Cost-Benefit Analysis (New)
- **Budget-Aware Journal Ranking**: Journals sorted by affordability first, then fit score.
- **18 Journal APC Profiles**: IEEE ~$2,800, Elsevier ~$3,200-3,400, Nature MI $11,990, JMLR $0 (diamond OA).
- **CostAssessment Model**: Tracks APC, publication model, waiver availability, and affordability status.
- **analyze_apc MCP Tool**: One-click APC comparison report across all Q1 journals.

### Feynman Method Interactive Coach (New)
- **30+ Probing Questions**: Per-dimension question banks targeting methodology, novelty, evaluation, writing, reproducibility, and limitations.
- **Auto-Targeting Weak Dimensions**: Generates questions for dimensions scoring below 70.
- **Difficulty Mixing**: Basic, probing, and challenging questions per weak dimension.
- **generate_feynman_session MCP Tool**: Forces you to articulate and defend your work before submission.

### alphaXiv Structured Paper Summaries (New)
- **AlphaXivProvider**: Fetches AI-generated structured markdown overviews instead of parsing raw PDFs.
- **Dual-Source Reading**: alphaXiv first → cache → PyPDF2 fallback.
- **Structured Chunking**: Section-aware markdown splitting preserves equations and tables.
- **Rate Limit Handling**: Automatic retry with exponential backoff on 429 errors.

### Version Management (New)
- **check_crane_version**: Compare local version against GitHub Releases, get compatibility assessment.
- **upgrade_crane**: Automated upgrade with backup, git pull, uv sync, and verification.
- **rollback_crane**: Restore from backup directory or git tag on failure.
- **Startup Auto-Check**: CRANE checks for updates on launch (configurable via `CRANE_CHECK_VERSION_ON_START`).
- **Migration Framework**: Apply/skip/unskip version migrations with persistent state tracking.

### Core Features
- **Section-level Paper Review**: Detects 6 common issues per section (logic errors, data inconsistencies, overclaiming, missing completeness, AI writing traces, figure quality).
- **LaTeX Structure Parsing**: Automatically detects `\section{}`, `\subsection{}`, and `\appendix`.
- **3-LLM Paper Verification**: An AI review process with Auditor, Detector, and Editor roles.
- **AI Writing Detection**: Three-layer analysis: L1 Vocabulary, L2 Paragraph Rhythm, and L3 Academic Subjectivity.
- **PICOS Screening**: Automated extraction of Population/Intervention/Comparison/Outcome/Study Design elements with weighted matching.
- **Protected Zones**: Automatically protects verified content from accidental modification.
- **Workspace Management**: Stateless design, automatically parsing workspace from git context.

---

## Comparison: CRANE vs. Alternatives

| Feature | CRANE | Zotero | Mendeley | Obsidian |
|---------|-------|--------|----------|----------|
| **AI Autonomy** | Native MCP | Third-party plugins | Limited | Manual setup |
| **Q1 Evaluation** | 7-dim evidence-first | None | None | None |
| **Journal Matching** | Profile-based (18 Q1) | None | None | None |
| **Revision Planning** | 3-layer + ROI sorting | None | None | None |
| **PICOS Screening** | Automated extraction | None | None | Manual |
| **Paper Auditing** | Section-level Logic/AI | None | None | Manual |
| **Citation Check** | Automated (BibTeX) | Semi-automated | Semi-automated | Manual |
| **Developer-First** | CLI/MCP/YAML | GUI-heavy | GUI-heavy | Note-heavy |

---

## Real-World Use Cases

### 1. The Systematic Literature Review
*Scenario*: A PhD student needs to screen 500 papers on "LoRa Security".
- **CRANE Action**: Run `run_pipeline(topic="LoRa Security", max_papers=500)`.
- **Result**: CRANE searches arXiv/OpenAlex, downloads PDFs, extracts abstracts, and creates a GitHub project board with milestones for screening, while annotating each YAML file with AI-extracted methodology.

### 2. The Collaborative Paper Drafting
*Scenario*: A team is writing a NeurIPS submission and wants to ensure consistency.
- **CRANE Action**: `check_citations(manuscript_path="main.tex")` followed by `review_paper_sections()`.
- **Result**: CRANE identifies 3 missing references and flags a data inconsistency where "Table 1" shows 85% accuracy but the "Abstract" claims 87%.

### 3. The Q1 Submission Preparation
*Scenario*: A researcher wants to evaluate if their paper is ready for a Q1 journal.
- **CRANE Action**: `evaluate_paper_v2(paper_path="main.tex")` followed by `match_journal_v2(paper_path="main.tex")`.
- **Result**: CRANE scores all 7 dimensions (Methodology: 78, Evaluation: 65, ...), flags that the Evaluation gate is borderline, recommends IEEE TPAMI (target), TNNLS (backup), Pattern Recognition (safe), and generates a revision backlog: "Add ablation study (+12 impact), Include statistical significance tests (+8 impact)".

### 4. The Continuous Research Monitor
*Scenario*: A researcher wants to stay updated on "Diffusion Models" weekly.
- **CRANE Action**: Schedule a job to run `search_papers` and `add_reference` for new hits.
- **Result**: Every Monday, the researcher checks their GitHub Issues to see a curated list of new papers, summarized and ready for deep reading.

### 5. The Pre-Submission Feynman Rehearsal
*Scenario*: A researcher wants to test their understanding before submitting to a Q1 journal.
- **CRANE Action**: `generate_feynman_session(paper_path="main.tex", mode="pre_submission")`.
- **Result**: CRANE generates 5-10 probing questions targeting weak dimensions (e.g., "Your evaluation shows 2% improvement — is that statistically significant?"), forcing the researcher to articulate and defend their work. Unanswerable questions become revision items.

### 6. The APC-Aware Journal Selection
*Scenario*: A researcher has a $3,000 publication budget and needs to choose a Q1 journal.
- **CRANE Action**: `analyze_apc(paper_path="main.tex", budget_usd=3000)`.
- **Result**: CRANE ranks 18 Q1 journals by affordability: 12 within budget (IEEE TPAMI $2,800), 3 near budget, 3 over budget (Nature MI $11,990). Recommends the highest-fit journal within budget with desk-reject risk assessment.

---

## Development

CRANE is built for researchers who code.

### Environment Setup
```bash
cd ~/.opencode-crane
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

### Running Tests
```bash
# Full test suite (1300+ tests)
uv run pytest tests/ -v
# Coverage report
uv run pytest tests/ --cov=crane --cov-report=term-missing
# Benchmark integration tests only
uv run pytest tests/benchmark/ -v
```

### Project Structure
```
src/crane/
  models/          # Data models (Paper, PaperProfile, EvidenceLedger, etc.)
  services/        # Business logic (20+ services)
  tools/           # MCP tool registration (56 tools)
  config/          # Domain packs and configuration
  templates/llm/   # Prompt templates for future LLM integration
  providers/       # Academic data sources (arXiv, OpenAlex, etc.)
data/
  journals/        # Q1 journal profiles (18 journals) + conference templates
  review_patterns.yaml  # 10 criticism patterns for reviewer simulation
tests/
  services/        # Unit tests per service
  models/          # Model validation tests
  benchmark/       # Integration tests with synthetic LaTeX papers
  config/          # Domain pack tests
```

---

## License
MIT License

## Citation
```bibtex
@article{zhang2025scaling,
  title={Scaling Laws in Scientific Discovery with AI and Robot Scientists},
  author={Zhang, Pengsong and others},
  journal={arXiv preprint arXiv:2503.22444},
  year={2025}
}
```

---

<a name="full-installation-guide"></a>
## Appendix: Full Installation Guide (Executable by AI)

> **Note to AI Agent**: These steps are independent.

### 1. Toolchain
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
curl -fsSL https://bun.sh/install | bash
hash -r
```

### 2. Manual Installation
```bash
git clone https://github.com/AugustChaoTW/opencode-crane.git ~/.opencode-crane
cd ~/.opencode-crane && uv sync
```

### 3. Plugins & Configuration
```bash
OPENCODE="$HOME/.config/opencode"
cat > "$OPENCODE/package.json" << 'EOF'
{
  "dependencies": {
    "@opencode-ai/plugin": "^1.3.2",
    "oh-my-opencode": "^3.12.3",
    "opencode-claude-auth": "^1.3.1"
  }
}
EOF
cd "$OPENCODE" && bun install

# Memory System Plugin
git clone --depth 1 https://github.com/AugustChaoTW/aug-money.git /tmp/aug-money
cd /tmp/aug-money/opencode-memory-system && bun install && bun run build
mkdir -p "$OPENCODE/plugins/memory-system"
cp dist/index.js dist/sql-wasm.wasm package.json "$OPENCODE/plugins/memory-system/"
rm -rf /tmp/aug-money
```

### 4. Write Configuration
```bash
OPENCODE="$HOME/.config/opencode"
cat > "$OPENCODE/opencode.json" << 'EOF'
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": [
    "oh-my-opencode",
    "opencode-claude-auth",
    "./plugins/memory-system"
  ],
  "mcp": {
    "crane": {
      "type": "local",
      "command": ["sh", "-c", "cd $HOME/.opencode-crane && uv run crane"],
      "enabled": true
    }
  }
}
EOF
```
