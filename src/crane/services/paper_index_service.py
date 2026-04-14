"""Fast single-pass paper index builder using Linux tools (grep, sed, wc).

Builds a .{stem}_index.yaml alongside the LaTeX file.  All downstream review
tools (evaluate_paper_v2, run_submission_check, crane_diagnose, …) can read
from this index instead of re-parsing the file independently.

Cache invalidation is based on file mtime — no stale data.
"""

from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path
from typing import Any

import yaml


class PaperIndexService:
    """Builds and caches a structured index from a LaTeX paper."""

    # Pre-scan regex patterns — one pass extracts counts for all 6 review dimensions
    _PRESCAN_PATTERNS: dict[str, str] = {
        "informal_language": r"\b(awesome|cool|nice|amazing|stuff|basically)\b",
        "method_claims": (
            r"\b(we\s+propose|we\s+introduce|our\s+method|our\s+approach|we\s+present)\b"
        ),
        "novelty_keywords": (
            r"\b(novel|state-of-the-art|sota|our\s+contribution|first\s+to)\b"
        ),
        "benchmark_keywords": (
            r"\b(benchmark|dataset|baseline|leaderboard|evaluate|outperform)\b"
        ),
        "limitation_keywords": (
            r"\b(limitation|shortcoming|constraint|drawback|future\s+work)\b"
        ),
        "repro_keywords": (
            r"\b(hyperparameter|training\s+setup|implementation\s+details"
            r"|random\s+seed|code\s+available)\b"
        ),
    }

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def build(self, paper_path: str | Path, force: bool = False) -> dict[str, Any]:
        """Build index.  Returns cached copy if mtime unchanged and force=False.

        Args:
            paper_path: Absolute path to the .tex file.
            force: Rebuild even when a fresh cache exists.

        Returns:
            Index dict with keys: _meta, structure, counts, flags, prescan, results.
        """
        path = Path(paper_path)
        if not path.exists():
            raise FileNotFoundError(f"Paper not found: {path}")

        index_path = self._index_path(path)
        mtime = path.stat().st_mtime

        if not force and index_path.exists():
            try:
                existing: dict = yaml.safe_load(index_path.read_text(encoding="utf-8")) or {}
                if existing.get("_meta", {}).get("mtime") == mtime:
                    return existing
            except Exception:
                pass

        raw = path.read_text(encoding="utf-8")
        index: dict[str, Any] = {
            "_meta": {
                "source": path.name,
                "mtime": mtime,
                "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "schema": "1",
            },
            "structure": self._extract_structure(path, raw),
            "counts": self._extract_counts(raw),
            "flags": self._extract_flags(raw),
            "prescan": self._extract_prescan(raw),
            "results": {
                "crane_review_full": None,
                "evaluate_paper_v2": None,
                "crane_diagnose": None,
            },
        }

        index_path.write_text(
            yaml.dump(index, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
        return index

    def load(self, paper_path: str | Path) -> dict[str, Any] | None:
        """Return the fresh cached index, or None if missing/stale."""
        path = Path(paper_path)
        index_path = self._index_path(path)
        if not index_path.exists() or not path.exists():
            return None
        try:
            existing: dict = yaml.safe_load(index_path.read_text(encoding="utf-8")) or {}
            if existing.get("_meta", {}).get("mtime") == path.stat().st_mtime:
                return existing
        except Exception:
            pass
        return None

    def update_results(self, paper_path: str | Path, key: str, data: Any) -> None:
        """Persist a result entry into the index file for downstream reuse."""
        path = Path(paper_path)
        index_path = self._index_path(path)
        if not index_path.exists():
            return
        try:
            existing: dict = yaml.safe_load(index_path.read_text(encoding="utf-8")) or {}
            existing.setdefault("results", {})[key] = data
            index_path.write_text(
                yaml.dump(existing, allow_unicode=True, default_flow_style=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Private extraction helpers                                           #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _index_path(paper_path: Path) -> Path:
        return paper_path.parent / f".{paper_path.stem}_index.yaml"

    def _extract_structure(self, path: Path, raw: str) -> dict[str, Any]:
        title = ""
        m = re.search(r"\\title\{([^}]+)\}", raw)
        if m:
            title = m.group(1).strip()

        return {
            "title": title,
            "abstract": self._extract_abstract(path, raw),
            "sections": self._grep_sections(path, raw),
            "total_lines": raw.count("\n") + 1,
        }

    def _extract_abstract(self, path: Path, raw: str) -> str:
        """Extract abstract text via subprocess sed (single OS call)."""
        try:
            result = subprocess.run(
                ["sed", "-n", r"/\\begin{abstract}/,/\\end{abstract}/p", str(path)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            text = re.sub(
                r"\\begin\{abstract\}|\\end\{abstract\}", "", result.stdout
            ).strip()
            return text[:500]
        except Exception:
            m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", raw, re.DOTALL)
            return m.group(1).strip()[:500] if m else ""

    def _grep_sections(self, path: Path, raw: str) -> list[dict[str, Any]]:
        """Extract section list with line numbers via subprocess grep."""
        try:
            result = subprocess.run(
                [
                    "grep",
                    "-n",
                    r"\\\(section\|subsection\|subsubsection\)\b",
                    str(path),
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            grep_lines = result.stdout.splitlines()
        except Exception:
            grep_lines = []

        sections: list[dict[str, Any]] = []
        for line in grep_lines:
            if ":" not in line:
                continue
            lineno_str, content = line.split(":", 1)
            sm = re.search(
                r"\\(section|subsection|subsubsection)\{([^}]+)\}", content
            )
            if sm:
                sections.append(
                    {
                        "name": sm.group(2).strip(),
                        "level": {
                            "section": 1,
                            "subsection": 2,
                            "subsubsection": 3,
                        }[sm.group(1)],
                        "start_line": int(lineno_str),
                    }
                )
        return sections

    def _extract_counts(self, raw: str) -> dict[str, int]:
        return {
            "words": len(re.findall(r"\b\w+\b", raw)),
            "figures": len(re.findall(r"\\begin\{figure\*?\}", raw)),
            "tables": len(re.findall(r"\\begin\{table\*?\}", raw)),
            "equations": len(re.findall(
                r"\\begin\{(?:equation|align|eqnarray|multline)\*?\}", raw
            )),
            "citations": len(re.findall(r"\\cite(?:p|t|alt|author|year)?\{", raw)),
        }

    def _extract_flags(self, raw: str) -> dict[str, bool]:
        lower = raw.lower()
        return {
            "has_code": bool(
                re.search(r"github\.com|gitlab\.com|code\s+available|repository", lower)
            ),
            "has_appendix": bool(re.search(r"\\appendix\b", raw)),
        }

    def _extract_prescan(self, raw: str) -> dict[str, int]:
        return {
            key: len(re.findall(pattern, raw, re.IGNORECASE))
            for key, pattern in self._PRESCAN_PATTERNS.items()
        }
