# Trust Calibration in CRANE

`TrustCalibrationService` introduces explainable autonomy control for AI-assisted research workflows.

## Autonomy Levels

- **Level 0 — Pure Assistance**
  - The tool suggests actions only.
  - Human confirmation is always required.
  - Permission mapping: `soft_deny` behavior (`ask`).

- **Level 1 — Semi-Autonomous**
  - The tool can act only for high-confidence, low-risk actions.
  - Uncertain actions are escalated to human review.
  - Permission mapping: high-confidence actions `allow`, uncertain actions `ask`.

- **Level 2 — Mostly Autonomous**
  - The tool acts automatically for most routine actions.
  - High-risk or high-uncertainty actions still require confirmation.
  - Permission mapping: default `allow`, high-risk/high-uncertainty `ask`.

- **Level 3 — Full Autonomy**
  - The tool executes actions autonomously.
  - Post-action logging is mandatory for accountability.
  - Permission mapping: `allow` + logging requirement.

## Explainable Inputs Used for Calibration

Calibration decisions are based on:

- AI output confidence
- evidence span coverage and missing evidence indicators
- contradiction/hallucination signals
- task risk level
- user trust/risk preferences
- user feedback trends (accept/reject/override/error)

The returned structure is:

```json
{
  "autonomy_level": 2,
  "uncertainty": 0.31,
  "recommended_action": "execute_with_monitoring",
  "responsibility": {"human_pct": 35.0, "ai_pct": 65.0},
  "trust_score": 0.72
}
```
