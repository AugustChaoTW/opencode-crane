"""Impact graph service: adjacency-list traceability graph."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from crane.models.traceability import TraceabilityNode, get_node_type_from_id


class ImpactGraphService:
    """Adjacency-list graph of traceability nodes.

    Edges represent dependency: add_edge(from_id, to_id) means
    ``from_id`` depends on ``to_id``.

    * Forward edges  (self._forward):  to_id  → {from_ids that depend on it}
    * Backward edges (self._backward): from_id → {to_ids it depends on}
    """

    def __init__(self) -> None:
        self._nodes: dict[str, TraceabilityNode] = {}
        # forward edges: node → nodes that depend on it
        self._forward: dict[str, set[str]] = {}
        # backward edges: node → nodes it depends on
        self._backward: dict[str, set[str]] = {}

    # ------------------------------------------------------------------
    # Node management
    # ------------------------------------------------------------------

    def add_node(
        self,
        node_id: str,
        document_ref: str = "",
        inferred: bool = False,
    ) -> None:
        """Add a node if it does not already exist."""
        if node_id in self._nodes:
            return
        node_type = get_node_type_from_id(node_id)
        self._nodes[node_id] = TraceabilityNode(
            node_id=node_id,
            node_type=node_type,
            document_ref=document_ref,
            inferred=inferred,
        )
        self._forward.setdefault(node_id, set())
        self._backward.setdefault(node_id, set())

    def get_node(self, node_id: str) -> TraceabilityNode | None:
        """Return the node for *node_id*, or None if not present."""
        return self._nodes.get(node_id)

    def get_all_nodes(self) -> list[TraceabilityNode]:
        """Return all nodes in insertion-stable order."""
        return list(self._nodes.values())

    # ------------------------------------------------------------------
    # Edge management
    # ------------------------------------------------------------------

    def add_edge(self, from_id: str, to_id: str) -> None:
        """Record that *from_id* depends on *to_id*.

        Both nodes are created (as stubs) if they don't yet exist.
        The forward graph stores  to_id   → {from_id, …}
        The backward graph stores from_id → {to_id, …}
        """
        if from_id not in self._nodes:
            self.add_node(from_id)
        if to_id not in self._nodes:
            self.add_node(to_id)

        self._forward[to_id].add(from_id)
        self._backward[from_id].add(to_id)

        # Keep TraceabilityNode lists in sync
        from_node = self._nodes[from_id]
        to_node = self._nodes[to_id]
        if to_id not in from_node.depends_on:
            from_node.depends_on.append(to_id)
        if from_id not in to_node.depended_by:
            to_node.depended_by.append(from_id)

    # ------------------------------------------------------------------
    # Graph traversal
    # ------------------------------------------------------------------

    def get_downstream(self, node_id: str, depth: int = 10) -> list[str]:
        """BFS: all nodes that depend (directly or transitively) on *node_id*.

        Returns node IDs in BFS order, excluding the root itself.
        """
        if node_id not in self._nodes:
            return []
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(node_id, 0)])
        result: list[str] = []

        while queue:
            current, d = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            if current != node_id:
                result.append(current)
            if d < depth:
                for neighbor in sorted(self._forward.get(current, set())):
                    if neighbor not in visited:
                        queue.append((neighbor, d + 1))

        return result

    def get_upstream(self, node_id: str, depth: int = 10) -> list[str]:
        """BFS: all nodes that *node_id* depends on (directly or transitively).

        Returns node IDs in BFS order, excluding the root itself.
        """
        if node_id not in self._nodes:
            return []
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(node_id, 0)])
        result: list[str] = []

        while queue:
            current, d = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            if current != node_id:
                result.append(current)
            if d < depth:
                for neighbor in sorted(self._backward.get(current, set())):
                    if neighbor not in visited:
                        queue.append((neighbor, d + 1))

        return result

    # ------------------------------------------------------------------
    # Graph analysis
    # ------------------------------------------------------------------

    def find_orphans(self) -> list[str]:
        """Return node IDs that have no edges (neither upstream nor downstream)."""
        return [
            node_id
            for node_id in self._nodes
            if not self._forward.get(node_id) and not self._backward.get(node_id)
        ]

    def find_broken_links(self, all_known_ids: set[str]) -> list[tuple[str, str]]:
        """Return (from_id, to_id) pairs where *to_id* is not in *all_known_ids*.

        These represent edges that reference non-existent nodes.
        """
        broken: list[tuple[str, str]] = []
        for from_id, dependencies in self._backward.items():
            for to_id in sorted(dependencies):
                if to_id not in all_known_ids:
                    broken.append((from_id, to_id))
        return broken

    def get_subgraph(self, root_ids: list[str]) -> "ImpactGraphService":
        """Return a new graph containing only nodes reachable from *root_ids*.

        "Reachable" includes both upstream and downstream of every root.
        """
        reachable: set[str] = set(root_ids)
        for rid in root_ids:
            reachable.update(self.get_downstream(rid))
            reachable.update(self.get_upstream(rid))

        sub = ImpactGraphService()
        for node_id in reachable:
            if node_id in self._nodes:
                orig = self._nodes[node_id]
                sub.add_node(node_id, document_ref=orig.document_ref, inferred=orig.inferred)

        for from_id in reachable:
            for to_id in self._backward.get(from_id, set()):
                if to_id in reachable:
                    sub.add_edge(from_id, to_id)

        return sub

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_adjacency_dict(self) -> dict[str, list[str]]:
        """Serialize graph as ``{node_id: [downstream_ids]}``.

        The downstream list contains nodes that depend on *node_id*.
        """
        return {
            node_id: sorted(self._forward.get(node_id, set()))
            for node_id in self._nodes
        }

    @classmethod
    def from_adjacency_dict(cls, data: dict[str, list[str]]) -> "ImpactGraphService":
        """Reconstruct a graph from a ``{node_id: [downstream_ids]}`` dict.

        The forward dict maps ``node_id → [nodes that depend on it]``,
        so each entry ``(node_id, downstream_id)`` corresponds to
        ``add_edge(downstream_id, node_id)``.
        """
        graph = cls()
        # First pass: ensure all nodes exist
        for node_id, downstream in data.items():
            graph.add_node(node_id)
            for dep_id in downstream:
                graph.add_node(dep_id)
        # Second pass: add edges
        for node_id, downstream in data.items():
            for dep_id in downstream:
                graph.add_edge(dep_id, node_id)
        return graph
