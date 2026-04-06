"""Data models for journal-aware writing style analysis.

Defines the full type hierarchy for style metrics, guides, diagnostics,
and rewrite suggestions used across the writing-style pipeline (v0.10.1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ReadabilityMetrics:
    """Readability scores for a text passage.

    Attributes:
        flesch_kincaid_grade: Flesch-Kincaid grade level (0-20).
        smog_index: SMOG readability index.
        avg_sentence_length: Mean number of words per sentence.
        avg_word_length: Mean number of characters per word.
    """

    flesch_kincaid_grade: float = 0.0
    smog_index: float = 0.0
    avg_sentence_length: int = 0
    avg_word_length: float = 0.0


@dataclass
class VocabularyMetrics:
    """Lexical diversity and technicality measures.

    Attributes:
        type_token_ratio: Unique words / total words (0-1).
        avg_word_frequency_rank: Higher means more common vocabulary.
        technical_term_density: Fraction of technical terms (0-1).
        unique_word_count: Count of distinct word forms.
    """

    type_token_ratio: float = 0.0
    avg_word_frequency_rank: float = 0.0
    technical_term_density: float = 0.0
    unique_word_count: int = 0


@dataclass
class GrammarMetrics:
    """Grammatical voice and tense distribution.

    Attributes:
        passive_voice_ratio: Fraction of sentences using passive voice (0-1).
        present_tense_ratio: Fraction of verbs in present tense.
        past_tense_ratio: Fraction of verbs in past tense.
        nominalization_ratio: Fraction of nominalised forms (0-1).
    """

    passive_voice_ratio: float = 0.0
    present_tense_ratio: float = 0.0
    past_tense_ratio: float = 0.0
    nominalization_ratio: float = 0.0


@dataclass
class ArgumentationMetrics:
    """Claim/evidence density in academic prose.

    Attributes:
        claim_count: Number of claim-bearing sentences detected.
        evidence_count: Number of evidence-bearing sentences detected.
        claim_evidence_ratio: claims / max(evidence, 1).
        assertion_types: Mapping of assertion type to count,
            e.g. ``{"hypothesis": 3, "finding": 5}``.
    """

    claim_count: int = 0
    evidence_count: int = 0
    claim_evidence_ratio: float = 0.0
    assertion_types: dict[str, int] = field(default_factory=dict)


@dataclass
class StyleMetrics:
    """Aggregated style metrics for a text passage.

    Bundles readability, vocabulary, grammar, and argumentation
    sub-metrics with a timestamp.

    Attributes:
        readability: Readability sub-metrics.
        vocabulary: Vocabulary sub-metrics.
        grammar: Grammar sub-metrics.
        argumentation: Argumentation sub-metrics.
        timestamp: ISO-8601 creation timestamp.
    """

    readability: ReadabilityMetrics = field(default_factory=ReadabilityMetrics)
    vocabulary: VocabularyMetrics = field(default_factory=VocabularyMetrics)
    grammar: GrammarMetrics = field(default_factory=GrammarMetrics)
    argumentation: ArgumentationMetrics = field(default_factory=ArgumentationMetrics)
    timestamp: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())


@dataclass
class ExemplarSnippet:
    """A real-world writing example drawn from a journal paper.

    Used inside :class:`StyleGuide` to provide concrete reference
    text for each section type.

    Attributes:
        text: Verbatim snippet text.
        section: Section name the snippet belongs to
            (e.g. ``"Introduction"``).
        source_paper: Citation key or identifier of the source paper.
        metrics: Style metrics computed on this snippet.
    """

    text: str = ""
    section: str = ""
    source_paper: str = ""
    metrics: StyleMetrics = field(default_factory=StyleMetrics)


@dataclass
class StyleGuide:
    """Journal-level writing style reference built from exemplar papers.

    Attributes:
        journal_name: Full journal name
            (e.g. ``"IEEE Transactions on Neural Networks"``).
        domain: Research domain tag
            (e.g. ``"computer_science"``, ``"cybersecurity"``).
        metrics: Averaged :class:`StyleMetrics` across all analysed papers.
        section_targets: Per-section metric targets, mapping section name to
            a dict of ``{metric_name: target_value}``.
        exemplars: Concrete snippets from analysed papers.
        sample_size: Number of papers used to build this guide.
        confidence_score: Confidence in the guide (0-1), derived from
            sample size and metric variance.
        created_at: ISO-8601 creation timestamp.
    """

    journal_name: str = ""
    domain: str = ""
    metrics: StyleMetrics = field(default_factory=StyleMetrics)
    section_targets: dict[str, dict[str, float]] = field(default_factory=dict)
    exemplars: list[ExemplarSnippet] = field(default_factory=list)
    sample_size: int = 0
    confidence_score: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())


@dataclass
class StyleIssue:
    """A single style deviation from the journal target.

    Attributes:
        category: Metric category
            (``"readability"``, ``"vocabulary"``, ``"grammar"``,
            ``"argumentation"``).
        severity: ``"critical"``, ``"major"``, or ``"minor"``.
        description: Human-readable explanation.
        example_span: The offending text span.
        journal_target: What the journal guide expects.
        recommended_fix: Actionable suggestion.
    """

    category: str = ""
    severity: str = "minor"
    description: str = ""
    example_span: str = ""
    journal_target: str = ""
    recommended_fix: str = ""


@dataclass
class RewriteSuggestion:
    """An AI-generated or heuristic rewrite for a text span.

    Attributes:
        original_text: The original text to be rewritten.
        suggested_text: The proposed replacement.
        rationale: Why this rewrite improves journal fit.
        exemplar_source: Citation key of the exemplar used as reference.
        confidence: Confidence in the suggestion (0-1).
    """

    original_text: str = ""
    suggested_text: str = ""
    rationale: str = ""
    exemplar_source: str = ""
    confidence: float = 0.0


@dataclass
class SectionDiagnosis:
    """Diagnosis report for a single paper section.

    Compares the section's current metrics against the journal
    style guide targets and surfaces issues with suggestions.

    Attributes:
        section_name: Name of the section diagnosed.
        current_metrics: Metrics computed on the section text.
        target_metrics: Target metrics from the style guide.
        deviation_score: Overall deviation (0-100, lower is better).
        issues: Detected style issues sorted by severity.
        suggestions: Concrete rewrite suggestions.
    """

    section_name: str = ""
    current_metrics: StyleMetrics = field(default_factory=StyleMetrics)
    target_metrics: StyleMetrics = field(default_factory=StyleMetrics)
    deviation_score: float = 0.0
    issues: list[StyleIssue] = field(default_factory=list)
    suggestions: list[RewriteSuggestion] = field(default_factory=list)
