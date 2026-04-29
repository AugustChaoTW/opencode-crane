"""Knowledge Gap Elevation Service.

Evaluates knowledge gaps between concepts in a research paper and classifies
them into field/domain/paper levels with concrete suggestions for elevating
the research to Q1 journal quality.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from crane.services.citation_graph_service import CitationGraphService
from crane.services.paper_knowledge_graph_service import PaperKnowledgeGraphService


class GapLevel(str, Enum):
    FIELD = "field"    # 能推升期刊層級（Q2→Q1 潛力）
    DOMAIN = "domain"  # 子領域影響力
    PAPER = "paper"    # 細節補充，不影響期刊層級


LEVEL_TO_POTENTIAL = {
    GapLevel.FIELD: "Q2→Q1",
    GapLevel.DOMAIN: "Q3→Q2",
    GapLevel.PAPER: "影響有限",
}


@dataclass
class KnowledgeGap:
    concept_a: str
    concept_b: str
    gap_description: str
    level: GapLevel
    elevation_potential: str   # "Q3→Q2" | "Q2→Q1" | "Q1穩定" | "影響有限"
    reframe_suggestion: str    # 具體建議，不是泛論
    supporting_evidence: list[str] = field(default_factory=list)


class KnowledgeGapElevationService:
    """Evaluate knowledge gaps and produce research elevation suggestions."""

    def evaluate(
        self,
        paper_path: str,
        kg=None,  # PaperKnowledgeGraph | None — avoid circular import at top level
        top_n: int = 5,
        refs_dir: str = "references",
    ) -> list[KnowledgeGap]:
        """Evaluate knowledge gaps for a paper.

        Args:
            paper_path: Path to the paper file (.tex or .pdf).
            kg:         Pre-built PaperKnowledgeGraph (Token saving: skip rebuild if provided).
            top_n:      Maximum number of gaps to return.
            refs_dir:   Directory containing reference YAML files and embeddings.

        Returns:
            List of KnowledgeGap sorted by level (field > domain > paper).
        """
        if kg is None:
            svc = PaperKnowledgeGraphService()
            kg = svc.build(paper_path)

        current_rq = self._read_current_rq(paper_path)

        pairs: list[tuple[str, str]] = []

        # Source 1: concept gaps from KG
        kg_pairs = self._gaps_from_kg(kg)
        pairs.extend(kg_pairs)

        # Source 2: semantic gaps from citation graph
        cg_pairs = self._gaps_from_citation_graph(refs_dir)
        pairs.extend(cg_pairs)

        # Deduplicate (order-insensitive)
        seen: set[frozenset[str]] = set()
        unique_pairs: list[tuple[str, str]] = []
        for a, b in pairs:
            key = frozenset([a, b])
            if key not in seen:
                seen.add(key)
                unique_pairs.append((a, b))

        # Build KnowledgeGap objects
        gaps: list[KnowledgeGap] = []
        for concept_a, concept_b in unique_pairs:
            level = self._evaluate_level(concept_a, concept_b, kg)
            elevation_potential = LEVEL_TO_POTENTIAL[level]

            gap = KnowledgeGap(
                concept_a=concept_a,
                concept_b=concept_b,
                gap_description=f"No direct connection found between '{concept_a}' and '{concept_b}'",
                level=level,
                elevation_potential=elevation_potential,
                reframe_suggestion="",
            )
            gap.reframe_suggestion = self._generate_reframe(gap, current_rq)
            gaps.append(gap)

        # Sort by level priority: field > domain > paper
        _level_order = {GapLevel.FIELD: 0, GapLevel.DOMAIN: 1, GapLevel.PAPER: 2}
        gaps.sort(key=lambda g: _level_order[g.level])

        result = gaps[:top_n]

        self._write_to_trace(result, paper_path)

        return result

    # ------------------------------------------------------------------
    # Gap sources
    # ------------------------------------------------------------------

    def _gaps_from_kg(self, kg) -> list[tuple[str, str]]:
        """Extract concept gap pairs from the knowledge graph.

        Filters out pairs where both nodes share the same type and both
        have frequency < 2 (too marginal).
        """
        svc = PaperKnowledgeGraphService()
        raw_gaps = svc.find_concept_gaps(kg)

        pairs: list[tuple[str, str]] = []
        for gap in raw_gaps:
            node_a = kg.nodes.get(gap["source"])
            node_b = kg.nodes.get(gap["target"])

            if node_a is None or node_b is None:
                pairs.append((gap["source"], gap["target"]))
                continue

            # Filter: same type AND both frequency < 2 → too marginal
            if node_a.node_type == node_b.node_type and node_a.frequency < 2 and node_b.frequency < 2:
                continue

            pairs.append((gap["source"], gap["target"]))

        return pairs

    def _gaps_from_citation_graph(self, refs_dir: str = "references") -> list[tuple[str, str]]:
        """Extract concept gap pairs from the citation graph's semantic gaps.

        Returns empty list if refs_dir doesn't exist or has no data.
        """
        try:
            refs_path = Path(refs_dir)
            if not refs_path.exists():
                return []

            cg_svc = CitationGraphService(refs_dir=refs_dir)
            semantic_gaps = cg_svc.find_semantic_gaps()

            pairs: list[tuple[str, str]] = []
            for gap in semantic_gaps:
                rep_papers = gap.get("representative_papers", [])
                if len(rep_papers) >= 2:
                    pairs.append((str(rep_papers[0]), str(rep_papers[1])))
                elif len(rep_papers) == 1:
                    pairs.append((str(rep_papers[0]), f"Cluster_{gap.get('cluster_id', 0)}"))

            return pairs
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Level evaluation
    # ------------------------------------------------------------------

    def _evaluate_level(self, concept_a: str, concept_b: str, kg) -> GapLevel:
        """Classify a concept gap into field/domain/paper level.

        Field-level (any of):
          - node types differ (cross-type gap)
          - any concept has frequency >= 3
          - any concept type is "method" or "dataset"

        Paper-level:
          - both frequencies == 1 AND same node type

        Otherwise: Domain-level.
        """
        node_a = kg.nodes.get(concept_a)
        node_b = kg.nodes.get(concept_b)

        # If nodes not in KG (e.g., came from citation graph), default to domain
        if node_a is None or node_b is None:
            return GapLevel.DOMAIN

        type_a = node_a.node_type
        type_b = node_b.node_type
        freq_a = node_a.frequency
        freq_b = node_b.frequency

        # Field-level conditions
        if type_a != type_b:
            return GapLevel.FIELD
        if freq_a >= 3 or freq_b >= 3:
            return GapLevel.FIELD
        if type_a in ("method", "dataset") or type_b in ("method", "dataset"):
            return GapLevel.FIELD

        # Paper-level: both frequency == 1 and same type
        if freq_a == 1 and freq_b == 1:
            return GapLevel.PAPER

        return GapLevel.DOMAIN

    # ------------------------------------------------------------------
    # Reframe suggestion
    # ------------------------------------------------------------------

    def _generate_reframe(self, gap: KnowledgeGap, current_rq: str) -> str:
        """Generate a concrete reframe suggestion for the given gap."""
        concept_a = gap.concept_a
        concept_b = gap.concept_b

        if current_rq:
            rq_snippet = current_rq[:50]
            return (
                f"將 RQ 從「{rq_snippet}...」聚焦到"
                f"「{concept_a} 在 {concept_b} 情境下的影響與機制」"
            )

        return (
            f"聚焦研究問題到「{concept_a} 在 {concept_b} 情境下的影響與機制」"
            f"，探索兩者交叉點以提升貢獻層級"
        )

    def _read_current_rq(self, paper_path: str) -> str:
        """Read the current research question from Paper Trace YAML.

        Looks for _paper_trace/v2/6_research_question.yaml relative to paper_path.
        Returns empty string if file not found or unparseable.
        """
        paper = Path(paper_path)
        trace_file = paper.parent / "_paper_trace" / "v2" / "6_research_question.yaml"

        if not trace_file.exists():
            return ""

        try:
            with open(trace_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data:
                return ""

            # Try research_question.text first, then core_research_question.text
            rq = data.get("research_question", {})
            if isinstance(rq, dict):
                text = rq.get("text", "")
                if text:
                    return str(text)

            crq = data.get("core_research_question", {})
            if isinstance(crq, dict):
                text = crq.get("text", "")
                if text:
                    return str(text)

            return ""
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Write to Paper Trace
    # ------------------------------------------------------------------

    def _write_to_trace(self, gaps: list[KnowledgeGap], paper_path: str) -> None:
        """Write gap analysis results back to 6_research_question.yaml."""
        paper = Path(paper_path)
        trace_file = paper.parent / "_paper_trace" / "v2" / "6_research_question.yaml"

        if not trace_file.exists():
            return

        try:
            with open(trace_file, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            field_gaps = [g for g in gaps if g.level == GapLevel.FIELD]
            domain_gaps = [g for g in gaps if g.level == GapLevel.DOMAIN]
            paper_gaps = [g for g in gaps if g.level == GapLevel.PAPER]

            gap_analysis: dict[str, Any] = {
                "field_level_count": len(field_gaps),
                "domain_level_count": len(domain_gaps),
                "paper_level_count": len(paper_gaps),
            }

            if gaps:
                gap_analysis["top_reframe"] = gaps[0].reframe_suggestion

            data["gap_analysis"] = gap_analysis

            with open(trace_file, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

        except Exception:
            # Write-back is best-effort; do not crash the evaluate() call
            pass
