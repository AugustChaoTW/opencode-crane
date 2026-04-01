---
name: opencode-crane
description: >
  CRANE - Autonomous research assistant. Provides complete academic research
  workflow: paper search and management, research task planning and tracking
  via GitHub Issues, PDF reading and annotation, reference management with
  BibTeX and YAML. Trigger phrases: "search papers", "add reference",
  "create task", "research progress", "literature review", "experiment design",
  "write paper", "annotate paper", "milestone progress".
---

# CRANE - Autonomous Research Assistant

## SECTION 1: Tool Inventory

### Project Management
- `init_research` — Initialize repo as research project (labels, milestones, directories)
- `get_project_info` — Get project info (repo, branch, milestone stats, reference count)

### Paper Search
- `search_papers` — Search arXiv for academic papers
- `download_paper` — Download paper PDF to references/pdfs/
- `read_paper` — Extract full text from paper PDF

### Reference Management
- `add_reference` — Add reference to references/ (YAML + BibTeX)
- `list_references` — List all references with optional filtering
- `get_reference` — Get full details of a single reference
- `search_references` — Full-text search across references
- `remove_reference` — Remove a reference
- `annotate_reference` — Add AI annotations (summary, contributions, methodology)

### Task Management (GitHub Issues)
- `create_task` — Create research task with phase/type/priority labels
- `list_tasks` — List tasks filtered by phase, state, milestone
- `view_task` — View task details with comment history
- `update_task` — Update task labels, milestone, assignee
- `report_progress` — Post progress comment on a task
- `close_task` — Complete a task with reason
- `get_milestone_progress` — View research phase progress statistics

### Citation Verification
- `check_citations` — Validate all \cite{key} in manuscript exist in references/
- `verify_reference` — Verify reference metadata (DOI, year, title) matches expected values
- `check_all_references` — Check metadata completeness for all references

### Screening & Comparison
- `screen_reference` — Record include/exclude/maybe decision for a reference
- `list_screened_references` — List all screened references with optional decision filter
- `compare_papers` — Create comparison matrix for multiple papers

### Workspace
- `workspace_status` — View workspace overview (repo, references, tasks, todos, milestones)

### Workflow Orchestration
- `run_pipeline` — Execute predefined multi-step workflows with checkpoints and recovery hints
- `run_submission_check` — Complete pre-submission verification: literature review + experiments + framing + health check

## SECTION 2: WORKFLOW TRIGGER RULES

Use these rules first. Prefer `run_pipeline` for multi-step goals; prefer atomic tools for single precise actions.

### Decision Tree
1. If user intent is broad workflow (initialize project or literature-review flow) -> use `run_pipeline`.
2. If user asks for one specific operation (single paper add, create one task, update one issue) -> use atomic tool directly.
3. If user asks for progress/status overview -> call progress tools directly (`get_milestone_progress` plus `list_tasks`).
4. If workflow fails partway -> switch to atomic tools and resume from failed step.

### Trigger Mapping
- "文獻回顧" / "literature review" / "survey" / "搜尋論文" -> `run_pipeline(pipeline="literature-review", topic=<extracted_topic>, max_papers=5)`
- "初始化" / "setup" / "init" -> `run_pipeline(pipeline="full-setup")`
- "加入這篇論文" / single paper add request -> use `add_reference` directly (not pipeline)
- "建立任務" / specific task request -> use `create_task` directly
- "檢查引用" / "verify citations" / "check references" -> use `check_citations` with manuscript_path or manuscript_text
- "驗證這篇論文" / "verify reference metadata" -> use `verify_reference` with key and expected values
- "檢查所有文獻" / "check all references metadata" -> use `check_all_references`
- "工作區狀態" / "workspace overview" / "project status" -> use `workspace_status`
- "進度" / "status" -> call `get_milestone_progress` + `list_tasks`
- "投稿前檢查" / "do before submission check" / "submission check" -> `run_submission_check(paper_path, project_dir)`

### Chaining Rule (No Extra Prompt Needed)
After a matched workflow trigger, execute all required next steps automatically in one tool-call plan:
- literature review flow: search -> add -> download -> read -> annotate -> create task
- full setup flow: init -> create starter tasks

## SECTION 3: SUBMISSION CHECK WORKFLOW

### `run_submission_check` — Complete Pre-Submission Verification

