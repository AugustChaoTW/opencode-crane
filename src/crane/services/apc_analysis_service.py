from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from crane.models.paper_profile import CostAssessment, JournalFit


class APCAnalysisService:
    """Analyze APC costs and provide budget-aware journal recommendations."""

    def __init__(self, profiles_path: str | Path | None = None):
        root = Path(__file__).resolve().parents[3]
        self.profiles_path = (
            Path(profiles_path)
            if profiles_path is not None
            else root / "data" / "journals" / "q1_journal_profiles.yaml"
        )
        self.journals = self._load_profiles(self.profiles_path)

    def _load_profiles(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            raise FileNotFoundError(f"Journal profiles file not found: {path}")

        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or "journals" not in raw:
            raise ValueError("Journal profiles YAML must be a mapping with a 'journals' key")

        journals = raw.get("journals", [])
        if not isinstance(journals, list):
            raise ValueError("'journals' must be a list")
        return [journal for journal in journals if isinstance(journal, dict)]

    def assess_cost(self, journal: dict, budget_usd: float | None = None) -> CostAssessment:
        """Assess cost for a single journal given a budget."""
        apc_usd = float(journal.get("apc_usd", 0.0) or 0.0)
        publication_model = str(journal.get("open_access_type", "unknown") or "unknown").lower()
        waiver_available = bool(journal.get("waiver_available", False))

        if budget_usd is None:
            status = "no_budget"
            delta = 0.0
        elif apc_usd == 0 and publication_model in {"subscription", "diamond_oa"}:
            status = "within_budget"
            delta = budget_usd
        elif apc_usd <= budget_usd:
            status = "within_budget"
            delta = budget_usd - apc_usd
        elif apc_usd <= budget_usd * 1.1:
            status = "near_budget"
            delta = budget_usd - apc_usd
        else:
            status = "over_budget"
            delta = budget_usd - apc_usd
            if waiver_available:
                status = "waiver_possible"

        return CostAssessment(
            apc_usd=apc_usd,
            publication_model=publication_model
            if publication_model in {"subscription", "gold_oa", "hybrid", "diamond_oa", "unknown"}
            else "unknown",
            affordability_status=status,
            budget_delta_usd=delta,
            apc_stale=self._is_apc_stale(journal),
            waiver_available=waiver_available,
        )

    def rank_by_affordability(
        self,
        fits: list[JournalFit],
        costs: list[CostAssessment],
        budget_usd: float | None = None,
    ) -> list[tuple[JournalFit, CostAssessment]]:
        """Re-rank journal fits by affordability bucket, then by fit score."""
        pairs = list(zip(fits, costs, strict=False))
        bucket_order = {
            "within_budget": 0,
            "near_budget": 1,
            "waiver_possible": 2,
            "over_budget": 3,
            "no_budget": 4,
        }

        if budget_usd is None:
            return sorted(
                pairs,
                key=lambda item: (-item[0].overall_fit, item[1].apc_usd, item[0].journal_name),
            )

        ranked = sorted(
            pairs,
            key=lambda item: (
                bucket_order.get(item[1].affordability_status, 99),
                -item[0].overall_fit,
                item[1].apc_usd,
                item[0].journal_name,
            ),
        )
        return ranked

    def generate_apc_report(
        self,
        fits: list[JournalFit],
        costs: list[CostAssessment],
        budget_usd: float | None = None,
    ) -> str:
        """Generate markdown APC comparison report."""
        ranked = self.rank_by_affordability(fits, costs, budget_usd=budget_usd)
        total = len(ranked)
        affordable = sum(
            1 for _, cost in ranked if cost.affordability_status in {"within_budget", "near_budget"}
        )
        budget_text = f"${budget_usd:,.0f}" if budget_usd is not None else "Not specified"

        lines = [
            "# APC Analysis Report",
            "",
            f"**Budget**: {budget_text} | **Affordable journals**: {affordable}/{total}",
            "",
        ]

        sections = [
            ("Within Budget", {"within_budget"}),
            ("Near Budget (within 10%)", {"near_budget"}),
            ("Waiver Possible", {"waiver_possible"}),
            ("Over Budget", {"over_budget"}),
            ("No Budget", {"no_budget"}),
        ]

        for title, statuses in sections:
            lines.append(f"## {title}")
            lines.append("| Journal | APC | Fit Score | Model | Status |")
            lines.append("|---------|-----|-----------|-------|--------|")
            rows = [(fit, cost) for fit, cost in ranked if cost.affordability_status in statuses]
            if not rows:
                lines.append("| - | - | - | - | - |")
            else:
                for fit, cost in rows:
                    status = cost.affordability_status.replace("_", " ")
                    lines.append(
                        f"| {fit.journal_name} | ${cost.apc_usd:,.0f} | {fit.overall_fit:.2f} | "
                        f"{cost.publication_model} | {status} |"
                    )
            lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def _is_apc_stale(self, journal: dict[str, Any]) -> bool:
        timestamp = str(journal.get("apc_last_updated", "") or "").strip()
        if not timestamp:
            return False

        try:
            updated = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=UTC)
        except ValueError:
            return False

        age_days = (datetime.now(tz=UTC) - updated.astimezone(UTC)).days
        return age_days > 183
