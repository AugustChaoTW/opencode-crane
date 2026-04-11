from __future__ import annotations

import re
from pathlib import Path

from crane.models.paper_profile import (
    EvidenceItem,
    EvidenceLedger,
    EvidencePattern,
    EvidenceSignal,
    NoveltyShape,
    PaperProfile,
    PaperType,
)
from crane.services.latex_parser import get_all_sections_flat, parse_latex_sections


class PaperProfileService:
    def extract_profile(self, paper_path: str | Path) -> PaperProfile:
        structure = parse_latex_sections(paper_path)
        text = structure.raw_text
        sections = {
            section.name.lower(): section.content for section in get_all_sections_flat(structure)
        }

        paper_type = self.classify_paper_type(text, sections)
        method_family = self.detect_method_family(text)
        evidence_pattern = self.detect_evidence_pattern(text)
        novelty_shape = self.detect_novelty_shape(text)
        reproducibility_maturity = self.assess_reproducibility(text)

        num_figures = len(re.findall(r"\\begin\{figure\*?\}", text, flags=re.IGNORECASE))
        num_tables = len(re.findall(r"\\begin\{table\*?\}", text, flags=re.IGNORECASE))
        num_equations = len(
            re.findall(
                r"\\begin\{(?:equation|align|eqnarray|multline)\*?\}", text, flags=re.IGNORECASE
            )
        )
        num_references = self._count_references(text)
        word_count = len(re.findall(r"\b\w+\b", text))
        has_code = bool(
            re.search(
                r"\b(github\.com|gitlab\.com|code\s+available|repository)\b", text, re.IGNORECASE
            )
        )
        has_appendix = bool(structure.appendices) or bool(re.search(r"\\appendix\b", text))

        validation_scale = self._detect_validation_scale(text)
        citation_neighborhood = self._detect_citation_neighborhood(text)
        problem_domain = self._detect_problem_domain(text)
        keywords = self._extract_keywords(text)

        return PaperProfile(
            paper_type=paper_type,
            method_family=method_family,
            evidence_pattern=evidence_pattern,
            validation_scale=validation_scale,
            citation_neighborhood=citation_neighborhood,
            novelty_shape=novelty_shape,
            reproducibility_maturity=reproducibility_maturity,
            problem_domain=problem_domain,
            keywords=keywords,
            word_count=word_count,
            has_code=has_code,
            has_appendix=has_appendix,
            num_figures=num_figures,
            num_tables=num_tables,
            num_equations=num_equations,
            num_references=num_references,
        )

    def extract_evidence(self, paper_path: str | Path) -> EvidenceLedger:
        structure = parse_latex_sections(paper_path)
        ledger = EvidenceLedger()

        for section in get_all_sections_flat(structure):
            section_name = section.name
            for sentence in self._split_sentences(section.content):
                claim_match = re.search(
                    r"\b(we\s+(?:propose|present|show|demonstrate|find|analyze)|our\s+(?:results|analysis|method)|(?:may|might)\s+suggest)\b",
                    sentence,
                    re.IGNORECASE,
                )
                if claim_match:
                    signal = EvidenceSignal.OBSERVED
                    confidence = 0.9
                    if re.search(r"\b(may|might|suggests?)\b", sentence, re.IGNORECASE):
                        signal = EvidenceSignal.INFERRED
                        confidence = 0.6
                    ledger.items.append(
                        EvidenceItem(
                            claim=sentence.strip()[:220],
                            section=section_name,
                            span=sentence.strip(),
                            signal=signal,
                            confidence=confidence,
                        )
                    )

        text = structure.raw_text
        if re.search(r"\b(experiment|result|evaluation)\b", text, re.IGNORECASE) and not re.search(
            r"\b(baseline|dataset|benchmark)\b", text, re.IGNORECASE
        ):
            ledger.items.append(
                EvidenceItem(
                    claim="expected empirical support",
                    section="global",
                    span="missing benchmark or dataset details",
                    signal=EvidenceSignal.MISSING,
                    confidence=1.0,
                )
            )

        return ledger

    def classify_paper_type(self, text: str, sections: dict[str, str]) -> PaperType:
        normalized_sections = {name.lower() for name in sections}
        title = self._extract_title(text).lower()
        num_references = self._count_references(text)

        has_experiment_section = any(
            token in section
            for section in normalized_sections
            for token in ("experiment", "results", "evaluation")
        )
        has_empirical_terms = bool(
            re.search(r"\b(benchmark|dataset|accuracy|f1|auc|ablation)\b", text, re.IGNORECASE)
        )

        has_system_section = any(
            token in section
            for section in normalized_sections
            for token in ("system", "architecture", "implementation")
        )
        has_deployment_terms = bool(
            re.search(
                r"\b(deploy|deployment|production|latency|throughput|serving)\b",
                text,
                re.IGNORECASE,
            )
        )

        has_theorem_terms = bool(
            re.search(
                r"\b(theorem|proof|lemma|proposition|corollary)\b",
                text,
                re.IGNORECASE,
            )
        )
        has_math_formulation = bool(
            re.search(
                r"\\begin\{(?:equation|align|eqnarray|multline)\*?\}|\$[^$]+\$",
                text,
                re.IGNORECASE,
            )
        )

        if ("survey" in title or "review" in title) and num_references > 50:
            return PaperType.SURVEY
        if has_theorem_terms and has_math_formulation:
            return PaperType.THEORETICAL
        if has_experiment_section and has_empirical_terms:
            return PaperType.EMPIRICAL
        if has_system_section and has_deployment_terms:
            return PaperType.SYSTEM
        return PaperType.UNKNOWN

    def detect_method_family(self, text: str) -> str:
        families: dict[str, tuple[str, ...]] = {
            "deep learning": ("neural network", "deep learning", "transformer", "cnn", "rnn"),
            "optimization": ("optimization", "convex", "gradient descent", "lagrangian", "solver"),
            "graph learning": ("graph neural", "gnn", "graph embedding", "message passing"),
            "reinforcement learning": (
                "reinforcement learning",
                "policy",
                "actor-critic",
                "q-learning",
            ),
            "probabilistic modeling": (
                "bayesian",
                "probabilistic",
                "markov",
                "variational inference",
            ),
            "nlp": ("language model", "tokenization", "machine translation", "sentiment", "nlp"),
        }
        lowered = text.lower()
        best_family = ""
        best_hits = 0
        for family, keywords in families.items():
            hits = sum(1 for keyword in keywords if keyword in lowered)
            if hits > best_hits:
                best_hits = hits
                best_family = family
        return best_family

    def detect_evidence_pattern(self, text: str) -> EvidencePattern:
        benchmark_hits = len(
            re.findall(
                r"\b(benchmark|ablation|baseline|dataset|sota|leaderboard)\b", text, re.IGNORECASE
            )
        )
        application_hits = len(
            re.findall(
                r"\b(case study|real-world|deployment|user study|industry)\b", text, re.IGNORECASE
            )
        )
        theorem_hits = len(
            re.findall(r"\b(theorem|proof|lemma|proposition|corollary)\b", text, re.IGNORECASE)
        )

        max_hits = max(benchmark_hits, application_hits, theorem_hits)
        if max_hits == 0:
            return EvidencePattern.UNKNOWN
        if benchmark_hits == max_hits and benchmark_hits >= application_hits + theorem_hits:
            return EvidencePattern.BENCHMARK_HEAVY
        if application_hits == max_hits and application_hits >= benchmark_hits + theorem_hits:
            return EvidencePattern.APPLICATION_HEAVY
        if theorem_hits == max_hits and theorem_hits >= benchmark_hits + application_hits:
            return EvidencePattern.THEOREM_HEAVY
        return EvidencePattern.MIXED

    def detect_novelty_shape(self, text: str) -> NoveltyShape:
        lowered = text.lower()
        if re.search(
            r"\b(we propose|we introduce|novel method|new algorithm|architecture)\b", lowered
        ):
            return NoveltyShape.NEW_METHOD
        if re.search(r"\b(we apply|application to|applied to|in the domain of)\b", lowered):
            return NoveltyShape.NEW_APPLICATION
        if re.search(r"\b(we analyze|analysis of|study of|diagnostic)\b", lowered):
            return NoveltyShape.NEW_ANALYSIS
        if re.search(r"\b(extends prior|incremental|build upon|improve existing)\b", lowered):
            return NoveltyShape.INCREMENTAL
        return NoveltyShape.UNKNOWN

    def assess_reproducibility(self, text: str) -> float:
        checks = [
            r"\b(github\.com|code\s+available|open[- ]source|repository)\b",
            r"\b(hyperparameter|learning rate|batch size|epoch)\b",
            r"\b(train(?:ing)?/test|validation split|data split|cross-validation)\b",
            r"\b(random seed|seeded|deterministic)\b",
            r"\b(hardware|gpu|runtime|implementation details)\b",
        ]
        score = sum(1 for pattern in checks if re.search(pattern, text, re.IGNORECASE))
        return round(score / len(checks), 3)

    def _extract_title(self, text: str) -> str:
        match = re.search(r"\\title\{([^}]*)\}", text)
        return match.group(1) if match else ""

    def _count_references(self, text: str) -> int:
        bibitems = len(re.findall(r"\\bibitem\{", text))
        cite_keys = 0
        for cite_group in re.findall(r"\\cite\w*\{([^}]*)\}", text):
            cite_keys += len([key for key in cite_group.split(",") if key.strip()])
        return max(bibitems, cite_keys)

    def _detect_validation_scale(self, text: str) -> str:
        datasets = len(re.findall(r"\b(dataset|benchmark|corpus)\b", text, re.IGNORECASE))
        numbers = [int(value) for value in re.findall(r"\b(\d{3,7})\b", text)]
        max_n = max(numbers) if numbers else 0
        if datasets >= 5 or max_n >= 100000:
            return "large"
        if datasets >= 2 or max_n >= 10000:
            return "medium"
        if datasets > 0:
            return "small"
        return ""

    def _detect_citation_neighborhood(self, text: str) -> list[str]:
        venues = [
            "NeurIPS",
            "ICML",
            "ICLR",
            "ACL",
            "EMNLP",
            "CVPR",
            "ECCV",
            "AAAI",
            "KDD",
            "IEEE",
            "Nature",
            "Science",
        ]
        seen: list[str] = []
        lowered = text.lower()
        for venue in venues:
            if venue.lower() in lowered:
                seen.append(venue)
        return seen

    def _detect_problem_domain(self, text: str) -> str:
        domain_map: dict[str, tuple[str, ...]] = {
            "natural language processing": ("nlp", "language model", "machine translation", "text"),
            "computer vision": ("image", "vision", "detection", "segmentation"),
            "speech": ("speech", "audio", "asr", "speaker"),
            "recommender systems": ("recommendation", "recommender", "ranking"),
            "security": ("security", "attack", "defense", "vulnerability"),
            "robotics": ("robot", "manipulation", "navigation", "control"),
        }
        lowered = text.lower()
        for domain, patterns in domain_map.items():
            if any(pattern in lowered for pattern in patterns):
                return domain
        return ""

    def _extract_keywords(self, text: str) -> list[str]:
        explicit = re.search(r"\\keywords\{([^}]*)\}", text, flags=re.IGNORECASE)
        if explicit:
            return [token.strip() for token in explicit.group(1).split(",") if token.strip()]

        key_terms = [
            "transformer",
            "benchmark",
            "theorem",
            "optimization",
            "ablation",
            "deployment",
            "robustness",
            "generalization",
            "reproducibility",
        ]
        lowered = text.lower()
        return [term for term in key_terms if term in lowered]

    def _split_sentences(self, text: str) -> list[str]:
        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            return []
        return [
            segment.strip() for segment in re.split(r"(?<=[.!?])\s+", normalized) if segment.strip()
        ]
