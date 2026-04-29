"""Paper Knowledge Graph Service.

Builds a knowledge graph from a research paper by extracting concepts and
relationships from each section using LLM (with graceful fallback to keyword
extraction when no API key is available).

The graph is cached on disk at ``_paper_trace/v2/kg_cache.json`` and
invalidated by SHA-256 hash comparison.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import requests

from crane.services.section_chunker import SectionChunker

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class KGNode:
    concept: str
    section: str
    frequency: int
    node_type: str  # "method" | "dataset" | "metric" | "claim" | "concept"


@dataclass
class KGEdge:
    source: str
    target: str
    relation: str   # "supports" | "contradicts" | "extends" | "uses" | "defines"
    evidence: str   # limited to 100 chars
    confidence: float


@dataclass
class PaperKnowledgeGraph:
    paper_path: str
    nodes: dict[str, KGNode] = field(default_factory=dict)
    edges: list[KGEdge] = field(default_factory=list)
    file_hash: str = ""


# ---------------------------------------------------------------------------
# LLM prompt
# ---------------------------------------------------------------------------

_EXTRACTION_PROMPT = """\
Given this section of a research paper:
{section_text}

Extract concepts and relationships. Output ONLY valid JSON:
{{"concepts": [{{"name": "...", "type": "method|dataset|metric|claim|concept"}}],
 "relations": [{{"from": "...", "to": "...", "type": "supports|contradicts|extends|uses|defines", "evidence": "..."}}]}}
