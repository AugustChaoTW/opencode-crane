---
name: opencode-crane
description: >
  CRANE — Autonomous research assistant MCP server with 124 tools covering
  the full academic research lifecycle. Key trigger phrases:
  "paper trace" / "do paper trace" → trace_paper;
  "evaluate paper" / "score paper" → evaluate_paper_v2;
  "review paper" / "detect defects" → crane_review_full;
  "diagnose paper" / "diagnose section" → crane_diagnose;
  "submission check" / "投稿前檢查" → run_submission_check;
  "simulate submission" / "acceptance probability" → simulate_submission_outcome;
  "review pipeline" / "full review" → run_review_pipeline;
  "build index" / "scan paper" → build_paper_index;
  "semantic search" / "find similar" → semantic_search;
  "ask library" / "rag" → ask_library;
  "match journal" → match_journal_v2;
  "citation graph" → visualize_citations;
  "karpathy review" / "code review" → karpathy_review;
  "literature review" / "search papers" → run_pipeline(pipeline="literature-review");
  "init project" / "setup" → run_pipeline(pipeline="full-setup");
  "what can crane do" / "help" → crane_help(topic=...) or list_workflows().
---

# CRANE — Autonomous Research Assistant

## QUICK START: Unsure which tool to use?

Call **`crane_help(topic="<your intent>")`** first. It maps natural language to the exact tool + parameters.

```python
crane_help("do paper trace")         # → trace_paper
crane_help("review my paper")        # → crane_review_full + evaluate_paper_v2
crane_help("submission check")       # → run_submission_check
crane_help("find similar papers")    # → semantic_search
crane_help("what can crane do")      # → lists all major workflows
```

Or call `list_workflows()` to see all built-in multi-step pipelines.
Or call `workspace_status()` to see what is ready to use in this project.

---

## SECTION 1: Trigger → Tool Mapping (Use This First)

### Paper Traceability

| User says | Tool | Call |
|---|---|---|
| "do paper trace" / "paper trace" / "trace this paper" / "整理這篇" | `trace_paper` | `trace_paper(paper_path="<path>", mode="full")` |
| "paper trace status" / "trace completeness" | `trace_paper` | `trace_paper(paper_path="<path>", mode="status")` |
| "trace viz" / "trace graph" | `get_traceability_viz` | `get_traceability_viz(paper_path="<path>", output_format="mermaid")` |
| add rq / add contribution / add experiment | `trace_add` | `trace_add(paper_path="<path>", item_type="rq", item_id="RQ1", data={...})` |

`trace_paper` creates `_paper_trace/v{n}/` with 10 YAML documents (RQ → Contribution → Experiment → Figure/Table → Citation → Risk → Dataset → Baseline → Artifact → Index).

### Paper Evaluation

| User says | Tool | Call |
|---|---|---|
| "evaluate paper" / "score paper" / "論文評分" | `evaluate_paper_v2` | `evaluate_paper_v2(paper_path="<path>")` |
| "revision report" / "修改建議" | `generate_revision_report` | `generate_revision_report(paper_path="<path>")` |
| "Feynman session" / "probing questions" | `generate_feynman_session` | `generate_feynman_session(paper_path="<path>")` |
| "match journal" / "期刊推薦" | `match_journal_v2` | `match_journal_v2(paper_path="<path>", budget_usd=3000)` |
| "APC cost" / "publication cost" | `analyze_apc` | `analyze_apc(paper_path="<path>")` |

### Defect Detection & Style

| User says | Tool | Call |
|---|---|---|
| "review paper" / "detect defects" / "full review" | `crane_review_full` | `crane_review_full(paper_content="<latex or blank>")` |
| "diagnose paper" / "論文診斷" | `crane_diagnose` | `crane_diagnose(paper_path="<path>", journal_name="<j>", scope="paper")` |
| "diagnose section" / "章節診斷" | `crane_diagnose` | `crane_diagnose(paper_path="<path>", journal_name="<j>", scope="section", section_name="<s>")` |
| "review sections" / "section issues" | `review_paper_sections` | `review_paper_sections(paper_path="<path>")` |

