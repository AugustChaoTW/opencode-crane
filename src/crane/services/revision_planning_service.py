from __future__ import annotations

import re
from collections import defaultdict, deque

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

    def build_dependency_graph(self, revision_items: list[dict]) -> dict:
        """Build heuristic dependency graph between revision items.

        Rules:
        - Methodology work should precede Evaluation work.
        - Items mentioning experiment additions should precede table/figure updates.
        - Writing Quality is treated as parallel with non-writing dimensions.
        """
        dependencies: list[dict[str, object]] = []
        item_count = len(revision_items)

        for source_idx, source in enumerate(revision_items):
            source_dim = str(source.get("dimension", "")).strip().lower()
            source_text = self._item_text(source)

            for target_idx, target in enumerate(revision_items):
                if source_idx == target_idx:
                    continue

                target_dim = str(target.get("dimension", "")).strip().lower()
                target_text = self._item_text(target)

                if "writing quality" in {source_dim, target_dim} and source_dim != target_dim:
                    continue

                if source_dim == "methodology" and target_dim == "evaluation":
                    dependencies.append(
                        {
                            "from": source_idx,
                            "to": target_idx,
                            "reason": "Methodology fixes should land before evaluation updates",
                        }
                    )
                    continue

                if self._mentions_add_experiment(source_text) and self._mentions_table_or_figure(
                    target_text
                ):
                    dependencies.append(
                        {
                            "from": source_idx,
                            "to": target_idx,
                            "reason": "Table/figure updates depend on newly added experiments",
                        }
                    )

        unique_dependencies = self._dedupe_dependencies(dependencies)
        critical_path = self._compute_critical_path(item_count, unique_dependencies)
        parallel_groups = self._build_parallel_groups(item_count, unique_dependencies)

        return {
            "dependencies": unique_dependencies,
            "critical_path": critical_path,
            "parallel_groups": parallel_groups,
        }

    def define_quality_criteria(self, item: dict) -> str:
        """Define measurable completion criteria for a revision item."""
        dimension = str(item.get("dimension", "")).strip().lower()
        issue_type = str(item.get("issue_type", "")).strip().lower()
        description = str(item.get("description", "")).strip().lower()

        if dimension == "methodology" and issue_type == "missing_ablation":
            return "Ablation study shows impact of each component with ≥3 variants tested"
        if dimension == "evaluation" and issue_type == "weak_baseline":
            return "At least 3 state-of-the-art baselines compared on the same datasets"
        if dimension == "evaluation" and issue_type in {"missing_significance", "weak_statistics"}:
            return "Statistical significance reported for key comparisons (e.g., p-values or confidence intervals)"
        if dimension == "novelty":
            return "Related-work comparison table clearly differentiates contributions against at least 3 closest papers"
        if dimension == "reproducibility":
            return "Implementation details, hyperparameters, and environment settings are complete and executable"
        if dimension == "presentation":
            return "All figures/tables are legible, referenced in text, and contain self-contained captions"
        if dimension == "writing quality":
            return "Argument flow is coherent with concise claims and no unresolved reviewer-facing ambiguities"

        if "ablation" in description:
            return "Ablation section includes controlled component-level analysis with reproducible settings"
        if "baseline" in description:
            return "Baseline section includes fair, like-for-like comparisons against competitive methods"
        if "experiment" in description:
            return "New experiments include setup, metrics, and result interpretation aligned with research claims"

        return "Revision is complete when objective evidence is added and the affected dimension score improves by at least +5"

    def generate_execution_plan(self, revision_items: list[dict]) -> dict:
        """Generate phased execution plan with dependencies and quality checkpoints."""
        graph = self.build_dependency_graph(revision_items)
        parallel_groups: list[list[int]] = graph["parallel_groups"]

        phases: list[dict[str, object]] = []
        quality_criteria: dict[int, str] = {}

        for phase_index, group in enumerate(parallel_groups, start=1):
            for item_idx in group:
                quality_criteria[item_idx] = self.define_quality_criteria(revision_items[item_idx])

            phases.append(
                {
                    "phase": phase_index,
                    "items": group,
                    "estimated_effort": self._estimate_phase_effort(group, revision_items),
                }
            )

        risks = self._identify_execution_risks(revision_items, graph)
        critical_path = graph["critical_path"]

        return {
            "phases": phases,
            "critical_path_length": len(critical_path),
            "parallelizable": any(len(group) > 1 for group in parallel_groups),
            "risks": risks,
            "quality_criteria": quality_criteria,
            "dependency_graph": graph,
        }

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

    def generate_report(
        self,
        dimension_scores: list[DimensionScore],
        gates_passed: bool,
        readiness: str,
        plan: RevisionPlan,
    ) -> str:
        """Backward-compatible report entrypoint with execution planning section."""
        scorecard = self.generate_scorecard(dimension_scores, gates_passed, readiness)
        evidence = self.generate_evidence_view(dimension_scores)
        backlog = self.generate_revision_backlog(plan)
        revision_items = self._build_revision_items(plan, dimension_scores)
        execution_plan = self.generate_execution_plan(revision_items)
        execution_plan_markdown = self._generate_execution_plan_markdown(
            revision_items, execution_plan
        )
        return "\n\n---\n\n".join([scorecard, evidence, backlog, execution_plan_markdown])

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

    def _build_revision_items(
        self, plan: RevisionPlan, dimension_scores: list[DimensionScore]
    ) -> list[dict[str, object]]:
        score_by_dimension = {d.dimension.lower(): d.score for d in dimension_scores}
        revision_items: list[dict[str, object]] = []

        for item in plan.items:
            dim_key = item.dimension.lower()
            before_score = float(score_by_dimension.get(dim_key, 0.0))
            revision_items.append(
                {
                    "dimension": item.dimension,
                    "issue_type": self._infer_issue_type(item.suggestion),
                    "description": item.suggestion,
                    "before_score": before_score,
                    "projected_after": round(min(100.0, before_score + item.expected_impact), 2),
                    "action_items": [item.suggestion],
                    "effort": item.effort.value,
                    "priority": item.priority.value,
                }
            )

        return revision_items

    def _infer_issue_type(self, suggestion: str) -> str:
        text = suggestion.lower()
        if "ablation" in text:
            return "missing_ablation"
        if "baseline" in text:
            return "weak_baseline"
        if "significance" in text or "statistical" in text:
            return "missing_significance"
        if "experiment" in text:
            return "missing_experiment"
        if "reproduc" in text:
            return "reproducibility_gap"
        if "writing" in text or "clarity" in text:
            return "writing_clarity"
        return "general_improvement"

    def _generate_execution_plan_markdown(
        self, revision_items: list[dict[str, object]], execution_plan: dict
    ) -> str:
        lines = ["## 4. Execution Plan", ""]

        phases: list[dict[str, object]] = execution_plan.get("phases", [])
        quality_criteria: dict[int, str] = execution_plan.get("quality_criteria", {})
        dependency_graph: dict = execution_plan.get("dependency_graph", {})

        lines.append(f"- Critical path length: {execution_plan.get('critical_path_length', 0)}")
        lines.append(f"- Parallelizable: {execution_plan.get('parallelizable', False)}")
        lines.append("")

        lines.append("### Phased Execution")
        for phase in phases:
            phase_no = self._to_int(phase.get("phase", 0))
            estimated_effort = str(phase.get("estimated_effort", "medium"))
            phase_items = phase.get("items", [])
            phase_item_indices = phase_items if isinstance(phase_items, list) else []
            lines.append(
                f"- Phase {phase_no} ({estimated_effort} effort): "
                + ", ".join(f"#{idx}" for idx in phase_item_indices)
            )
        if not phases:
            lines.append("- No revision items to schedule")
        lines.append("")

        lines.append("### Dependencies")
        dependencies: list[dict] = dependency_graph.get("dependencies", [])
        if not dependencies:
            lines.append("- None")
        else:
            for dep in dependencies:
                lines.append(f"- #{dep['from']} → #{dep['to']}: {dep['reason']}")
        lines.append("")

        lines.append("### Quality Criteria by Item")
        for idx, item in enumerate(revision_items):
            criteria = quality_criteria.get(idx, self.define_quality_criteria(item))
            lines.append(
                f"- #{idx} [{item.get('dimension', 'Unknown')}]: "
                f"{item.get('description', 'No description')}"
            )
            lines.append(f"  - Completion criteria: {criteria}")
        if not revision_items:
            lines.append("- None")
        lines.append("")

        lines.append("### Risks")
        risks: list[str] = execution_plan.get("risks", [])
        if not risks:
            lines.append("- None")
        else:
            for risk in risks:
                lines.append(f"- {risk}")

        return "\n".join(lines).rstrip()

    def _item_text(self, item: dict) -> str:
        parts = [
            str(item.get("description", "")),
            str(item.get("issue_type", "")),
            " ".join(str(v) for v in item.get("action_items", [])),
        ]
        return " ".join(parts).lower()

    def _mentions_add_experiment(self, text: str) -> bool:
        return bool(re.search(r"\b(add|run|include|conduct)\b.*\bexperiment", text))

    def _mentions_table_or_figure(self, text: str) -> bool:
        return bool(
            re.search(r"\b(update|revise|improve|add)\b.*\b(table|figure|plot|chart)", text)
        )

    def _dedupe_dependencies(
        self, dependencies: list[dict[str, object]]
    ) -> list[dict[str, object]]:
        seen: set[tuple[int, int]] = set()
        unique: list[dict[str, object]] = []
        for dep in dependencies:
            source_idx = self._dep_index(dep, "from")
            target_idx = self._dep_index(dep, "to")
            key = (source_idx, target_idx)
            if key in seen:
                continue
            seen.add(key)
            unique.append(dep)
        return unique

    def _compute_critical_path(
        self, item_count: int, dependencies: list[dict[str, object]]
    ) -> list[int]:
        if item_count == 0:
            return []

        graph: dict[int, list[int]] = defaultdict(list)
        indegree = [0] * item_count
        for dep in dependencies:
            source_idx = self._dep_index(dep, "from")
            target_idx = self._dep_index(dep, "to")
            graph[source_idx].append(target_idx)
            indegree[target_idx] += 1

        queue: deque[int] = deque(i for i, d in enumerate(indegree) if d == 0)
        topo_order: list[int] = []
        while queue:
            node = queue.popleft()
            topo_order.append(node)
            for neighbor in graph[node]:
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    queue.append(neighbor)

        if len(topo_order) != item_count:
            return [0]

        dist = [1] * item_count
        prev = [-1] * item_count
        for node in topo_order:
            for neighbor in graph[node]:
                if dist[node] + 1 > dist[neighbor]:
                    dist[neighbor] = dist[node] + 1
                    prev[neighbor] = node

        end = max(range(item_count), key=lambda idx: dist[idx])
        path: list[int] = []
        while end != -1:
            path.append(end)
            end = prev[end]
        path.reverse()
        return path

    def _build_parallel_groups(
        self, item_count: int, dependencies: list[dict[str, object]]
    ) -> list[list[int]]:
        if item_count == 0:
            return []

        graph: dict[int, list[int]] = defaultdict(list)
        indegree = [0] * item_count
        for dep in dependencies:
            source_idx = self._dep_index(dep, "from")
            target_idx = self._dep_index(dep, "to")
            graph[source_idx].append(target_idx)
            indegree[target_idx] += 1

        ready = sorted([idx for idx, degree in enumerate(indegree) if degree == 0])
        groups: list[list[int]] = []

        while ready:
            current_group = ready
            groups.append(current_group)
            next_ready: list[int] = []

            for node in current_group:
                for neighbor in graph[node]:
                    indegree[neighbor] -= 1
                    if indegree[neighbor] == 0:
                        next_ready.append(neighbor)

            ready = sorted(next_ready)

        if sum(len(group) for group in groups) < item_count:
            scheduled = {idx for group in groups for idx in group}
            leftovers = [idx for idx in range(item_count) if idx not in scheduled]
            if leftovers:
                groups.append(leftovers)

        return groups

    def _estimate_phase_effort(self, group: list[int], revision_items: list[dict]) -> str:
        if not group:
            return "low"

        effort_score = 0
        weight = {"low": 1, "medium": 2, "high": 3}
        for idx in group:
            effort_key = str(revision_items[idx].get("effort", "medium")).lower()
            effort_score += weight.get(effort_key, 2)

        average = effort_score / len(group)
        if average >= 2.5:
            return "high"
        if average >= 1.75:
            return "medium"
        return "low"

    def _identify_execution_risks(self, revision_items: list[dict], graph: dict) -> list[str]:
        risks: list[str] = []
        dependencies: list[dict] = graph.get("dependencies", [])
        critical_path: list[int] = graph.get("critical_path", [])

        if len(critical_path) >= 3:
            risks.append("Long dependency chain may delay downstream revisions")
        if dependencies and not any(
            "methodology" in str(item.get("dimension", "")).lower() for item in revision_items
        ):
            risks.append(
                "Evaluation-heavy revisions without methodology grounding may weaken claims"
            )

        low_margin = 0
        for item in revision_items:
            before_score = float(item.get("before_score", 0.0))
            projected_after = float(item.get("projected_after", before_score))
            if projected_after - before_score < 4.0:
                low_margin += 1
        if low_margin >= 2:
            risks.append("Multiple low-impact items may not move readiness enough")

        return risks

    def _dep_index(self, dependency: dict[str, object], key: str) -> int:
        return self._to_int(dependency.get(key, 0))

    def _to_int(self, value: object) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            return int(value) if value.isdigit() else 0
        return 0
