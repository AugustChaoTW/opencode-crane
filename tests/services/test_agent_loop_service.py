"""TDD Tests for Agent Loop Service (v0.14.8)

Run with:
  pytest tests/services/test_agent_loop_service.py -v
"""

import pytest
from unittest.mock import MagicMock, patch

from src.crane.services.agent_loop_service import (
    AgentLoopService,
    LoopState,
    LoopResult,
    LoopIteration,
    create_agent_loop,
)


class TestAgentLoopService:
    def test_default_max_iterations(self):
        service = create_agent_loop()
        assert service.max_iterations == 300

    def test_custom_max_iterations(self):
        service = create_agent_loop(max_iterations=10)
        assert service.max_iterations == 10

    def test_initial_state_idle(self):
        service = create_agent_loop()
        assert service.get_state() == LoopState.IDLE

    def test_run_completes_within_max_iterations(self):
        service = create_agent_loop(max_iterations=5)

        mock_executor = MagicMock(return_value={"status": "done"})

        result = service.run(
            task_description="test task",
            domain="ml",
            tool_executor=mock_executor,
        )

        assert result.iterations_completed <= 5
        assert result.state in [LoopState.DONE, LoopState.MAX_ITERATIONS]

    def test_early_termination_on_success(self):
        service = create_agent_loop(max_iterations=100)

        result = service.run(
            task_description="test",
            tool_executor=lambda t, ctx: {"status": "done"},
        )

        assert result.state == LoopState.DONE

    def test_max_iterations_stops_loop(self):
        service = create_agent_loop(max_iterations=3)

        result = service.run(
            task_description="test",
            tool_executor=lambda t, ctx: {"status": "continue"},
        )

        assert result.iterations_completed == 3
        assert result.state == LoopState.MAX_ITERATIONS

    def test_interruption_stops_loop(self):
        service = create_agent_loop(max_iterations=100)

        def slow_executor(tool, ctx):
            service.interrupt()
            return {"status": "done"}

        service.run(task_description="test", tool_executor=slow_executor)

        assert service.get_state() == LoopState.INTERRUPTED

    def test_token_threshold_triggers_compaction(self):
        service = create_agent_loop(max_iterations=100, token_threshold=100)

        call_count = 0
        def executor(tool, ctx):
            nonlocal call_count
            call_count += 1
            return {"status": "continue"}

        result = service.run(
            task_description="test",
            tool_executor=executor,
        )

        assert call_count > 0

    def test_statistics_show_iterations(self):
        service = create_agent_loop(max_iterations=5)

        service.run(
            task_description="test",
            tool_executor=lambda t, ctx: {"status": "done"},
        )

        stats = service.get_statistics()

        assert "iterations" in stats
        assert stats["iterations"] >= 1
        assert "tool_history" in stats


class TestLoopState:
    def test_all_states_defined(self):
        assert LoopState.IDLE.value == "idle"
        assert LoopState.RUNNING.value == "running"
        assert LoopState.COMPACTING.value == "compacting"
        assert LoopState.DONE.value == "done"
        assert LoopState.INTERRUPTED.value == "interrupted"
        assert LoopState.MAX_ITERATIONS.value == "max_iterations"


class TestLoopResult:
    def test_result_has_required_fields(self):
        result = LoopResult(
            execution_id="test-id",
            state=LoopState.DONE,
            iterations_completed=1,
            tools_executed=["tool1"],
            tool_results=[{"status": "done"}],
            total_elapsed_sec=1.0,
            final_context={},
        )

        assert result.execution_id == "test-id"
        assert result.state == LoopState.DONE
        assert result.iterations_completed == 1


class TestIntegration:
    def test_full_loop_with_mock_tools(self):
        service = create_agent_loop(max_iterations=2)

        def mock_executor(tool_name, ctx):
            return {"status": "done", "tool": tool_name}

        result = service.run(
            task_description="Run ML experiment",
            domain="ml",
            tool_executor=mock_executor,
        )

        assert result.execution_id
        assert result.iterations_completed >= 1
        assert result.total_elapsed_sec > 0


@pytest.fixture
def service():
    return create_agent_loop(max_iterations=10)