### Pre-Submission & Simulation

| User says | Tool | Call |
|---|---|---|
| "submission check" / "投稿前檢查" | `run_submission_check` | `run_submission_check(paper_path="<path>", project_dir="<root>")` |
| "simulate submission" / "acceptance probability" | `simulate_submission_outcome` | `simulate_submission_outcome(paper_path="<path>", target_journal="<j>")` |
| "submission risk" / "desk reject" | `crane_assess_risk` | `crane_assess_risk(desk_reject_score=75, ...)` |
| "generate cover letter" | `crane_generate_cover_letter` | `crane_generate_cover_letter(paper_path="<path>", journal_name="<j>")` |
| "submission checklist" | `generate_submission_checklist` | `generate_submission_checklist(paper_path="<path>")` |

### Paper Index & Review Pipeline (v0.14.2)

| User says | Tool | Call |
|---|---|---|
| "build index" / "scan paper" | `build_paper_index` | `build_paper_index(paper_path="<path>")` |
| "review pipeline" / "full paper review" | `run_review_pipeline` | `run_review_pipeline(paper_path="<path>", journal_name="<j>")` |

`run_review_pipeline` is the **fastest full review path**: builds index → crane_review_full → evaluate_paper_v2 → section_review. Each step reuses the index, no re-parsing.

### Literature & References

| User says | Tool | Call |
|---|---|---|
| "literature review" / "search papers" / "文獻回顧" | `run_pipeline` | `run_pipeline(pipeline="literature-review", topic="<topic>", max_papers=5)` |
| "search arxiv" | `search_papers` | `search_papers(query="<topic>", max_results=10)` |
| "add reference" | `add_reference` | `add_reference(paper_id="<arxiv_id>")` |
| "semantic search" / "find similar" / "語意搜尋" | `semantic_search` | `semantic_search(query="<topic>", k=5)` |
| "ask library" / "rag question" / "查詢文獻" | `ask_library` | `ask_library(question="<question>")` |
| "citation graph" / "visualize citations" | `visualize_citations` | `visualize_citations(mode="graph", output_format="mermaid")` |

### Karpathy Code Review

| User says | Tool | Call |
|---|---|---|
| "karpathy review" / "code review" | `karpathy_review` | `karpathy_review(code_path="<path>", description="<desc>")` |
| "simplicity check" / "code simplicity" | `check_code_simplicity` | `check_code_simplicity(code_path="<path>")` |
| "review code changes" | `review_code_changes` | `review_code_changes(diff_content="<diff>")` |
| "experiment plan" / "implementation plan" | `plan_experiment_implementation` | `plan_experiment_implementation(description="<desc>")` |
| "success criteria" | `define_experiment_success_criteria` | `define_experiment_success_criteria(experiment_description="<desc>")` |

### Workspace & Discovery

| User says | Tool | Call |
|---|---|---|
| "workspace status" / "project status" | `workspace_status` | `workspace_status()` |
| "list workflows" / "what can crane do" | `list_workflows` | `list_workflows()` |
| "check prerequisites" / "is tool ready" | `check_prerequisites` | `check_prerequisites("semantic_search")` |
| "help" / "which tool should I use" | `crane_help` | `crane_help(topic="<intent>")` |
| "init project" / "setup" | `run_pipeline` | `run_pipeline(pipeline="full-setup")` |

---

## SECTION 2: Prerequisite Guard

Before calling these tools, check prerequisites first — they will fail silently otherwise:

| Tool | Prerequisite | Fix |
|---|---|---|
| `semantic_search` | `embeddings.yaml` exists | `build_embeddings()` |
| `ask_library` | `chunks/` directory populated | `chunk_papers()` |
| `visualize_citations` | `embeddings.yaml` exists | `build_embeddings()` |
| `get_research_clusters` | `embeddings.yaml` exists | `build_embeddings()` |
| `evaluate_paper_v2` | Paper file (.tex/.pdf) exists | Confirm `paper_path` |
| `review_paper_sections` | Paper file (.tex/.pdf) exists | Confirm `paper_path` |

