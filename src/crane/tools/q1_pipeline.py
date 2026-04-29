"""CARE Q1 Elevation Pipeline — CARE main flow MCP tool.

Stages:
  C — Contradiction detection
  A — Awareness / Knowledge gap elevation
  R — Reasoning / Research positioning
  E — Explainability / Feynman evidence evaluation
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from crane.services.contradiction_detection_service import ContradictionDetectionService
from crane.services.evidence_evaluation_service import EvidenceEvaluationService
from crane.services.feynman_session_service import FeynmanSessionService
from crane.services.knowledge_gap_elevation_service import KnowledgeGapElevationService
from crane.services.paper_knowledge_graph_service import PaperKnowledgeGraphService
from crane.services.research_positioning_service import ResearchPositioningService
from crane.services.section_chunker import SectionChunker

# ---------------------------------------------------------------------------
# Path auto-detection helpers
# ---------------------------------------------------------------------------


def _resolve_paper_path(paper_path: str | None) -> str:
    """Resolve paper path from argument, Paper Trace YAML, or workspace scan."""
    if paper_path:
        return paper_path

    # 1. Read _paper_trace/v2/1_contribution.yaml's paper_path field
    trace = Path("_paper_trace/v2/1_contribution.yaml")
    if trace.exists():
        try:
            data = yaml.safe_load(trace.read_text()) or {}
            if data.get("paper_path") and data["paper_path"] != ".":
                return data["paper_path"]
        except Exception:
            pass

    # 2. Scan workspace for a unique .tex or .pdf file
    for pattern in ["*.tex", "*.pdf"]:
        files = list(Path(".").glob(pattern))
        if len(files) == 1:
            return str(files[0])

    raise ValueError("Cannot auto-detect paper_path — please provide it explicitly.")


def _resolve_journal(target_journal: str | None) -> str | None:
    """Resolve target journal from argument or submission config."""
    if target_journal:
        return target_journal
    config = Path(".crane/journal-system/submission-config.yaml")
    if config.exists():
        try:
            data = yaml.safe_load(config.read_text()) or {}
            return data.get("target_journal") or data.get("journal")
        except Exception:
            pass
    return None


# ---------------------------------------------------------------------------
# SHA-256 helper
# ---------------------------------------------------------------------------


def _sha256(paper_path: str) -> str:
    """Return SHA-256 hex digest of a file, or empty string on error."""
    try:
        return hashlib.sha256(Path(paper_path).read_bytes()).hexdigest()
    except FileNotFoundError:
        return ""


# ---------------------------------------------------------------------------
# Stage cache helpers
# ---------------------------------------------------------------------------

CACHE_FILE = Path("_paper_trace/v2/care_stage_cache.json")


def _load_cache_data() -> dict:
    """Load the cache JSON file, returning empty dict on any error."""
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text()) or {}
        except Exception:
            pass
    return {}


def _stage_cached(stage: str, paper_hash: str) -> bool:
    """Return True if stage data is cached for the given paper hash."""
    if not paper_hash:
        return False
    data = _load_cache_data()
    entry = data.get(stage)
    return isinstance(entry, dict) and entry.get("paper_hash") == paper_hash


def _load_stage_cache(stage: str) -> dict:
    """Load cached stage result (caller must verify with _stage_cached first)."""
    data = _load_cache_data()
    entry = data.get(stage, {})
    return entry.get("result", {})


def _save_stage_cache(stage: str, result: dict, paper_hash: str) -> None:
    """Persist stage result to the cache file."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = _load_cache_data()
    data[stage] = {"paper_hash": paper_hash, "result": result}
    try:
        CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Bloom level diagnosis
# ---------------------------------------------------------------------------


