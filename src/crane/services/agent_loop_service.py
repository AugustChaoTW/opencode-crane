"""Agent Loop Service - Crane version of ml-intern submission_loop"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from crane.services.mcp_tool_orchestration_service import MCPToolOrchestrationService


class LoopState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPACTING = "compacting"
    DONE = "done"
    INTERRUPTED = "interrupted"
    MAX_ITERATIONS = "max_iterations"


@dataclass
class LoopIteration:
    iteration: int
    tool_calls: list[dict[str, Any]]
    results: list[dict[str, Any]]
    elapsed_sec: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class LoopResult:
    execution_id: str
    state: LoopState
    iterations_completed: int
    tools_executed: list[str]
    tool_results: list[dict[str, Any]]
    total_elapsed_sec: float
    final_context: dict[str, Any]
    error: str | None = None


class AgentLoopService:
    """Agentic loop service matching ml-intern submission_loop architecture.

    Features:
    - max_iterations config (default: 300)
    - Iteration tracking and statistics
    - Early termination conditions
    - Tool routing via MCPToolOrchestrationService
    """

    DEFAULT_MAX_ITERATIONS = 300
    DEFAULT_TOKEN_THRESHOLD = 170_000

    def __init__(
        self,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        token_threshold: int = DEFAULT_TOKEN_THRESHOLD,
    ):
        self.max_iterations = max_iterations
        self.token_threshold = token_threshold
        self.tool_orchestrator = MCPToolOrchestrationService()
        self._reset()

    def _reset(self):
        self.execution_id = ""
        self.state = LoopState.IDLE
        self.iterations: list[LoopIteration] = []
        self.context: dict[str, Any] = {}
        self.tool_calls_history: list[str] = []

    def run(
        self,
        task_description: str,
        domain: str | None = None,
        tool_executor: Callable[[str, dict], dict] | None = None,
    ) -> LoopResult:
        """Run the agent loop for a task.

        Args:
            task_description: Task to execute
            domain: Optional domain hint (ml, se, hci, theory, systems)
            tool_executor: Optional custom tool executor function

        Returns:
            LoopResult with execution details
        """
        self._reset()
        self.execution_id = str(uuid.uuid4())
        self.state = LoopState.RUNNING

        start_time = time.time()
        selected = self.tool_orchestrator.orchestrate_task(task_description, domain=domain)
        tools = selected.get("selected_tools", [])

        iteration = 0
        while iteration < self.max_iterations and self.state == LoopState.RUNNING:
            iteration += 1
            iter_start = time.time()

            iter_tool_calls = []
            iter_results = []

            for tool_name in tools:
                if tool_executor:
                    result = tool_executor(tool_name, {"task": task_description, "context": self.context})
                else:
                    result = {"status": "skipped", "tool": tool_name, "message": "No executor provided"}

                iter_tool_calls.append({"tool": tool_name, "arguments": {"task": task_description}})
                iter_results.append(result)

                self.tool_calls_history.append(tool_name)
                self.context[tool_name] = result

            elapsed = time.time() - iter_start
            self.iterations.append(LoopIteration(
                iteration=iteration,
                tool_calls=iter_tool_calls,
                results=iter_results,
                elapsed_sec=elapsed,
            ))

            if self._check_early_termination(iter_results):
                break

            if self._estimate_tokens() > self.token_threshold:
                self.state = LoopState.COMPACTING
                break

        total_elapsed = time.time() - start_time

        if self.state == LoopState.RUNNING:
            if iteration >= self.max_iterations:
                self.state = LoopState.MAX_ITERATIONS
            else:
                self.state = LoopState.DONE

        tools_executed = [tc["tool"] for ic in self.iterations for tc in ic.tool_calls]
        tool_results = [r for ic in self.iterations for r in ic.results]

        return LoopResult(
            execution_id=self.execution_id,
            state=self.state,
            iterations_completed=iteration,
            tools_executed=tools_executed,
            tool_results=tool_results,
            total_elapsed_sec=total_elapsed,
            final_context=self.context,
        )

    def _check_early_termination(self, results: list[dict[str, Any]]) -> bool:
        """Check if results indicate early termination."""
        if not results:
            return False

        for result in results:
            status = str(result.get("status", "")).lower()
            if status in ("done", "success", "complete"):
                return True

            error = result.get("error", "")
            if error and "fatal" in error.lower():
                return True

        return False

    def _estimate_tokens(self) -> int:
        """Estimate current token usage from context."""
        import json
        context_str = json.dumps(self.context)
        return len(context_str) // 4

    def get_statistics(self) -> dict[str, Any]:
        """Get loop execution statistics."""
        if not self.iterations:
            return {
                "execution_id": self.execution_id,
                "state": self.state.value,
                "iterations": 0,
                "total_tools": 0,
                "total_elapsed_sec": 0.0,
                "tool_history": [],
            }

        total_tools = sum(len(ic.tool_calls) for ic in self.iterations)
        total_elapsed = sum(ic.elapsed_sec for ic in self.iterations)

        tool_counter: dict[str, int] = {}
        for tool in self.tool_calls_history:
            tool_counter[tool] = tool_counter.get(tool, 0) + 1

        return {
            "execution_id": self.execution_id,
            "state": self.state.value,
            "iterations": len(self.iterations),
            "total_tools": total_tools,
            "total_elapsed_sec": round(total_elapsed, 4),
            "tool_history": tool_counter,
            "context_keys": list(self.context.keys()),
        }

    def interrupt(self):
        """Interrupt the running loop."""
        if self.state == LoopState.RUNNING:
            self.state = LoopState.INTERRUPTED

    def get_state(self) -> LoopState:
        """Get current loop state."""
        return self.state


def create_agent_loop(
    max_iterations: int = 300,
    token_threshold: int = 170_000,
) -> AgentLoopService:
    """Factory function to create AgentLoopService."""
    return AgentLoopService(
        max_iterations=max_iterations,
        token_threshold=token_threshold,
    )