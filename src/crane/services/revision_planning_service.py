from __future__ import annotations

from crane.models.paper_profile import (
    DimensionScore,
    RevisionEffort,
    RevisionItem,
    RevisionPlan,
    RevisionPriority,
)


class RevisionPlanningService:
    """Generate and manage revision plans from evaluation scores."""

    _GATE_DIMENSIONS = {"methodology", "novelty", "evaluation"}
    _EFFORT_WEIGHT = {
        RevisionEffort.LOW: 1.0,
        RevisionEffort.MEDIUM: 2.0,
        RevisionEffort.HIGH: 4.0,
    }

    def generate_plan(
        self, dimension_scores: list[DimensionScore], current_overall: float
    ) -> RevisionPlan:
        """Generate a prioritized revision plan from dimension scores."""
        items: list[RevisionItem] = []

        for dim in dimension_scores:
            suggestion = (
                dim.suggestions[0]
                if dim.suggestions
                else f"Improve {dim.dimension} based on identified evidence gaps"
            )
            items.append(
                RevisionItem(
                    dimension=dim.dimension,
                    suggestion=suggestion,
                    priority=self._priority_for(dim.dimension, dim.score),
                    effort=self._effort_for(dim.score),
                    expected_impact=self._impact_for(dim.score),
                    depends_on=[],
                    status="pending",
                )
            )

        plan = RevisionPlan(items=items, current_score=current_overall, projected_score=0.0)
        plan.projected_score = self.estimate_projected_score(plan)
        return plan

    def sort_by_roi(self, plan: RevisionPlan) -> RevisionPlan:
        """Sort items by ROI = expected_impact / effort_weight."""
        plan.items.sort(
            key=lambda item: item.expected_impact / self._EFFORT_WEIGHT[item.effort],
            reverse=True,
        )
        return plan

    def group_by_timeline(self, plan: RevisionPlan) -> dict[str, list[RevisionItem]]:
        """Group revision items into immediate/medium_term/long_term."""
        return {
            "immediate": [i for i in plan.items if i.priority == RevisionPriority.IMMEDIATE],
            "medium_term": [i for i in plan.items if i.priority == RevisionPriority.MEDIUM_TERM],
            "long_term": [i for i in plan.items if i.priority == RevisionPriority.LONG_TERM],
        }

    def estimate_projected_score(self, plan: RevisionPlan) -> float:
        """Estimate projected score if all IMMEDIATE items are completed."""
        immediate_impact = sum(item.expected_impact for item in plan.immediate_items)
        return round(min(100.0, plan.current_score + immediate_impact), 2)

    def check_dependencies(self, plan: RevisionPlan) -> list[tuple[str, str]]:
        """Identify dependency pairs between revision items."""
        dimensions = {item.dimension.lower() for item in plan.items}
        dependencies: list[tuple[str, str]] = []

        rules = [
            ("methodology", "evaluation"),
            ("novelty", "evaluation"),
            ("methodology", "reproducibility"),
        ]
        for prerequisite, dependent in rules:
            if prerequisite in dimensions and dependent in dimensions:
                dependencies.append((prerequisite, dependent))

        return dependencies

    def create_snapshot(self, dimension_scores: list[DimensionScore]) -> dict:
        """Create a snapshot of current scores for later comparison."""
        score_by_dimension = {d.dimension: d.score for d in dimension_scores}
        confidence_by_dimension = {d.dimension: d.confidence for d in dimension_scores}
        overall = (
            round(sum(d.score for d in dimension_scores) / len(dimension_scores), 2)
            if dimension_scores
            else 0.0
        )
        return {
            "overall": overall,
            "scores": score_by_dimension,
            "confidence": confidence_by_dimension,
            "count": len(dimension_scores),
        }

    def compare_snapshots(self, before: dict, after: dict) -> dict:
        """Compare before/after snapshots and compute deltas per dimension."""
        before_scores: dict[str, float] = before.get("scores", {})
        after_scores: dict[str, float] = after.get("scores", {})

        all_dimensions = sorted(set(before_scores) | set(after_scores))
        per_dimension: dict[str, dict[str, float]] = {}
        improved = 0
        regressed = 0

        for dim in all_dimensions:
            old_score = float(before_scores.get(dim, 0.0))
            new_score = float(after_scores.get(dim, 0.0))
            delta = round(new_score - old_score, 2)
            if delta > 0:
                improved += 1
            elif delta < 0:
                regressed += 1
            per_dimension[dim] = {
                "before": old_score,
                "after": new_score,
                "delta": delta,
            }

        overall_before = float(before.get("overall", 0.0))
        overall_after = float(after.get("overall", 0.0))

        return {
            "overall": {
                "before": overall_before,
                "after": overall_after,
                "delta": round(overall_after - overall_before, 2),
            },
            "dimensions": per_dimension,
            "summary": {
                "improved": improved,
                "regressed": regressed,
                "unchanged": len(all_dimensions) - improved - regressed,
            },
        }

    def generate_scorecard(
        self, dimension_scores: list[DimensionScore], gates_passed: bool, readiness: str
    ) -> str:
        """Layer 1: Scorecard markdown."""
        overall = (
            round(sum(d.score for d in dimension_scores) / len(dimension_scores), 2)
            if dimension_scores
            else 0.0
        )
        gates = "pass" if gates_passed else "fail"

        lines = [
            "# Q1 Readiness Scorecard",
            "",
            (f"**Overall**: {overall}/100 | **Readiness**: {readiness} | **Gates**: {gates}"),
            "",
            "| Dimension | Score | Confidence | Status |",
            "|-----------|-------|------------|--------|",
        ]

        for dim in dimension_scores:
            lines.append(
                f"| {dim.dimension} | {dim.score:g} | {dim.confidence:g} | {self._status_emoji(dim.score)} |"
            )

        lines.extend(["", "## Top Blockers"])

        blockers = sorted([d for d in dimension_scores if d.score < 60], key=lambda d: d.score)
        if not blockers:
            lines.append("1. None")
        else:
            for index, blocker in enumerate(blockers[:3], start=1):
                reason = (
                    blocker.reason_codes[0] if blocker.reason_codes else "insufficient evidence"
                )
                lines.append(f"{index}. {blocker.dimension} ({blocker.score:g}) — {reason}")

        return "\n".join(lines)

    def generate_evidence_view(self, dimension_scores: list[DimensionScore]) -> str:
        """Layer 2: Evidence View markdown."""
        lines = ["# Evidence View", ""]

        if not dimension_scores:
            lines.append("No dimensions to evaluate.")
            return "\n".join(lines)

        for dim in dimension_scores:
            lines.extend(
                [
                    f"## {dim.dimension}",
                    f"- Score: {dim.score:g}",
                    f"- Confidence: {dim.confidence:g}",
                    "- Evidence spans:",
                ]
            )
            lines.extend(self._bullet_lines(dim.evidence_spans))
            lines.append("- Missing evidence:")
            lines.extend(self._bullet_lines(dim.missing_evidence))
            lines.append("- Reason codes:")
            lines.extend(self._bullet_lines(dim.reason_codes))
            lines.append("")

        return "\n".join(lines).rstrip()

    def generate_revision_backlog(self, plan: RevisionPlan) -> str:
        """Layer 3: Revision Backlog markdown."""
        grouped = self.group_by_timeline(plan)
        projected = self.estimate_projected_score(plan)
        lines = [
            "# Revision Backlog",
            "",
            f"**Current Score**: {plan.current_score:g} → **Projected**: {projected:g}",
            "",
        ]

        section_meta: list[tuple[str, str]] = [
            ("Immediate (Must Fix)", "immediate"),
            ("Medium Term", "medium_term"),
            ("Long Term (Polish)", "long_term"),
        ]

        for title, key in section_meta:
            lines.append(f"## {title}")
            section_items = grouped[key]
            if not section_items:
                lines.append("- [ ] None")
                lines.append("")
                continue
            for item in section_items:
                lines.append(
                    "- [ ] "
                    f"{item.suggestion} | Dimension: {item.dimension} | "
                    f"Effort: {item.effort.value} | Impact: +{item.expected_impact:g}"
                )
            lines.append("")

        return "\n".join(lines).rstrip()

    def generate_full_report(
        self,
        dimension_scores: list[DimensionScore],
        gates_passed: bool,
        readiness: str,
        plan: RevisionPlan,
    ) -> str:
        """Generate complete 3-layer Markdown report combining all views."""
        scorecard = self.generate_scorecard(dimension_scores, gates_passed, readiness)
        evidence = self.generate_evidence_view(dimension_scores)
        backlog = self.generate_revision_backlog(plan)
        return "\n\n---\n\n".join([scorecard, evidence, backlog])

    def _priority_for(self, dimension: str, score: float) -> RevisionPriority:
        dim_key = dimension.lower()
        if score < 60 and dim_key in self._GATE_DIMENSIONS:
            return RevisionPriority.IMMEDIATE
        if score < 80:
            return RevisionPriority.MEDIUM_TERM
        return RevisionPriority.LONG_TERM

    def _effort_for(self, score: float) -> RevisionEffort:
        if score < 30:
            return RevisionEffort.HIGH
        if score < 60:
            return RevisionEffort.MEDIUM
        return RevisionEffort.LOW

    def _impact_for(self, score: float) -> float:
        return round(max(0.0, min(20.0, (80.0 - score) * 0.5)), 2)

    def _status_emoji(self, score: float) -> str:
        if score >= 80:
            return "✅"
        if score >= 60:
            return "⚠️"
        return "❌"

    def _bullet_lines(self, values: list[str]) -> list[str]:
        if not values:
            return ["  - None"]
        return [f"  - {value}" for value in values]
