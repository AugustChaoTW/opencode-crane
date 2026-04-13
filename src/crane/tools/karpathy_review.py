"""Karpathy Coding Review tools.

Exposes CRANE's KarpathyReviewService as MCP tools so an LLM agent can
apply Andrej Karpathy's four software-development principles to its own
generated code and experiment plans.

  1. Think Before Coding  — plan_experiment_implementation
  2. Simplicity First     — check_code_simplicity
  3. Surgical Changes     — review_code_changes
  4. Goal-Driven Execution — define_experiment_success_criteria
  5. Combined             — karpathy_review
"""

from __future__ import annotations

from typing import Any

from crane.services.karpathy_review_service import KarpathyReviewService


def register_tools(mcp: Any) -> None:
    """Register Karpathy review tools with the MCP server."""

    svc = KarpathyReviewService()

    # -----------------------------------------------------------------------
    # Tool 1: plan_experiment_implementation  (Principle 1 — Think Before Coding)
    # -----------------------------------------------------------------------

    @mcp.tool()
    def plan_experiment_implementation(
        task: str,
        existing_code_summary: str = "",
    ) -> dict[str, Any]:
        """Generate an explicit pre-coding plan for an experiment or implementation task.

        Karpathy Principle 1: Think Before Coding.
        Surfaces assumptions, alternative interpretations, simpler alternatives,
        and clarifying questions so that LLM agents stop and reason *before*
        they write code.

        Args:
            task:                   Description of what needs to be implemented.
            existing_code_summary:  Brief description of relevant existing code
                                    (helps detect potential duplication).

        Returns:
            Dict with:
              - task: echoed task description
              - assumptions: list of implicit assumptions that should be confirmed
              - interpretations: narrow vs broad reading of the task
              - simpler_alternatives: ideas for simpler solutions
              - success_criteria: verifiable conditions for "done"
              - checkpoints: ordered milestones (confirm → test → implement → check)
              - clarifying_questions: questions to ask before writing code
        """
        plan = svc.plan_before_coding(task=task, existing_code_summary=existing_code_summary)
        return {
            "task": plan.task,
            "assumptions": plan.assumptions,
            "interpretations": plan.interpretations,
            "simpler_alternatives": plan.simpler_alternatives,
            "success_criteria": plan.success_criteria,
            "checkpoints": plan.checkpoints,
            "clarifying_questions": plan.clarifying_questions,
        }

    # -----------------------------------------------------------------------
    # Tool 2: check_code_simplicity  (Principle 2 — Simplicity First)
    # -----------------------------------------------------------------------

    @mcp.tool()
    def check_code_simplicity(
        code: str,
        context: str = "",
    ) -> dict[str, Any]:
        """Review code for unnecessary complexity against the Simplicity First principle.

        Karpathy Principle 2: Simplicity First.
        Flags over-engineering, speculative abstractions, deep nesting, dead code,
        and files that are too long for a single responsibility.

        Args:
            code:    Python source code to review.
            context: Optional one-sentence description of what the code is supposed to do.

        Returns:
            Dict with:
              - passed: True if score ≥ 70
              - score: 0-100 (100 = no issues found)
              - violations: list of {principle, severity, message, line_hint, suggestion}
              - summary: human-readable verdict
              - recommendations: list of actionable suggestions
        """
        result = svc.check_code_simplicity(code=code, context=context)
        return {
            "passed": result.passed,
            "score": result.score,
            "violations": [
                {
                    "principle": v.principle,
                    "severity": v.severity,
                    "message": v.message,
                    "line_hint": v.line_hint,
                    "suggestion": v.suggestion,
                }
                for v in result.violations
            ],
            "summary": result.summary,
            "recommendations": result.recommendations,
        }

    # -----------------------------------------------------------------------
    # Tool 3: review_code_changes  (Principle 3 — Surgical Changes)
    # -----------------------------------------------------------------------

    @mcp.tool()
    def review_code_changes(
        original: str,
        modified: str,
        stated_goal: str = "",
    ) -> dict[str, Any]:
        """Verify that code changes are minimal and on-target (surgical).

        Karpathy Principle 3: Surgical Changes.
        Detects scope creep by counting diff hunks, changed lines, and whitespace-only
        reformatting that had nothing to do with the stated goal.

        Args:
            original:    Original source code before the change.
            modified:    Modified source code after the change.
            stated_goal: What the change was supposed to accomplish (used in summary).

        Returns:
            Dict with:
              - passed: True if changes appear targeted
              - score: 0-100
              - violations: list of surgical-change violations
              - summary: narrative verdict including hunk/line counts
              - recommendations: how to tighten the change set
        """
        result = svc.review_code_changes(
            original=original, modified=modified, stated_goal=stated_goal
        )
        return {
            "passed": result.passed,
            "score": result.score,
            "violations": [
                {
                    "principle": v.principle,
                    "severity": v.severity,
                    "message": v.message,
                    "line_hint": v.line_hint,
                    "suggestion": v.suggestion,
                }
                for v in result.violations
            ],
            "summary": result.summary,
            "recommendations": result.recommendations,
        }

    # -----------------------------------------------------------------------
    # Tool 4: define_experiment_success_criteria  (Principle 4 — Goal-Driven Execution)
    # -----------------------------------------------------------------------

    @mcp.tool()
    def define_experiment_success_criteria(
        goal: str,
        domain: str = "experiment",
    ) -> dict[str, Any]:
        """Convert a vague research goal into verifiable, measurable success criteria.

        Karpathy Principle 4: Goal-Driven Execution.
        Stops LLMs from starting work without a clear "done" condition.
        Returns concrete criteria, metrics, anti-goals, and verification steps.

        Args:
            goal:   The vague goal (e.g., "improve accuracy on AffectCorpus").
            domain: Context type — one of "experiment" | "paper" | "code" | "review".
                    Selects domain-appropriate structural criteria and verification steps.

        Returns:
            Dict with:
              - goal: echoed goal
              - criteria: concrete, measurable pass/fail conditions
              - metrics: specific metrics with thresholds to fill in
              - anti_goals: explicit constraints (do NOT do X)
              - verification_steps: ordered steps to confirm the goal was met
        """
        sc = svc.define_success_criteria(goal=goal, domain=domain)
        return {
            "goal": sc.goal,
            "criteria": sc.criteria,
            "metrics": sc.metrics,
            "anti_goals": sc.anti_goals,
            "verification_steps": sc.verification_steps,
        }

    # -----------------------------------------------------------------------
    # Tool 5: karpathy_review  (all 4 principles combined)
    # -----------------------------------------------------------------------

    @mcp.tool()
    def karpathy_review(
        code: str,
        original_code: str = "",
        stated_goal: str = "",
        domain: str = "experiment",
    ) -> dict[str, Any]:
        """Run all applicable Karpathy checks and return a unified report.

        Applies all four Karpathy principles to a code snapshot (or code diff):
          1. Think Before Coding  — plans are surfaced as a reminder
          2. Simplicity First     — checks for over-engineering
          3. Surgical Changes     — checks if original_code is provided
          4. Goal-Driven Execution — converts the stated_goal into success criteria

        Args:
            code:          Code to review (the "after" version if comparing).
            original_code: Original code before changes. When provided, enables the
                           Surgical Changes (Principle 3) check.
            stated_goal:   What the code / change is supposed to accomplish.
            domain:        "experiment" | "paper" | "code" | "review" — used for
                           domain-specific success criteria (Principle 4).

        Returns:
            Dict with:
              - stated_goal: echoed
              - domain: echoed
              - overall_passed: True only when ALL applicable checks pass
              - overall_score: weighted average of individual scores (0-100)
              - simplicity: full check_code_simplicity result
              - surgical: full review_code_changes result (null when original_code is empty)
              - success_criteria: define_experiment_success_criteria result
              - summary: high-level human-readable verdict
        """
        result = svc.karpathy_review(
            code=code,
            original_code=original_code,
            stated_goal=stated_goal,
            domain=domain,
        )
        return result