Keep evidence under 100 characters."""

_VALID_NODE_TYPES = {"method", "dataset", "metric", "claim", "concept"}
_VALID_RELATION_TYPES = {"supports", "contradicts", "extends", "uses", "defines"}

# Keywords that suggest concept type via simple heuristic
_TYPE_HINTS: list[tuple[str, str]] = [
    (r"\baccuracy|f1|precision|recall|auc|mse|rmse|bleu|rouge\b", "metric"),
    (r"\bdataset|benchmark|corpus|collection\b", "dataset"),
    (r"\bmodel|method|algorithm|approach|framework|architecture\b", "method"),
    (r"\bwe claim|we argue|we show|we prove|hypothesis\b", "claim"),
]


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class PaperKnowledgeGraphService:
    """Build and query knowledge graphs extracted from research papers."""

    _CACHE_SUBPATH = "_paper_trace/v2/kg_cache.json"

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._chunker = SectionChunker()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, paper_path: str, force_rebuild: bool = False) -> PaperKnowledgeGraph:
        """Build (or load from cache) the knowledge graph for *paper_path*.

        Args:
            paper_path:    Path to a ``.tex`` or ``.pdf`` paper file.
            force_rebuild: Skip cache even if hash matches.

        Returns:
            A :class:`PaperKnowledgeGraph` with populated nodes and edges.
        """
        path = Path(paper_path)
        current_hash = self._sha256(path)

        if not force_rebuild and self._is_cache_valid(paper_path, current_hash):
            return self._load_cache(paper_path)

        # Parse sections
        if path.suffix.lower() == ".tex":
            sections = self._chunker.chunk_latex_paper(path)
        else:
            sections = self._chunker.chunk_pdf_paper(path)

        kg = PaperKnowledgeGraph(paper_path=paper_path, file_hash=current_hash)

        for section in sections:
            if not section.content.strip():
                continue
            extracted = self._extract_from_section(section.content, section.canonical_name)
            self._merge_into_kg(kg, extracted, section.canonical_name)

        self._save_cache(paper_path, kg)
        return kg

    def find_concept_gaps(self, kg: PaperKnowledgeGraph) -> list[dict[str, Any]]:
        """Find node pairs that have no connecting edge.

        A "gap" is a pair of concepts (A, B) where both A and B appear in the
        graph as nodes but there is no edge between them in either direction.
        Returns pairs sorted by combined frequency (most frequent first).

        Returns:
            List of dicts with keys ``source``, ``target``,
            ``source_type``, ``target_type``.
        """
        if len(kg.nodes) < 2:
            return []

        # Build adjacency set for O(1) lookup
        connected: set[frozenset[str]] = set()
        for edge in kg.edges:
            connected.add(frozenset([edge.source, edge.target]))

        node_keys = list(kg.nodes.keys())
        gaps: list[dict[str, Any]] = []

        for i, a in enumerate(node_keys):
            for b in node_keys[i + 1 :]:
                if frozenset([a, b]) not in connected:
                    node_a = kg.nodes[a]
                    node_b = kg.nodes[b]
                    gaps.append(
                        {
                            "source": a,
                            "target": b,
                            "source_type": node_a.node_type,
                            "target_type": node_b.node_type,
                            "combined_frequency": node_a.frequency + node_b.frequency,
                        }
                    )

        gaps.sort(key=lambda x: x["combined_frequency"], reverse=True)
        return gaps

    def to_mermaid(self, kg: PaperKnowledgeGraph) -> str:
        """Render the knowledge graph as a Mermaid ``graph TD`` diagram.

        Returns:
            Mermaid diagram string.
        """
        lines = ["graph TD"]

        # Nodes
        for concept, node in kg.nodes.items():
            safe_id = re.sub(r"[^A-Za-z0-9_]", "_", concept)
            label = f"{concept}\\n[{node.node_type}]"
            lines.append(f'    {safe_id}["{label}"]')

        # Edges
        for edge in kg.edges:
            src_id = re.sub(r"[^A-Za-z0-9_]", "_", edge.source)
            tgt_id = re.sub(r"[^A-Za-z0-9_]", "_", edge.target)
            label = edge.relation
            lines.append(f"    {src_id} -->|{label}| {tgt_id}")

        if len(lines) == 1:
            lines.append('    A["No concepts extracted"]')

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _cache_path(self, paper_path: str) -> Path:
        paper = Path(paper_path)
        return paper.parent / self._CACHE_SUBPATH

    def _is_cache_valid(self, paper_path: str, current_hash: str | None = None) -> bool:
        """Return True if a valid cache exists whose hash matches the file."""
        cache = self._cache_path(paper_path)
        if not cache.exists():
            return False
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            if current_hash is None:
                current_hash = self._sha256(Path(paper_path))
            return data.get("file_hash") == current_hash
        except Exception:
            return False

    def _load_cache(self, paper_path: str) -> PaperKnowledgeGraph:
        cache = self._cache_path(paper_path)
        data = json.loads(cache.read_text(encoding="utf-8"))
        nodes = {k: KGNode(**v) for k, v in data.get("nodes", {}).items()}
        edges = [KGEdge(**e) for e in data.get("edges", [])]
        return PaperKnowledgeGraph(
            paper_path=paper_path,
            nodes=nodes,
            edges=edges,
            file_hash=data.get("file_hash", ""),
        )

    def _save_cache(self, paper_path: str, kg: PaperKnowledgeGraph) -> None:
        cache = self._cache_path(paper_path)
        cache.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "paper_path": kg.paper_path,
            "file_hash": kg.file_hash,
            "nodes": {k: asdict(v) for k, v in kg.nodes.items()},
            "edges": [asdict(e) for e in kg.edges],
        }
        cache.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # LLM extraction
    # ------------------------------------------------------------------

    def _extract_from_section(
        self, section_text: str, section_name: str
    ) -> dict[str, Any]:
        """Extract concepts and relations from section text.

        Tries LLM first; falls back to keyword extraction on failure.
        """
        if self._api_key:
            result = self._call_llm(section_text)
            if result is not None:
                return result
        return self._keyword_fallback(section_text, section_name)

    def _call_llm(self, section_text: str) -> dict[str, Any] | None:
        """Call OpenAI-compatible API and return parsed JSON or None on failure."""
        prompt = _EXTRACTION_PROMPT.format(section_text=section_text[:3000])
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                    "max_tokens": 1000,
                    "response_format": {"type": "json_object"},
                },
                timeout=30,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception:
            return None

    @staticmethod
    def _keyword_fallback(text: str, section_name: str) -> dict[str, Any]:
        """Heuristic concept extraction when LLM is unavailable."""
        words = re.findall(r"\b[A-Z][a-zA-Z]{3,}\b", text)
        freq: dict[str, int] = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1

        # Take top-10 by frequency
        top = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:10]

        concepts = []
        for name, _ in top:
            node_type = "concept"
            for pattern, t in _TYPE_HINTS:
                if re.search(pattern, name, re.IGNORECASE):
                    node_type = t
                    break
            concepts.append({"name": name, "type": node_type})

        # Emit simple co-occurrence edges between consecutive top concepts
        relations = []
        for i in range(len(top) - 1):
            a, _ = top[i]
            b, _ = top[i + 1]
            relations.append(
                {
                    "from": a,
                    "to": b,
                    "type": "supports",
                    "evidence": f"co-occurrence in {section_name}",
                }
            )

        return {"concepts": concepts, "relations": relations}

    # ------------------------------------------------------------------
    # Graph building helpers
    # ------------------------------------------------------------------

    def _merge_into_kg(
        self,
        kg: PaperKnowledgeGraph,
        extracted: dict[str, Any],
        section_name: str,
    ) -> None:
        """Merge extracted concepts and relations into *kg* in-place."""
        for c in extracted.get("concepts", []):
            name = str(c.get("name", "")).strip()
            if not name:
                continue
            node_type = c.get("type", "concept")
            if node_type not in _VALID_NODE_TYPES:
                node_type = "concept"

            if name in kg.nodes:
                kg.nodes[name].frequency += 1
            else:
                kg.nodes[name] = KGNode(
                    concept=name,
                    section=section_name,
                    frequency=1,
                    node_type=node_type,
                )

        for r in extracted.get("relations", []):
            src = str(r.get("from", "")).strip()
            tgt = str(r.get("to", "")).strip()
            rel = r.get("type", "supports")
            evidence = str(r.get("evidence", ""))[:100]

            if not src or not tgt:
                continue
            if rel not in _VALID_RELATION_TYPES:
                rel = "supports"

            kg.edges.append(
                KGEdge(
                    source=src,
                    target=tgt,
                    relation=rel,
                    evidence=evidence,
                    confidence=0.8,
                )
            )

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _sha256(path: Path) -> str:
        if not path.exists():
            return ""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