Executes integrated 4-step workflow:
1. **Literature Review** — Scan existing references library, generate checklist with PDF status
2. **Experiment Results** — Collate experiment data (CSV/JSON/YAML) from repo
3. **Framing Analysis** — Detect overclaiming, terminology issues, weak justification
4. **Paper Health Check** — Q1 standards evaluation + section-level review (6 issue types)

**Output**: Generates `BEFORE_SUBMISSION_RUN{n}/` directory with:
```
BEFORE_SUBMISSION_RUN1/
├── reports/
│   ├── LITERATURE_REVIEW.md            (PDF checklist)
│   ├── EXP_RESULTS.md                  (experiment collation)
│   ├── FRAMING_ANALYSIS.md             (overclaiming issues)
│   └── PAPER_HEALTH_REPORT.md          (Q1 + section review)
└── references/
```

**Parameters**:
- `paper_path`: LaTeX main file (e.g., `papers/TMLR/TMLR-MAIN.tex`). Auto-detected if omitted.
- `project_dir`: Project root (default: current directory)

**Returns**:
```python
{
    "status": "completed" | "failed",
    "version": 1,  # Auto-incremented BEFORE_SUBMISSION_RUNn
    "submission_dir": "/path/to/BEFORE_SUBMISSION_RUN1/",
    "checkpoints": ["literature_review", "experiment_results", "framing_analysis", "paper_health_check"],
    "reports": {
        "literature": {"file": "...", "reference_count": 42, "pdf_complete": 40},
        "experiments": {"file": "...", "experiment_count": 156, "data_sources": 5},
        "framing": {"file": "...", "total_issues": 8, "critical": 2, "high": 3},
        "health": {"file": "...", "overall_score": 78.5, "readiness": "ready_with_revisions"}
    },
    "completed_at": "2025-03-27T...",
    "error": "..."  # if failed
}
```

## SECTION 4: PIPELINE USAGE

### `run_pipeline` Parameters
- `pipeline`: `"literature-review"` or `"full-setup"`
- `topic`: search topic (required for `"literature-review"`)
- `max_papers`: number of papers to process (default `5`)
- `source`: paper source (default `"arxiv"`)
- `skip_steps`: skip named steps (e.g. `"download"`, `"read"`, `"annotate"`)
- `stop_after`: execute through one step and stop (e.g. `"search"`)
- `dry_run`: preview planned steps only; no artifacts created
- `refs_dir`, `project_dir`: override directories when needed

### Examples
```python
run_pipeline(pipeline="literature-review", topic="transformer alignment", max_papers=5)
run_pipeline(pipeline="literature-review", topic="RAG evaluation", stop_after="search")
run_pipeline(pipeline="literature-review", topic="multimodal reasoning", skip_steps=["download", "read"])
run_pipeline(pipeline="full-setup", dry_run=True)
```

### Control Rules
- Use `stop_after` when user wants to review candidate papers before adding/downloading.
- Use `skip_steps` when prerequisites already exist (e.g. PDFs already present -> skip `download`; notes already present -> skip `annotate`).
- Use `dry_run` to preview workflow plan before running destructive or large operations.

## SECTION 4: ERROR RECOVERY

### Pipeline Failure Recovery
If `run_pipeline` returns `status="failed"` and `failed_step=X`, resume with atomic tools from step `X`:
- `search` failed -> retry `search_papers(query, max_results)`
- `add` failed -> run `add_reference(...)` for each selected paper
- `download` failed -> run `download_paper(paper_id)`
- `read` failed -> run `read_paper(paper_id)`
- `annotate` failed -> run `annotate_reference(key, ...)`
- `create_task` failed -> run `create_task(...)`

### Known External Failures
- arXiv rate limit/network issue: wait briefly, then retry `search_papers`; reduce `max_results` if repeated.
- GitHub CLI failure (`gh`): verify auth with `gh auth status`, then retry task tools.

### Recovery Operating Rule
Never restart from zero by default. Use `completed_steps` + `failed_step` from pipeline result to continue only missing steps.

## SECTION 5: CONVENTIONS

### Reference Conventions
- All references stored in `references/papers/{key}.yaml`
- BibTeX aggregated in `references/bibliography.bib`
- PDFs stored in `references/pdfs/{key}.pdf`
- Key format: `{first_author_surname}{year}-{keyword}` (e.g. `vaswani2017-attention`)

### Issue Label Conventions
- Phase: `phase:literature-review`, `phase:proposal`, `phase:experiment`, `phase:writing`, `phase:review`
- Type: `type:search`, `type:read`, `type:analysis`, `type:code`, `type:write`
- Priority: `priority:high`, `priority:medium`, `priority:low`