def _diagnose_bloom_level(sections: list) -> str:
    """Diagnose Bloom taxonomy level from section text keywords."""
    text = " ".join(s.content for s in sections).lower()
    if any(w in text for w in ["novel framework", "we propose", "new method"]):
        return "Create"
    if any(w in text for w in ["we evaluate", "we compare", "outperforms"]):
        return "Evaluate"
    if any(w in text for w in ["we analyze", "we investigate", "we examine"]):
        return "Analyze"
    if any(w in text for w in ["we apply", "we implement", "we use"]):
        return "Apply"
    return "Understand"


_BLOOM_ORDER = ["Understand", "Apply", "Analyze", "Evaluate", "Create"]


def _target_bloom_level(current: str) -> str:
    """Return the next Bloom level above current (or current if already at top)."""
    idx = _BLOOM_ORDER.index(current) if current in _BLOOM_ORDER else 0
    return _BLOOM_ORDER[min(idx + 1, len(_BLOOM_ORDER) - 1)]


# ---------------------------------------------------------------------------
# Stage formatters
# ---------------------------------------------------------------------------


def _format_stage_C(contradictions: list) -> dict:
    """Format ContradictionDetectionService output into stage_C dict."""
    c_dicts = [c.to_dict() if hasattr(c, "to_dict") else dict(c) for c in contradictions]
    high = sum(1 for c in c_dicts if c.get("severity") == "high")
    return {
        "total": len(c_dicts),
        "high_severity": high,
        "contradictions": c_dicts,
    }


def _format_stage_A(gaps: list, bloom_level: str) -> dict:
    """Format KnowledgeGapElevationService output into stage_A dict."""
    field_gaps = []
    for g in gaps:
        gap_dict: dict[str, Any] = {}
        if hasattr(g, "__dict__"):
            gap_dict = {
                "concept_a": g.concept_a,
                "concept_b": g.concept_b,
                "gap_description": g.gap_description,
                "level": g.level.value if hasattr(g.level, "value") else str(g.level),
                "elevation_potential": g.elevation_potential,
                "reframe_suggestion": g.reframe_suggestion,
            }
        else:
            gap_dict = dict(g)
        if gap_dict.get("level") == "field":
            field_gaps.append(gap_dict)

    return {
        "bloom_level": bloom_level,
        "target_bloom": _target_bloom_level(bloom_level),
        "total_gaps": len(gaps),
        "field_level_gaps": field_gaps,
        "all_gaps": [
            {
                "concept_a": g.concept_a,
                "concept_b": g.concept_b,
                "level": g.level.value if hasattr(g.level, "value") else str(g.level),
                "reframe_suggestion": g.reframe_suggestion,
            }
            if hasattr(g, "concept_a")
            else dict(g)
            for g in gaps
        ],
    }


# ---------------------------------------------------------------------------
# Action items builder
# ---------------------------------------------------------------------------


def _build_action_items(
    stage_C: dict | None,
    stage_A: dict | None,
    stage_R: dict | None,
    stage_E: dict | None,
) -> list[dict]:
    """Build prioritised action items from all stage results."""
    items: list[dict] = []

    # From stage_C: high severity contradictions → priority 1 tasks
    for c in (stage_C or {}).get("contradictions", []):
        if c.get("severity") == "high":
            items.append(
                {
                    "priority": 1,
                    "stage": "C",
                    "task": (
                        f"修正 {c.get('location_a', '?')} 與 "
                        f"{c.get('location_b', '?')} 的矛盾：{c.get('suggested_fix', '')}"
                    ),
                }
            )

    # From stage_A: top-2 field-level gaps → priority 2 tasks
    for g in (stage_A or {}).get("field_level_gaps", [])[:2]:
        items.append(
            {
                "priority": 2,
                "stage": "A",
                "task": g.get("reframe_suggestion", "重新框架 RQ 以對應 field-level gap"),
            }
        )

    return sorted(items, key=lambda x: x["priority"])


# ---------------------------------------------------------------------------
# Readiness score
# ---------------------------------------------------------------------------


