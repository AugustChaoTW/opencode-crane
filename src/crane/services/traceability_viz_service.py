"""Traceability visualization service: Mermaid and DOT diagram generation."""
from __future__ import annotations

import re

from crane.models.traceability import get_node_type_from_id
from crane.services.impact_graph_service import ImpactGraphService


class TraceabilityVizService:
    """Generate Mermaid flowchart and Graphviz DOT diagrams from a traceability graph."""

    # (fill_color, font_color)
    MERMAID_COLORS: dict[str, tuple[str, str]] = {
        "rq":           ("#4A90D9", "#FFFFFF"),
        "contribution": ("#E6821E", "#FFFFFF"),
        "experiment":   ("#9B59B6", "#FFFFFF"),
        "figure":       ("#27AE60", "#FFFFFF"),
        "table":        ("#27AE60", "#FFFFFF"),
        "risk":         ("#E74C3C", "#FFFFFF"),
        "section":      ("#95A5A6", "#FFFFFF"),
        "reference":    ("#1ABC9C", "#FFFFFF"),
        "artifact":     ("#8B4513", "#FFFFFF"),
        "change":       ("#F39C12", "#FFFFFF"),
        "unknown":      ("#CCCCCC", "#333333"),
    }

    # Graphviz shapes per node type
    DOT_SHAPES: dict[str, str] = {
        "rq":           "box",
        "contribution": "box",
        "experiment":   "box",
        "figure":       "box",
        "table":        "box",
        "risk":         "diamond",
        "section":      "ellipse",
        "reference":    "box",
        "artifact":     "box",
        "change":       "box",
        "unknown":      "box",
    }

    # ------------------------------------------------------------------
    # Mermaid
    # ------------------------------------------------------------------

    def get_mermaid(
        self,
        graph: ImpactGraphService,
        title: str = "Paper Traceability",
    ) -> str:
        """Generate a Mermaid ``flowchart LR`` diagram from *graph*."""
        lines: list[str] = [f"---\ntitle: {title}\n---", "flowchart LR"]

        # classDef declarations
        for node_type, (fill, color) in self.MERMAID_COLORS.items():
            lines.append(f"    classDef {node_type} fill:{fill},color:{color}")

        lines.append("")

        # Node declarations
        nodes = graph.get_all_nodes()
        if not nodes:
            lines.append("    %% (empty graph)")
            return "\n".join(lines)

        for node in nodes:
            safe_id = self._mermaid_safe_id(node.node_id)
            label = self._node_label(node.node_id)
            node_type = node.node_type
            # Risk nodes use rhombus/diamond shape in Mermaid: {label}
            if node_type == "risk":
                lines.append(f'    {safe_id}{{"{label}"}}:::{node_type}')
            else:
                lines.append(f'    {safe_id}["{label}"]:::{node_type}')

        lines.append("")

        # Edges (forward: to_id → from_id means from_id depends on to_id)
        adj = graph.to_adjacency_dict()
        for node_id in sorted(adj):
            for dep_id in sorted(adj[node_id]):
                src = self._mermaid_safe_id(node_id)
                dst = self._mermaid_safe_id(dep_id)
                lines.append(f"    {src} --> {dst}")

        return "\n".join(lines)

    def _mermaid_safe_id(self, node_id: str) -> str:
        """Convert a node ID to a Mermaid-safe identifier (no colons or spaces)."""
        return re.sub(r"[^A-Za-z0-9_]", "_", node_id)

    def _mermaid_node_style(self, node_type: str) -> str:
        """Return Mermaid ``classDef`` style string for *node_type*."""
        fill, color = self.MERMAID_COLORS.get(
            node_type, self.MERMAID_COLORS["unknown"]
        )
        return f"fill:{fill},color:{color}"

    # ------------------------------------------------------------------
    # DOT
    # ------------------------------------------------------------------

    def get_dot(
        self,
        graph: ImpactGraphService,
        title: str = "Paper Traceability",
    ) -> str:
        """Generate a Graphviz DOT diagram from *graph*."""
        escaped_title = title.replace('"', '\\"')
        lines: list[str] = [
            f'digraph "{escaped_title}" {{',
            "    rankdir=LR;",
            '    node [fontname="Helvetica"];',
            "",
        ]

        nodes = graph.get_all_nodes()
        if not nodes:
            lines.append('    // (empty graph)')
            lines.append("}")
            return "\n".join(lines)

        for node in nodes:
            node_type = node.node_type
            fill, fontcolor = self.MERMAID_COLORS.get(
                node_type, self.MERMAID_COLORS["unknown"]
            )
            shape = self.DOT_SHAPES.get(node_type, "box")
            label = self._node_label(node.node_id).replace('"', '\\"')
            safe_id = node.node_id.replace('"', '\\"')
            lines.append(
                f'    "{safe_id}" [label="{label}", shape={shape}, style=filled,'
                f' fillcolor="{fill}", fontcolor="{fontcolor}"];'
            )

        lines.append("")

        # Edges: the forward dict gives node_id → [nodes that depend on it]
        adj = graph.to_adjacency_dict()
        for node_id in sorted(adj):
            for dep_id in sorted(adj[node_id]):
                src = node_id.replace('"', '\\"')
                dst = dep_id.replace('"', '\\"')
                lines.append(f'    "{src}" -> "{dst}";')

        lines.append("}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _node_label(self, node_id: str) -> str:
        """Human-readable label from a node ID.

        Examples:
            ``RQ1``       → ``RQ1``
            ``Fig:1``     → ``Fig 1``
            ``Ref:smith`` → ``Ref smith``
            ``Sec:1``     → ``Sec 1``
        """
        # Replace colons with a space for readability
        return node_id.replace(":", " ")
