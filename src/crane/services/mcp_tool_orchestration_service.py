from __future__ import annotations

import ast
import re
import time
import uuid
from itertools import combinations
from pathlib import Path
from typing import Any


class MCPToolOrchestrationService:
    DOMAIN_DEFINITIONS: dict[str, dict[str, Any]] = {
        "ml": {
            "aliases": ["ml", "machine learning", "deep learning", "neural", "ai"],
            "keywords": [
                "model",
                "training",
                "evaluation",
                "ablation",
                "embedding",
                "dataset",
            ],
            "description": "ML/Deep Learning workflows and model-centric evaluation",
        },
        "se": {
            "aliases": ["se", "software engineering", "software", "architecture", "dev"],
            "keywords": [
                "architecture",
                "pipeline",
                "workflow",
                "quality",
                "code",
                "best practice",
            ],
            "description": "Software engineering practices and architecture evaluation",
        },
        "hci": {
            "aliases": ["hci", "human-computer interaction", "ux", "usability", "user study"],
            "keywords": [
                "user",
                "feedback",
                "study",
                "interaction",
                "survey",
                "framing",
            ],
            "description": "HCI research including user studies and feedback analysis",
        },
        "theory": {
            "aliases": ["theory", "algorithms", "algorithm", "proof", "complexity"],
            "keywords": [
                "proof",
                "theorem",
                "complexity",
                "formal",
                "verification",
                "consistency",
            ],
            "description": "Theoretical CS, proof/verification, and complexity analysis",
        },
        "systems": {
            "aliases": ["systems", "distributed", "performance", "reproducibility", "infra"],
            "keywords": [
                "latency",
                "throughput",
                "profile",
                "runtime",
                "reproducibility",
                "deployment",
            ],
            "description": "Systems/distributed research and performance profiling",
        },
    }

    MODULE_DOMAIN_MAP: dict[str, list[str]] = {
        "papers": ["ml", "theory"],
        "references": ["ml", "theory", "hci"],
        "semantic_search": ["ml", "se", "theory"],
        "citation_graph": ["ml", "theory"],
        "ask_library": ["ml", "hci"],
        "tasks": ["se"],
        "project": ["se"],
        "workspace": ["se", "systems"],
        "pipeline": ["se", "ml"],
        "citations": ["theory", "ml"],
        "screening": ["hci", "ml"],
        "section_review": ["hci", "se"],
        "q1_evaluation": ["ml", "hci"],
        "journal_strategy": ["ml", "se"],
        "evaluation_v2": ["ml", "se", "hci"],
        "research_positioning": ["theory", "ml"],
        "first_principles": ["theory"],
        "submission_simulation": ["systems", "ml"],
        "submission_check": ["se", "systems"],
        "version_tools": ["systems", "se"],
        "permission_rules": ["se", "systems"],
        "agent_mgmt": ["se", "hci"],
        "transport_tools": ["systems", "se"],
        "figures": ["ml", "hci"],
    }

    CAPABILITY_KEYWORDS: dict[str, list[str]] = {
        "paper_search": ["search", "paper", "reference", "library"],
        "experiment_evaluation": ["evaluate", "evaluation", "benchmark", "ablation"],
        "code_alignment": ["code", "pipeline", "workflow", "tool", "integration"],
        "architecture_review": ["architecture", "design", "structure", "system"],
        "feedback_analysis": ["feedback", "framing", "review", "user"],
        "proof_verification": ["proof", "verify", "consistency", "formal", "theory"],
        "complexity_analysis": ["complexity", "effort", "cost", "latency", "throughput"],
        "performance_profiling": ["performance", "speed", "latency", "runtime", "profile"],
        "reproducibility_check": ["reproducibility", "citation", "metadata", "check"],
        "coordination": ["task", "project", "status", "orchestrate", "plan"],
    }

    SYNERGY_RULES: list[tuple[str, str, float]] = [
        ("paper_search", "proof_verification", 0.08),
        ("experiment_evaluation", "performance_profiling", 0.09),
        ("code_alignment", "architecture_review", 0.08),
        ("feedback_analysis", "reproducibility_check", 0.07),
        ("coordination", "performance_profiling", 0.06),
    ]

    def __init__(self):
        self.tool_registry: dict[str, dict[str, Any]] = {}
        self.combo_history: list[dict[str, Any]] = []
        for metadata in self._discover_tools():
            self.register_tool(metadata)

    def register_tool(self, tool_metadata: dict) -> bool:
        name = str(tool_metadata.get("name", "")).strip()
        if not name:
            return False

        domains = tool_metadata.get("domains") or []
        if not isinstance(domains, list) or not domains:
            primary_domain = self._normalize_domain(str(tool_metadata.get("domain", "")))
            domains = [primary_domain] if primary_domain else ["se"]
        normalized_domains = [d for d in (self._normalize_domain(d) for d in domains) if d]
        if not normalized_domains:
            normalized_domains = ["se"]

        capabilities = tool_metadata.get("capabilities") or []
        if not isinstance(capabilities, list) or not capabilities:
            capability = (
                str(tool_metadata.get("capability", "coordination")).strip() or "coordination"
            )
            capabilities = [capability]
        clean_capabilities = [str(cap).strip().lower() for cap in capabilities if str(cap).strip()]
        if not clean_capabilities:
            clean_capabilities = ["coordination"]

        success_rate = float(tool_metadata.get("success_rate", 0.85))
        if success_rate < 0.0:
            success_rate = 0.0
        if success_rate > 1.0:
            success_rate = 1.0

        avg_latency_sec = float(tool_metadata.get("avg_latency_sec", 2.0))
        token_cost = int(tool_metadata.get("token_cost", 900))

        self.tool_registry[name] = {
            "name": name,
            "domain": normalized_domains[0],
            "domains": normalized_domains,
            "capability": clean_capabilities[0],
            "capabilities": clean_capabilities,
            "success_rate": success_rate,
            "avg_latency_sec": max(avg_latency_sec, 0.1),
            "token_cost": max(token_cost, 0),
            "module": str(tool_metadata.get("module", "")),
        }
        return True

    def list_available_tools(self, domain: str | None = None) -> list:
        tools = list(self.tool_registry.values())
        normalized_domain = self._normalize_domain(domain or "")
        if normalized_domain:
            tools = [t for t in tools if normalized_domain in t.get("domains", [])]
        return sorted(tools, key=lambda item: item["name"])

    def select_tools(self, task_description: str, domain: str | None = None) -> list:
        task_text = task_description.strip()
        if not task_text:
            return []

        target_domains = self._infer_domains(task_text, domain)
        task_tokens = self._tokenize(task_text)
        capability_targets = self._extract_capability_targets(task_tokens)

        scored: list[dict[str, Any]] = []
        for metadata in self.tool_registry.values():
            domain_score = self._domain_score(metadata, target_domains)
            capability_score = self._capability_score(metadata, capability_targets, task_tokens)
            name_score = self._name_score(metadata["name"], task_tokens)
            success_score = float(metadata.get("success_rate", 0.0))
            score = (
                (0.45 * domain_score)
                + (0.35 * capability_score)
                + (0.1 * name_score)
                + (0.1 * success_score)
            )
            if score >= 0.25:
                row = dict(metadata)
                row["selection_score"] = round(score, 4)
                scored.append(row)

        if not scored:
            fallback = sorted(
                self.tool_registry.values(), key=lambda item: item["success_rate"], reverse=True
            )
            return [dict(item) for item in fallback[:3]]

        scored.sort(key=lambda item: (item["selection_score"], item["success_rate"]), reverse=True)

        selected = scored[:6]
        if len(target_domains) > 1:
            selected = self._ensure_cross_domain_coverage(selected, scored, target_domains)
        return selected

    def estimate_tool_combo_effectiveness(self, tools: list, task: str) -> float:
        metadata = self._resolve_tool_metadata(tools)
        if not metadata:
            return 0.0

        base = sum(float(item.get("success_rate", 0.0)) for item in metadata) / len(metadata)
        domains = {domain for item in metadata for domain in item.get("domains", [])}
        capabilities = {cap for item in metadata for cap in item.get("capabilities", [])}

        domain_bonus = min(0.08, max(0, len(domains) - 1) * 0.02)
        synergy_bonus = self._synergy_bonus(capabilities)
        alignment_bonus = self._task_alignment_bonus(metadata, task)
        complexity_penalty = max(0.0, (len(metadata) - 6) * 0.02)

        score = base + domain_bonus + synergy_bonus + alignment_bonus - complexity_penalty
        return round(max(0.0, min(1.0, score)), 4)

    def execute_tool_sequence(self, tools: list, inputs: dict) -> dict:
        metadata = self._resolve_tool_metadata(tools)
        execution_id = str(uuid.uuid4())
        if not metadata:
            return {
                "execution_id": execution_id,
                "success": False,
                "success_rate": 0.0,
                "completed": [],
                "failed": [],
                "steps": [],
                "elapsed_sec": 0.0,
                "token_usage": 0,
            }

        executors = inputs.get("executors", {})
        if not isinstance(executors, dict):
            executors = {}
        tool_inputs = inputs.get("tool_inputs", {})
        if not isinstance(tool_inputs, dict):
            tool_inputs = {}
        context = inputs.get("context", {})
        if not isinstance(context, dict):
            context = {}

        start = time.perf_counter()
        steps: list[dict[str, Any]] = []
        completed: list[str] = []
        failed: list[str] = []

        for item in metadata:
            tool_name = item["name"]
            executor = executors.get(tool_name)
            payload = tool_inputs.get(tool_name, {})
            if not isinstance(payload, dict):
                payload = {}

            step_start = time.perf_counter()
            if callable(executor):
                try:
                    output = executor(payload, context)
                    state = "success"
                    if isinstance(output, dict) and str(output.get("status", "")).lower() in {
                        "failed",
                        "error",
                    }:
                        state = "failed"
                except Exception as exc:
                    output = {"status": "failed", "error": str(exc)}
                    state = "failed"
            else:
                output = {
                    "status": "planned",
                    "message": "No executor provided; step validated for orchestration plan",
                }
                state = "planned"

            elapsed = round(time.perf_counter() - step_start, 4)
            steps.append(
                {"tool": tool_name, "state": state, "output": output, "elapsed_sec": elapsed}
            )
            context[tool_name] = output

            if state == "failed":
                failed.append(tool_name)
            else:
                completed.append(tool_name)

        total_elapsed = round(time.perf_counter() - start, 4)
        success_rate = round(len(completed) / len(metadata), 4)
        token_usage = sum(int(item.get("token_cost", 0)) for item in metadata)

        return {
            "execution_id": execution_id,
            "success": len(failed) == 0,
            "success_rate": success_rate,
            "completed": completed,
            "failed": failed,
            "steps": steps,
            "elapsed_sec": total_elapsed,
            "token_usage": token_usage,
            "final_context": context,
        }

    def evaluate_combo_performance(self, tools: list, task: str, outcome: dict) -> float:
        metadata = self._resolve_tool_metadata(tools)
        if not metadata:
            return 0.0

        predicted = self.estimate_tool_combo_effectiveness(tools, task)
        success_rate = float(outcome.get("success_rate", 0.0))
        elapsed_sec = float(outcome.get("elapsed_sec", len(metadata) * 2.0))
        token_usage = float(
            outcome.get("token_usage", sum(m.get("token_cost", 0) for m in metadata))
        )

        speed_score = max(0.0, min(1.0, 1.0 - (elapsed_sec / max(20.0, len(metadata) * 12.0))))
        cost_score = max(0.0, min(1.0, 1.0 - (token_usage / max(12000.0, len(metadata) * 1500.0))))
        observed = (0.6 * success_rate) + (0.25 * speed_score) + (0.15 * cost_score)
        final_score = round(max(0.0, min(1.0, (0.8 * observed) + (0.2 * predicted))), 4)

        for item in metadata:
            name = item["name"]
            current = float(self.tool_registry[name].get("success_rate", 0.85))
            self.tool_registry[name]["success_rate"] = round(
                (0.85 * current) + (0.15 * success_rate), 4
            )

        self.combo_history.append(
            {
                "tools": [item["name"] for item in metadata],
                "task": task,
                "predicted": predicted,
                "observed": round(observed, 4),
                "final": final_score,
            }
        )
        return final_score

    def orchestrate_task(
        self,
        task_description: str,
        domain: str | None = None,
        available_tools: list[str] | None = None,
    ) -> dict[str, Any]:
        selected = self.select_tools(task_description, domain=domain)
        if available_tools:
            allowed = set(available_tools)
            selected = [item for item in selected if item["name"] in allowed]

        selected_names = [item["name"] for item in selected]
        estimated_success = self.estimate_tool_combo_effectiveness(selected_names, task_description)
        confidence = round(
            sum(
                float(item.get("selection_score", item.get("success_rate", 0.0)))
                for item in selected
            )
            / max(len(selected), 1),
            4,
        )

        execution_steps = [
            {
                "step": idx + 1,
                "tool": item["name"],
                "purpose": item["capability"],
                "estimated_latency_sec": item["avg_latency_sec"],
            }
            for idx, item in enumerate(selected)
        ]

        return {
            "selected_tools": selected_names,
            "confidence": confidence,
            "estimated_success_rate": estimated_success,
            "execution_plan": {
                "domains": sorted({d for item in selected for d in item.get("domains", [])}),
                "steps": execution_steps,
                "estimated_time_sec": round(
                    sum(step["estimated_latency_sec"] for step in execution_steps), 2
                ),
                "estimated_token_cost": sum(int(item.get("token_cost", 0)) for item in selected),
            },
        }

    def _discover_tools(self) -> list[dict[str, Any]]:
        tools_dir = Path(__file__).resolve().parents[1] / "tools"
        discovered: list[dict[str, Any]] = []
        for file_path in sorted(tools_dir.glob("*.py")):
            if file_path.name == "__init__.py":
                continue
            module = file_path.stem
            default_domains = self.MODULE_DOMAIN_MAP.get(module, ["se"])
            try:
                tree = ast.parse(file_path.read_text(encoding="utf-8"))
            except Exception:
                continue

            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef):
                    continue
                if not self._has_mcp_tool_decorator(node):
                    continue

                capabilities = self._infer_capabilities(node.name, module)
                domain = default_domains[0]
                discovered.append(
                    {
                        "name": node.name,
                        "domain": domain,
                        "domains": default_domains,
                        "capability": capabilities[0],
                        "capabilities": capabilities,
                        "success_rate": self._base_success_rate(module, node.name),
                        "avg_latency_sec": self._base_latency(module, node.name),
                        "token_cost": self._base_token_cost(module, node.name),
                        "module": module,
                    }
                )
        return discovered

    def _has_mcp_tool_decorator(self, node: ast.FunctionDef) -> bool:
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                func = decorator.func
                if isinstance(func, ast.Attribute) and func.attr == "tool":
                    return True
            if isinstance(decorator, ast.Attribute) and decorator.attr == "tool":
                return True
        return False

    def _infer_capabilities(self, tool_name: str, module: str) -> list[str]:
        text = f"{tool_name} {module}".lower()
        matched: list[str] = []
        for capability, keywords in self.CAPABILITY_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                matched.append(capability)
        if not matched:
            matched.append("coordination")
        return matched

    def _base_success_rate(self, module: str, tool_name: str) -> float:
        text = f"{module} {tool_name}".lower()
        if any(keyword in text for keyword in ["check", "list", "get", "status", "view"]):
            return 0.93
        if any(keyword in text for keyword in ["run", "simulate", "evaluate", "review"]):
            return 0.86
        if any(keyword in text for keyword in ["upgrade", "rollback", "delete", "remove"]):
            return 0.82
        return 0.88

    def _base_latency(self, module: str, tool_name: str) -> float:
        text = f"{module} {tool_name}".lower()
        if any(keyword in text for keyword in ["run", "simulate", "evaluate", "review"]):
            return 4.0
        if any(keyword in text for keyword in ["search", "match", "analyze"]):
            return 2.8
        return 1.6

    def _base_token_cost(self, module: str, tool_name: str) -> int:
        text = f"{module} {tool_name}".lower()
        if any(keyword in text for keyword in ["run", "simulate", "report", "evaluate", "review"]):
            return 1800
        if any(keyword in text for keyword in ["search", "match", "analyze", "question"]):
            return 1300
        return 700

    def _normalize_domain(self, domain: str) -> str:
        value = (domain or "").strip().lower()
        if not value:
            return ""
        for key, config in self.DOMAIN_DEFINITIONS.items():
            aliases = [key, *(str(alias).lower() for alias in config.get("aliases", []))]
            if value in aliases:
                return key
        return ""

    def _infer_domains(self, task_description: str, explicit_domain: str | None) -> list[str]:
        normalized = self._normalize_domain(explicit_domain or "")
        if normalized:
            return [normalized]

        task_text = task_description.lower()
        scores: dict[str, int] = {}
        explicit_hits: set[str] = set()
        for key, config in self.DOMAIN_DEFINITIONS.items():
            aliases = [key, *(str(alias).lower() for alias in config.get("aliases", []))]
            keywords = [str(item).lower() for item in config.get("keywords", [])]
            if any(alias in task_text for alias in aliases):
                explicit_hits.add(key)
            points = sum(1 for term in aliases + keywords if term in task_text)
            if points > 0:
                scores[key] = points

        if not scores:
            return ["se"]

        max_score = max(scores.values())
        inferred = {domain for domain, score in scores.items() if score >= max_score - 1}
        inferred.update(explicit_hits)
        return sorted(inferred)

    def _tokenize(self, text: str) -> set[str]:
        return {token for token in re.findall(r"[a-z]+", text.lower()) if len(token) >= 3}

    def _extract_capability_targets(self, tokens: set[str]) -> set[str]:
        targets: set[str] = set()
        for capability, keywords in self.CAPABILITY_KEYWORDS.items():
            if any(keyword.split(" ")[0] in tokens for keyword in keywords):
                targets.add(capability)
        if not targets:
            targets.add("coordination")
        return targets

    def _domain_score(self, metadata: dict[str, Any], target_domains: list[str]) -> float:
        tool_domains = set(metadata.get("domains", []))
        if not target_domains:
            return 0.5
        overlap = tool_domains.intersection(target_domains)
        return len(overlap) / len(set(target_domains))

    def _capability_score(
        self,
        metadata: dict[str, Any],
        capability_targets: set[str],
        task_tokens: set[str],
    ) -> float:
        tool_capabilities = set(metadata.get("capabilities", []))
        direct = len(tool_capabilities.intersection(capability_targets)) / max(
            len(capability_targets), 1
        )

        keyword_hits = 0
        keyword_pool = [
            keyword
            for cap in tool_capabilities
            for keyword in self.CAPABILITY_KEYWORDS.get(cap, [])
        ]
        for keyword in keyword_pool:
            if keyword.split(" ")[0] in task_tokens:
                keyword_hits += 1

        keyword_score = min(1.0, keyword_hits / 3.0)
        return min(1.0, (0.7 * direct) + (0.3 * keyword_score))

    def _name_score(self, tool_name: str, task_tokens: set[str]) -> float:
        name_tokens = set(tool_name.lower().split("_"))
        overlap = name_tokens.intersection(task_tokens)
        return min(1.0, len(overlap) / 2.0)

    def _synergy_bonus(self, capabilities: set[str]) -> float:
        total = 0.0
        for first, second, bonus in self.SYNERGY_RULES:
            if first in capabilities and second in capabilities:
                total += bonus
        return min(0.2, total)

    def _task_alignment_bonus(self, metadata: list[dict[str, Any]], task: str) -> float:
        task_tokens = self._tokenize(task)
        if not task_tokens:
            return 0.0
        hit_count = 0
        for item in metadata:
            name_tokens = set(item["name"].lower().split("_"))
            capability_tokens = {
                keyword.split(" ")[0]
                for capability in item.get("capabilities", [])
                for keyword in self.CAPABILITY_KEYWORDS.get(capability, [])
            }
            if name_tokens.intersection(task_tokens) or capability_tokens.intersection(task_tokens):
                hit_count += 1
        return min(0.08, (hit_count / len(metadata)) * 0.08)

    def _ensure_cross_domain_coverage(
        self,
        selected: list[dict[str, Any]],
        scored: list[dict[str, Any]],
        target_domains: list[str],
    ) -> list[dict[str, Any]]:
        covered = {domain for item in selected for domain in item.get("domains", [])}
        output = list(selected)
        for domain in target_domains:
            if domain in covered:
                continue
            candidate = next((item for item in scored if domain in item.get("domains", [])), None)
            if candidate is None:
                fallback = next(
                    (
                        item
                        for item in sorted(
                            self.tool_registry.values(),
                            key=lambda row: float(row.get("success_rate", 0.0)),
                            reverse=True,
                        )
                        if domain in item.get("domains", [])
                    ),
                    None,
                )
                if fallback is not None:
                    candidate = dict(fallback)
                    candidate["selection_score"] = float(candidate.get("selection_score", 0.25))
            if candidate is None:
                continue
            output.append(candidate)
            covered.update(candidate.get("domains", []))
        unique: dict[str, dict[str, Any]] = {}
        for item in output:
            unique[item["name"]] = item
        deduped = list(unique.values())
        deduped.sort(key=lambda row: row.get("selection_score", 0.0), reverse=True)
        return deduped[:6]

    def _resolve_tool_metadata(self, tools: list) -> list[dict[str, Any]]:
        resolved: list[dict[str, Any]] = []
        for item in tools:
            if isinstance(item, dict):
                name = str(item.get("name", "")).strip()
            else:
                name = str(item).strip()
            if name and name in self.tool_registry:
                resolved.append(self.tool_registry[name])
        return resolved

    def get_domain_definitions(self) -> dict[str, dict[str, Any]]:
        return self.DOMAIN_DEFINITIONS

    def benchmark_selection_accuracy(self, benchmark: list[dict[str, Any]]) -> dict[str, Any]:
        if not benchmark:
            return {"cases": 0, "accuracy": 0.0}

        scores: list[float] = []
        for case in benchmark:
            task = str(case.get("task", ""))
            domain = str(case.get("domain", ""))
            expert_tools = set(case.get("expert_tools", []))
            selected = {item["name"] for item in self.select_tools(task, domain=domain)}
            if not expert_tools:
                continue
            recall = len(selected.intersection(expert_tools)) / len(expert_tools)
            scores.append(recall)

        accuracy = sum(scores) / len(scores) if scores else 0.0
        return {"cases": len(scores), "accuracy": round(accuracy, 4)}

    def benchmark_execution_success(self, tools: list[str]) -> dict[str, Any]:
        metadata = self._resolve_tool_metadata(tools)
        if not metadata:
            return {"tool_count": 0, "mean_success_rate": 0.0}
        mean_success = sum(item["success_rate"] for item in metadata) / len(metadata)
        return {"tool_count": len(metadata), "mean_success_rate": round(mean_success, 4)}