def _compute_readiness(results: dict) -> float:
    """Compute overall Q1 readiness score (0.0–1.0)."""
    scores = []
    if "stage_C" in results:
        high = results["stage_C"].get("high_severity", 0)
        total = max(results["stage_C"].get("total", 1), 1)
        scores.append(1.0 - (high / total) * 0.5)
    if "stage_E" in results:
        scores.append(results["stage_E"].get("feynman_score", 0.5))
    return round(sum(scores) / max(len(scores), 1), 2)


# ---------------------------------------------------------------------------
# Paper Trace write-back
# ---------------------------------------------------------------------------


def _write_report_to_trace(results: dict, paper_hash: str) -> None:
    """Write key findings back to Paper Trace YAML files."""
    trace_dir = Path("_paper_trace/v2")
    trace_dir.mkdir(parents=True, exist_ok=True)

    # 8_limitation_reviewer_risk.yaml: high severity contradictions + field gaps
    risk_path = trace_dir / "8_limitation_reviewer_risk.yaml"
    risk_data: dict[str, Any] = {}
    if risk_path.exists():
        try:
            risk_data = yaml.safe_load(risk_path.read_text()) or {}
        except Exception:
            pass

    high_contradictions = [
        c
        for c in results.get("stage_C", {}).get("contradictions", [])
        if c.get("severity") == "high"
    ]
    field_gaps = results.get("stage_A", {}).get("field_level_gaps", [])

    risk_data["care_pipeline"] = {
        "paper_hash": paper_hash,
        "high_severity_contradictions": high_contradictions,
        "field_level_gaps": field_gaps,
    }
    try:
        risk_path.write_text(yaml.dump(risk_data, allow_unicode=True))
    except Exception:
        pass

    # 7_change_log_impact.yaml: execution record
    log_path = trace_dir / "7_change_log_impact.yaml"
    log_data: dict[str, Any] = {}
    if log_path.exists():
        try:
            log_data = yaml.safe_load(log_path.read_text()) or {}
        except Exception:
            pass

    log_data.setdefault("care_runs", [])
    log_data["care_runs"].append(
        {
            "paper_hash": paper_hash,
            "stages_run": results.get("stages_run", []),
            "overall_q1_readiness": results.get("overall_q1_readiness"),
        }
    )
    try:
        log_path.write_text(yaml.dump(log_data, allow_unicode=True))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Core pipeline runner
# ---------------------------------------------------------------------------


def _run_pipeline(
    paper_path: str,
    target_journal: str | None,
    stages: list[str] | None,
    skip_cache: bool,
) -> dict[str, Any]:
    """Execute the CARE pipeline stages and return combined results."""
    # Token savings: parse paper once
    chunker = SectionChunker()
    try:
        if paper_path.endswith(".pdf"):
            parsed_sections = chunker.chunk_pdf_paper(paper_path)
        else:
            parsed_sections = chunker.chunk_latex_paper(paper_path)
    except Exception:
        parsed_sections = []

    # Build KG once (handles its own cache internally)
    try:
        kg = PaperKnowledgeGraphService().build(paper_path, force_rebuild=skip_cache)
    except Exception:
        kg = None

    paper_hash = _sha256(paper_path)
    results: dict[str, Any] = {}

    active_stages = stages or ["C", "A", "R", "E"]

    # ---- Stage C: Contradiction Detection ----
    if "C" in active_stages:
        if not skip_cache and _stage_cached("C", paper_hash):
            results["stage_C"] = _load_stage_cache("C")
        else:
            try:
                contradictions = ContradictionDetectionService().detect(
                    paper_path, sections=parsed_sections, kg=kg
                )
                results["stage_C"] = _format_stage_C(contradictions)
            except Exception as e:
                results["stage_C"] = {"error": str(e), "total": 0, "high_severity": 0, "contradictions": []}
            _save_stage_cache("C", results["stage_C"], paper_hash)

    # ---- Stage A: Awareness / Knowledge Gap ----
    if "A" in active_stages:
        if not skip_cache and _stage_cached("A", paper_hash):
            results["stage_A"] = _load_stage_cache("A")
        else:
            bloom_level = _diagnose_bloom_level(parsed_sections)
            try:
                gaps = KnowledgeGapElevationService().evaluate(paper_path, kg=kg)
                results["stage_A"] = _format_stage_A(gaps, bloom_level)
            except Exception as e:
                results["stage_A"] = {
                    "error": str(e),
                    "bloom_level": bloom_level,
                    "target_bloom": _target_bloom_level(bloom_level),
                    "total_gaps": 0,
                    "field_level_gaps": [],
                    "all_gaps": [],
                }
            _save_stage_cache("A", results["stage_A"], paper_hash)

    # ---- Stage R: Reasoning / Research Positioning ----
    if "R" in active_stages:
        try:
            positioning = ResearchPositioningService().analyze_positioning(paper_path)
        except Exception as e:
            positioning = {"error": str(e)}
        results["stage_R"] = {"positioning": positioning}

    # ---- Stage E: Explainability / Feynman ----
    if "E" in active_stages:
        try:
            evaluation = EvidenceEvaluationService(mode="hybrid").evaluate(paper_path)
            feynman = FeynmanSessionService().generate_session(
                dimension_scores=evaluation.dimension_scores,
                mode="post_evaluation",
                num_questions=3,
            )
            results["stage_E"] = {
                "feynman_score": round(evaluation.overall_score / 100, 3),
                "top_questions": [q.question for q in feynman.questions[:3]],
                "weak_dimensions": feynman.weak_dimensions,
            }
        except Exception as e:
            results["stage_E"] = {"error": str(e), "feynman_score": 0.5}

    return results


