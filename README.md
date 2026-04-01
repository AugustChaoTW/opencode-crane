# CRANE: Autonomous AI Research Assistant

**Your AI-powered researcher that handles literature, tasks, and paper verification.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Server-orange.svg)](https://modelcontextprotocol.io/)

---

## 30-Second Elevator Pitch

CRANE is an **Autonomous Research Assistant MCP Server** that transforms how you conduct academic research. Built for [OpenCode](https://github.com/anomalyco/opencode), it bridges the gap between AI agents and research workflows. It doesn't just "summarize papers"—it manages your entire pipeline: from searching multi-source databases (arXiv, OpenAlex) and tracking tasks via GitHub Issues, to performing deep section-level paper audits and citation verification. CRANE keeps your research structured, traceable, and publication-ready.

---

## 5 Key Differentiators

1.  **Workflow Autonomy**: Unlike static managers (Zotero), CRANE is built for AI agents to *execute* tasks, not just store them.
2.  **Section-Level Auditing**: Automatically detects logic errors, data inconsistencies, and AI-writing patterns within your LaTeX manuscript.
3.  **Stateless GitHub Integration**: Uses GitHub Issues as a live, collaborative backend for research task tracking.
4.  **Evidence Traceability**: Every insight and summary is mapped back to the original source PDF, ensuring scientific rigor.
5.  **Native OpenCode Support**: Zero-config integration with OpenCode agents, allowing you to run research pipelines via natural language.

---

## Feature Matrix (Workflow Phases)

CRANE provides **23+ MCP Tools** organized across 6 research phases:

| Phase | Core Tools | Purpose |
|-------|------------|---------|
| **Initialization** | `init_research`, `get_project_info` | Set up GitHub milestones, labels, and local file structure. |
| **Literature Review** | `search_papers`, `add_reference`, `read_paper` | Multi-source search, BibTeX sync, and AI-powered summarization. |
| **Task Management** | `create_task`, `list_tasks`, `report_progress` | Track research goals using GitHub Issues with phase-specific labels. |
| **Verification** | `check_citations`, `verify_reference` | Ensure every claim is cited and metadata (DOI/Year) is accurate. |
| **Writing & Audit** | `review_paper_sections`, `verify_paper` | Automated checks for logic, framing, and AI writing traces. |
| **Submission** | `run_submission_check`, `recommend_journals` | Final Q1-standard readiness evaluation and journal strategy. |

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
            | (FastMCP / Python Service)  |
            +--------------+--------------+
                           |
      +--------------------+--------------------+
      |                    |                    |
+-----v-----+        +-----v-----+        +-----v-----+
|  GitHub   |        | Local FS  |        | Academic  |
| API (gh)  |        | (YAML/Bib)|        | APIs      |
+-----+-----+        +-----+-----+        +-----+-----+
      |                    |                    |
      | - Tasks/Issues     | - Meta (YAML)      | - arXiv     |
      | - Milestones       | - BibTeX           | - OpenAlex  |
      | - Progress         | - PDFs             | - Crossref  |
      +--------------------+--------------------+-------------+
```

---

## Key Features (Detail)

- **Section-level Paper Review**: Detects 6 common issues per section (logic errors, data inconsistencies, overclaiming, missing completeness, AI writing traces, figure quality).
- **LaTeX Structure Parsing**: Automatically detects `\section{}`, `\subsection{}`, and `\appendix`.
- **3-LLM Paper Verification**: An AI review process with Auditor, Detector, and Editor roles.
- **AI Writing Detection**: Three-layer analysis: L1 Vocabulary, L2 Paragraph Rhythm, and L3 Academic Subjectivity.
- **Protected Zones**: Automatically protects verified content from accidental modification.
- **Workspace Management**: Stateless design, automatically parsing workspace from git context.

---

## Comparison: CRANE vs. Alternatives

| Feature | CRANE | Zotero | Mendeley | Obsidian |
|---------|-------|--------|----------|----------|
| **AI Autonomy** | Native MCP | Third-party plugins | Limited | Manual setup |
| **Workflow Tracking** | GitHub Issues | Folders/Tags | Folders/Tags | Linked Notes |
| **Paper Auditing** | Section-level Logic/AI | None | None | Manual |
| **Citation Check** | Automated (BibTeX) | Semi-automated | Semi-automated | Manual |
| **Data Provenance** | Evidence Traceability | Manual notes | Manual notes | Manual links |
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

### 3. The Continuous Research Monitor
*Scenario*: A researcher wants to stay updated on "Diffusion Models" weekly.
- **CRANE Action**: Schedule a job to run `search_papers` and `add_reference` for new hits.
- **Result**: Every Monday, the researcher checks their GitHub Issues to see a curated list of new papers, summarized and ready for deep reading.

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
# Full test suite
uv run pytest tests/ -v
# Coverage report
uv run pytest tests/ --cov=crane --cov-report=term-missing
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
