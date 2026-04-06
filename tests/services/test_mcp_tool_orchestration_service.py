# pyright: reportMissingImports=false

from __future__ import annotations

from typing import Any

import pytest

from crane.services.mcp_tool_orchestration_service import MCPToolOrchestrationService


@pytest.fixture
def service() -> MCPToolOrchestrationService:
    return MCPToolOrchestrationService()


@pytest.fixture
def synthetic_service() -> MCPToolOrchestrationService:
    svc = MCPToolOrchestrationService()
    svc.tool_registry = {}
    tools = [
        {
            "name": "ml_search",
            "domain": "ml",
            "domains": ["ml"],
            "capability": "paper_search",
            "capabilities": ["paper_search"],
            "success_rate": 0.95,
            "avg_latency_sec": 1.2,
            "token_cost": 400,
        },
        {
            "name": "ml_eval",
            "domain": "ml",
            "domains": ["ml"],
            "capability": "experiment_evaluation",
            "capabilities": ["experiment_evaluation"],
            "success_rate": 0.94,
            "avg_latency_sec": 2.0,
            "token_cost": 800,
        },
        {
            "name": "se_arch",
            "domain": "se",
            "domains": ["se"],
            "capability": "architecture_review",
            "capabilities": ["architecture_review"],
            "success_rate": 0.92,
            "avg_latency_sec": 1.4,
            "token_cost": 500,
        },
        {
            "name": "hci_feedback",
            "domain": "hci",
            "domains": ["hci"],
            "capability": "feedback_analysis",
            "capabilities": ["feedback_analysis"],
            "success_rate": 0.91,
            "avg_latency_sec": 1.6,
            "token_cost": 450,
        },
        {
            "name": "theory_verify",
            "domain": "theory",
            "domains": ["theory"],
            "capability": "proof_verification",
            "capabilities": ["proof_verification"],
            "success_rate": 0.93,
            "avg_latency_sec": 1.8,
            "token_cost": 600,
        },
        {
            "name": "systems_profile",
            "domain": "systems",
            "domains": ["systems"],
            "capability": "performance_profiling",
            "capabilities": ["performance_profiling"],
            "success_rate": 0.96,
            "avg_latency_sec": 2.2,
            "token_cost": 700,
        },
        {
            "name": "systems_repro",
            "domain": "systems",
            "domains": ["systems"],
            "capability": "reproducibility_check",
            "capabilities": ["reproducibility_check"],
            "success_rate": 0.94,
            "avg_latency_sec": 1.5,
            "token_cost": 500,
        },
        {
            "name": "coord_plan",
            "domain": "se",
            "domains": ["se", "systems"],
            "capability": "coordination",
            "capabilities": ["coordination", "code_alignment"],
            "success_rate": 0.9,
            "avg_latency_sec": 1.3,
            "token_cost": 300,
        },
    ]
    for tool in tools:
        assert svc.register_tool(tool)
    return svc


def test_registry_discovers_existing_tools(service: MCPToolOrchestrationService) -> None:
    assert len(service.tool_registry) >= 83
    assert "search_papers" in service.tool_registry
    assert "run_pipeline" in service.tool_registry


def test_domain_definitions_include_five_cs_subdomains(
    service: MCPToolOrchestrationService,
) -> None:
    domains = service.get_domain_definitions()
    assert {"ml", "se", "hci", "theory", "systems"}.issubset(set(domains))


def test_list_available_tools_filters_by_domain(
    synthetic_service: MCPToolOrchestrationService,
) -> None:
    systems_tools = synthetic_service.list_available_tools("systems")
    assert systems_tools
    assert all("systems" in tool["domains"] for tool in systems_tools)


def test_register_tool_requires_name(synthetic_service: MCPToolOrchestrationService) -> None:
    assert synthetic_service.register_tool({"domain": "ml"}) is False


def test_register_tool_normalizes_and_clamps_values(
    synthetic_service: MCPToolOrchestrationService,
) -> None:
    ok = synthetic_service.register_tool(
        {
            "name": "test_tool",
            "domain": "Machine Learning",
            "capability": "paper_search",
            "success_rate": 5.0,
            "avg_latency_sec": -1.0,
            "token_cost": -5,
        }
    )
    assert ok
    metadata = synthetic_service.tool_registry["test_tool"]
    assert metadata["domains"] == ["ml"]
    assert metadata["success_rate"] == 1.0
    assert metadata["avg_latency_sec"] == 0.1
    assert metadata["token_cost"] == 0


def test_select_tools_returns_empty_for_blank_task(
    synthetic_service: MCPToolOrchestrationService,
) -> None:
    assert synthetic_service.select_tools("   ", domain="ml") == []


def test_select_tools_ml_task_prioritizes_ml_tools(
    synthetic_service: MCPToolOrchestrationService,
) -> None:
    selected = synthetic_service.select_tools(
        "search papers and evaluate model ablation performance",
        domain="ml",
    )
    names = [item["name"] for item in selected]
    assert "ml_search" in names
    assert "ml_eval" in names


def test_select_tools_se_task_picks_architecture_tool(
    synthetic_service: MCPToolOrchestrationService,
) -> None:
    selected = synthetic_service.select_tools(
        "review software architecture and improve pipeline quality",
        domain="software engineering",
    )
    names = [item["name"] for item in selected]
    assert "se_arch" in names


