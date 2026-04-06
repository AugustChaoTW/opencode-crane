# pyright: reportMissingImports=false
"""Build journal-specific writing style guides from reference papers.

Analyses a set of exemplar papers for a given journal, computes per-section
:class:`~crane.models.writing_style_models.StyleMetrics`, and aggregates
them into a :class:`~crane.models.writing_style_models.StyleGuide`.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crane.models.writing_style_models import (
    ArgumentationMetrics,
    ExemplarSnippet,
    GrammarMetrics,
    ReadabilityMetrics,
    StyleGuide,
    StyleMetrics,
    VocabularyMetrics,
)
from crane.services.section_chunker import Section, SectionChunker

_SENTENCE_RE = re.compile(r"[^.!?]*[.!?]")

_PASSIVE_RE = re.compile(
    r"\b(?:is|are|was|were|been|being|be)\s+\w+(?:ed|en)\b",
    re.IGNORECASE,
)

_PAST_TENSE_RE = re.compile(r"\b\w+ed\b")

_NOMINALIZATION_RE = re.compile(r"\b\w+(?:tion|ment|ness|ity|ence|ance)\b", re.IGNORECASE)

_CLAIM_MARKERS = re.compile(
    r"\b(?:we\s+(?:propose|argue|show|demonstrate|claim|hypothesize|find)"
    r"|this\s+(?:paper|work|study)\s+(?:proposes|shows|demonstrates)"
    r"|our\s+(?:results?|findings?|approach)"
    r"|it\s+is\s+(?:shown|demonstrated|evident))\b",
    re.IGNORECASE,
)

_EVIDENCE_MARKERS = re.compile(
    r"\b(?:table\s+\d|figure\s+\d|fig\.\s*\d|experiment|dataset"
    r"|results?\s+(?:show|indicate|demonstrate|suggest)"
    r"|p\s*[<>=]\s*\d|statistically\s+significant"
    r"|as\s+shown\s+in)\b",
    re.IGNORECASE,
)

_SYLLABLE_OVERRIDES: dict[str, int] = {}

_COMMON_WORDS: set[str] = {
    "the",
    "be",
    "to",
    "of",
    "and",
    "a",
    "in",
    "that",
    "have",
    "i",
    "it",
    "for",
    "not",
    "on",
    "with",
    "he",
    "as",
    "you",
    "do",
    "at",
    "this",
    "but",
    "his",
    "by",
    "from",
    "they",
    "we",
    "say",
    "her",
    "she",
    "or",
    "an",
    "will",
    "my",
    "one",
    "all",
    "would",
    "there",
    "their",
    "what",
    "so",
    "up",
    "out",
    "if",
    "about",
    "who",
    "get",
    "which",
    "go",
    "me",
    "when",
    "make",
    "can",
    "like",
    "time",
    "no",
    "just",
    "him",
    "know",
    "take",
    "people",
    "into",
    "year",
    "your",
    "good",
    "some",
    "could",
    "them",
    "see",
    "other",
    "than",
    "then",
    "now",
    "look",
    "only",
    "come",
    "its",
    "over",
    "think",
    "also",
    "back",
    "after",
    "use",
    "two",
    "how",
    "our",
    "work",
    "first",
    "well",
    "way",
    "even",
    "new",
    "want",
    "because",
    "any",
    "these",
    "give",
    "day",
    "most",
    "us",
    "is",
    "are",
    "was",
    "were",
    "been",
    "has",
    "had",
    "did",
    "does",
    "may",
    "might",
    "should",
    "must",
    "shall",
    "more",
    "very",
    "such",
    "much",
    "many",
    "each",
    "both",
    "few",
    "before",
    "between",
    "through",
    "during",
    "without",
    "again",
}


def _count_syllables(word: str) -> int:
    """Estimate syllable count for an English word."""
    word = word.lower().strip()
    if word in _SYLLABLE_OVERRIDES:
        return _SYLLABLE_OVERRIDES[word]
    if len(word) <= 3:
        return 1
    vowels = "aeiouy"
    count = 0
    prev_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count -= 1
    return max(count, 1)


def _sentences(text: str) -> list[str]:
    """Split text into sentences (simplified)."""
    return [s.strip() for s in _SENTENCE_RE.findall(text) if s.strip()]


def _words(text: str) -> list[str]:
    """Tokenise text into lowercase alphabetic words."""
    return [w.lower() for w in re.findall(r"[A-Za-z]+", text)]


class StyleGuideBuilder:
    """Analyse exemplar papers and produce a :class:`StyleGuide`.

    Uses :class:`SectionChunker` to split papers into sections,
    computes :class:`StyleMetrics` per section, then aggregates
    section-level metrics into a journal-level guide with exemplar
    snippets.
    """

    def __init__(self) -> None:
        self._chunker = SectionChunker()

    def build_from_papers(
        self,
        journal_name: str,
        paper_paths: list[str | Path],
        domain: str = "computer_science",
    ) -> StyleGuide:
        """Analyse papers and produce a journal-level style guide.

        Args:
            journal_name: Target journal name.
            paper_paths: Paths to ``.tex`` or ``.pdf`` papers.
            domain: Research domain tag.

        Returns:
            A :class:`StyleGuide` built from the analysed papers.
        """
        all_section_metrics: dict[str, list[StyleMetrics]] = {}
        exemplars: list[ExemplarSnippet] = []

        for paper_path in paper_paths:
            path = Path(paper_path)
            sections = self._extract_sections(path)
            for sec in sections:
                if not sec.content.strip():
                    continue
                metrics = self.calculate_style_metrics(sec.content)
                all_section_metrics.setdefault(sec.canonical_name, []).append(metrics)

                if sec.word_count >= 50:
                    snippet_text = self._excerpt(sec.content, max_words=120)
                    exemplars.append(
                        ExemplarSnippet(
                            text=snippet_text,
                            section=sec.canonical_name,
                            source_paper=path.stem,
                            metrics=metrics,
                        )
                    )

        aggregated = self._aggregate_metrics(
            [m for mlist in all_section_metrics.values() for m in mlist]
        )
        section_targets = {
            sec_name: self._metrics_to_target_dict(self._aggregate_metrics(mlist))
            for sec_name, mlist in all_section_metrics.items()
        }
        sample_size = len(paper_paths)
        confidence = self._confidence_from_sample_size(sample_size)

        return StyleGuide(
            journal_name=journal_name,
            domain=domain,
            metrics=aggregated,
            section_targets=section_targets,
            exemplars=exemplars,
            sample_size=sample_size,
            confidence_score=confidence,
            created_at=datetime.now(tz=timezone.utc).isoformat(),
        )

    def calculate_style_metrics(self, text: str) -> StyleMetrics:
        """Compute all style sub-metrics for *text*."""
        return StyleMetrics(
            readability=self._readability(text),
            vocabulary=self._vocabulary(text),
            grammar=self._grammar(text),
            argumentation=self._argumentation(text),
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        )

    def _extract_sections(self, path: Path) -> list[Section]:
        if path.suffix == ".tex":
            return self._chunker.chunk_latex_paper(path)
        if path.suffix == ".pdf":
            return self._chunker.chunk_pdf_paper(path)
        return self._chunker.chunk_text(path.read_text(encoding="utf-8"))

    @staticmethod
    def _readability(text: str) -> ReadabilityMetrics:
        """Simplified Flesch-Kincaid and SMOG calculations."""
        sents = _sentences(text)
        words = _words(text)

        if not words:
            return ReadabilityMetrics()

        num_sentences = max(len(sents), 1)
        num_words = len(words)
        num_syllables = sum(_count_syllables(w) for w in words)
        polysyllable_count = sum(1 for w in words if _count_syllables(w) >= 3)

        avg_sentence_length = num_words // num_sentences
        avg_word_length = sum(len(w) for w in words) / num_words

        # Flesch-Kincaid Grade Level
        fk_grade = 0.39 * (num_words / num_sentences) + 11.8 * (num_syllables / num_words) - 15.59
        fk_grade = max(0.0, min(fk_grade, 20.0))

        # SMOG Index (simplified)
        smog = 1.0430 * math.sqrt(polysyllable_count * (30 / num_sentences)) + 3.1291
        smog = max(0.0, smog)

        return ReadabilityMetrics(
            flesch_kincaid_grade=round(fk_grade, 2),
            smog_index=round(smog, 2),
            avg_sentence_length=avg_sentence_length,
            avg_word_length=round(avg_word_length, 2),
        )

    @staticmethod
    def _vocabulary(text: str) -> VocabularyMetrics:
        words = _words(text)
        if not words:
            return VocabularyMetrics()
        unique = set(words)
        common_count = sum(1 for w in words if w in _COMMON_WORDS)
        freq_rank = common_count / len(words) if words else 0.0
        tech_words = [w for w in words if len(w) > 7 and w not in _COMMON_WORDS]
        return VocabularyMetrics(
            type_token_ratio=round(len(unique) / len(words), 4),
            avg_word_frequency_rank=round(freq_rank, 4),
            technical_term_density=round(len(tech_words) / len(words), 4),
            unique_word_count=len(unique),
        )

    @staticmethod
    def _grammar(text: str) -> GrammarMetrics:
        sents = _sentences(text)
        num_sentences = max(len(sents), 1)
        words = _words(text)
        num_words = max(len(words), 1)

        passive_count = len(_PASSIVE_RE.findall(text))
        past_count = len(_PAST_TENSE_RE.findall(text))
        nominalization_count = len(_NOMINALIZATION_RE.findall(text))

        present_ratio = max(0.0, 1.0 - (past_count / num_words))

        return GrammarMetrics(
            passive_voice_ratio=round(min(passive_count / num_sentences, 1.0), 4),
            present_tense_ratio=round(min(present_ratio, 1.0), 4),
            past_tense_ratio=round(min(past_count / num_words, 1.0), 4),
            nominalization_ratio=round(min(nominalization_count / num_words, 1.0), 4),
        )

    @staticmethod
    def _argumentation(text: str) -> ArgumentationMetrics:
        sents = _sentences(text)
        claims = sum(1 for s in sents if _CLAIM_MARKERS.search(s))
        evidence = sum(1 for s in sents if _EVIDENCE_MARKERS.search(s))

        assertion_types: dict[str, int] = {}
        for s in sents:
            if _CLAIM_MARKERS.search(s):
                assertion_types["claim"] = assertion_types.get("claim", 0) + 1
            if _EVIDENCE_MARKERS.search(s):
                assertion_types["evidence"] = assertion_types.get("evidence", 0) + 1

        return ArgumentationMetrics(
            claim_count=claims,
            evidence_count=evidence,
            claim_evidence_ratio=round(claims / max(evidence, 1), 4),
            assertion_types=assertion_types,
        )

    @staticmethod
    def _aggregate_metrics(metrics_list: list[StyleMetrics]) -> StyleMetrics:
        """Average a list of metrics into a single representative set."""
        if not metrics_list:
            return StyleMetrics()
        n = len(metrics_list)

        def _avg(values: list[float]) -> float:
            return round(sum(values) / len(values), 4) if values else 0.0

        def _avg_int(values: list[int]) -> int:
            return round(sum(values) / len(values)) if values else 0

        return StyleMetrics(
            readability=ReadabilityMetrics(
                flesch_kincaid_grade=_avg(
                    [m.readability.flesch_kincaid_grade for m in metrics_list]
                ),
                smog_index=_avg([m.readability.smog_index for m in metrics_list]),
                avg_sentence_length=_avg_int(
                    [m.readability.avg_sentence_length for m in metrics_list]
                ),
                avg_word_length=_avg([m.readability.avg_word_length for m in metrics_list]),
            ),
            vocabulary=VocabularyMetrics(
                type_token_ratio=_avg([m.vocabulary.type_token_ratio for m in metrics_list]),
                avg_word_frequency_rank=_avg(
                    [m.vocabulary.avg_word_frequency_rank for m in metrics_list]
                ),
                technical_term_density=_avg(
                    [m.vocabulary.technical_term_density for m in metrics_list]
                ),
                unique_word_count=_avg_int([m.vocabulary.unique_word_count for m in metrics_list]),
            ),
            grammar=GrammarMetrics(
                passive_voice_ratio=_avg([m.grammar.passive_voice_ratio for m in metrics_list]),
                present_tense_ratio=_avg([m.grammar.present_tense_ratio for m in metrics_list]),
                past_tense_ratio=_avg([m.grammar.past_tense_ratio for m in metrics_list]),
                nominalization_ratio=_avg([m.grammar.nominalization_ratio for m in metrics_list]),
            ),
            argumentation=ArgumentationMetrics(
                claim_count=_avg_int([m.argumentation.claim_count for m in metrics_list]),
                evidence_count=_avg_int([m.argumentation.evidence_count for m in metrics_list]),
                claim_evidence_ratio=_avg(
                    [m.argumentation.claim_evidence_ratio for m in metrics_list]
                ),
                assertion_types={},
            ),
        )

    @staticmethod
    def _metrics_to_target_dict(metrics: StyleMetrics) -> dict[str, float]:
        """Flatten a StyleMetrics into a dict of target values."""
        return {
            "flesch_kincaid_grade": metrics.readability.flesch_kincaid_grade,
            "smog_index": metrics.readability.smog_index,
            "avg_sentence_length": float(metrics.readability.avg_sentence_length),
            "avg_word_length": metrics.readability.avg_word_length,
            "type_token_ratio": metrics.vocabulary.type_token_ratio,
            "technical_term_density": metrics.vocabulary.technical_term_density,
            "passive_voice_ratio": metrics.grammar.passive_voice_ratio,
            "nominalization_ratio": metrics.grammar.nominalization_ratio,
        }

    @staticmethod
    def _confidence_from_sample_size(n: int) -> float:
        """Heuristic confidence: caps at 0.95 for n >= 30."""
        if n <= 0:
            return 0.0
        return round(min(1.0 - 1.0 / (n + 1), 0.95), 4)

    @staticmethod
    def _excerpt(text: str, max_words: int = 120) -> str:
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words]) + " ..."
