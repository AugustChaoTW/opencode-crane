"""crane_help — Natural language intent → CRANE tool lookup.

Allows Claude to resolve vague user requests ("do paper trace", "review my paper")
to the exact tool name + recommended parameters without guessing.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Intent → tool mapping
# Each entry: intent keywords (lowercase) → tool recommendation dict
# ---------------------------------------------------------------------------

_INTENT_MAP: list[tuple[list[str], dict[str, Any]]] = [
    # ── Paper Traceability ─────────────────────────────────────────────────
    (
        ["paper trace", "trace paper", "do paper trace", "paper track",
         "paper tracking", "traceability", "trace this", "整理這篇",
         "research trace", "lifecycle trace"],
        {
            "tool": "trace_paper",
            "description": "Trace a paper's complete research lifecycle (RQ→Contribution→Experiment→…).",
            "call": 'trace_paper(paper_path="<path/to/paper.tex>", mode="full")',
            "modes": ["full (default)", "init", "update", "status", "viz"],
            "output": "_paper_trace/v{n}/ with 10 YAML documents",
            "see_also": ["trace_add", "get_traceability_viz", "get_traceability_status"],
        },
    ),
    (
        ["trace status", "traceability status", "trace completeness"],
        {
            "tool": "trace_paper",
            "description": "Show research control chain completeness (read-only).",
            "call": 'trace_paper(paper_path="<path>", mode="status")',
            "see_also": ["get_traceability_status", "verify_traceability_chain"],
        },
    ),
    (
        ["trace visualization", "trace viz", "trace graph", "traceability graph"],
        {
            "tool": "get_traceability_viz",
            "description": "Generate Mermaid or DOT visualization of the trace chain.",
            "call": 'get_traceability_viz(paper_path="<path>", output_format="mermaid")',
            "see_also": ["trace_paper"],
        },
    ),
    # ── Paper Evaluation ───────────────────────────────────────────────────
    (
        ["evaluate paper", "score paper", "paper score", "rate paper",
         "7 dimension", "evidence evaluation", "paper quality",
         "evaluate my paper", "assess paper", "論文評分"],
        {
            "tool": "evaluate_paper_v2",
            "description": "7-dimension evidence scoring (methodology, novelty, evaluation, …).",
            "call": 'evaluate_paper_v2(paper_path="<path/to/paper.tex>")',
            "output": "overall_score (0-100), gates_passed, readiness, revision_plan",
            "prerequisite": 'check_prerequisites("evaluate_paper_v2")',
            "see_also": ["generate_revision_report", "crane_diagnose", "crane_review_full"],
        },
    ),
    (
        ["revision report", "revision plan", "generate report", "rewrite plan",
         "修改建議", "revision suggestions"],
        {
            "tool": "generate_revision_report",
            "description": "3-layer markdown report: scorecard + evidence + revision backlog.",
            "call": 'generate_revision_report(paper_path="<path>")',
            "see_also": ["evaluate_paper_v2"],
        },
    ),
    # ── Defect Detection ───────────────────────────────────────────────────
    (
        ["review paper", "defect", "full review", "detect defects",
         "pre-submission review", "critical issues", "crane review",
         "paper problems", "review full"],
        {
            "tool": "crane_review_full",
            "description": "Comprehensive defect detection: CRITICAL / MAJOR / MINOR.",
            "call": 'crane_review_full(paper_content="<latex content or leave blank>")',
            "output": "defect list by severity with fix-time estimates",
            "see_also": ["crane_diagnose", "evaluate_paper_v2"],
        },
    ),
    (
        ["diagnose paper", "diagnose section", "section diagnosis",
         "style diagnosis", "writing style check", "framing check",
         "論文診斷", "章節診斷"],
        {
            "tool": "crane_diagnose",
            "description": "Diagnose style/framing issues at paper or section scope.",
            "call": 'crane_diagnose(paper_path="<path>", journal_name="<journal>", scope="paper")',
            "modes": ["scope='paper' (default)", "scope='section' + section_name='<name>'"],
            "see_also": ["crane_review_full", "review_paper_sections"],
        },
    ),
    # ── Submission Pipeline ────────────────────────────────────────────────
    (
        ["submission check", "before submission", "投稿前檢查",
         "pre-submission", "submit check", "submission pipeline"],
        {
            "tool": "run_submission_check",
            "description": "4-step pre-submission check: literature + experiments + framing + health.",
            "call": 'run_submission_check(paper_path="<path>", project_dir="<root>")',
            "output": "BEFORE_SUBMISSION_RUN{n}/ with 4 report files",
            "tip": "Call build_paper_index first to speed up the paper parsing steps.",
            "see_also": ["crane_review_full", "simulate_submission_outcome"],
        },
    ),
    (
        ["simulate submission", "submission outcome", "acceptance probability",
         "rejection risk", "journal prediction", "投稿預測"],
        {
            "tool": "simulate_submission_outcome",
            "description": "Predict journal acceptance probability with scenario analysis.",
            "call": 'simulate_submission_outcome(paper_path="<path>", target_journal="<journal>")',
            "see_also": ["crane_assess_risk", "match_journal_v2"],
        },
    ),
    (
        ["risk assessment", "submission risk", "desk reject", "crane assess",
         "投稿風險"],
        {
            "tool": "crane_assess_risk",
            "description": "Assess desk-reject / reviewer / ethics / writing risk.",
            "call": "crane_assess_risk(desk_reject_score=75, reviewer_expectations_score=75, ...)",
            "see_also": ["simulate_submission_outcome"],
        },
    ),
    # ── Review Pipeline (v0.14.2) ──────────────────────────────────────────
    (
        ["review pipeline", "full paper review", "run review", "orchestrate review",
         "complete review", "end to end review", "build index and review"],
        {
            "tool": "run_review_pipeline",
            "description": "Orchestrated 4-step review: index → defect → evaluate → section.",
            "call": 'run_review_pipeline(paper_path="<path>", journal_name="<journal>")',
            "output": "Accumulated results in paper_index.yaml",
            "speed": "Fastest route — reuses index across all steps.",
            "see_also": ["build_paper_index", "evaluate_paper_v2", "crane_review_full"],
        },
    ),
    (
        ["build index", "paper index", "index paper", "scan paper",
         "快速掃描", "build paper index"],
        {
            "tool": "build_paper_index",
            "description": "Fast single-pass scan (grep/sed). Builds .{stem}_index.yaml. Cached by mtime.",
            "call": 'build_paper_index(paper_path="<path>")',
            "output": "structure, counts (words/figures/tables), flags, prescan keyword counts",
            "see_also": ["run_review_pipeline"],
        },
    ),
    # ── Journal Matching ───────────────────────────────────────────────────
    (
        ["match journal", "find journal", "journal recommendation",
         "which journal", "期刊推薦", "journal matching"],
        {
            "tool": "match_journal_v2",
            "description": "Match paper against Q1 journals; returns target/backup/safe recommendations.",
            "call": 'match_journal_v2(paper_path="<path>", budget_usd=3000)',
            "see_also": ["analyze_apc", "crane_journal_questionnaire"],
        },
    ),
    # ── Literature Search ──────────────────────────────────────────────────
    (
        ["search papers", "find papers", "arxiv search", "literature review",
         "搜尋論文", "文獻回顧", "survey"],
        {
            "tool": "run_pipeline",
            "description": "Multi-step literature-review pipeline: search→add→download→read→annotate.",
            "call": 'run_pipeline(pipeline="literature-review", topic="<topic>", max_papers=5)',
            "see_also": ["search_papers", "add_reference", "annotate_reference"],
        },
    ),
    (
        ["semantic search", "find similar", "similar papers", "embedding search",
         "語意搜尋", "相似論文"],
        {
            "tool": "semantic_search",
            "description": "Embedding-based similarity search. Requires embeddings built first.",
            "call": 'semantic_search(query="<topic>", k=5)',
            "anchor_mode": 'semantic_search(anchor_paper_key="<key>", k=5)',
            "prerequisite": 'check_prerequisites("semantic_search")  # ensures embeddings exist',
            "see_also": ["build_embeddings", "get_research_clusters"],
        },
    ),
    (
        ["build embeddings", "ollama embeddings", "local embeddings",
         "nomic embed", "embed papers", "embedding model"],
        {
            "tool": "build_embeddings",
            "description": "Build vector embeddings. Supports OpenAI and local Ollama (no API key).",
            "call": 'build_embeddings()',
            "ollama_call": 'build_embeddings(provider="ollama")  # uses nomic-embed-text locally',
            "ollama_custom": 'build_embeddings(provider="ollama", model="mxbai-embed-large")',
            "tip": "Ollama must be running: `ollama serve` + `ollama pull nomic-embed-text`",
            "see_also": ["semantic_search", "check_prerequisites"],
        },
    ),
    (
        ["ask library", "ask papers", "rag", "question answering",
         "what does paper say", "查詢文獻庫"],
        {
            "tool": "ask_library",
            "description": "RAG question-answering over chunked paper library.",
            "call": 'ask_library(question="<question>")',
            "prerequisite": 'check_prerequisites("ask_library")  # ensures chunks exist',
            "see_also": ["chunk_papers", "semantic_search"],
        },
    ),
    # ── Citation / Reference ───────────────────────────────────────────────
    (
        ["citation graph", "visualize citations", "citation network",
         "citation cluster", "引用圖", "citation visualization"],
        {
            "tool": "visualize_citations",
            "description": "Graph or cluster view of citation network.",
            "call": 'visualize_citations(mode="graph", output_format="mermaid")',
            "modes": ["mode='graph' + output_format='mermaid'|'figure'",
                      "mode='clusters' (always mermaid)"],
            "prerequisite": 'check_prerequisites("visualize_citations")',
            "see_also": ["build_embeddings", "get_research_clusters"],
        },
    ),
    # ── Karpathy Review ────────────────────────────────────────────────────
    (
        ["karpathy review", "code review", "experiment review",
         "karpathy principles"],
        {
            "tool": "karpathy_review",
            "description": "4-principle review: Think Before Coding, Simplicity First, Surgical, Goal-Driven.",
            "call": 'karpathy_review(code_path="<path>", description="<what this code does>")',
            "see_also": ["check_code_simplicity", "review_code_changes",
                         "plan_experiment_implementation"],
        },
    ),
    (
        ["simplicity check", "code simplicity", "check simplicity"],
        {
            "tool": "check_code_simplicity",
            "description": "Audit code for unnecessary complexity (Karpathy Simplicity First principle).",
            "call": 'check_code_simplicity(code_path="<path>")',
            "see_also": ["karpathy_review"],
        },
    ),
    # ── Workspace / Status ─────────────────────────────────────────────────
    (
        ["workspace status", "project status", "what can i do",
         "工作區狀態", "project overview", "crane status"],
        {
            "tool": "workspace_status",
            "description": "Workspace overview with capabilities, suggested_next_actions, references, tasks.",
            "call": "workspace_status()",
            "tip": "Use 'capabilities' field to see which advanced tools are ready to use.",
            "see_also": ["check_prerequisites", "list_workflows"],
        },
    ),
    (
        ["list workflows", "what workflows", "available workflows",
         "what can crane do", "crane capabilities", "help"],
        {
            "tool": "list_workflows",
            "description": "List all built-in research workflows with steps and estimated time.",
            "call": "list_workflows()",
            "see_also": ["workspace_status", "check_prerequisites"],
        },
    ),
    (
        ["chain coverage", "coverage report", "trace coverage", "chain completeness",
         "isolated nodes", "fix chain", "鏈條覆蓋率", "孤立節點修復"],
        {
            "tool": "get_chain_coverage",
            "description": (
                "Compute RQ→Experiment + Contribution→Evidence + Experiment→Figure "
                "coverage (0–1). Returns per-node breakdown and ready-to-run fix actions."
            ),
            "call": 'get_chain_coverage(paper_path="<path>")',
            "output": "chain_coverage, breakdown, isolated_nodes, suggested_actions",
            "see_also": ["verify_traceability_chain", "find_orphan_artifacts", "trace_add"],
        },
    ),
    (
        ["check prerequisites", "prerequisites", "ready to use",
         "is tool ready", "前置條件"],
        {
            "tool": "check_prerequisites",
            "description": "Check if a tool's required resources (embeddings, chunks, PDFs) are ready.",
            "call": 'check_prerequisites("semantic_search")',
            "see_also": ["workspace_status"],
        },
    ),
    # ── Init / Setup ───────────────────────────────────────────────────────
    (
        ["init project", "setup project", "initialize", "新增專案",
         "create project", "setup research"],
        {
            "tool": "run_pipeline",
            "description": "Full project setup: labels, milestones, directory structure.",
            "call": 'run_pipeline(pipeline="full-setup")',
            "see_also": ["init_research", "init_traceability"],
        },
    ),
]


def _lookup(topic: str) -> list[dict[str, Any]]:
    """Return matching tool recommendations for a natural language topic."""
    q = topic.lower().strip()
    matches = []
    for keywords, rec in _INTENT_MAP:
        if any(kw in q for kw in keywords):
            matches.append(rec)
    return matches


def register_tools(mcp):
    """Register crane_help tool with the MCP server."""

    @mcp.tool()
    def crane_help(topic: str = "") -> dict[str, Any]:
        """Resolve a natural language intent to CRANE tool recommendations.

        Call this whenever you are unsure which CRANE tool to use for a user request.
        Returns the exact tool name, call syntax, and related tools.

        Common topics:
            "paper trace"          → trace_paper
            "evaluate paper"       → evaluate_paper_v2
            "review paper"         → crane_review_full
            "submission check"     → run_submission_check
            "semantic search"      → semantic_search
            "build index"          → build_paper_index
            "review pipeline"      → run_review_pipeline
            "match journal"        → match_journal_v2
            "list workflows"       → list_workflows + workspace_status
            "karpathy review"      → karpathy_review

        Args:
            topic: Natural language description of what you want to do.
                   Examples: "do paper trace", "review my paper before submission",
                   "find similar papers", "what can crane do".

        Returns:
            {
                "topic": str,
                "matches": [
                    {
                        "tool": str,          # exact tool name
                        "description": str,
                        "call": str,          # ready-to-use call template
                        "prerequisite": str,  # check this first (if any)
                        "see_also": [str],    # related tools
                        ...
                    },
                    ...
                ],
                "tip": str
            }
        """
        if not topic:
            return {
                "topic": "",
                "matches": [],
                "tip": (
                    "Provide a topic string. Examples: 'paper trace', 'evaluate paper', "
                    "'submission check', 'semantic search'. "
                    "Or call list_workflows() to see all built-in pipelines, "
                    "or workspace_status() to see what is ready to use."
                ),
            }

        matches = _lookup(topic)

        if not matches:
            return {
                "topic": topic,
                "matches": [],
                "tip": (
                    f"No direct match for '{topic}'. Try: "
                    "list_workflows() for pipeline names, "
                    "workspace_status() for capability overview, "
                    "or check_prerequisites('<tool_name>') before running a tool."
                ),
            }

        return {
            "topic": topic,
            "matches": matches,
            "tip": (
                "Use the 'call' field as a template. "
                "Replace <path> with the actual paper path. "
                "Check 'prerequisite' if listed before running."
            ),
        }
