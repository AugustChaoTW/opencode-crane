from __future__ import annotations

from typing import Any

from crane.services.trust_calibration_service import TrustCalibrationService


def register_tools(mcp):
    @mcp.tool()
    def calibrate_trust(
        task_description: str,
        ai_output: dict[str, Any],
        autonomy_level: int = 1,
        user_preferences: dict[str, Any] | None = None,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        service = TrustCalibrationService()
        preferences = user_preferences or {}
        risk_score = preferences.get("risk_score")
        decisions = (
            preferences.get("decisions") if isinstance(preferences.get("decisions"), list) else []
        )

        return service.evaluate_calibration(
            task=task_description,
            output=ai_output,
            autonomy_level=autonomy_level,
            user_preferences=preferences,
            risk_score=float(risk_score) if isinstance(risk_score, int | float) else None,
            decisions=decisions,
            project_dir=project_dir,
        )
