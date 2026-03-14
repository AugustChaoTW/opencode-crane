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

## Core Tools

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

### Project Management
- `init_research` — Initialize repo as research project (labels, milestones, directories)
- `get_project_info` — Get project info (repo, branch, milestone stats, reference count)

## Research Workflow

### Standard Flow
1. `init_research` — Initialize project
2. `search_papers` → `add_reference` → `annotate_reference` — Build reference library
3. `create_task` — Plan tasks for each research phase
4. `report_progress` — Record findings during work
5. `close_task` — Complete tasks
6. `get_milestone_progress` — Track overall progress

### Literature Review Flow
1. Search papers with `search_papers`
2. Add important papers with `add_reference`
3. Download and read with `download_paper` + `read_paper`
4. Record notes with `annotate_reference`
5. Track reading tasks with `create_task`

### Reference Conventions
- All references stored in `references/papers/{key}.yaml`
- BibTeX aggregated in `references/bibliography.bib`
- PDFs stored in `references/pdfs/{key}.pdf`
- Key format: `{first_author_surname}{year}-{keyword}` (e.g. `vaswani2017-attention`)

### Issue Label Conventions
- Phase: `phase:literature-review`, `phase:proposal`, `phase:experiment`, `phase:writing`, `phase:review`
- Type: `type:search`, `type:read`, `type:analysis`, `type:code`, `type:write`
- Priority: `priority:high`, `priority:medium`, `priority:low`
