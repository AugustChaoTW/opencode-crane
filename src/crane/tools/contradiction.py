"""Contradiction detection MCP tool."""

from __future__ import annotations

from typing import Any

from crane.services.contradiction_detection_service import ContradictionDetectionService


def register_tools(mcp):
    """Register contradiction detection tool with the MCP server."""

    @mcp.tool()
    def detect_contradictions(
        paper_path: str,
        types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Detect contradictions in a research paper across four layers.

        Runs up to four detectors depending on *types*:

        - **numerical**      – hyperparameter/metric mismatches between paper
          and sibling code files (via PaperCodeAlignmentService).
        - **claim_evidence** – strong claims (state-of-the-art, novel, …) with
          no supporting number or citation within ±200 characters.
        - **cross_section**  – semantic conflicts between section pairs, using
          embedding-based pre-filtering + LLM judgement (or keyword fallback).
        - **citation**       – "contradicts" edges extracted from the paper's
          knowledge graph.

        Args:
            paper_path: Path to the .tex or .pdf paper file.
            types:      List of detector types to run.  Omit (or pass null) to
                        run all four.  Valid values: "numerical",
                        "claim_evidence", "cross_section", "citation".

        Returns:
            Dict with total count, high-severity count, and contradiction list.

        Example output::

            {
              "total": 3,
              "high_severity": 1,
              "contradictions": [
                {
                  "type": "cross_section",
                  "location_a": "Abstract",
                  "location_b": "Table 3",
                  "description": "Abstract claims 15% improvement; Table 3 shows 2.3%",
                  "severity": "high",
                  "reviewer_attack_prob": 0.87,
                  "suggested_fix": "Correct Abstract figure or explain discrepancy"
                }
              ]
            }
        """
        svc = ContradictionDetectionService()
        contradictions = svc.detect(paper_path=paper_path, types=types)

        contradiction_dicts = [c.to_dict() for c in contradictions]
        high_count = sum(1 for c in contradictions if c.severity == "high")

        return {
            "total": len(contradiction_dicts),
            "high_severity": high_count,
            "contradictions": contradiction_dicts,
        }
