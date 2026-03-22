"""Screening and comparison workflow tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from crane.services.reference_service import ReferenceService


class ScreeningDecision(Enum):
    INCLUDE = "include"
    EXCLUDE = "exclude"
    MAYBE = "maybe"


@dataclass
class ScreeningResult:
    paper_key: str
    decision: ScreeningDecision
    reason: str
    criteria: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ComparisonDimension:
    name: str
    values: dict[str, str] = field(default_factory=dict)


@dataclass
class ComparisonMatrix:
    papers: list[str]
    dimensions: list[ComparisonDimension] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "papers": self.papers,
            "dimensions": [{"name": d.name, "values": d.values} for d in self.dimensions],
        }


class ScreeningService:
    """Service for reference screening and comparison."""

    def __init__(self, refs_dir: str | Path = "references"):
        self.ref_service = ReferenceService(refs_dir)

    def screen(
        self,
        paper_key: str,
        decision: str,
        reason: str = "",
        criteria: list[str] | None = None,
    ) -> ScreeningResult:
        """Record a screening decision for a paper."""
        try:
            dec = ScreeningDecision(decision.lower())
        except ValueError:
            raise ValueError(f"Invalid decision: {decision}. Use include/exclude/maybe")

        data = self.ref_service.get(paper_key)

        result = ScreeningResult(
            paper_key=paper_key,
            decision=dec,
            reason=reason,
            criteria=criteria or [],
        )

        existing = data.get("screening", {})
        existing["decision"] = dec.value
        existing["reason"] = reason
        existing["criteria"] = criteria or []
        existing["timestamp"] = result.timestamp

        from crane.utils.yaml_io import write_paper_yaml

        data["screening"] = existing
        papers_dir = str(Path(self.ref_service.refs_path) / "papers")
        write_paper_yaml(papers_dir, paper_key, data)

        return result

    def list_screened(
        self,
        decision: str | None = None,
    ) -> list[dict[str, Any]]:
        """List all screened references with optional decision filter."""
        results = []
        for key in self.ref_service.get_all_keys():
            data = self.ref_service.get(key)
            screening = data.get("screening", {})
            if not screening:
                continue

            if decision and screening.get("decision") != decision:
                continue

            results.append(
                {
                    "key": key,
                    "title": data.get("title", ""),
                    "decision": screening.get("decision", ""),
                    "reason": screening.get("reason", ""),
                    "criteria": screening.get("criteria", []),
                }
            )

        return results

    def compare(
        self,
        paper_keys: list[str],
        dimensions: list[str] | None = None,
    ) -> ComparisonMatrix:
        """Create a comparison matrix for multiple papers."""
        if len(paper_keys) < 2:
            raise ValueError("Need at least 2 papers to compare")

        default_dimensions = [
            "year",
            "authors",
            "venue",
            "methodology",
            "dataset",
            "metric",
            "result",
        ]

        dims = dimensions or default_dimensions

        papers_data = {}
        for key in paper_keys:
            try:
                papers_data[key] = self.ref_service.get(key)
            except ValueError:
                raise ValueError(f"Paper not found: {key}")

        comparison_dims = []
        for dim_name in dims:
            dim = ComparisonDimension(name=dim_name)
            for key, data in papers_data.items():
                value = self._extract_dimension(data, dim_name)
                dim.values[key] = value
            comparison_dims.append(dim)

        return ComparisonMatrix(
            papers=paper_keys,
            dimensions=comparison_dims,
        )

    def _extract_dimension(self, data: dict[str, Any], dimension: str) -> str:
        """Extract a specific dimension value from paper data."""
        if dimension == "year":
            return str(data.get("year", ""))
        elif dimension == "authors":
            authors = data.get("authors", [])
            if isinstance(authors, list):
                return ", ".join(str(a) for a in authors[:3])
            return str(authors)
        elif dimension == "venue":
            return str(data.get("venue", ""))
        elif dimension == "doi":
            return str(data.get("doi", ""))

        annotations = data.get("ai_annotations", {}) or {}
        if dimension == "methodology":
            return str(annotations.get("methodology", ""))
        elif dimension == "key_contributions":
            contributions = annotations.get("key_contributions", [])
            if isinstance(contributions, list):
                return "; ".join(str(c) for c in contributions[:3])
            return str(contributions)

        return str(data.get(dimension, ""))