def test_select_tools_cross_domain_mixes_ml_and_se(
    synthetic_service: MCPToolOrchestrationService,
) -> None:
    selected = synthetic_service.select_tools(
        "machine learning experiment reproducibility and software architecture alignment",
    )
    domains = {domain for tool in selected for domain in tool["domains"]}
    assert "ml" in domains
    assert "se" in domains


def test_estimate_effectiveness_in_range(synthetic_service: MCPToolOrchestrationService) -> None:
    score = synthetic_service.estimate_tool_combo_effectiveness(
        ["ml_search", "ml_eval"], "evaluate model"
    )
    assert 0.0 <= score <= 1.0


def test_estimate_effectiveness_gains_from_synergy(
    synthetic_service: MCPToolOrchestrationService,
) -> None:
    single = synthetic_service.estimate_tool_combo_effectiveness(
        ["systems_profile"], "profile performance"
    )
    combo = synthetic_service.estimate_tool_combo_effectiveness(
        ["ml_eval", "systems_profile"],
        "evaluate model performance",
    )
    assert combo >= single


def test_execute_tool_sequence_without_executors_marks_planned(
    synthetic_service: MCPToolOrchestrationService,
) -> None:
    out = synthetic_service.execute_tool_sequence(["ml_search", "ml_eval"], inputs={})
    assert out["success"] is True
    assert out["success_rate"] == 1.0
    assert all(step["state"] == "planned" for step in out["steps"])


def test_execute_tool_sequence_handles_failures(
    synthetic_service: MCPToolOrchestrationService,
) -> None:
    def ok_executor(payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        context["ok"] = payload.get("value", 1)
        return {"status": "success", "value": context["ok"]}

    def fail_executor(_payload: dict[str, Any], _context: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("boom")

    out = synthetic_service.execute_tool_sequence(
        ["ml_search", "theory_verify"],
        inputs={
            "executors": {"ml_search": ok_executor, "theory_verify": fail_executor},
            "tool_inputs": {"ml_search": {"value": 7}},
            "context": {},
        },
    )
    assert out["success"] is False
    assert out["failed"] == ["theory_verify"]
    assert 0.0 < out["success_rate"] < 1.0


def test_evaluate_combo_performance_returns_score_and_updates_priors(
    synthetic_service: MCPToolOrchestrationService,
) -> None:
    before = synthetic_service.tool_registry["ml_search"]["success_rate"]
    score = synthetic_service.evaluate_combo_performance(
        ["ml_search", "ml_eval"],
        task="evaluate model",
        outcome={"success_rate": 1.0, "elapsed_sec": 1.0, "token_usage": 200},
    )
    after = synthetic_service.tool_registry["ml_search"]["success_rate"]
    assert 0.0 <= score <= 1.0
    assert after >= before
    assert len(synthetic_service.combo_history) == 1


def test_orchestrate_task_returns_required_structure(
    synthetic_service: MCPToolOrchestrationService,
) -> None:
    out = synthetic_service.orchestrate_task(
        "run machine learning evaluation and systems profiling",
        domain="ml",
    )
    assert set(out) == {"selected_tools", "confidence", "estimated_success_rate", "execution_plan"}
    assert isinstance(out["selected_tools"], list)
    assert isinstance(out["execution_plan"], dict)


def test_orchestrate_task_respects_available_tools_filter(
    synthetic_service: MCPToolOrchestrationService,
) -> None:
    out = synthetic_service.orchestrate_task(
        "evaluate model and profile performance",
        available_tools=["systems_profile", "ml_eval"],
    )
    assert set(out["selected_tools"]).issubset({"systems_profile", "ml_eval"})


def test_benchmark_selection_accuracy_exceeds_target(
    synthetic_service: MCPToolOrchestrationService,
) -> None:
    benchmark = [
        {"task": "search papers for deep learning", "domain": "ml", "expert_tools": ["ml_search"]},
        {
            "task": "evaluate model ablation and benchmark",
            "domain": "ml",
            "expert_tools": ["ml_eval"],
        },
        {
            "task": "software architecture review",
            "domain": "se",
            "expert_tools": ["se_arch"],
        },
        {
            "task": "user feedback analysis",
            "domain": "hci",
            "expert_tools": ["hci_feedback"],
        },
        {
            "task": "proof verification and consistency",
            "domain": "theory",
            "expert_tools": ["theory_verify"],
        },
        {
            "task": "performance profiling in distributed systems",
            "domain": "systems",
            "expert_tools": ["systems_profile"],
        },
    ]
    result = synthetic_service.benchmark_selection_accuracy(benchmark)
    assert result["cases"] == 6
    assert result["accuracy"] >= 0.8


def test_benchmark_execution_success_exceeds_target(
    synthetic_service: MCPToolOrchestrationService,
) -> None:
    result = synthetic_service.benchmark_execution_success(
        ["ml_search", "ml_eval", "systems_profile", "systems_repro"]
    )
    assert result["tool_count"] == 4
    assert result["mean_success_rate"] >= 0.9


def test_execute_tool_sequence_returns_failure_for_unknown_tools(
    synthetic_service: MCPToolOrchestrationService,
) -> None:
    out = synthetic_service.execute_tool_sequence(["does_not_exist"], inputs={})
    assert out["success"] is False
    assert out["success_rate"] == 0.0
