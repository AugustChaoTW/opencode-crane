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
    SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")

    _FACTUAL_HINTS = (
        "improves",
        "improved",
        "increases",
        "increased",
        "decreases",
        "decreased",
        "reduces",
        "reduced",
        "outperforms",
        "achieves",
        "achieved",
        "shows",
        "demonstrates",
        "yields",
        "results in",
        "%",
    )
    _INFERENCE_HINTS = (
        "therefore",
        "thus",
        "hence",
        "suggests",
        "implies",
        "indicates",
    )
    _SPECULATION_HINTS = (
        "may",
        "might",
        "could",
        "possibly",
        "perhaps",
        "likely",
        "potentially",
        "we believe",
        "we hypothesize",
        "we assume",
    )

    _POSITIVE_RELATION_WORDS = (
        "improves",
        "improved",
        "improving",
        "enhances",
        "increases",
        "increased",
        "boosts",
        "outperforms",
        "better",
        "higher",
    )
    _NEGATIVE_RELATION_WORDS = (
        "degrades",
        "degraded",
        "worsens",
        "worsened",
        "decreases",
        "decreased",
        "reduces",
        "reduced",
        "worse",
        "lower",
    )

    _RELATION_PATTERN = re.compile(
        r"\b(?P<subject>[A-Za-z][A-Za-z0-9_\-\s]{1,80}?)\s+"
        r"(?P<relation>improves|improved|enhances|increases|increased|boosts|"
        r"outperforms|degrades|degraded|worsens|worsened|decreases|decreased|"
        r"reduces|reduced|is better than|is worse than)\s+"
        r"(?P<object>[A-Za-z][A-Za-z0-9_\-\s]{1,80})\b",
        re.IGNORECASE,
    )

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

    def _extract_claim_sentences(self, manuscript_text: str) -> list[str]:
        """Extract candidate factual claim sentences from manuscript text."""
        compact_text = " ".join(manuscript_text.split())
        if not compact_text:
            return []

        raw_sentences = self.SENTENCE_SPLIT_PATTERN.split(compact_text)
        claim_sentences: list[str] = []
        for sentence in raw_sentences:
            cleaned = sentence.strip()
            if not cleaned:
                continue

            lowered = cleaned.lower()
            has_citation = bool(self.CITE_PATTERN.search(cleaned))
            looks_factual = any(hint in lowered for hint in self._FACTUAL_HINTS)
            looks_inferential = any(hint in lowered for hint in self._INFERENCE_HINTS)
            looks_speculative = any(hint in lowered for hint in self._SPECULATION_HINTS)
            has_number = bool(re.search(r"\d", cleaned))
            if (
                has_citation
                or looks_factual
                or looks_inferential
                or looks_speculative
                or has_number
            ):
                claim_sentences.append(cleaned)

        return claim_sentences

    def _reference_has_complete_metadata(self, key: str) -> bool:
        """Return True when citation metadata is complete enough to verify claim support."""
        try:
            ref = self.ref_service.get(key)
        except ValueError:
            return False

        if not isinstance(ref, dict):
            return False
        return bool(ref.get("title") and ref.get("authors") and ref.get("year"))

    def analyze_claims(self, manuscript_text: str) -> list[dict[str, Any]]:
        """
        Classify manuscript claims by evidence level (Hallucination Destroyer).

        Evidence levels:
        - VERIFIED: claim has citation with existing key and complete metadata
        - PROBABLE: claim has citation with existing key but incomplete metadata
        - INFERRED: no citation, claim uses deductive/inferential language
        - SPECULATIVE: no citation and no direct verifiable support

        Args:
            manuscript_text: Manuscript text content.

        Returns:
            List of claim dicts with text, evidence_level, citation_key, confidence.
        """
        cited_keys = set(self.extract_cite_keys(manuscript_text))
        claims: list[dict[str, Any]] = []

        for sentence in self._extract_claim_sentences(manuscript_text):
            sentence_keys = self.extract_cite_keys(sentence)
            citation_key = sentence_keys[0] if sentence_keys else ""
            lowered = sentence.lower()

            if citation_key:
                if citation_key in cited_keys and self._reference_has_complete_metadata(
                    citation_key
                ):
                    evidence_level = "VERIFIED"
                    confidence = 0.95
                elif citation_key in cited_keys:
                    evidence_level = "PROBABLE"
                    confidence = 0.75
                else:
                    evidence_level = "SPECULATIVE"
                    confidence = 0.35
            elif any(hint in lowered for hint in self._INFERENCE_HINTS):
                evidence_level = "INFERRED"
                confidence = 0.6
            elif any(hint in lowered for hint in self._SPECULATION_HINTS):
                evidence_level = "SPECULATIVE"
                confidence = 0.35
            else:
                evidence_level = "INFERRED"
                confidence = 0.5

            claims.append(
                {
                    "text": sentence,
                    "evidence_level": evidence_level,
                    "citation_key": citation_key,
                    "confidence": confidence,
                }
            )

        return claims

    def _extract_relation_signature(self, claim_text: str) -> tuple[str, str, str] | None:
        """Extract (subject, object, polarity) relation signature from claim text."""
        match = self._RELATION_PATTERN.search(claim_text)
        if not match:
            return None

        subject = " ".join(match.group("subject").lower().split())
        obj = " ".join(match.group("object").lower().split())
        relation = match.group("relation").lower()

        if relation in self._POSITIVE_RELATION_WORDS or relation == "is better than":
            polarity = "positive"
        elif relation in self._NEGATIVE_RELATION_WORDS or relation == "is worse than":
            polarity = "negative"
        else:
            return None

        return subject, obj, polarity

    def scan_contradictions(self, claims: list[dict[str, Any]]) -> list[dict[str, str]]:
        """
        Scan claims for logical contradictions via keyword-pattern polarity checks.

        Args:
            claims: Claim dicts from analyze_claims().

        Returns:
            List of contradiction records with claim_a, claim_b, reason.
        """
        contradictions: list[dict[str, str]] = []
        relation_claims: list[tuple[str, str, str, str]] = []

        for claim in claims:
            claim_text = str(claim.get("text", "")).strip()
            if not claim_text:
                continue
            signature = self._extract_relation_signature(claim_text)
            if signature is None:
                continue
            subject, obj, polarity = signature
            relation_claims.append((subject, obj, polarity, claim_text))

        for idx, (subj_a, obj_a, polarity_a, text_a) in enumerate(relation_claims):
            for subj_b, obj_b, polarity_b, text_b in relation_claims[idx + 1 :]:
                same_direction = subj_a == subj_b and obj_a == obj_b
                reverse_direction = subj_a == obj_b and obj_a == subj_b
                polarity_conflict = polarity_a != polarity_b

                if polarity_conflict and (same_direction or reverse_direction):
                    reason = (
                        f"Conflicting polarity for relationship between '{subj_a}' and '{obj_a}'"
                    )
                    contradictions.append(
                        {
                            "claim_a": text_a,
                            "claim_b": text_b,
                            "reason": reason,
                        }
                    )

        return contradictions

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
            - claims: list[dict] claim-level evidence classifications
            - unverified_count: int (INFERRED + SPECULATIVE claims)
            - contradictions: list[dict] contradiction pairs with explanation
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

        claims = self.analyze_claims(manuscript_text)
        contradictions = self.scan_contradictions(claims)
        unverified_count = sum(
            1 for claim in claims if claim.get("evidence_level") in {"INFERRED", "SPECULATIVE"}
        )

        return {
            "valid": len(missing) == 0,
            "total_citations": len(cited_keys),
            "found": found,
            "missing": missing,
            "unused": unused,
            "claims": claims,
            "unverified_count": unverified_count,
            "contradictions": contradictions,
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
