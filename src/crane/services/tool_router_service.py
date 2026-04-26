from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from crane.services.mcp_tool_orchestration_service import MCPToolOrchestrationService


@dataclass
class RoutingContext:
    """Context for tool routing decisions"""
    task: str
    domain: str | None = None
    token_count: int = 0
    previous_tools: list[str] = field(default_factory=list)
    agent_history: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RoutingDecision:
    """Routing decision result"""
    selected_tools: list[str]
    confidence: float
    reasoning: str
    alternatives: list[str] = field(default_factory=list)


class ToolRouterService:
    """
    Enhanced tool router with context awareness,
    dynamic performance tracking, and token-based optimization.
    """

    def __init__(
        self,
        max_tools_per_step: int = 6,
        confidence_threshold: float = 0.25,
        token_threshold: int = 170000,
    ):
        self.max_tools_per_step = max_tools_per_step
        self.confidence_threshold = confidence_threshold
        self.token_threshold = token_threshold
        self._orchestrator = MCPToolOrchestrationService()
        self._performance_cache: dict[str, dict[str, Any]] = {}

    def select_tools_with_context(self, context: RoutingContext) -> RoutingDecision:
        """Select tools considering routing context"""
        task = context.task.strip()
        if not task:
            return RoutingDecision(
                selected_tools=[],
                confidence=0.0,
                reasoning="Empty task description"
            )

        domain = context.domain or self._infer_domain(task)
        selected = self._orchestrator.select_tools(task, domain)

        if context.previous_tools:
            selected = self._filter_previous(selected, context.previous_tools)

        if context.token_count >= self.token_threshold:
            selected = self._optimize_for_tokens(selected, context.token_count)

        tool_names = [t.get("name", "") for t in selected[: self.max_tools_per_step]]
        alternatives = [t.get("name", "") for t in selected[self.max_tools_per_step : self.max_tools_per_step + 3]]

        confidence = self._calculate_confidence(tool_names, task)

        return RoutingDecision(
            selected_tools=tool_names,
            confidence=confidence,
            reasoning=self._build_reasoning(context, len(tool_names)),
            alternatives=alternatives,
        )

    def _infer_domain(self, task: str) -> str | None:
        """Infer domain from task description"""
        task_lower = task.lower()
        if any(kw in task_lower for kw in ["model", "training", "embedding", "dataset"]):
            return "ml"
        if any(kw in task_lower for kw in ["code", "pipeline", "workflow"]):
            return "se"
        if any(kw in task_lower for kw in ["user", "feedback", "framing"]):
            return "hci"
        if any(kw in task_lower for kw in ["proof", "theorem", "complexity"]):
            return "theory"
        return None

    def _filter_previous(self, tools: list, previous: list[str]) -> list:
        """Filter out previously used tools"""
        previous_set = set(previous)
        filtered = [t for t in tools if t.get("name", "") not in previous_set]
        return filtered[: self.max_tools_per_step] if filtered else tools[:1]

    def _optimize_for_tokens(self, tools: list, token_count: int) -> list:
        """Optimize tool selection for token efficiency"""
        if not tools:
            return tools

        optimized = sorted(
            tools,
            key=lambda t: (
                t.get("token_cost", 900) if t.get("token_cost", 900) else 900,
                -(t.get("success_rate", 0.85)),
            )
        )
        return optimized[: self.max_tools_per_step]

    def _calculate_confidence(self, tools: list[str], task: str) -> float:
        """Calculate confidence score for selected tools"""
        if not tools:
            return 0.0

        total_confidence = 0.0
        for tool_name in tools:
            metadata = self._orchestrator.tool_registry.get(tool_name, {})
            total_confidence += metadata.get("success_rate", 0.85)

        avg_confidence = total_confidence / len(tools)
        task_length_factor = min(1.0, len(task) / 100.0)
        return round(avg_confidence * task_length_factor, 2)

    def _build_reasoning(self, context: RoutingContext, tool_count: int) -> str:
        """Build reasoning string for decision"""
        parts = []

        if context.token_count >= self.token_threshold:
            parts.append("Token-optimized")
        if context.previous_tools:
            parts.append("Context-aware")
        if context.domain:
            parts.append(f"Domain: {context.domain}")

        if parts:
            return f"{', '.join(parts)} selection ({tool_count} tools)"
        return f"Standard selection ({tool_count} tools)"