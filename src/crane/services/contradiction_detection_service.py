"""Contradiction Detection Service.

Detects four layers of contradictions in research papers:
  1. NUMERICAL   — paper vs. code hyperparameter / metric mismatches
  2. CLAIM_EVIDENCE — unsupported strong claims (no number or citation nearby)
  3. CROSS_SECTION — semantic conflicts between sections (LLM or keyword fallback)
  4. CITATION      — "contradicts" edges from a PaperKnowledgeGraph
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

import requests

from crane.services.paper_code_alignment_service import PaperCodeAlignmentService
from crane.services.paper_knowledge_graph_service import PaperKnowledgeGraph
from crane.services.section_chunker import Section, SectionChunker

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class ContradictionType(str, Enum):
    NUMERICAL = "numerical"
    CLAIM_EVIDENCE = "claim_evidence"
    CROSS_SECTION = "cross_section"
    CITATION = "citation"


@dataclass
class Contradiction:
    type: ContradictionType
    location_a: str
    location_b: str
    description: str        # limited to 80 chars
    severity: str           # "high" | "medium" | "low"
    reviewer_attack_prob: float
    suggested_fix: str      # limited to 60 chars

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "location_a": self.location_a,
            "location_b": self.location_b,
            "description": self.description,
            "severity": self.severity,
            "reviewer_attack_prob": self.reviewer_attack_prob,
            "suggested_fix": self.suggested_fix,
        }


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_STRONG_CLAIM_PATTERN = re.compile(
    r"\b(state[-\s]of[-\s]the[-\s]art|novel|significantly|outperform(?:s|ed|ing)?)\b",
    re.IGNORECASE,
)
_NUMBER_OR_CITATION_PATTERN = re.compile(
    r"(\d+\.?\d*\s*%?|\[\d+\]|\(\d{4}\)|\bcite\b)",
    re.IGNORECASE,
)

# Section pairs always checked when embedding is unavailable
_FALLBACK_PAIRS: list[tuple[str, str]] = [
    ("Abstract", "Introduction"),
    ("Abstract", "Discussion"),
    ("Abstract", "Conclusion"),
    ("Introduction", "Conclusion"),
]

_SEVERITY_TO_ATTACK_PROB: dict[str, float] = {
    "high": 0.87,
    "medium": 0.55,
    "low": 0.25,
}

_NEGATION_KEYWORDS = re.compile(
    r"\b(no|not|however|contrary|contradict|unlike|but|although|whereas)\b",
    re.IGNORECASE,
)

# LLM config (OpenAI-compatible)
_LLM_API_URL = "https://api.openai.com/v1/chat/completions"
_LLM_MODEL = "gpt-4o-mini"
_LLM_CROSS_SECTION_PROMPT = """\
Compare these two paper sections and decide if they contain a direct contradiction.
Section A ({name_a}):
{text_a}

Section B ({name_b}):
{text_b}

