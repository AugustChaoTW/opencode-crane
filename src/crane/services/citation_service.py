"""
Citation verification service.
Validates citation consistency between manuscripts and reference library.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from crane.services.reference_service import ReferenceService


class CitationService:
    """Service for citation verification and validation."""

    # Regex to match \cite{key1,key2,...} in LaTeX
    CITE_PATTERN = re.compile(r"\\cite\{([^}]+)\}")

    def __init__(self, refs_dir: str | Path = "references"):
        self.ref_service = ReferenceService(refs_dir)

    def extract_cite_keys(self, text: str) -> list[str]:
        """
        Extract all citation keys from LaTeX text.

        Args:
            text: LaTeX document text

        Returns:
            List of unique citation keys found in text.
        """
        keys: list[str] = []
        for match in self.CITE_PATTERN.finditer(text):
            # Split comma-separated keys: \cite{key1,key2,key3}
            raw_keys = match.group(1).split(",")
            for key in raw_keys:
                key = key.strip()
                if key and key not in keys:
                    keys.append(key)
        return keys

    def check_local_consistency(
        self,
        manuscript_path: str | Path,
        manuscript_text: str | None = None,
    ) -> dict[str, Any]:
        """
        Check if all citations in manuscript exist in reference library.

        Args:
            manuscript_path: Path to manuscript file (used for context)
            manuscript_text: Manuscript text content (if None, reads from path)

        Returns:
            Dict with:
            - valid: bool (True if all citations exist)
            - total_citations: int
            - found: list[str] (keys that exist in references/)
            - missing: list[str] (keys NOT in references/)
            - unused: list[str] (references not cited in manuscript)
        """
        # Get text content
        if manuscript_text is None:
            path = Path(manuscript_path)
            if not path.exists():
                raise FileNotFoundError(f"Manuscript not found: {manuscript_path}")
            manuscript_text = path.read_text(encoding="utf-8")

        # Extract citations from manuscript
        cited_keys = self.extract_cite_keys(manuscript_text)

        # Get all reference keys
        ref_keys = self.ref_service.get_all_keys()

        # Compare
        found = [k for k in cited_keys if k in ref_keys]
        missing = [k for k in cited_keys if k not in ref_keys]
        unused = [k for k in ref_keys if k not in cited_keys]

        return {
            "valid": len(missing) == 0,
            "total_citations": len(cited_keys),
            "found": found,
            "missing": missing,
            "unused": unused,
        }

    def check_metadata(
        self,
        key: str,
        expected_doi: str = "",
        expected_year: int | None = None,
        expected_title: str = "",
    ) -> dict[str, Any]:
        """
        Verify reference metadata matches expected values.

        Args:
            key: Reference citation key
            expected_doi: Expected DOI (optional)
            expected_year: Expected publication year (optional)
            expected_title: Expected title substring (optional)

        Returns:
            Dict with:
            - valid: bool (True if all checks pass)
            - key: str
            - checks: dict with field-level results
        """
        try:
            ref = self.ref_service.get(key)
        except ValueError:
            return {
                "valid": False,
                "key": key,
                "error": f"Reference not found: {key}",
                "checks": {},
            }

        checks: dict[str, dict[str, Any]] = {}
        all_valid = True

        # Check DOI
        if expected_doi:
            actual_doi = str(ref.get("doi", ""))
            doi_match = actual_doi.lower() == expected_doi.lower()
            checks["doi"] = {
                "expected": expected_doi,
                "actual": actual_doi,
                "match": doi_match,
            }
            if not doi_match:
                all_valid = False

        # Check year
        if expected_year is not None:
            actual_year = ref.get("year", 0)
            year_match = actual_year == expected_year
            checks["year"] = {
                "expected": expected_year,
                "actual": actual_year,
                "match": year_match,
            }
            if not year_match:
                all_valid = False

        # Check title (substring match)
        if expected_title:
            actual_title = str(ref.get("title", "")).lower()
            title_match = expected_title.lower() in actual_title
            checks["title"] = {
                "expected": expected_title,
                "actual": ref.get("title", ""),
                "match": title_match,
            }
            if not title_match:
                all_valid = False

        return {
            "valid": all_valid,
            "key": key,
            "checks": checks,
        }

    def check_all_metadata(
        self,
        manuscript_text: str | None = None,
        manuscript_path: str | Path | None = None,
    ) -> list[dict[str, Any]]:
        """
        Check metadata consistency for all cited references.

        Args:
            manuscript_text: Manuscript text (optional)
            manuscript_path: Path to manuscript (optional)

        Returns:
            List of per-reference check results.
        """
        # Get text content
        if manuscript_text is None and manuscript_path is not None:
            path = Path(manuscript_path)
            if path.exists():
                manuscript_text = path.read_text(encoding="utf-8")

        if manuscript_text is None:
            # Check all references if no manuscript provided
            keys = self.ref_service.get_all_keys()
        else:
            keys = self.extract_cite_keys(manuscript_text)

        results = []
        for key in keys:
            try:
                ref = self.ref_service.get(key)
                # Basic metadata presence check
                result = {
                    "key": key,
                    "valid": True,
                    "checks": {},
                }

                # Check required fields
                if not ref.get("title"):
                    result["checks"]["title"] = {"present": False, "match": False}
                    result["valid"] = False
                else:
                    result["checks"]["title"] = {"present": True, "match": True}

                if not ref.get("authors"):
                    result["checks"]["authors"] = {"present": False, "match": False}
                    result["valid"] = False
                else:
                    result["checks"]["authors"] = {"present": True, "match": True}

                if not ref.get("year") or ref.get("year") == 0:
                    result["checks"]["year"] = {"present": False, "match": False}
                    result["valid"] = False
                else:
                    result["checks"]["year"] = {"present": True, "match": True}

                results.append(result)
            except ValueError:
                results.append(
                    {
                        "key": key,
                        "valid": False,
                        "error": f"Reference not found: {key}",
                        "checks": {},
                    }
                )

        return results