```python
# Quick pattern: always run this before advanced tools
check_prerequisites("semantic_search")   # returns {"ready": true/false, "missing": [...]}
```

---

## SECTION 3: Paper Traceability Workflow (trace_paper)

### What it does
Creates `_paper_trace/v{n}/` co-located with the paper. Contains 10 YAML files:

```
_paper_trace/v1/
├── 1_research_context.yaml      ← RQ, hypothesis, scope
├── 2_contribution_claims.yaml   ← novelty claims + evidence links
├── 3_experiment_log.yaml        ← experiments + results
├── 4_figure_table_registry.yaml ← figures/tables + captions
├── 5_citation_index.yaml        ← citation rationale
├── 6_change_impact_log.yaml     ← tracked changes
├── 7_reviewer_risk.yaml         ← anticipated reviewer objections
├── 8_limitation_log.yaml        ← acknowledged limitations
├── 9_dataset_baseline.yaml      ← datasets + baselines
└── 10_artifact_inventory.yaml   ← code/data/model artifacts
```

### Trigger phrase → mode mapping

```python
"do paper trace"      → trace_paper(mode="full")     # init + infer all
"init trace"          → trace_paper(mode="init")      # blank templates only
"update trace"        → trace_paper(mode="update")    # add/edit items
"trace status"        → trace_paper(mode="status")    # read-only completeness
"trace viz"           → trace_paper(mode="viz")       # Mermaid + DOT
```

### Adding items to existing trace
```python
trace_add(paper_path="<path>", item_type="rq",           item_id="RQ1",  data={"text": "..."})
trace_add(paper_path="<path>", item_type="contribution",  item_id="C1",   data={"claim": "..."})
trace_add(paper_path="<path>", item_type="experiment",    item_id="E1",   data={"name": "..."})
trace_add(paper_path="<path>", item_type="figure_table",  item_id="F1",   data={"caption": "..."})
trace_add(paper_path="<path>", item_type="reference",     item_id="R1",   data={"key": "..."})
trace_add(paper_path="<path>", item_type="risk",          item_id="RK1",  data={"concern": "..."})
trace_add(paper_path="<path>", item_type="dataset",       item_id="D1",   data={"name": "..."})
trace_add(paper_path="<path>", item_type="baseline",      item_id="B1",   data={"name": "..."})
```

---

## SECTION 4: Complete Pre-Submission Workflow

### Fastest path (v0.14.2+)
```python
# Step 1: build index once (Linux scan, <1s, cached)
build_paper_index(paper_path="papers/main.tex")

# Step 2: orchestrated review (reuses index, ~10-15s total)
run_review_pipeline(paper_path="papers/main.tex", journal_name="Nature")
```

### Full path (maximum detail)
```python
# 1. Paper trace
trace_paper(paper_path="papers/main.tex", mode="full")

# 2. Evaluate (7-dimension scoring)
evaluate_paper_v2(paper_path="papers/main.tex")

# 3. Defect detection
crane_review_full()  # reads from project_dir

# 4. Style diagnosis
crane_diagnose(paper_path="papers/main.tex", journal_name="Nature", scope="paper")

# 5. Journal match
match_journal_v2(paper_path="papers/main.tex", budget_usd=3000)

# 6. Simulate submission
simulate_submission_outcome(paper_path="papers/main.tex", target_journal="Nature")

# 7. Submission check (generates BEFORE_SUBMISSION_RUN{n}/)
run_submission_check(paper_path="papers/main.tex", project_dir=".")
```

---

## SECTION 5: Literature Review Pipeline

```python
# Full automatic pipeline
run_pipeline(pipeline="literature-review", topic="transformer alignment", max_papers=5)

# Step-by-step control
run_pipeline(pipeline="literature-review", topic="RAG evaluation", stop_after="search")
run_pipeline(pipeline="literature-review", topic="multimodal", skip_steps=["download", "read"])
run_pipeline(pipeline="full-setup", dry_run=True)
```