Output ONLY valid JSON:
{{"is_contradiction": true|false, "severity": "high|medium|low", "reason": "<50 chars"}}"""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ContradictionDetectionService:
    """Detect multi-layer contradictions in a research paper."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._chunker = SectionChunker()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(
        self,
        paper_path: str,
        sections: list[Section] | None = None,
        kg: PaperKnowledgeGraph | None = None,
        types: list[str] | None = None,
    ) -> list[Contradiction]:
        """Detect contradictions in a paper across up to four layers.

        Args:
            paper_path: Path to the .tex or .pdf paper file.
            sections:   Pre-parsed sections (avoids re-parsing if already done).
            kg:         Pre-built knowledge graph (avoids rebuild if already done).
            types:      Subset of detector types to run.  None = run all four.
                        Valid values: "numerical", "claim_evidence",
                        "cross_section", "citation".

        Returns:
            List of :class:`Contradiction` objects, sorted by severity.
        """
        enabled = set(types) if types else {t.value for t in ContradictionType}

        # Lazy-load sections only when a detector that needs them is enabled
        _needs_sections = enabled & {
            ContradictionType.CLAIM_EVIDENCE.value,
            ContradictionType.CROSS_SECTION.value,
        }
        if sections is None and _needs_sections:
            try:
                sections = self._chunker.chunk_latex_paper(paper_path)
            except Exception:
                sections = []

        results: list[Contradiction] = []

        if ContradictionType.NUMERICAL.value in enabled:
            results.extend(self._detect_numerical(paper_path))

        if ContradictionType.CLAIM_EVIDENCE.value in enabled and sections is not None:
            results.extend(self._detect_claim_evidence(sections))

        if ContradictionType.CROSS_SECTION.value in enabled and sections is not None:
            results.extend(self._detect_cross_section(sections))

        if ContradictionType.CITATION.value in enabled and kg is not None:
            results.extend(self._detect_citation(kg))

        # Sort: high → medium → low
        _order = {"high": 0, "medium": 1, "low": 2}
        results.sort(key=lambda c: _order.get(c.severity, 3))
        return results

    # ------------------------------------------------------------------
    # Detector 1: numerical (reuses PaperCodeAlignmentService)
    # ------------------------------------------------------------------

    def _detect_numerical(self, paper_path: str) -> list[Contradiction]:
        """Find hyperparameter/metric mismatches between paper and sibling code."""
        from pathlib import Path

        paper = Path(paper_path)
        parent = paper.parent

        # Look for a Python file or sub-directory next to the paper
        code_path: str | None = None
        for candidate in sorted(parent.rglob("*.py")):
            if "__pycache__" not in str(candidate):
                code_path = str(candidate.parent)
                break
        # Also accept a direct .py file alongside the .tex
        if code_path is None:
            py_files = [f for f in parent.glob("*.py") if "__pycache__" not in str(f)]
            if py_files:
                code_path = str(py_files[0])

        if code_path is None:
            return []

        try:
            svc = PaperCodeAlignmentService(refs_dir=str(parent))
            latex_settings = svc.extract_latex_settings(str(paper))
            code_settings = svc.extract_code_settings(code_path)
            report = svc.compare_settings(latex_settings, code_settings)
        except Exception:
            return []

        contradictions: list[Contradiction] = []
        for mismatch in report.get("mismatches", []):
            key = mismatch.get("key", "unknown")
            latex_val = mismatch.get("latex_value", "")
            code_val = mismatch.get("code_value", "")
            reason = mismatch.get("reason", "")
            category = mismatch.get("category", "hyperparameter")

            if reason == "missing_in_code":
                desc = f"{category} '{key}'={latex_val} in paper but absent in code"
                fix = f"Add {key} to code or remove from paper"
            else:
                desc = f"{category} '{key}' paper={latex_val} vs code={code_val}"
                fix = f"Align {key}: paper says {latex_val}, code uses {code_val}"

            contradictions.append(
                Contradiction(
                    type=ContradictionType.NUMERICAL,
                    location_a=paper.name,
                    location_b=str(Path(code_path).name),
                    description=desc[:80],
                    severity="high",
                    reviewer_attack_prob=_SEVERITY_TO_ATTACK_PROB["high"],
                    suggested_fix=fix[:60],
                )
            )
        return contradictions

    # ------------------------------------------------------------------
    # Detector 2: claim-evidence (reuses section_review logic)
    # ------------------------------------------------------------------

    def _detect_claim_evidence(self, sections: list[Section]) -> list[Contradiction]:
        """Flag strong claims that have no supporting number or citation nearby."""
        contradictions: list[Contradiction] = []

        for section in sections:
            text = section.content or ""
            for match in _STRONG_CLAIM_PATTERN.finditer(text):
                start = max(0, match.start() - 200)
                end = min(len(text), match.end() + 200)
                window = text[start:end]

                if not _NUMBER_OR_CITATION_PATTERN.search(window):
                    claim_word = match.group(0)
                    desc = f"'{claim_word}' claim in {section.name} has no supporting evidence"
                    fix = f"Add citation or metric supporting '{claim_word[:20]}' claim"
                    contradictions.append(
                        Contradiction(
                            type=ContradictionType.CLAIM_EVIDENCE,
                            location_a=section.name,
                            location_b="",
                            description=desc[:80],
                            severity="high",
                            reviewer_attack_prob=_SEVERITY_TO_ATTACK_PROB["high"],
                            suggested_fix=fix[:60],
                        )
                    )
        return contradictions

    # ------------------------------------------------------------------
    # Detector 3: cross-section (semantic prefilter + LLM / keyword fallback)
    # ------------------------------------------------------------------

    def _semantic_prefilter(self, sections: list[Section]) -> list[tuple[Section, Section]]:
        """Return section pairs with potential semantic overlap (0.3 ≤ sim < 0.95).

        Falls back to fixed Abstract/Intro vs Discussion/Conclusion pairs when
        embeddings are unavailable.
        """
        if not sections:
            return []

        # Attempt embedding-based filtering
        embedding_pairs = self._try_embedding_prefilter(sections)
        if embedding_pairs is not None:
            return embedding_pairs

        # Fallback: check canonical section names against fixed pairs
        section_map: dict[str, Section] = {
            s.canonical_name: s for s in sections if s.canonical_name
        }
        result: list[tuple[Section, Section]] = []
        for name_a, name_b in _FALLBACK_PAIRS:
            sec_a = section_map.get(name_a)
            sec_b = section_map.get(name_b)
            if sec_a and sec_b:
                result.append((sec_a, sec_b))
        return result

    def _try_embedding_prefilter(
        self, sections: list[Section]
    ) -> list[tuple[Section, Section]] | None:
        """Try to compute cosine-similarity pairs via OpenAI embeddings.

        Returns None if embedding is unavailable (no API key / network error).
        """
        if not self._api_key:
            return None

        try:
            import numpy as np
        except ImportError:
            return None

        # Embed all sections
        embeddings: dict[str, list[float]] = {}
        for sec in sections:
            if not sec.content:
                continue
            vec = self._embed_text(sec.content[:1000])  # truncate for speed
            if vec is None:
                return None  # if any embed fails, use fallback
            embeddings[sec.name] = vec

        if len(embeddings) < 2:
            return None

        names = list(embeddings.keys())
        vecs = [np.array(embeddings[n]) for n in names]

        result: list[tuple[Section, Section]] = []
        section_by_name = {s.name: s for s in sections}

        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = vecs[i], vecs[j]
                norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
                if norm_a == 0 or norm_b == 0:
                    continue
                sim = float(np.dot(a, b) / (norm_a * norm_b))
                if 0.3 <= sim < 0.95:
                    sec_a = section_by_name.get(names[i])
                    sec_b = section_by_name.get(names[j])
                    if sec_a and sec_b:
                        result.append((sec_a, sec_b))
        return result

    def _embed_text(self, text: str) -> list[float] | None:
        """Embed text via OpenAI embeddings API. Returns None on failure."""
        if not self._api_key:
            return None
        try:
            response = requests.post(
                _LLM_API_URL.replace("/chat/completions", "/embeddings"),
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": "text-embedding-3-small", "input": text},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()["data"][0]["embedding"]
        except Exception:
            return None

    def _detect_cross_section(self, sections: list[Section]) -> list[Contradiction]:
        """Detect semantic conflicts between section pairs."""
        pairs = self._semantic_prefilter(sections)
        contradictions: list[Contradiction] = []

        for sec_a, sec_b in pairs:
            if self._api_key:
                result = self._llm_check_contradiction(sec_a, sec_b)
            else:
                result = self._keyword_negation_check(sec_a, sec_b)

            if result is None or not result.get("is_contradiction"):
                continue

            severity = result.get("severity", "medium")
            reason = str(result.get("reason", "potential cross-section conflict"))[:50]

            contradictions.append(
                Contradiction(
                    type=ContradictionType.CROSS_SECTION,
                    location_a=sec_a.name,
                    location_b=sec_b.name,
                    description=reason[:80],
                    severity=severity,
                    reviewer_attack_prob=_SEVERITY_TO_ATTACK_PROB.get(severity, 0.55),
                    suggested_fix=f"Reconcile claims in {sec_a.name} and {sec_b.name}"[:60],
                )
            )
        return contradictions

    def _llm_check_contradiction(
        self, sec_a: Section, sec_b: Section
    ) -> dict[str, Any] | None:
        """Ask LLM whether two sections contradict. Returns parsed JSON or None."""
        prompt = _LLM_CROSS_SECTION_PROMPT.format(
            name_a=sec_a.name,
            text_a=(sec_a.content or "")[:600],
            name_b=sec_b.name,
            text_b=(sec_b.content or "")[:600],
        )
        try:
            response = requests.post(
                _LLM_API_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": _LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 80,
                    "temperature": 0,
                },
                timeout=30,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
            return json.loads(content)
        except Exception:
            return None

    def _keyword_negation_check(
        self, sec_a: Section, sec_b: Section
    ) -> dict[str, Any] | None:
        """Heuristic: flag pair if one section has negation words near shared concepts."""
        text_a = (sec_a.content or "").lower()
        text_b = (sec_b.content or "").lower()

        # Extract significant words (>4 chars) from both sections
        words_a = {w for w in re.findall(r"\b[a-z]{5,}\b", text_a)}
        words_b = {w for w in re.findall(r"\b[a-z]{5,}\b", text_b)}
        shared = words_a & words_b

        if not shared:
            return None

        has_negation_a = bool(_NEGATION_KEYWORDS.search(text_a))
        has_negation_b = bool(_NEGATION_KEYWORDS.search(text_b))

        if has_negation_a or has_negation_b:
            return {
                "is_contradiction": True,
                "severity": "low",
                "reason": f"negation near shared concept in {sec_a.name}/{sec_b.name}"[:50],
            }
        return None

    # ------------------------------------------------------------------
    # Detector 4: citation (from KG edges)
    # ------------------------------------------------------------------

    def _detect_citation(self, kg: PaperKnowledgeGraph) -> list[Contradiction]:
        """Find contradicts edges in the knowledge graph."""
        contradictions: list[Contradiction] = []
        for edge in kg.edges:
            if edge.relation != "contradicts":
                continue
            desc = f"{edge.source} contradicts {edge.target}: {edge.evidence}"
            fix = f"Clarify stance on {edge.source} vs {edge.target}"
            contradictions.append(
                Contradiction(
                    type=ContradictionType.CITATION,
                    location_a=edge.source,
                    location_b=edge.target,
                    description=desc[:80],
                    severity="medium",
                    reviewer_attack_prob=_SEVERITY_TO_ATTACK_PROB["medium"],
                    suggested_fix=fix[:60],
                )
            )
        return contradictions
