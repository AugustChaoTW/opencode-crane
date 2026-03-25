from __future__ import annotations

import csv
import math
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import requests
import yaml

from crane.services.reference_service import ReferenceService

OPENALEX_SOURCES_API_URL = "https://api.openalex.org/sources"
OPENALEX_EMAIL = "opencode-crane@example.com"

QUARTILE_SCORES = {
    "Q1": 1.0,
    "Q2": 0.8,
    "Q3": 0.6,
    "Q4": 0.4,
}

STOPWORDS = {
    "about",
    "after",
    "also",
    "among",
    "analysis",
    "approach",
    "approaches",
    "based",
    "between",
    "both",
    "computer",
    "data",
    "demonstrate",
    "design",
    "different",
    "effects",
    "experiments",
    "findings",
    "focus",
    "from",
    "have",
    "into",
    "learned",
    "learning",
    "method",
    "methods",
    "model",
    "models",
    "paper",
    "performance",
    "present",
    "problem",
    "propose",
    "proposed",
    "results",
    "show",
    "shows",
    "study",
    "such",
    "system",
    "task",
    "tasks",
    "their",
    "these",
    "this",
    "using",
    "with",
}


class JournalRecommender:
    def __init__(self, data_dir: str | Path | None = None):
        root = (
            Path(data_dir)
            if data_dir is not None
            else Path(__file__).resolve().parents[3] / "data" / "journals"
        )
        self.data_dir = root
        self.sjr_path = self.data_dir / "sjr_snapshot.csv"
        self.templates_path = self.data_dir / "conference_templates.yaml"
        self._openalex_cache: dict[str, dict[str, Any]] = {}
        self._candidates = self._load_candidates()
        self._alias_map = self._build_alias_map(self._candidates)

    def analyze_cited_journals(self, refs_dir: str | Path) -> dict[str, int]:
        ref_service = ReferenceService(refs_dir)
        counts: Counter[str] = Counter()

        for key in ref_service.get_all_keys():
            reference = ref_service.get(key)
            venue_name = self._extract_venue_name(reference)
            if not venue_name:
                continue
            counts[self._canonicalize_name(venue_name)] += 1

        return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))

    def query_journal_metrics(self, journal_name: str) -> dict[str, Any]:
        canonical_name = self._canonicalize_name(journal_name)
        cached = self._openalex_cache.get(canonical_name)
        if cached is not None:
            return cached

        try:
            response = requests.get(
                OPENALEX_SOURCES_API_URL,
                params={"search": journal_name, "per_page": 5, "mailto": OPENALEX_EMAIL},
                timeout=10,
            )
            response.raise_for_status()
            results = response.json().get("results", [])
        except Exception:
            self._openalex_cache[canonical_name] = {}
            return {}

        best_match: dict[str, Any] | None = None
        best_score = -1.0
        for result in results:
            display_name = str(result.get("display_name", ""))
            abbreviated = str(result.get("abbreviated_title", ""))
            score = self._name_similarity(canonical_name, display_name)
            if abbreviated:
                score = max(score, self._name_similarity(canonical_name, abbreviated))
            if score > best_score:
                best_match = result
                best_score = score

        if not best_match or best_score < 0.45:
            self._openalex_cache[canonical_name] = {}
            return {}

        summary_stats = best_match.get("summary_stats", {}) or {}
        metrics = {
            "id": best_match.get("id", ""),
            "full_name": best_match.get("display_name", journal_name),
            "works_count": int(best_match.get("works_count", 0) or 0),
            "cited_by_count": int(best_match.get("cited_by_count", 0) or 0),
            "h_index": int(summary_stats.get("h_index", 0) or 0),
            "2yr_mean_citedness": float(summary_stats.get("2yr_mean_citedness", 0.0) or 0.0),
            "is_in_doaj": bool(best_match.get("is_in_doaj", False)),
        }
        self._openalex_cache[canonical_name] = metrics
        return metrics

    def calculate_relevance_score(
        self,
        journal: dict[str, Any],
        topic: str,
        cited_journals: dict[str, int],
    ) -> float:
        topic_tokens = set(self._tokenize(topic))
        venue_tokens = set(
            self._tokenize(
                " ".join(
                    [
                        str(journal.get("full_name", "")),
                        str(journal.get("abbr", "")),
                        " ".join(journal.get("topics", [])),
                        " ".join(journal.get("aliases", [])),
                    ]
                )
            )
        )

        topic_score = 0.0
        if topic_tokens and venue_tokens:
            topic_score = len(topic_tokens & venue_tokens) / len(topic_tokens)

        citation_score = self._citation_fit_score(journal, cited_journals)
        quartile_score = QUARTILE_SCORES.get(str(journal.get("quartile", "")).upper(), 0.5)

        metrics = journal.get("openalex_metrics", {}) or {}
        impact_score = self._impact_score(
            cited_by_count=metrics.get("cited_by_count", 0),
            h_index=metrics.get("h_index", journal.get("h_index", 0)),
        )

        acceptance_rate = float(journal.get("acceptance_rate", 0.0) or 0.0)
        selectivity_fit = 0.0
        if acceptance_rate > 0:
            selectivity_fit = max(0.0, 1.0 - abs(acceptance_rate - 0.22) / 0.22)

        score = (
            0.45 * topic_score
            + 0.25 * citation_score
            + 0.15 * quartile_score
            + 0.10 * impact_score
            + 0.05 * selectivity_fit
        )
        return max(0.0, min(1.0, score))

    def recommend(self, paper_text: str, refs_dir: str | Path) -> list[dict[str, Any]]:
        topic = self._build_topic_query(paper_text)
        cited_journals = self.analyze_cited_journals(refs_dir)

        recommendations: list[dict[str, Any]] = []
        for candidate in self._candidates:
            enriched_candidate = dict(candidate)
            enriched_candidate["openalex_metrics"] = self.query_journal_metrics(
                str(candidate.get("full_name", ""))
            )
            score = self.calculate_relevance_score(enriched_candidate, topic, cited_journals)
            recommendations.append(
                {
                    "abbr": str(candidate.get("abbr", ""))[:5],
                    "full_name": str(candidate.get("full_name", "")),
                    "acceptance_rate": float(candidate.get("acceptance_rate", 0.0) or 0.0),
                    "relevance_score": round(score, 4),
                    "quartile": str(candidate.get("quartile", "")),
                }
            )

        recommendations.sort(
            key=lambda item: (
                -item["relevance_score"],
                item["acceptance_rate"] if item["acceptance_rate"] > 0 else 1.0,
                item["full_name"],
            )
        )
        return recommendations[:5]

    def find_similar_papers_in_journal(
        self,
        paper_keywords: list[str],
        journal_name: str,
        max_results: int = 10,
    ) -> dict[str, Any]:
        """Find similar papers in a specific journal based on keywords.

        Args:
            paper_keywords: Keywords from the target paper
            journal_name: Name or abbreviation of the journal
            max_results: Maximum number of similar papers to return

        Returns:
            Dict with similar_papers list and match statistics.
        """
        canonical_name = self._canonicalize_name(journal_name)
        journal_metrics = self.query_journal_metrics(canonical_name)

        if not journal_metrics:
            return {
                "journal": journal_name,
                "similar_papers": [],
                "match_count": 0,
                "total_searched": 0,
                "match_rate": 0.0,
                "keywords_matched": [],
                "recommendation": "Journal not found in database",
            }

        journal_id = journal_metrics.get("id", "")

        try:
            query = " ".join(paper_keywords[:5])
            response = requests.get(
                "https://api.openalex.org/works",
                params={
                    "filter": f"primary_location.source.id:{journal_id}",
                    "search": query,
                    "per_page": max_results,
                    "mailto": OPENALEX_EMAIL,
                },
                timeout=15,
            )
            response.raise_for_status()
            results = response.json().get("results", [])
        except Exception:
            return {
                "journal": canonical_name,
                "similar_papers": [],
                "match_count": 0,
                "total_searched": 0,
                "match_rate": 0.0,
                "keywords_matched": [],
                "recommendation": "Failed to query OpenAlex API",
            }

        similar_papers = []
        keywords_matched = set()

        for work in results:
            title = str(work.get("title", "")).lower()
            abstract_inverted = work.get("abstract_inverted_index") or {}
            abstract = " ".join(
                word
                for word, positions in sorted(
                    [(w, min(p)) for w, p in abstract_inverted.items()],
                    key=lambda x: x[1],
                )
            ).lower()

            combined_text = f"{title} {abstract}"
            matched_keywords = [kw for kw in paper_keywords if kw.lower() in combined_text]

            if matched_keywords:
                keywords_matched.update(matched_keywords)

                authors = []
                for authorship in work.get("authorships", [])[:3]:
                    author = authorship.get("author", {})
                    if author.get("display_name"):
                        authors.append(author["display_name"])

                similar_papers.append(
                    {
                        "title": work.get("title", ""),
                        "authors": authors,
                        "year": work.get("publication_year", 0),
                        "doi": (work.get("doi") or "").replace("https://doi.org/", ""),
                        "url": work.get("doi", "")
                        or f"https://openalex.org/{work.get('id', '').split('/')[-1]}",
                        "keywords_matched": matched_keywords,
                        "match_score": len(matched_keywords) / max(len(paper_keywords), 1),
                    }
                )

        total_searched = len(results)
        match_count = len(similar_papers)
        match_rate = match_count / max(total_searched, 1)

        if match_count >= 3:
            recommendation = f"STRONG FIT: {match_count} similar papers found in {canonical_name}"
        elif match_count >= 1:
            recommendation = (
                f"MODERATE FIT: {match_count} similar papers found, consider framing adjustments"
            )
        else:
            recommendation = "WEAK FIT: No similar papers found, consider different journal"

        return {
            "journal": canonical_name,
            "similar_papers": sorted(similar_papers, key=lambda x: -x["match_score"]),
            "match_count": match_count,
            "total_searched": total_searched,
            "match_rate": round(match_rate, 2),
            "keywords_matched": sorted(keywords_matched),
            "recommendation": recommendation,
        }

    def _load_candidates(self) -> list[dict[str, Any]]:
        if not self.sjr_path.exists():
            raise FileNotFoundError(f"SJR snapshot not found: {self.sjr_path}")

        candidates: list[dict[str, Any]] = []
        with self.sjr_path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                aliases = self._split_multi_value(row.get("aliases", ""))
                topics = self._split_multi_value(row.get("topics", ""))
                full_name = str(row.get("full_name", "")).strip()
                abbr = str(row.get("abbr", "")).strip()
                if not full_name or not abbr:
                    continue

                candidate = {
                    "full_name": full_name,
                    "abbr": abbr[:5].upper(),
                    "quartile": str(row.get("quartile", "Q2")).strip().upper(),
                    "acceptance_rate": float(row.get("acceptance_rate", 0.0) or 0.0),
                    "h_index": int(row.get("h_index", 0) or 0),
                    "topics": topics,
                    "aliases": sorted(set([full_name, abbr, *aliases])),
                    "venue_type": str(row.get("venue_type", "journal")).strip().lower(),
                }
                candidates.append(candidate)

        templates_payload = {}
        if self.templates_path.exists():
            templates_payload = (
                yaml.safe_load(self.templates_path.read_text(encoding="utf-8")) or {}
            )

        templates = templates_payload.get("conferences", []) or []
        by_name = {self._normalize_name(item["full_name"]): item for item in candidates}

        for template in templates:
            full_name = str(template.get("full_name", "")).strip()
            if not full_name:
                continue
            normalized = self._normalize_name(full_name)
            candidate = by_name.get(normalized)
            if candidate is None:
                candidate = {
                    "full_name": full_name,
                    "abbr": str(template.get("abbr", ""))[:5].upper(),
                    "quartile": str(template.get("quartile", "Q2")).upper(),
                    "acceptance_rate": 0.0,
                    "h_index": 0,
                    "topics": [],
                    "aliases": [full_name],
                    "venue_type": "conference",
                }
                by_name[normalized] = candidate
                candidates.append(candidate)

            candidate["abbr"] = str(template.get("abbr", candidate.get("abbr", "")))[:5].upper()
            candidate["aliases"] = sorted(
                set(candidate.get("aliases", []) + template.get("aliases", []))
            )
            candidate["topics"] = sorted(
                set(candidate.get("topics", []) + template.get("topic_keywords", []))
            )
            candidate["venue_type"] = "conference"

        return candidates

    def _build_alias_map(self, candidates: list[dict[str, Any]]) -> dict[str, str]:
        alias_map: dict[str, str] = {}
        for candidate in candidates:
            full_name = str(candidate.get("full_name", "")).strip()
            for alias in candidate.get("aliases", []):
                alias_map[self._normalize_name(alias)] = full_name
        return alias_map

    def _canonicalize_name(self, journal_name: str) -> str:
        normalized = self._normalize_name(journal_name)
        canonical = self._alias_map.get(normalized)
        return canonical if canonical else journal_name.strip()

    def _extract_venue_name(self, reference: dict[str, Any]) -> str:
        for field in ("venue", "journal", "container_title", "booktitle"):
            value = str(reference.get(field, "")).strip()
            if value:
                return value
        return ""

    def _build_topic_query(self, paper_text: str) -> str:
        tokens = self._tokenize(paper_text)
        if not tokens:
            return "artificial intelligence computer science"
        counts = Counter(tokens)
        return " ".join(token for token, _ in counts.most_common(12))

    def _tokenize(self, text: str) -> list[str]:
        cleaned = re.sub(r"[^a-zA-Z0-9]+", " ", text.lower())
        tokens = []
        for token in cleaned.split():
            if token in STOPWORDS:
                continue
            if len(token) < 2:
                continue
            if token.isdigit():
                continue
            tokens.append(token)
        return tokens

    def _split_multi_value(self, value: str) -> list[str]:
        if not value:
            return []
        parts = re.split(r"[|;]", value)
        return [part.strip() for part in parts if part.strip()]

    def _normalize_name(self, value: str) -> str:
        normalized = value.lower().replace("&", "and")
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
        return re.sub(r"\s+", " ", normalized).strip()

    def _name_similarity(self, query: str, candidate: str) -> float:
        normalized_query = self._normalize_name(query)
        normalized_candidate = self._normalize_name(candidate)
        if normalized_query == normalized_candidate:
            return 1.0
        if normalized_query in normalized_candidate or normalized_candidate in normalized_query:
            return 0.92
        return SequenceMatcher(None, normalized_query, normalized_candidate).ratio()

    def _citation_fit_score(self, journal: dict[str, Any], cited_journals: dict[str, int]) -> float:
        if not cited_journals:
            return 0.0

        max_count = max(cited_journals.values())
        aliases = [
            journal.get("full_name", ""),
            journal.get("abbr", ""),
            *journal.get("aliases", []),
        ]
        normalized_aliases = [self._normalize_name(str(alias)) for alias in aliases if alias]

        exact_score = 0.0
        for cited_name, count in cited_journals.items():
            normalized_cited = self._normalize_name(cited_name)
            if normalized_cited in normalized_aliases:
                exact_score = max(exact_score, count / max_count)

        similarity_score = 0.0
        for cited_name, count in cited_journals.items():
            normalized_cited = self._normalize_name(cited_name)
            similarity = max(
                SequenceMatcher(None, normalized_cited, normalized_alias).ratio()
                for normalized_alias in normalized_aliases
            )
            similarity_score = max(similarity_score, similarity * (count / max_count))

        return max(exact_score, similarity_score * 0.6)

    def _impact_score(self, cited_by_count: int, h_index: int) -> float:
        citation_component = min(1.0, math.log1p(max(cited_by_count, 0)) / 12.0)
        h_index_component = min(1.0, max(h_index, 0) / 400.0)
        return max(citation_component, h_index_component)