After literature is added:
```python
build_embeddings()                                    # enable semantic search
chunk_papers()                                        # enable ask_library
semantic_search(query="attention mechanism", k=5)    # find similar papers
ask_library(question="What methods improve robustness?")
visualize_citations(mode="clusters", output_format="mermaid")
```

---

## SECTION 6: Tool Inventory by Category

### Discovery & Help (call these first)
- `crane_help(topic)` — natural language → tool lookup
- `list_workflows()` — all built-in pipelines with steps + time estimates
- `workspace_status()` — capabilities, suggested_next_actions, reference count
- `check_prerequisites(tool_name)` — readiness check before running a tool

### Paper Traceability (Paper Trace System)
- `trace_paper(paper_path, mode)` — master entry: creates _paper_trace/v{n}/
- `trace_add(paper_path, item_type, item_id, data)` — add rq/contribution/experiment/…
- `init_traceability(paper_path)` — initialize traceability for a paper
- `get_traceability_status(paper_path)` — show chain completeness
- `get_traceability_viz(paper_path, output_format)` — Mermaid/DOT visualization
- `verify_traceability_chain(paper_path)` — validate all links
- `diff_trace_versions(paper_path)` — compare v{n} vs v{n-1}

### Paper Evaluation
- `evaluate_paper_v2(paper_path, mode)` — 7-dimension evidence scoring
- `match_journal_v2(paper_path, budget_usd)` — Q1 journal matching
- `analyze_apc(paper_path)` — APC cost analysis
- `generate_revision_report(paper_path)` — 3-layer revision report
- `generate_feynman_session(paper_path)` — probing questions for weak dimensions
- `evaluate_q1_standards(paper_path)` — Q1 readiness assessment

### Defect Detection & Style
- `crane_review_full(paper_content)` — CRITICAL/MAJOR/MINOR defect detection
- `crane_diagnose(paper_path, journal_name, scope)` — style/framing diagnosis
- `review_paper_sections(paper_path, sections, review_types)` — section-level issues
- `parse_paper_structure(paper_path)` — parse LaTeX structure

### Pre-Submission
- `run_submission_check(paper_path, project_dir)` — 4-step pre-submission pipeline
- `simulate_submission_outcome(paper_path, target_journal, num_scenarios)` — acceptance prediction
- `crane_assess_risk(...)` — 4-dimension risk assessment
- `generate_submission_checklist(paper_path)` — submission checklist
- `crane_generate_cover_letter(paper_path, journal_name)` — cover letter

### Paper Index (v0.14.2)
- `build_paper_index(paper_path, force)` — fast Linux scan → cached index
- `run_review_pipeline(paper_path, journal_name)` — orchestrated review pipeline

### Literature & References
- `run_pipeline(pipeline, topic, max_papers)` — multi-step literature pipeline
- `search_papers(query, max_results, source)` — arXiv/Semantic Scholar search
- `download_paper(paper_id)` — download PDF
- `read_paper(paper_id)` — extract full text
- `add_reference(paper_id)` — add to references/
- `list_references(filter)` — list references
- `get_reference(key)` — get one reference
- `annotate_reference(key, ...)` — AI annotations
- `remove_reference(key)` — remove reference
- `search_references(query)` — full-text search
- `screen_reference(key, decision)` — PICOS screening
- `compare_papers(keys)` — comparison matrix
- `check_citations(manuscript_path)` — validate \cite{} keys
- `verify_reference(key, ...)` — verify metadata
- `check_all_references()` — batch metadata check

### Semantic Search & RAG
- `semantic_search(query, anchor_paper_key, k)` — embedding-based search
- `build_embeddings()` — build embedding index
- `ask_library(question)` — RAG over chunked papers
- `chunk_papers()` — chunk PDFs for RAG
- `get_chunk_stats()` — chunking statistics

### Citation Graph
- `visualize_citations(mode, output_format, k_clusters)` — graph/cluster visualization
- `build_citation_graph()` — build graph structure
- `get_research_clusters(k)` — cluster papers by topic
- `find_citation_gaps()` — find missing important citations

