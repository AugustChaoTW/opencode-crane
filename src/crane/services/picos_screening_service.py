from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from crane.services.reference_service import ReferenceService


@dataclass
class PICOSCriteria:
    population: str = ""
    intervention: str = ""
    comparison: str = ""
    outcome: str = ""
    study_design: str = ""

    def __post_init__(self) -> None:
        self.population = self.population.strip()
        self.intervention = self.intervention.strip()
        self.comparison = self.comparison.strip()
        self.outcome = self.outcome.strip()
        self.study_design = self.study_design.strip()


@dataclass
class PICOSMatch:
    population_score: float
    intervention_score: float
    comparison_score: float
    outcome_score: float
    study_design_score: float
    overall_score: float
    matched_terms: dict[str, list[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.population_score = self._validate_score(self.population_score, "population_score")
        self.intervention_score = self._validate_score(
            self.intervention_score, "intervention_score"
        )
        self.comparison_score = self._validate_score(self.comparison_score, "comparison_score")
        self.outcome_score = self._validate_score(self.outcome_score, "outcome_score")
        self.study_design_score = self._validate_score(
            self.study_design_score, "study_design_score"
        )
        self.overall_score = self._validate_score(self.overall_score, "overall_score")

    @staticmethod
    def _validate_score(value: float, name: str) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be between 0.0 and 1.0")
        return float(value)


@dataclass
class PICOSScreeningResult:
    paper_key: str
    title: str
    match: PICOSMatch
    decision: str
    extracted_picos: PICOSCriteria

    def __post_init__(self) -> None:
        if self.decision not in {"include", "exclude", "maybe"}:
            raise ValueError("decision must be one of: include, exclude, maybe")


class PICOSScreeningService:
    _STOPWORDS = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "into",
        "is",
        "it",
        "of",
        "on",
        "or",
        "our",
        "that",
        "the",
        "their",
        "this",
        "to",
        "using",
        "use",
        "we",
        "with",
    }

    _STUDY_DESIGN_SYNONYMS: dict[str, set[str]] = {
        "empirical": {
            "empirical",
            "experiment",
            "experimental",
            "benchmark",
            "evaluation",
            "ablation",
            "dataset",
        },
        "theoretical": {
            "theoretical",
            "theory",
            "proof",
            "lemma",
            "theorem",
            "analysis",
            "bound",
        },
        "survey": {
            "survey",
            "review",
            "systematic",
            "meta-analysis",
            "meta analysis",
            "literature",
        },
    }

    _INTERVENTION_KEYWORDS = {
        "attention",
        "transformer",
        "cnn",
        "rnn",
        "framework",
        "method",
        "approach",
        "algorithm",
        "retrieval",
        "prompt",
        "fine-tuning",
        "finetuning",
    }

    _OUTCOME_KEYWORDS = {
        "accuracy",
        "f1",
        "precision",
        "recall",
        "auc",
        "latency",
        "throughput",
        "cost",
        "robustness",
        "efficiency",
        "performance",
    }

    _POPULATION_HINTS = {
        "patients",
        "models",
        "learners",
        "students",
        "participants",
        "dataset",
        "datasets",
        "documents",
        "images",
        "text",
        "language models",
    }

    _WEIGHTS = {
        "population": 0.25,
        "intervention": 0.25,
        "comparison": 0.15,
        "outcome": 0.20,
        "study_design": 0.15,
    }

    def __init__(self, refs_dir: str | Path = "references"):
        self.ref_service = ReferenceService(refs_dir)

    def extract_picos(self, paper_data: dict[str, Any]) -> PICOSCriteria:
        title = str(paper_data.get("title", ""))
        abstract = str(paper_data.get("abstract", ""))
        annotations = paper_data.get("ai_annotations", {}) or {}
        methodology = str(annotations.get("methodology", ""))
        contributions_raw = annotations.get("key_contributions", [])
        contributions = ""
        if isinstance(contributions_raw, list):
            contributions = " ".join(str(item) for item in contributions_raw)
        elif contributions_raw:
            contributions = str(contributions_raw)

        combined = " ".join([title, abstract, methodology, contributions]).strip()

        population = self._extract_population(title, abstract, methodology, contributions)
        intervention = self._extract_intervention(title, abstract, methodology, contributions)
        comparison = self._extract_comparison(abstract + " " + contributions)
        outcome = self._extract_outcome(abstract + " " + contributions)
        study_design = self._extract_study_design(combined)

        return PICOSCriteria(
            population=population,
            intervention=intervention,
            comparison=comparison,
            outcome=outcome,
            study_design=study_design,
        )

    def match_paper(self, paper_picos: PICOSCriteria, criteria: PICOSCriteria) -> PICOSMatch:
        pop_score, pop_terms = self._overlap_score(paper_picos.population, criteria.population)
        int_score, int_terms = self._overlap_score(paper_picos.intervention, criteria.intervention)
        cmp_score, cmp_terms = self._overlap_score(paper_picos.comparison, criteria.comparison)
        out_score, out_terms = self._overlap_score(paper_picos.outcome, criteria.outcome)

        paper_design = self._normalize_study_design_text(paper_picos.study_design)
        criteria_design = self._normalize_study_design_text(criteria.study_design)
        design_score, design_terms = self._overlap_score(paper_design, criteria_design)

        overall = (
            pop_score * self._WEIGHTS["population"]
            + int_score * self._WEIGHTS["intervention"]
            + cmp_score * self._WEIGHTS["comparison"]
            + out_score * self._WEIGHTS["outcome"]
            + design_score * self._WEIGHTS["study_design"]
        )

        return PICOSMatch(
            population_score=pop_score,
            intervention_score=int_score,
            comparison_score=cmp_score,
            outcome_score=out_score,
            study_design_score=design_score,
            overall_score=overall,
            matched_terms={
                "population": pop_terms,
                "intervention": int_terms,
                "comparison": cmp_terms,
                "outcome": out_terms,
                "study_design": design_terms,
            },
        )

    def screen_papers(
        self, paper_keys: list[str], criteria: PICOSCriteria, threshold: float = 0.5
    ) -> list[PICOSScreeningResult]:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")

        results: list[PICOSScreeningResult] = []
        for paper_key in paper_keys:
            paper_data = self.ref_service.get(paper_key)
            extracted = self.extract_picos(paper_data)
            match = self.match_paper(extracted, criteria)

            if match.overall_score >= threshold:
                decision = "include"
            elif match.overall_score >= threshold * 0.5:
                decision = "maybe"
            else:
                decision = "exclude"

            results.append(
                PICOSScreeningResult(
                    paper_key=paper_key,
                    title=str(paper_data.get("title", "")),
                    match=match,
                    decision=decision,
                    extracted_picos=extracted,
                )
            )

        return sorted(results, key=lambda item: item.match.overall_score, reverse=True)

    def _extract_population(
        self, title: str, abstract: str, methodology: str, contributions: str
    ) -> str:
        text = " ".join([title, abstract, methodology, contributions])
        extracted: list[str] = []

        for pattern in [
            r"\b(?:for|in|on|among|with)\s+([a-zA-Z0-9\-\s]{4,50}?)(?:,|\.|;|\busing\b|\bvia\b)",
            r"\b(?:target|focus(?:es|ed)? on)\s+([a-zA-Z0-9\-\s]{4,50}?)(?:,|\.|;)",
        ]:
            matches = re.findall(pattern, text, flags=re.IGNORECASE)
            for match in matches:
                candidate = " ".join(match.split()).strip().lower()
                if candidate and any(hint in candidate for hint in self._POPULATION_HINTS):
                    extracted.append(candidate)

        token_text = self._tokens_to_text(self._tokenize(text))
        for hint in sorted(self._POPULATION_HINTS):
            if hint in token_text and hint not in extracted:
                extracted.append(hint)

        return "; ".join(dict.fromkeys(extracted[:3]))

    def _extract_intervention(
        self, title: str, abstract: str, methodology: str, contributions: str
    ) -> str:
        text = " ".join([title, abstract, methodology, contributions]).lower()
        extracted: list[str] = []

        for keyword in sorted(self._INTERVENTION_KEYWORDS):
            if keyword in text:
                extracted.append(keyword)

        for pattern in [
            r"\b(?:we propose|we introduce|we present|our method|our approach)\s+([a-zA-Z0-9\-\s]{3,60}?)(?:,|\.|;)",
            r"\b(?:using|via)\s+([a-zA-Z0-9\-\s]{3,40}?)(?:\sto\s|,|\.|;)",
        ]:
            matches = re.findall(pattern, text, flags=re.IGNORECASE)
            for match in matches:
                candidate = " ".join(match.split()).strip()
                if candidate:
                    extracted.append(candidate)

        return "; ".join(dict.fromkeys(extracted[:5]))

    def _extract_comparison(self, text: str) -> str:
        extracted: list[str] = []

        baseline_terms = re.findall(r"\bbaseline\s+([a-zA-Z0-9\-]+)", text, flags=re.IGNORECASE)
        for term in baseline_terms:
            extracted.append(f"baseline {term.lower()}")

        for pattern in [
            r"\b(?:compared to|compared with|against|versus|vs\.?|than)\s+([a-zA-Z0-9\-\s]{3,40}?)(?:,|\.|;|\band\b|\bwhich\b|\bthat\b)",
            r"\b(?:baseline(?:s)?|state of the art|sota)\s*:?\s*([a-zA-Z0-9\-\s]{3,40}?)(?:,|\.|;)",
        ]:
            matches = re.findall(pattern, text, flags=re.IGNORECASE)
            for match in matches:
                candidate = " ".join(match.split()).strip().lower()
                if candidate:
                    extracted.append(candidate)
        return "; ".join(dict.fromkeys(extracted[:4]))

    def _extract_outcome(self, text: str) -> str:
        lowered = text.lower()
        extracted: list[str] = []

        for keyword in sorted(self._OUTCOME_KEYWORDS):
            if keyword in lowered:
                extracted.append(keyword)

        for pattern in [
            r"\b(?:improv(?:e|es|ed)|increase(?:s|d)?|reduce(?:s|d)?|achieve(?:s|d)?)\s+([a-zA-Z0-9\-\s]{3,40}?)(?:,|\.|;)",
            r"\b([a-zA-Z0-9\-\s]{3,30}?(?:accuracy|f1|precision|recall|latency|cost|performance))\b",
        ]:
            matches = re.findall(pattern, text, flags=re.IGNORECASE)
            for match in matches:
                candidate = " ".join(match.split()).strip().lower()
                if candidate:
                    extracted.append(candidate)

        return "; ".join(dict.fromkeys(extracted[:5]))

    def _extract_study_design(self, text: str) -> str:
        lowered = text.lower()
        for design in ["survey", "theoretical", "empirical"]:
            synonyms = self._STUDY_DESIGN_SYNONYMS[design]
            if any(term in lowered for term in synonyms):
                return design
        return ""

    def _normalize_study_design_text(self, value: str) -> str:
        lowered = value.lower().strip()
        if not lowered:
            return ""

        labels: list[str] = []
        for design, terms in self._STUDY_DESIGN_SYNONYMS.items():
            if lowered == design or any(term in lowered for term in terms):
                labels.append(design)

        if not labels:
            return lowered
        return " ".join(dict.fromkeys(labels))

    def _overlap_score(self, paper_text: str, criteria_text: str) -> tuple[float, list[str]]:
        criteria_tokens = self._tokenize(criteria_text)
        if not criteria_tokens:
            return 1.0, []

        paper_tokens = self._tokenize(paper_text)
        if not paper_tokens:
            return 0.0, []

        overlap = sorted(criteria_tokens & paper_tokens)
        score = len(overlap) / len(criteria_tokens)
        return min(1.0, max(0.0, score)), overlap

    def _tokenize(self, text: str) -> set[str]:
        tokens = re.findall(r"[a-zA-Z0-9\-]+", text.lower())
        return {
            token
            for token in tokens
            if len(token) > 2 and token not in self._STOPWORDS and not token.isdigit()
        }

    def _tokens_to_text(self, tokens: set[str]) -> str:
        return " ".join(sorted(tokens))