# ---------------------------------------------------------------------------
# MCP tool registration
# ---------------------------------------------------------------------------


def register_tools(mcp) -> None:
    """Register the q1_elevation_pipeline tool with the MCP server."""

    @mcp.tool()
    def q1_elevation_pipeline(
        paper_path: str | None = None,
        target_journal: str | None = None,
        stages: list[str] | None = None,
        skip_cache: bool = False,
    ) -> dict[str, Any]:
        """Run the CARE Q1 elevation pipeline on your paper.

        Stages: C (Contradiction), A (Awareness/Gaps), R (Reasoning), E (Explainability)
        Pass stages=["C","A"] to run only the first two stages.
        Automatically detects paper_path from Paper Trace if not provided.

        Args:
            paper_path:     Path to the paper (.tex or .pdf).  Auto-detected if omitted.
            target_journal: Target journal name.  Auto-detected from submission config if omitted.
            stages:         Subset of stages to run, e.g. ["C","A"].  None = run all four.
            skip_cache:     Force re-run even if stage results are cached.

        Returns:
            Dict with overall_q1_readiness, per-stage results, and action_items list.
        """
        resolved_path = _resolve_paper_path(paper_path)
        resolved_journal = _resolve_journal(target_journal)

        active_stages = stages or ["C", "A", "R", "E"]

        pipeline_results = _run_pipeline(
            paper_path=resolved_path,
            target_journal=resolved_journal,
            stages=active_stages,
            skip_cache=skip_cache,
        )

        overall = _compute_readiness(pipeline_results)
        paper_hash = _sha256(resolved_path)

        action_items = _build_action_items(
            stage_C=pipeline_results.get("stage_C"),
            stage_A=pipeline_results.get("stage_A"),
            stage_R=pipeline_results.get("stage_R"),
            stage_E=pipeline_results.get("stage_E"),
        )

        output: dict[str, Any] = {
            "paper_path": resolved_path,
            "target_journal": resolved_journal,
            "overall_q1_readiness": overall,
            "stages_run": active_stages,
            **pipeline_results,
            "action_items": action_items,
            "trace_updated": False,
        }

        # Write-back to Paper Trace (best effort)
        try:
            _write_report_to_trace(output, paper_hash)
            output["trace_updated"] = True
        except Exception:
            pass

        return output