### Karpathy Code Review
- `karpathy_review(code_path, description)` — 4-principle composite review
- `plan_experiment_implementation(description)` — think-before-coding
- `check_code_simplicity(code_path)` — simplicity audit
- `review_code_changes(diff_content)` — surgical change review
- `define_experiment_success_criteria(description)` — verifiable goals

### Journal Strategy & Style
- `crane_journal_setup(journal_name)` — journal style setup
- `crane_journal_questionnaire(paper_path)` — journal fit questionnaire
- `crane_extract_journal_style_guide(journal_name)` — extract style rules
- `crane_get_style_exemplars(journal_name)` — get exemplar sentences
- `crane_start_rewrite_session(paper_path, journal_name)` — guided rewrite
- `crane_suggest_rewrites(session_id)` — suggest rewrites
- `crane_submit_rewrite_choice(session_id, choice)` — accept/reject rewrite
- `crane_coach_chapter(paper_path, chapter)` — chapter-level coaching
- `crane_compare_sections(paper_path)` — compare section quality

### Task Management (GitHub Issues)
- `create_task(title, phase, type, priority)` — create research task
- `list_tasks(phase, state, milestone)` — list tasks
- `view_task(task_id)` — view task details
- `update_task(task_id, ...)` — update labels/milestone
- `report_progress(task_id, message)` — post progress comment
- `close_task(task_id, reason)` — complete task
- `get_milestone_progress()` — phase statistics

### Session & Memory
- `create_session(name)` / `load_session(id)` / `save_session(id)` / `delete_session(id)` / `list_sessions()`
- `add_agent_memory(content)` / `get_agent_memory(query)` / `clear_agent_memory()`

### Transport & Connectivity
- `transport_control(transport, action, host, port)` — sse/bridge lifecycle (start/stop/status)
- `broadcast_sse_event(event)` — broadcast to SSE clients
- `generate_bridge_jwt(secret)` — generate JWT for bridge

### CRANE Maintenance
- `check_crane_version()` — check for updates
- `upgrade_crane()` — upgrade to latest version
- `rollback_crane(version)` — rollback to previous version

---

## SECTION 7: Common Patterns

### Pattern 1: First time using CRANE in a project
```python
workspace_status()           # see what's available
run_pipeline(pipeline="full-setup")   # if not initialized
```

### Pattern 2: Start a paper trace session
```python
trace_paper(paper_path="paper/main.tex", mode="full")
# Then check what was inferred:
trace_paper(paper_path="paper/main.tex", mode="status")
```

### Pattern 3: Quick paper review before deadline
```python
build_paper_index(paper_path="paper/main.tex")          # <1s
run_review_pipeline(paper_path="paper/main.tex")         # ~10-15s, reuses index
```

### Pattern 4: Semantic literature exploration
```python
check_prerequisites("semantic_search")   # check embeddings
build_embeddings()                        # if not ready
semantic_search(query="contrastive learning for NLP", k=10)
ask_library(question="Which papers discuss data augmentation?")
visualize_citations(mode="clusters")
```

### Pattern 5: Full submission preparation
```python
evaluate_paper_v2(paper_path="paper/main.tex")
crane_diagnose(paper_path="paper/main.tex", journal_name="ACL", scope="paper")
simulate_submission_outcome(paper_path="paper/main.tex", target_journal="ACL")
run_submission_check(paper_path="paper/main.tex", project_dir=".")
```

---

## SECTION 8: Error Recovery

### Tool returns error / not ready
```python
check_prerequisites("semantic_search")  # → {"ready": false, "missing": [{"name": "embeddings", "fix_with": "build_embeddings"}]}
build_embeddings()  # fix it, then retry
```

### Pipeline fails midway
If `run_pipeline` returns `status="failed"` with `failed_step`, resume from that step with atomic tools.
If `run_submission_check` fails on one checkpoint, the output dir still has completed reports.

### MCP server needs restart (tools not found)
If a tool listed here is not available in the deferred list, the MCP server may need to restart (`upgrade_crane()` or restart OpenCode).
