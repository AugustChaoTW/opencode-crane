"""Karpathy Coding Review Service.

Applies four principles from Andrej Karpathy's critique of LLM coding habits
to research experiment code generated or modified within CRANE:

  1. Think Before Coding  — surface assumptions and ambiguities before writing
  2. Simplicity First     — flag over-engineering, unused abstractions
  3. Surgical Changes     — detect unnecessary edits beyond the stated scope
  4. Goal-Driven Execution — convert vague goals into verifiable success criteria
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import unified_diff
from typing import Any

# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class PrincipleViolation:
    principle: str  # "simplicity" | "surgical" | "think" | "goal"
    severity: str  # "low" | "medium" | "high"
    message: str
    line_hint: int | None = None
    suggestion: str = ""


@dataclass
class KarpathyReviewResult:
    passed: bool
    violations: list[PrincipleViolation] = field(default_factory=list)
    score: int = 100  # starts at 100, deducted per violation
    summary: str = ""
    recommendations: list[str] = field(default_factory=list)


@dataclass
class SuccessCriteria:
    goal: str
    criteria: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    anti_goals: list[str] = field(default_factory=list)
    verification_steps: list[str] = field(default_factory=list)


@dataclass
class ImplementationPlan:
    task: str
    assumptions: list[str] = field(default_factory=list)
    interpretations: list[str] = field(default_factory=list)
    simpler_alternatives: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    checkpoints: list[str] = field(default_factory=list)
    clarifying_questions: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Simplicity heuristics
# ---------------------------------------------------------------------------

_COMPLEXITY_PATTERNS: list[tuple[str, str, str]] = [
    # (regex, severity, message)
    (r"\bNotImplementedError\b", "medium", "Stub/placeholder left in production code"),
    (r"#\s*TODO|#\s*FIXME|#\s*HACK", "low", "TODO/FIXME comment — unresolved technical debt"),
    (r"class\s+\w+\(ABC\)", "medium", "Abstract base class — may be premature abstraction"),
    (r"@abstractmethod", "medium", "Abstract method — verify interface is actually needed"),
    (
        r"isinstance\(.*,\s*\(",
        "low",
        "isinstance with tuple — consider single-dispatch or simpler type",
    ),
    (r"lambda\s+\w+.*lambda", "medium", "Nested lambdas — use named functions for clarity"),
    (
        r"(\w+\s*=\s*\w+\s*if\s*\w+\s*else\s*\w+){3,}",
        "medium",
        "Chain of ternaries — consider lookup dict or function",
    ),
    (
        r"try:.*except\s+Exception\s*:",
        "low",
        "Bare except Exception — catching too broadly",
    ),
    (r"def\s+\w+\([^)]{120,}\)", "medium", "Function signature > 120 chars — too many parameters"),
    (r"if\s+True\b|if\s+False\b", "high", "Hardcoded boolean condition — dead code"),
    (r"pass\s*$", "low", "Empty pass block — may indicate incomplete implementation"),
    (r"global\s+\w+", "medium", "Global variable — prefer passing state explicitly"),
    (r"eval\(|exec\(", "high", "eval/exec — unsafe and unnecessary in almost all research code"),
    (r"import\s+\*", "high", "Star import — pollutes namespace, hides dependencies"),
    (r"(\s{4}){6,}", "low", "Deep nesting (6+ levels) — extract to function"),
]

_SPECULATIVE_PATTERNS: list[tuple[str, str]] = [
    # (pattern, description)
    (
        r"future|extensi|plugin|hook|callback|middleware|registry|factory|strategy",
        "Speculative extensibility keyword",
    ),
    (r"config\s*=\s*\{[^}]{200,}\}", "Large config dict — may be over-configurable"),
    (
        r"Optional\[.*\].*=\s*None.*Optional\[.*\].*=\s*None.*Optional\[.*\].*=\s*None",
        "Three or more Optional params — likely over-flexible API",
    ),
]


# ---------------------------------------------------------------------------
# Surgical-changes heuristics (diff analysis)
# ---------------------------------------------------------------------------


def _count_diff_hunks(original: str, modified: str) -> int:
    diff = list(unified_diff(original.splitlines(), modified.splitlines(), lineterm=""))
    return sum(1 for line in diff if line.startswith("@@"))


def _changed_line_count(original: str, modified: str) -> int:
    diff = list(unified_diff(original.splitlines(), modified.splitlines(), lineterm=""))
    return sum(
        1 for line in diff if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    )


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------


class KarpathyReviewService:
    """Apply Karpathy's four coding principles to research experiment code."""

    _SEVERITY_DEDUCTION = {"low": 5, "medium": 15, "high": 25}

    # ------------------------------------------------------------------
    # Principle 2: Simplicity First
    # ------------------------------------------------------------------

    def check_code_simplicity(
        self,
        code: str,
        context: str = "",
    ) -> KarpathyReviewResult:
        """Check code against the Simplicity First principle.

        Flags: unnecessary abstractions, speculative extensibility,
        deep nesting, unsafe patterns, dead code.

        Args:
            code:    Source code to review (Python preferred)
            context: Optional description of what the code is supposed to do

        Returns:
            KarpathyReviewResult with violations and score (100 = perfect).
        """
        violations: list[PrincipleViolation] = []

        lines = code.splitlines()
        for i, line in enumerate(lines, 1):
            for pattern, severity, message in _COMPLEXITY_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append(
                        PrincipleViolation(
                            principle="simplicity",
                            severity=severity,
                            message=message,
                            line_hint=i,
                            suggestion="Remove or simplify. Ask: is this complexity solving the stated problem?",
                        )
                    )
                    break  # one violation per line

        # Speculative patterns (whole-code scan)
        for pattern, desc in _SPECULATIVE_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                violations.append(
                    PrincipleViolation(
                        principle="simplicity",
                        severity="medium",
                        message=f"Possibly speculative: {desc}",
                        suggestion="Only add flexibility when there is a concrete, immediate need.",
                    )
                )

        # Line count heuristic
        loc = len([l for l in lines if l.strip() and not l.strip().startswith("#")])
        if loc > 300:
            violations.append(
                PrincipleViolation(
                    principle="simplicity",
                    severity="medium",
                    message=f"Code is {loc} non-comment lines — consider splitting into smaller units",
                    suggestion="Each function / class should have a single clear responsibility.",
                )
            )

        score = self._compute_score(violations)
        passed = score >= 70
        recs = self._simplicity_recommendations(violations)

        return KarpathyReviewResult(
            passed=passed,
            violations=violations,
            score=score,
            summary=self._simplicity_summary(score, violations, context),
            recommendations=recs,
        )

    # ------------------------------------------------------------------
    # Principle 3: Surgical Changes
    # ------------------------------------------------------------------

    def review_code_changes(
        self,
        original: str,
        modified: str,
        stated_goal: str = "",
    ) -> KarpathyReviewResult:
        """Review whether code changes are surgical (minimal and on-target).

        Flags: large hunks unrelated to stated goal, whitespace-only changes,
        reformatting of unchanged logic.

        Args:
            original:    Original source code
            modified:    Modified source code
            stated_goal: What the change was supposed to accomplish

        Returns:
            KarpathyReviewResult with surgical-change assessment.
        """
        violations: list[PrincipleViolation] = []

        hunks = _count_diff_hunks(original, modified)
        changed = _changed_line_count(original, modified)

        if changed == 0:
            return KarpathyReviewResult(
                passed=True,
                score=100,
                summary="No changes detected.",
                recommendations=[],
            )

        if hunks > 10:
            violations.append(
                PrincipleViolation(
                    principle="surgical",
                    severity="high",
                    message=f"Change spans {hunks} diff hunks — likely touches unrelated code",
                    suggestion="Split into separate commits: one per logical concern.",
                )
            )
        elif hunks > 5:
            violations.append(
                PrincipleViolation(
                    principle="surgical",
                    severity="medium",
                    message=f"Change spans {hunks} diff hunks — review for scope creep",
                    suggestion="Ensure every hunk is necessary for the stated goal.",
                )
            )

        if changed > 150:
            violations.append(
                PrincipleViolation(
                    principle="surgical",
                    severity="high",
                    message=f"{changed} lines changed — unusually large for a single task",
                    suggestion="Break into smaller, incremental commits.",
                )
            )

        # Detect whitespace-only hunks (reformatting)
        diff_lines = list(unified_diff(original.splitlines(), modified.splitlines(), lineterm=""))
        whitespace_only = sum(
            1
            for l in diff_lines
            if l.startswith(("+", "-")) and not l.startswith(("+++", "---")) and l[1:].strip() == ""
        )
        if whitespace_only > 10:
            violations.append(
                PrincipleViolation(
                    principle="surgical",
                    severity="low",
                    message=f"{whitespace_only} whitespace-only line changes — possible reformatting",
                    suggestion="Avoid reformatting lines you did not need to change.",
                )
            )

        score = self._compute_score(violations)
        passed = score >= 70

        summary_parts = [
            f"{changed} lines changed across {hunks} hunks.",
        ]
        if stated_goal:
            summary_parts.append(f"Stated goal: {stated_goal}")
        if passed:
            summary_parts.append("Changes appear surgical.")
        else:
            summary_parts.append("Changes may exceed the stated scope.")

        return KarpathyReviewResult(
            passed=passed,
            violations=violations,
            score=score,
            summary=" ".join(summary_parts),
            recommendations=[v.suggestion for v in violations],
        )

    # ------------------------------------------------------------------
    # Principle 4: Goal-Driven Execution
    # ------------------------------------------------------------------

    def define_success_criteria(
        self,
        goal: str,
        domain: str = "experiment",
    ) -> SuccessCriteria:
        """Convert a vague research goal into verifiable success criteria.

        Args:
            goal:   The vague goal (e.g., "improve accuracy on AffectCorpus")
            domain: "experiment" | "paper" | "code" | "review"

        Returns:
            SuccessCriteria with concrete, measurable criteria.
        """
        criteria = SuccessCriteria(goal=goal)

        # Heuristic: detect metrics mentioned in goal
        metric_patterns = {
            r"accurac": "Accuracy ≥ X% (specify the threshold before running)",
            r"f1|f-1|f score": "F1 ≥ X (macro/micro — specify which)",
            r"loss": "Loss < X after Y epochs (specify both)",
            r"latenc|speed|throughput": "Latency < Xms (p50 and p99 — specify percentile)",
            r"baseline|outperform": "Improvement > X% over named baseline (specify baseline version)",
            r"ablat": "Each ablated component shows ≥ Y% degradation when removed",
            r"reprod": "Results within ±2σ of reported numbers across 3 seeds",
        }

        for pattern, criterion in metric_patterns.items():
            if re.search(pattern, goal, re.IGNORECASE):
                criteria.criteria.append(criterion)

        # Always add structural criteria
        if domain == "experiment":
            criteria.criteria += [
                "Experiment completes without error on the target hardware",
                "All random seeds are fixed and logged",
                "Results are saved to a versioned output file",
            ]
            criteria.metrics += [
                "Primary metric: (fill in before running)",
                "Secondary metric: (fill in before running)",
                "Baseline for comparison: (fill in before running)",
            ]
            criteria.anti_goals += [
                "Do NOT change the dataset split",
                "Do NOT modify the baseline implementation",
                "Do NOT add new hyperparameters unless stated",
            ]
            criteria.verification_steps += [
                "1. Run with a tiny subset first to verify no crashes",
                "2. Check that output file was created and is non-empty",
                "3. Verify primary metric is within expected range",
                "4. Compare against baseline number recorded in experiment log",
            ]
        elif domain == "paper":
            criteria.criteria += [
                "All claimed numbers appear in at least one figure or table",
                "Every contribution in Section 1 is supported by ≥1 experiment",
                "No inline number differs from its source figure/table by > 0.1%",
            ]
            criteria.verification_steps += [
                "1. Run verify_traceability_chain() — all links must resolve",
                "2. Run get_pending_changes() — must return 0 pending items",
                "3. Run review_paper_sections() — no critical issues",
            ]
        elif domain == "code":
            criteria.criteria += [
                "All existing tests still pass",
                "New behavior is covered by at least one new test",
                "Ruff check reports no new violations",
                "Tool count in server.py is unchanged (or incremented by the expected delta)",
            ]
            criteria.verification_steps += [
                "1. uv run pytest tests/ -m 'not integration' -q",
                "2. uv run ruff check src/ tests/",
                "3. uv run python -c 'from crane.server import mcp; print(len(mcp._tool_manager._tools))'",
            ]

        return criteria

    # ------------------------------------------------------------------
    # Principle 1: Think Before Coding
    # ------------------------------------------------------------------

    def plan_before_coding(
        self,
        task: str,
        existing_code_summary: str = "",
    ) -> ImplementationPlan:
        """Generate an explicit pre-coding plan for a task.

        Surfaces assumptions, alternative interpretations, simpler alternatives,
        and clarifying questions before any code is written.

        Args:
            task:                   Description of the task to implement
            existing_code_summary:  Brief description of relevant existing code

        Returns:
            ImplementationPlan with assumptions, interpretations, and checkpoints.
        """
        plan = ImplementationPlan(task=task)

        # Generic assumptions (always applicable)
        plan.assumptions = [
            "Existing tests continue to pass after this change",
            "The change does not alter any public API unless explicitly stated",
            "Input validation follows the existing pattern in this codebase",
            "No new external dependencies are introduced",
        ]

        # Detect scope signals in task description
        scope_signals = {
            r"add\s+\w+\s+tool": "New tool registration requires updating server.py and install.sh EXPECTED_TOOLS",
            r"new\s+service": "New service lives in src/crane/services/ and needs tests in tests/services/",
            r"refactor": "Refactor should not change observable behavior — test before and after",
            r"fix\s+bug|fix:": "Bug fix should include a regression test that would have caught the original bug",
            r"update.*readme|readme.*update": "README change should be self-contained — no code changes needed",
            r"delete|remove": "Deletion should confirm nothing imports or calls the removed symbol",
        }

        for pattern, assumption in scope_signals.items():
            if re.search(pattern, task, re.IGNORECASE):
                plan.assumptions.append(assumption)

        # Interpretations
        plan.interpretations = [
            f"Interpretation A (narrow): {task} — touching only the minimum stated scope",
            f"Interpretation B (broad): {task} — including related cleanup or enhancements",
            "→ Confirm which interpretation is intended before writing code",
        ]

        # Simpler alternatives heuristic
        if re.search(r"new\s+class|abstract|base\s+class", task, re.IGNORECASE):
            plan.simpler_alternatives.append(
                "Consider a module-level function instead of a new class — classes add overhead"
            )
        if re.search(r"config|setting|option|flag", task, re.IGNORECASE):
            plan.simpler_alternatives.append(
                "Consider a hardcoded sensible default instead of a configurable option"
            )
        if re.search(r"cache|memo", task, re.IGNORECASE):
            plan.simpler_alternatives.append(
                "Consider whether the operation is fast enough without caching first"
            )

        # Success criteria
        plan.success_criteria = [
            "All pre-existing tests pass (uv run pytest -m 'not integration' -q)",
            "The specific behavior described in the task is demonstrably working",
            "No new ruff violations (uv run ruff check src/ tests/)",
        ]

        # Checkpoints
        plan.checkpoints = [
            "Checkpoint 1: Confirm interpretation before writing any code",
            "Checkpoint 2: Write tests that verify the new behavior",
            "Checkpoint 3: Implement until tests pass",
            "Checkpoint 4: Run full test suite — no regressions",
            "Checkpoint 5: Review diff — remove anything not required by the task",
        ]

        # Clarifying questions
        plan.clarifying_questions = [
            f"Which interpretation of '{task[:60]}...' is correct — A (narrow) or B (broad)?",
        ]
        if not existing_code_summary:
            plan.clarifying_questions.append(
                "Is there existing code that already does part of this? (avoids duplication)"
            )
        if re.search(r"user|caller|client", task, re.IGNORECASE):
            plan.clarifying_questions.append(
                "Who calls this? (affects API design: MCP tool vs internal service method)"
            )

        return plan

    # ------------------------------------------------------------------
    # Combined review (all 4 principles)
    # ------------------------------------------------------------------

    def karpathy_review(
        self,
        code: str,
        original_code: str = "",
        stated_goal: str = "",
        domain: str = "experiment",
    ) -> dict[str, Any]:
        """Run all applicable Karpathy checks and return a unified report.

        Args:
            code:          Code to review (after changes if comparing)
            original_code: Original code before changes (enables surgical check)
            stated_goal:   What the code/change is supposed to accomplish
            domain:        "experiment" | "paper" | "code" | "review"

        Returns:
            Dict with per-principle results and an overall pass/fail verdict.
        """
        results: dict[str, Any] = {"stated_goal": stated_goal, "domain": domain}

        # Principle 2: Simplicity
        simplicity = self.check_code_simplicity(code, context=stated_goal)
        results["simplicity"] = {
            "passed": simplicity.passed,
            "score": simplicity.score,
            "violations": [
                {
                    "principle": v.principle,
                    "severity": v.severity,
                    "message": v.message,
                    "line_hint": v.line_hint,
                    "suggestion": v.suggestion,
                }
                for v in simplicity.violations
            ],
            "summary": simplicity.summary,
            "recommendations": simplicity.recommendations,
        }

        # Principle 3: Surgical (only if original provided)
        if original_code:
            surgical = self.review_code_changes(original_code, code, stated_goal)
            results["surgical"] = {
                "passed": surgical.passed,
                "score": surgical.score,
                "violations": [
                    {
                        "principle": v.principle,
                        "severity": v.severity,
                        "message": v.message,
                        "suggestion": v.suggestion,
                    }
                    for v in surgical.violations
                ],
                "summary": surgical.summary,
                "recommendations": surgical.recommendations,
            }

        # Principle 4: Success criteria (if goal given)
        if stated_goal:
            criteria = self.define_success_criteria(stated_goal, domain=domain)
            results["success_criteria"] = {
                "goal": criteria.goal,
                "criteria": criteria.criteria,
                "metrics": criteria.metrics,
                "anti_goals": criteria.anti_goals,
                "verification_steps": criteria.verification_steps,
            }

        # Overall verdict
        all_passed = simplicity.passed
        if original_code:
            all_passed = all_passed and results["surgical"]["passed"]

        results["overall_passed"] = all_passed
        results["overall_score"] = simplicity.score

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_score(self, violations: list[PrincipleViolation]) -> int:
        score = 100
        for v in violations:
            score -= self._SEVERITY_DEDUCTION.get(v.severity, 10)
        return max(0, score)

    def _simplicity_summary(
        self, score: int, violations: list[PrincipleViolation], context: str
    ) -> str:
        if not violations:
            return "No simplicity issues detected."
        highs = [v for v in violations if v.severity == "high"]
        meds = [v for v in violations if v.severity == "medium"]
        lows = [v for v in violations if v.severity == "low"]
        parts = []
        if highs:
            parts.append(f"{len(highs)} high-severity issue(s)")
        if meds:
            parts.append(f"{len(meds)} medium-severity issue(s)")
        if lows:
            parts.append(f"{len(lows)} low-severity issue(s)")
        return f"Score {score}/100. Found: {', '.join(parts)}."

    def _simplicity_recommendations(self, violations: list[PrincipleViolation]) -> list[str]:
        seen: set[str] = set()
        recs: list[str] = []
        for v in sorted(violations, key=lambda x: ["high", "medium", "low"].index(x.severity)):
            if v.suggestion and v.suggestion not in seen:
                seen.add(v.suggestion)
                recs.append(v.suggestion)
        return recs[:5]  # top 5
