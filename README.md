# opencode-crane

**CRANE** — Autonomous Research Assistant MCP Server, specifically designed for [OpenCode](https://github.com/anomalyco/opencode).

Integrates the complete academic research workflow (Literature Search → Proposal → Experiment → Writing → Review) into a set of MCP tools, tracking tasks via GitHub Issues and maintaining references through file-based management (YAML + BibTeX).

> **CRANE**: Symbolizing wisdom, patience, and precision. A crane patiently observes the water surface and strikes with precision—just as a researcher extracts insights after deep literature reading.

---

## Key Features

- **Section-level Paper Review** — Detects 6 common issues per section (logic errors, data inconsistencies, overclaiming, missing completeness, AI writing traces, figure quality).
- **LaTeX Structure Parsing** — Automatically detects `\section{}`, `\subsection{}`, and `\appendix`.
- **3-LLM Paper Verification** — An AI review process with Auditor, Detector, and Editor roles.
- **AI Writing Detection** — Three-layer analysis: L1 Vocabulary, L2 Paragraph Rhythm, and L3 Academic Subjectivity.
- **Protected Zones** — Automatically protects verified content from accidental modification.
- **Journal Recommendation** — Recommends suitable Q1/Q2 journals for submission (OpenAlex + SJR).
- **Vector Graphics Generation** — Generates publication-quality PDF charts using Matplotlib/Seaborn.
- **Multi-source Paper Search** — Supports four major databases: arXiv, OpenAlex, Semantic Scholar, and Crossref.
- **Reference Library Management** — Dual-format storage (YAML + BibTeX) with search, filtering, and AI annotation support.
- **Metadata Standardization** — Automatic de-duplication, conflict resolution, and citation count aggregation.
- **Citation Verification** — Checks citation consistency in papers and validates reference metadata.
- **Screening and Comparison** — Inclusion/exclusion decisions for systematic reviews and multi-dimensional comparison matrices.
- **Evidence Traceability** — All AI outputs are traceable back to original sources.
- **Research Task Tracking** — Manages tasks and todos via GitHub Issues.
- **Workspace Management** — Stateless design, automatically parsing workspace from git context.
- **Reliable Execution** — Automatic retry mechanism, gracefully handling network failures.
- **Research Phase Management** — Tracks progress through Literature Review → Proposal → Experiment → Writing → Review.
- **Project Initialization** — One-click setup of research project structure (labels, milestones, directories, Issue Templates).
- **Native OpenCode Integration** — MCP Server architecture, allowing AI agents to operate directly via natural language.

---

## Quick Command Card

> 💡 **Quick Reference**: CRANE tools corresponding to common natural language commands.

| Your Need | Natural Language | Corresponding Tool |
|-----------|------------------|-------------------|
| 🚀 Init Project | `Initialize this repo as a research project` | `init_research` |
| 🔍 Search Papers | `Search for papers about transformers` | `search_papers` |
| 📥 Add Reference | `Add this paper to the library` | `add_reference` |
| 📄 Download PDF | `Download paper 2301.00001` | `download_paper` |
| 📖 Read Paper | `Read this paper and summarize it` | `read_paper` |
| ✅ Check Citations | `Check if all citations in the paper have references` | `check_citations` |
| 🔎 Verify Reference | `Verify DOI for vaswani2017-attention` | `verify_reference` |
| 📋 Create Task | `Create a literature review task` | `create_task` |
| 📝 Create Todo | `Create todo: review chapter 3` | `create_task(type="todo")` |
| 📊 Check Progress | `What is the current task progress?` | `get_milestone_progress` |
| 🏠 Workspace Status | `Show workspace status` | `workspace_status` |
| 🔄 Run Pipeline | `Help me with literature review` | `run_pipeline` |
| 📊 Screen Reference | `Mark this paper as included` | `screen_reference` |
| 🔍 Compare Papers | `Compare the differences between these three papers` | `compare_papers` |
| 🔬 Verify Paper | `Verify the quality of this paper` | `verify_paper` |
| 🎯 Recommend Journal | `Recommend journals for submission` | `recommend_journals` |
| 📊 Generate Figure | `Generate a comparison chart` | `generate_figure` |
| 📝 Review Sections | `Review the sections of this paper` | `review_paper_sections` |
| 🔍 Parse Structure | `Parse the chapter structure of this paper` | `parse_paper_structure` |

### Label Reference Table

| Category | Labels | Description |
|----------|--------|-------------|
| 🔖 CRANE Mark | `crane` | All issues managed by CRANE |
| 📌 Kind | `kind:task` / `kind:todo` | Task / Todo |
| 🎯 Phase | `phase:literature-review`, `phase:proposal`, `phase:experiment`, `phase:writing`, `phase:review` | Research Phase |
| 🏷️ Type | `type:search`, `type:read`, `type:analysis`, `type:code`, `type:write` | Nature of Task |
| ⚡ Priority | `priority:high`, `priority:medium`, `priority:low` | Priority Order |

### Typical Workflows

#### Literature Review Workflow
1. **Initialize** → `init_research`
2. **Search** → `search_papers` → `add_reference` → `download_paper`
3. **Read & Annotate** → `read_paper` → `annotate_reference`
4. **Screen & Compare** → `screen_reference` → `compare_papers`
5. **Track Task** → `create_task` → `report_progress` → `close_task`
6. **Verify Citations** → `check_citations` → `verify_reference`
7. **View Progress** → `workspace_status` → `get_milestone_progress`

#### 3-LLM Paper Verification Workflow
1. **Recommend Journals** → `recommend_journals`
2. **AUDIT** → LLM-A: Data traceability + Citation verification
3. **DETECTION** → LLM-B: L1/L2/L3 AI writing detection
4. **EDITING** → LLM-C: Constrained rewriting
5. **RE-VERIFY** → LLM-A: Verify changes (FAIL → back to Step 4)
6. **Generate Figures** → `generate_figure` / `generate_comparison`
7. **Report** → `PAPER_HEALTH_REPORT.md`

#### Section-level Paper Review Workflow
1. **Parse Structure** → `parse_paper_structure`
2. **Review Sections** → `review_paper_sections`
    - Logic errors (`logic`)
    - Data consistency (`data`)
    - Framing range (`framing`)
    - Completeness (`completeness`)
    - AI writing traces (`writing`)
    - Figure quality (`figures`)
3. **Generate Report** → `section_review_report.yaml`
4. **Fix Issues** → Fix one by one based on suggestions
5. **Re-verify** → Re-run review

### Section Review Types

| Type | Detection Items | Example of Common Issues |
|------|-----------------|--------------------------|
| `logic` | Python logic errors, algorithm correctness | `if "good" or "positive" in text` |
| `data` | Consistency in percentages, costs, latencies | 62.5% vs 87.5% contradiction |
| `framing` | Overclaiming, terminology misuse | "neuro-symbolic expert system" |
| `completeness` | Missing baselines, undiscussed limitations | Missing constrained decoding baseline |
| `writing` | AI writing traces, vague quantifiers | "It is worth noting that" |
| `figures` | Figure complexity, caption completeness | Figure 1 is overly complex |

### 3-LLM Role Definitions

| Role | Cognitive Mode | Responsibilities |
|------|----------------|------------------|
| **LLM-A (Auditor)** | Precise, Conservative, Binary Judgment | Data traceability, Citation verification, Re-verification |
| **LLM-B (Detector)** | Pattern-sensitive, Linguistic analysis | L1 Vocabulary, L2 Paragraph, L3 Subjectivity detection |
| **LLM-C (Editor)** | Creative, Domain expert | Constrained rewriting, maintaining Protected Zones |

---

## Quick Installation

### One-click Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/AugustChaoTW/opencode-crane/main/scripts/install.sh | bash
```

After installation, run the following in your research project:

```bash
cd ~/your-research-project
bash ~/.opencode-crane/scripts/setup-project.sh
```

Done. Launch OpenCode to start.

---

<!-- OPENCODE-INSTALL-GUIDE-BEGIN -->
## Installation Guide (Readable & Executable by OpenCode)

> **Note to AI Agent**: The following steps can be executed sequentially. Each step is an independent shell command with a verification method. If the user says "Help me install crane," follow this flow.

### System Requirements
Supported OS: Ubuntu 20.04+, Rocky Linux 8+, RHEL 8+, Fedora 36+

### One-click Install (Recommended)
```bash
curl -fsSL https://raw.githubusercontent.com/AugustChaoTW/opencode-crane/main/scripts/install.sh | bash
```
Proceed to **[Project Setup](#project-setup)**.

### Manual Installation
Copy and paste from top to bottom. Each line is independent.

#### Install Toolchain
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
curl -fsSL https://bun.sh/install | bash
hash -r
```

#### Install CRANE
```bash
git clone https://github.com/AugustChaoTW/opencode-crane.git ~/.opencode-crane
cd ~/.opencode-crane && uv sync
```

#### Install Plugins
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

git clone --depth 1 https://github.com/AugustChaoTW/aug-money.git /tmp/aug-money
cd /tmp/aug-money/opencode-memory-system && bun install && bun run build
mkdir -p "$OPENCODE/plugins/memory-system"
cp dist/index.js dist/sql-wasm.wasm package.json "$OPENCODE/plugins/memory-system/"
rm -rf /tmp/aug-money
```

#### Write Configuration
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

cat > "$OPENCODE/oh-my-opencode.json" << 'EOF'
{
  "$schema": "https://raw.githubusercontent.com/code-yeongyu/oh-my-opencode/master/assets/oh-my-opencode.schema.json",
  "google_auth": false,
  "agents": {}
}
EOF
```

#### Install SKILL.md
```bash
mkdir -p "$HOME/.config/opencode/skills/opencode-crane"
cp ~/.opencode-crane/SKILL.md "$HOME/.config/opencode/skills/opencode-crane/SKILL.md"
```

---

### Project Setup
Execute in your research project root to complete MCP + gitignore setup:

```bash
# Method A: Using Script (Recommended)
bash ~/.opencode-crane/scripts/setup-project.sh
```

```bash
# Method B: Manual
cd ~/your-research-project
mkdir -p .opencode
cat > .opencode/opencode.json << 'EOF'
{
  "mcp": {
    "crane": {
      "type": "local",
      "command": ["sh", "-c", "cd $HOME/.opencode-crane && uv run crane"],
      "enabled": true
    }
  }
}
EOF
mkdir -p .opencode/skills/opencode-crane
cp ~/.opencode-crane/SKILL.md .opencode/skills/opencode-crane/SKILL.md
grep -q "references/pdfs/" .gitignore 2>/dev/null || echo "references/pdfs/" >> .gitignore
```

#### Verification
```bash
cd ~/.opencode-crane && uv run python -c "from crane.server import mcp; print(f'OK: {len(mcp._tool_manager._tools)} tools registered')"
echo "oh-my-opencode:      $([ -d ~/.config/opencode/node_modules/oh-my-opencode ] && echo '✓' || echo '✗')"
echo "opencode-claude-auth: $([ -d ~/.config/opencode/node_modules/opencode-claude-auth ] && echo '✓' || echo '✗')"
echo "memory-system:        $([ -f ~/.config/opencode/plugins/memory-system/index.js ] && echo '✓' || echo '✗')"
```
Expected: `OK: N tools registered` + all ✓

#### Installation Checklist
- [ ] uv installed (`command -v uv`)
- [ ] bun installed (`command -v bun`)
- [ ] `~/.opencode-crane/.venv` exists
- [ ] `~/.config/opencode/package.json` exists
- [ ] `~/.config/opencode/node_modules/oh-my-opencode` exists
- [ ] `~/.config/opencode/node_modules/opencode-claude-auth` exists
- [ ] `~/.config/opencode/plugins/memory-system/index.js` exists
- [ ] `~/.config/opencode/opencode.json` contains `plugin` array
- [ ] `~/.config/opencode/oh-my-opencode.json` exists
- [ ] `~/.config/opencode/skills/opencode-crane/SKILL.md` exists
- [ ] Project `.opencode/opencode.json` has MCP configured (crane)
- [ ] Project `.gitignore` includes `references/pdfs/`

Launch OpenCode and type `Initialize this repo as a research project` to verify full functionality.
<!-- OPENCODE-INSTALL-GUIDE-END -->

---

## Update
```bash
cd ~/.opencode-crane && git pull && uv sync
cd ~/.config/opencode && bun install
```

## Uninstall
```bash
rm -rf ~/.opencode-crane
rm -rf ~/.config/opencode/plugins/memory-system
rm -f ~/.config/opencode/skills/opencode-crane/SKILL.md
rm -f ~/.config/opencode/oh-my-opencode.json
```

---

## Feature Overview

### 23+ MCP Tools in 7 Categories

#### Project Management (2 tools)
| Tool | Description |
|------|-------------|
| `init_research` | Initializes GitHub repo as a research project: creates labels, milestones, `references/` directory, and Issue Template. |
| `get_project_info` | Retrieves project information: repo name, branch, milestone progress, reference count. |

#### Paper Search (3 tools)
| Tool | Description |
|------|-------------|
| `search_papers` | Searches academic papers (arXiv, etc.), returns title, authors, abstract, DOI, PDF URL. |
| `download_paper` | Downloads paper PDF to `references/pdfs/`. |
| `read_paper` | Reads PDF and extracts full text (auto-downloads if missing). |

#### Reference Management (6 tools)
| Tool | Description |
|------|-------------|
| `add_reference` | Adds reference: writes `references/papers/{key}.yaml` + appends to `bibliography.bib`. |
| `list_references` | Lists all references, support keyword/tag filtering. |
| `get_reference` | Retrieves full details of a single reference (including AI annotations). |
| `search_references` | Full-text search across reference titles, authors, abstracts, and keywords. |
| `remove_reference` | Deletes reference (YAML + BibTeX entry + optional PDF deletion). |
| `annotate_reference` | Adds AI annotations: summary, key contributions, methodology, related issues. |

#### Citation Verification (3 tools)
| Tool | Description |
|------|-------------|
| `check_citations` | Checks if all `\cite{key}` in the paper exist in the library. |
| `verify_reference` | Validates reference metadata (DOI, year, title) against expectations. |
| `check_all_references` | Checks metadata completeness for all references (required fields). |

#### Task Management (7 tools)
| Tool | Description | Underlying Command |
|------|-------------|--------------------|
| `create_task` | Creates research task or todo (GitHub Issue), automatically adds labels. | `gh issue create` |
| `list_tasks` | Lists tasks/todos, filtered by phase/status/type. | `gh issue list` |
| `view_task` | Views single task content and comment history. | `gh issue view` |
| `update_task` | Updates task labels, milestones, assignees. | `gh issue edit` |
| `report_progress` | Comments on task to report progress. | `gh issue comment` |
| `close_task` | Closes/completes task. | `gh issue close` |
| `get_milestone_progress` | Retrieves progress statistics for research phases. | `gh api` |

#### Workspace (1 tool)
| Tool | Description |
|------|-------------|
| `workspace_status` | Queries workspace overview: repo, reference stats, tasks/todos, milestone progress. |

#### Workflow (2 tools)
| Tool | Description |
|------|-------------|
| `run_pipeline` | Executes predefined multi-step workflows (`literature-review` / `full-setup`). |
| `run_submission_check` | Executes integrated pre-submission verification workflow. |

---

## Usage Examples

After installation, use natural language in OpenCode:

### Initialization
```
> Initialize this repo as a research project
```

### Literature Review
```
> Search for papers about transformer attention mechanism
> Add the top 3 papers to the library
> Download the first one and summarize its key points
```

### Citation Verification
```
> Check if all citations in my manuscript.tex have corresponding references
> Verify if the DOI for vaswani2017-attention is correct
> List all references missing author information
```

### Task & Todo Management
```
> Create a literature review task: read 5 papers related to attention
> Create a todo: review the draft of chapter 3
> What is the current task progress?
> List all todo items
> Mark task #1 as completed
```

### Workspace Status
```
> Show workspace status
> How many references are in this project? What is the task progress?
```

---

## Research Workflow Phases

```
Phase 1: Initialization
  init_research → Create labels / milestones / references directory

Phase 2: Literature Review
  search_papers → add_reference → download_paper → read_paper → annotate_reference
  create_task(phase="literature-review") → report_progress → close_task

Phase 3: Proposal
  list_references → create_task(phase="proposal")

Phase 4: Experiment
  create_task(phase="experiment") → report_progress

Phase 5: Writing
  get_reference → check_citations → create_task(phase="writing")

Phase 6: Review
  create_task(phase="review") → get_milestone_progress
```

---

## Architecture Design

### Service Layer
CRANE uses an architecture that separates the service layer from the tool layer to ensure code reusability and testability:

```
src/crane/
├── workspace.py               # Workspace resolution module
│   ├── WorkspaceContext       # Immutable workspace context (owner/repo, paths)
│   └── resolve_workspace()    # Auto-resolves workspace from git context
│
├── services/                  # Business Logic Layer
│   ├── paper_service.py       # arXiv Search / Download / Read
│   ├── reference_service.py   # YAML + BibTeX CRUD
│   ├── task_service.py        # GitHub Issues Management (with todo support)
│   └── citation_service.py    # Citation verification logic
│
├── tools/                     # MCP Tool Layer (Thin wrappers)
│   ├── papers.py              # → PaperService
│   ├── references.py          # → ReferenceService
│   ├── tasks.py               # → TaskService
│   ├── citations.py           # → CitationService
│   ├── pipeline.py            # Workflow orchestration → all services
│   ├── project.py             # Project initialization
│   └── workspace.py           # Workspace status queries
│
└── server.py                  # MCP Server Entry Point
```

### Workspace System
CRANE uses a stateless design, automatically parsing the workspace from the git context for each call:
- **Workspace Identification**: Uses `owner/repo` (GitHub repo) as the standard ID.
- **Auto-detection**: Automatically resolves the git repo from `cwd`.
- **State Reconstruction**: Mixed reading — References (file-based) + Issues (GitHub API).

```
Workspace State Sources:
├── references/           # File-based storage
│   ├── papers/*.yaml     # Reference metadata
│   ├── pdfs/*.pdf        # PDF files
│   └── bibliography.bib  # BibTeX summary
│
└── GitHub Issues         # Tasks and Todos
    ├── kind:task         # General tasks
    ├── kind:todo         # Runtime todos
    ├── phase:*           # Research phases
    └── priority:*        # Priorities
```

---

## Development

### Environment Setup
```bash
cd ~/.opencode-crane
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

### Running Tests
```bash
# Full test suite
.venv/bin/python -m pytest tests/ -v

# Specific test categories
.venv/bin/python -m pytest tests/services/ -v    # Service layer tests
.venv/bin/python -m pytest tests/tools/ -v       # Tool layer tests
.venv/bin/python -m pytest tests/integration/ -v # Integration tests

# Coverage report
.venv/bin/python -m pytest tests/ --cov=crane --cov-report=term-missing
```

---

## Design Documents
For full specifications, please refer to [`OPENCODE_GH_FEAT_DESIGN.md`](./OPENCODE_GH_FEAT_DESIGN.md).

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
