from __future__ import annotations

from typing import Any

from crane.services.permission_rule_service import PermissionRuleService


class TrustCalibrationService:
    AUTONOMY_LEVELS = {
        0: "Pure Assistance",
        1: "Semi-Autonomous",
        2: "Mostly Autonomous",
        3: "Full Autonomy",
    }

    HIGH_CONFIDENCE_UNCERTAINTY = 0.25
    MODERATE_UNCERTAINTY = 0.55
    HIGH_UNCERTAINTY = 0.75

    MODERATE_RISK = 0.60
    HIGH_RISK = 0.80

    def __init__(self):
        self.trust_score = 0.65
        self.feedback_history: list[dict[str, Any]] = []

    def quantify_uncertainty(self, output: dict[str, Any], task: str) -> float:
        confidence = self._clamp(self._to_float(output.get("confidence", 0.5)), 0.0, 1.0)
        base_uncertainty = 1.0 - confidence

        evidence_spans = output.get("evidence_spans", [])
        evidence_count = len(evidence_spans) if isinstance(evidence_spans, list) else 0
        if evidence_count >= 3:
            evidence_penalty = 0.0
        elif evidence_count >= 1:
            evidence_penalty = 0.12
        else:
            evidence_penalty = 0.25

        missing_evidence = output.get("missing_evidence", [])
        missing_count = len(missing_evidence) if isinstance(missing_evidence, list) else 0
        missing_penalty = min(0.25, missing_count * 0.08)

        contradictions = output.get("contradictions", [])
        contradiction_count = len(contradictions) if isinstance(contradictions, list) else 0
        contradiction_penalty = min(0.20, contradiction_count * 0.10)

        hallucination_penalty = 0.25 if bool(output.get("hallucination_detected", False)) else 0.0
        complexity_penalty = self._task_complexity_penalty(task)

        uncertainty = (
            base_uncertainty * 0.55
            + evidence_penalty
            + missing_penalty
            + contradiction_penalty
            + hallucination_penalty
            + complexity_penalty
        )
        return round(self._clamp(uncertainty, 0.0, 1.0), 4)

    def get_autonomy_level(self, task: str, user_preferences: dict[str, Any]) -> int:
        if bool(user_preferences.get("require_human_approval", False)):
            return 0

        preferred_level = user_preferences.get("preferred_autonomy_level")
        if isinstance(preferred_level, int):
            base_level = self._clamp_level(preferred_level)
        else:
            user_trust = self._clamp(
                self._to_float(user_preferences.get("trust_score", self.trust_score)),
                0.0,
                1.0,
            )
            risk_tolerance = self._clamp(
                self._to_float(user_preferences.get("risk_tolerance", 0.5)),
                0.0,
                1.0,
            )
            base_level = self._derive_level_from_profile(user_trust, risk_tolerance)

        if self._is_high_risk_task(task):
            return max(0, base_level - 1)
        return base_level

    def adjust_autonomy(self, current_level: int, uncertainty: float, risk_score: float) -> int:
        level = self._clamp_level(current_level)
        uncertainty = self._clamp(uncertainty, 0.0, 1.0)
        risk_score = self._clamp(risk_score, 0.0, 1.0)

        if uncertainty >= self.HIGH_UNCERTAINTY or risk_score >= self.HIGH_RISK:
            return max(0, level - 2)

        if uncertainty >= self.MODERATE_UNCERTAINTY or risk_score >= self.MODERATE_RISK:
            return max(0, level - 1)

        if uncertainty <= 0.15 and risk_score <= 0.20 and self.trust_score >= 0.80:
            return min(3, level + 2)

        if uncertainty <= self.HIGH_CONFIDENCE_UNCERTAINTY and risk_score <= 0.35:
            return min(3, level + 1)

        return level

    def generate_responsibility_report(self, decisions: list[dict[str, Any]]) -> dict[str, Any]:
        if not decisions:
            return {
                "human_pct": 50.0,
                "ai_pct": 50.0,
                "human_decisions": 0,
                "ai_decisions": 0,
                "total_decisions": 0,
            }

        human_weight = 0.0
        ai_weight = 0.0
        human_decisions = 0
        ai_decisions = 0

        for decision in decisions:
            actor = str(decision.get("actor", "ai")).strip().lower()
            level = self._clamp_level(decision.get("autonomy_level", 1))

            if actor == "human":
                human_weight += 1.0
                human_decisions += 1
            else:
                ai_weight += 1.0
                ai_decisions += 1

            if bool(decision.get("requires_human", False)):
                human_weight += 0.5

            if bool(decision.get("overridden_by_human", False)):
                human_weight += 0.75
                ai_weight = max(0.0, ai_weight - 0.25)

            if level <= 1:
                human_weight += 0.2
            elif level >= 2:
                ai_weight += 0.2

        total_weight = human_weight + ai_weight
        if total_weight <= 0:
            human_pct = 50.0
            ai_pct = 50.0
        else:
            human_pct = round((human_weight / total_weight) * 100.0, 2)
            ai_pct = round((ai_weight / total_weight) * 100.0, 2)

        return {
            "human_pct": human_pct,
            "ai_pct": ai_pct,
            "human_decisions": human_decisions,
            "ai_decisions": ai_decisions,
            "total_decisions": len(decisions),
        }

    def calibrate_trust(self, user_feedback: dict[str, Any]) -> dict[str, Any]:
        previous = self.trust_score

        satisfaction = self._clamp(self._to_float(user_feedback.get("satisfaction", 0.5)), 0.0, 1.0)
        accepted = max(0, int(self._to_float(user_feedback.get("accepted_recommendations", 0.0))))
        rejected = max(0, int(self._to_float(user_feedback.get("rejected_recommendations", 0.0))))
        override_rate = self._clamp(
            self._to_float(user_feedback.get("override_rate", 0.0)), 0.0, 1.0
        )
        error_reports = max(0, int(self._to_float(user_feedback.get("error_reports", 0.0))))

        total_feedback = accepted + rejected
        acceptance_ratio = accepted / total_feedback if total_feedback > 0 else 0.5

        alignment_score = (
            satisfaction * 0.50 + acceptance_ratio * 0.35 + (1.0 - override_rate) * 0.15
        )
        penalty = min(0.20, error_reports * 0.05)
        target_score = self._clamp(alignment_score - penalty, 0.0, 1.0)

        self.trust_score = round(self._clamp(previous * 0.60 + target_score * 0.40, 0.0, 1.0), 4)

        delta = round(self.trust_score - previous, 4)
        if delta > 0.02:
            trend = "increasing"
        elif delta < -0.02:
            trend = "decreasing"
        else:
            trend = "stable"

        if self.trust_score < 0.45:
            autonomy_cap = 1
        elif self.trust_score < 0.75:
            autonomy_cap = 2
        else:
            autonomy_cap = 3

        snapshot = {
            "trust_score": self.trust_score,
            "previous_trust_score": previous,
            "delta": delta,
            "trend": trend,
            "recommended_autonomy_cap": autonomy_cap,
        }
        self.feedback_history.append(snapshot)
        return snapshot

    def permission_decision_for_level(
        self,
        task: str,
        autonomy_level: int,
        uncertainty: float,
        risk_score: float,
        project_dir: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        level = self._clamp_level(autonomy_level)
        uncertainty = self._clamp(uncertainty, 0.0, 1.0)
        risk_score = self._clamp(risk_score, 0.0, 1.0)

        permission_service = PermissionRuleService(project_dir=project_dir)
        baseline = permission_service.evaluate_action(action=task, context=context)

        requires_logging = False
        if level == 0:
            final_decision = "ask"
            rationale = "Level 0 enforces human confirmation for all actions."
        elif level == 1:
            if baseline == "allow" and uncertainty <= self.HIGH_CONFIDENCE_UNCERTAINTY:
                final_decision = "allow"
                rationale = "Level 1 allows only high-confidence actions permitted by rules."
            elif baseline == "deny":
                final_decision = "deny"
                rationale = "Permission rules deny this action."
            else:
                final_decision = "ask"
                rationale = "Level 1 routes uncertain actions to human confirmation."
        elif level == 2:
            if baseline == "deny":
                final_decision = "deny"
                rationale = "Permission rules deny this action."
            elif uncertainty >= self.HIGH_UNCERTAINTY or risk_score >= self.HIGH_RISK:
                final_decision = "ask"
                rationale = "Level 2 asks human on high-risk or high-uncertainty actions."
            else:
                final_decision = "allow"
                rationale = "Level 2 auto-allows non-critical actions."
        else:
            final_decision = "allow"
            requires_logging = True
            rationale = "Level 3 enables full autonomy with mandatory post-action logging."

        return {
            "baseline_permission": baseline,
            "decision": final_decision,
            "requires_logging": requires_logging,
            "rationale": rationale,
        }

    def evaluate_calibration(
        self,
        task: str,
        output: dict[str, Any],
        autonomy_level: int,
        user_preferences: dict[str, Any] | None = None,
        risk_score: float | None = None,
        decisions: list[dict[str, Any]] | None = None,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        preferences = user_preferences or {}
        uncertainty = self.quantify_uncertainty(output=output, task=task)

        baseline_level = self.get_autonomy_level(task=task, user_preferences=preferences)
        current_level = min(self._clamp_level(autonomy_level), baseline_level)

        if risk_score is None:
            risk_score = self._estimate_risk(task=task, output=output)
        risk_score = self._clamp(risk_score, 0.0, 1.0)

        adjusted_level = self.adjust_autonomy(
            current_level=current_level,
            uncertainty=uncertainty,
            risk_score=risk_score,
        )

        permission_result = self.permission_decision_for_level(
            task=task,
            autonomy_level=adjusted_level,
            uncertainty=uncertainty,
            risk_score=risk_score,
            project_dir=project_dir,
            context=preferences.get("permission_context")
            if isinstance(preferences, dict)
            else None,
        )

        responsibility = self.generate_responsibility_report(decisions or [])
        if "feedback" in preferences and isinstance(preferences["feedback"], dict):
            trust_update = self.calibrate_trust(preferences["feedback"])
            current_trust = trust_update["trust_score"]
        else:
            current_trust = self.trust_score

        recommended_action = self._recommended_action(
            permission_decision=permission_result["decision"],
            autonomy_level=adjusted_level,
        )

        return {
            "autonomy_level": adjusted_level,
            "autonomy_level_name": self.AUTONOMY_LEVELS[adjusted_level],
            "uncertainty": uncertainty,
            "risk_score": round(risk_score, 4),
            "recommended_action": recommended_action,
            "responsibility": {
                "human_pct": responsibility["human_pct"],
                "ai_pct": responsibility["ai_pct"],
            },
            "trust_score": round(current_trust, 4),
            "permission_decision": permission_result["decision"],
            "baseline_permission": permission_result["baseline_permission"],
            "requires_logging": permission_result["requires_logging"],
            "explanation": permission_result["rationale"],
        }

    def _derive_level_from_profile(self, trust_score: float, risk_tolerance: float) -> int:
        if trust_score < 0.45 or risk_tolerance < 0.30:
            return 0
        if trust_score < 0.65 or risk_tolerance < 0.50:
            return 1
        if trust_score < 0.82 or risk_tolerance < 0.80:
            return 2
        return 3

    def _recommended_action(self, permission_decision: str, autonomy_level: int) -> str:
        if permission_decision == "deny":
            return "block_and_request_confirmation"
        if permission_decision == "ask":
            return "request_human_confirmation"
        if autonomy_level >= 2:
            return "execute_with_monitoring"
        return "suggest_and_wait_for_human"

    def _estimate_risk(self, task: str, output: dict[str, Any]) -> float:
        explicit = output.get("risk_score")
        if isinstance(explicit, int | float):
            return float(explicit)

        risk = 0.25
        lowered_task = task.lower()
        high_risk_markers = (
            "delete",
            "submit",
            "publish",
            "overwrite",
            "production",
            "external",
            "credentials",
        )
        if any(marker in lowered_task for marker in high_risk_markers):
            risk += 0.40

        if bool(output.get("hallucination_detected", False)):
            risk += 0.20

        missing_evidence = output.get("missing_evidence", [])
        if isinstance(missing_evidence, list):
            risk += min(0.20, len(missing_evidence) * 0.05)

        return risk

    def _is_high_risk_task(self, task: str) -> bool:
        lowered = task.lower()
        return any(
            marker in lowered
            for marker in ("delete", "submit", "publish", "overwrite", "credentials", "external")
        )

    def _task_complexity_penalty(self, task: str) -> float:
        lowered = task.lower()
        cues = ("novel", "hypothesis", "exploratory", "open-ended", "unclear")
        return 0.10 if any(cue in lowered for cue in cues) else 0.0

    def _clamp(self, value: float, lower: float, upper: float) -> float:
        return max(lower, min(upper, value))

    def _clamp_level(self, level: Any) -> int:
        numeric = int(self._to_float(level, default=0.0))
        return int(self._clamp(float(numeric), 0.0, 3.0))

    def _to_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
