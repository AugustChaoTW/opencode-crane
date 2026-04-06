# pyright: reportMissingImports=false

from __future__ import annotations

from crane.models.writing_style_models import (
    ArgumentationMetrics,
    ExemplarSnippet,
    GrammarMetrics,
    ReadabilityMetrics,
    RewriteSuggestion,
    SectionDiagnosis,
    StyleGuide,
    StyleIssue,
    StyleMetrics,
    VocabularyMetrics,
)


class TestReadabilityMetrics:
    def test_defaults(self) -> None:
        m = ReadabilityMetrics()
        assert m.flesch_kincaid_grade == 0.0
        assert m.smog_index == 0.0
        assert m.avg_sentence_length == 0
        assert m.avg_word_length == 0.0

    def test_custom_values(self) -> None:
        m = ReadabilityMetrics(
            flesch_kincaid_grade=12.5,
            smog_index=10.3,
            avg_sentence_length=18,
            avg_word_length=5.2,
        )
        assert m.flesch_kincaid_grade == 12.5
        assert m.avg_sentence_length == 18


class TestVocabularyMetrics:
    def test_defaults(self) -> None:
        m = VocabularyMetrics()
        assert m.type_token_ratio == 0.0
        assert m.unique_word_count == 0

    def test_custom_values(self) -> None:
        m = VocabularyMetrics(
            type_token_ratio=0.72,
            avg_word_frequency_rank=0.45,
            technical_term_density=0.12,
            unique_word_count=340,
        )
        assert m.type_token_ratio == 0.72
        assert m.unique_word_count == 340


class TestGrammarMetrics:
    def test_defaults(self) -> None:
        m = GrammarMetrics()
        assert m.passive_voice_ratio == 0.0
        assert m.nominalization_ratio == 0.0

    def test_custom_values(self) -> None:
        m = GrammarMetrics(passive_voice_ratio=0.3, past_tense_ratio=0.4)
        assert m.passive_voice_ratio == 0.3
        assert m.past_tense_ratio == 0.4


class TestArgumentationMetrics:
    def test_defaults(self) -> None:
        m = ArgumentationMetrics()
        assert m.claim_count == 0
        assert m.assertion_types == {}

    def test_assertion_types_dict(self) -> None:
        m = ArgumentationMetrics(
            claim_count=3,
            evidence_count=5,
            claim_evidence_ratio=0.6,
            assertion_types={"hypothesis": 2, "finding": 3},
        )
        assert m.assertion_types["hypothesis"] == 2
        assert m.claim_evidence_ratio == 0.6


class TestStyleMetrics:
    def test_defaults_create_sub_metrics(self) -> None:
        m = StyleMetrics()
        assert isinstance(m.readability, ReadabilityMetrics)
        assert isinstance(m.vocabulary, VocabularyMetrics)
        assert isinstance(m.grammar, GrammarMetrics)
        assert isinstance(m.argumentation, ArgumentationMetrics)
        assert m.timestamp

    def test_sub_metric_independence(self) -> None:
        m1 = StyleMetrics()
        m2 = StyleMetrics()
        m1.readability.flesch_kincaid_grade = 15.0
        assert m2.readability.flesch_kincaid_grade == 0.0


class TestExemplarSnippet:
    def test_creation(self) -> None:
        s = ExemplarSnippet(
            text="We propose a novel approach.",
            section="Introduction",
            source_paper="smith2024",
        )
        assert s.section == "Introduction"
        assert s.source_paper == "smith2024"
        assert isinstance(s.metrics, StyleMetrics)


class TestStyleGuide:
    def test_defaults(self) -> None:
        g = StyleGuide()
        assert g.journal_name == ""
        assert g.sample_size == 0
        assert g.exemplars == []
        assert g.section_targets == {}

    def test_full_construction(self) -> None:
        g = StyleGuide(
            journal_name="IEEE TPAMI",
            domain="computer_science",
            sample_size=10,
            confidence_score=0.9,
            section_targets={
                "Introduction": {"flesch_kincaid_grade": 12.0},
            },
            exemplars=[ExemplarSnippet(text="example", section="Intro")],
        )
        assert g.journal_name == "IEEE TPAMI"
        assert g.sample_size == 10
        assert len(g.exemplars) == 1
        assert "Introduction" in g.section_targets


class TestStyleIssue:
    def test_defaults(self) -> None:
        i = StyleIssue()
        assert i.severity == "minor"
        assert i.category == ""

    def test_creation(self) -> None:
        i = StyleIssue(
            category="readability",
            severity="critical",
            description="Sentences too long",
            example_span="This sentence ... 60 words.",
            journal_target="avg 20 words",
            recommended_fix="Break into shorter sentences.",
        )
        assert i.severity == "critical"
        assert i.category == "readability"


class TestRewriteSuggestion:
    def test_creation(self) -> None:
        r = RewriteSuggestion(
            original_text="The system was implemented.",
            suggested_text="We implemented the system.",
            rationale="Active voice preferred.",
            exemplar_source="jones2023",
            confidence=0.85,
        )
        assert r.confidence == 0.85
        assert r.exemplar_source == "jones2023"


class TestSectionDiagnosis:
    def test_defaults(self) -> None:
        d = SectionDiagnosis()
        assert d.section_name == ""
        assert d.deviation_score == 0.0
        assert d.issues == []
        assert d.suggestions == []

    def test_full_construction(self) -> None:
        issue = StyleIssue(category="grammar", severity="major")
        suggestion = RewriteSuggestion(confidence=0.7)
        d = SectionDiagnosis(
            section_name="Methods",
            deviation_score=42.5,
            issues=[issue],
            suggestions=[suggestion],
        )
        assert d.section_name == "Methods"
        assert len(d.issues) == 1
        assert d.issues[0].severity == "major"
        assert d.suggestions[0].confidence == 0.7
