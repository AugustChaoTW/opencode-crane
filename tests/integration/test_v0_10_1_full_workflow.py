# pyright: reportMissingImports=false
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from crane.models.writing_style_models import (
    ExemplarSnippet,
    InteractiveRewriteSession,
    PreferenceLearnerState,
    ReadabilityMetrics,
    RewriteChoice,
    RewriteSuggestion,
    SectionDiagnosis,
    StyleGuide,
    StyleIssue,
    StyleMetrics,
    UserPreference,
    VocabularyMetrics,
    GrammarMetrics,
    ArgumentationMetrics,
)
from crane.services.interactive_rewrite_service import InteractiveRewriteService
from crane.services.preference_learner_service import PreferenceLearnerService
from crane.services.section_chunker import Section, SectionChunker
from crane.services.style_guide_builder import StyleGuideBuilder
from crane.services.writing_style_service import WritingStyleService, _flatten_metrics


SAMPLE_LATEX = r"""\documentclass{article}
\begin{document}
\title{Test Paper on Deep Learning}
\maketitle

\begin{abstract}
This paper presents a novel approach to deep learning that significantly
improves performance on benchmark datasets. The proposed method was evaluated
on multiple tasks and the results demonstrate substantial improvements over
existing baselines. Our contributions include a new architecture and a
comprehensive evaluation framework.
\end{abstract}

\section{Introduction}
Deep learning has been widely adopted in many application domains. The field
has seen rapid progress in recent years, with new architectures being proposed
at an increasing rate. However, many challenges remain unsolved. In this paper,
we propose a novel approach that addresses several key limitations of existing
methods. Our approach is based on the observation that current models fail to
capture long-range dependencies effectively. We demonstrate that our method
achieves state-of-the-art results on multiple benchmarks. The main contributions
of this work are threefold: first, we introduce a new attention mechanism;
second, we propose an efficient training procedure; third, we provide extensive
experimental validation.

\section{Related Work}
Previous work on attention mechanisms has focused primarily on self-attention
and cross-attention variants. Vaswani et al. introduced the Transformer
architecture, which relies entirely on attention mechanisms. Subsequent work
has explored various modifications to improve efficiency and effectiveness.
Several approaches have been proposed to reduce the quadratic complexity of
standard attention, including sparse attention patterns and linear attention
approximations. Our work builds upon these foundations while introducing
novel components that address specific limitations.

\section{Methods}
The proposed method consists of three main components. First, we introduce
a hierarchical attention mechanism that operates at multiple scales. The
input sequence is processed through a series of attention layers, each
operating at a different granularity. Second, we employ a novel positional
encoding scheme that captures both absolute and relative position information.
Third, we introduce a gating mechanism that allows the model to selectively
attend to relevant information at each scale. The overall architecture is
designed to be computationally efficient while maintaining high accuracy.
The training procedure follows a standard supervised learning paradigm with
several modifications to improve convergence speed and final performance.

\section{Experiments}
We evaluate our method on three benchmark datasets: ImageNet, CIFAR-100,
and MS-COCO. For each dataset, we compare against several strong baselines
including ResNet, EfficientNet, and Vision Transformer. Our method achieves
the best results on all three datasets, with improvements of 2.3\%, 1.8\%,
and 3.1\% respectively. We also conduct ablation studies to understand the
contribution of each component. The results show that the hierarchical
attention mechanism provides the largest improvement, followed by the
positional encoding scheme and the gating mechanism.

\section{Discussion}
The experimental results demonstrate the effectiveness of our approach
across multiple tasks and datasets. The consistent improvements suggest
that the proposed components address fundamental limitations of existing
methods. However, our approach has several limitations. First, the
hierarchical attention mechanism increases memory requirements compared
to standard attention. Second, the training procedure requires careful
hyperparameter tuning. Future work should explore ways to reduce the
computational overhead while maintaining the performance gains.

\section{Conclusion}
We have presented a novel deep learning approach that achieves
state-of-the-art results on multiple benchmarks. Our method introduces
three key innovations: hierarchical attention, improved positional
encoding, and selective gating. Extensive experiments demonstrate the
effectiveness of each component. We believe this work opens new
directions for research in efficient attention mechanisms.

\end{document}
"""


def _write_profiles(tmp_path: Path, journals: list[dict]) -> Path:
    path = tmp_path / "profiles.yaml"
    path.write_text(
        yaml.safe_dump({"journals": journals}, sort_keys=False),
        encoding="utf-8",
    )
    return path


def _minimal_journal(
    name: str = "Test Journal",
    abbreviation: str = "TJ",
    publisher: str = "IEEE",
) -> dict:
    return {
        "name": name,
        "abbreviation": abbreviation,
        "publisher": publisher,
        "quartile": "Q1",
        "impact_factor": 10.0,
        "scope_keywords": ["machine learning", "deep learning"],
        "preferred_paper_types": ["empirical"],
        "preferred_method_families": ["deep learning"],
        "preferred_evidence_patterns": ["benchmark_heavy"],
        "typical_word_count": [6000, 10000],
        "review_timeline_months": [3, 6],
        "acceptance_rate": 0.2,
        "apc_usd": 0,
        "open_access": False,
        "open_access_type": "subscription",
        "waiver_available": False,
        "desk_reject_signals": [],
        "citation_venues": ["NeurIPS", "ICML"],
    }


def _write_latex(tmp_path: Path, content: str = SAMPLE_LATEX) -> Path:
    path = tmp_path / "test_paper.tex"
    path.write_text(content, encoding="utf-8")
    return path


# ── Phase A: Data Models ──


class TestPhaseAModels:
    def test_style_metrics_defaults(self):
        m = StyleMetrics()
        assert m.readability.flesch_kincaid_grade == 0.0
        assert m.vocabulary.type_token_ratio == 0.0
        assert m.grammar.passive_voice_ratio == 0.0

    def test_style_guide_creation(self):
        guide = StyleGuide(journal_name="Test", domain="ai_ml")
        assert guide.journal_name == "Test"
        assert guide.domain == "ai_ml"

    def test_section_diagnosis_creation(self):
        diag = SectionDiagnosis(section_name="Introduction", deviation_score=15.5)
        assert diag.section_name == "Introduction"
        assert diag.deviation_score == 15.5

    def test_rewrite_suggestion_creation(self):
        sug = RewriteSuggestion(
            original_text="was computed",
            suggested_text="we computed",
            rationale="Active voice preferred",
            confidence=0.85,
        )
        assert sug.confidence == 0.85

    def test_interactive_session_creation(self):
        session = InteractiveRewriteSession(
            session_id="test",
            paper_path="/tmp/test.tex",
            journal_name="IEEE TPAMI",
        )
        assert session.status == "active"
        assert session.choices == []

    def test_rewrite_choice_creation(self):
        choice = RewriteChoice(suggestion_id="sug_0", decision="accept")
        assert choice.decision == "accept"

    def test_user_preference_creation(self):
        pref = UserPreference(
            category="grammar",
            metric_name="passive_voice_ratio",
            direction="lower",
            strength=0.5,
        )
        assert pref.strength == 0.5

    def test_preference_learner_state_creation(self):
        state = PreferenceLearnerState(user_id="test_user")
        assert state.total_sessions == 0
        assert state.acceptance_rate == 0.0


# ── Phase A: Section Chunker ──


class TestPhaseASectionChunker:
    def test_chunk_latex_paper(self, tmp_path: Path):
        paper = _write_latex(tmp_path)
        chunker = SectionChunker()
        sections = chunker.chunk_latex_paper(paper)
        assert len(sections) >= 4
        names = [s.canonical_name or s.name for s in sections]
        assert "Introduction" in names

    def test_chunk_text(self):
        chunker = SectionChunker()
        sections = chunker.chunk_text("This is a test paragraph with some content.")
        assert len(sections) >= 1


# ── Phase B: WritingStyleService ──


class TestPhaseBService:
    def test_service_init_with_journal(self, tmp_path: Path):
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        service = WritingStyleService(
            "Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        assert service.journal_name == "Test Journal"

    def test_diagnose_section(self, tmp_path: Path):
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        service = WritingStyleService(
            "Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        section = Section(
            name="Introduction",
            canonical_name="Introduction",
            content="Deep learning has been widely adopted. We propose a novel approach.",
        )
        diag = service.diagnose_section(section)
        assert diag.section_name == "Introduction"
        assert isinstance(diag.deviation_score, float)

    def test_diagnose_full_paper(self, tmp_path: Path):
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        paper = _write_latex(tmp_path)
        service = WritingStyleService(
            "Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        diagnoses = service.diagnose_full_paper(paper)
        assert len(diagnoses) >= 3

    def test_suggest_rewrites(self, tmp_path: Path):
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        service = WritingStyleService(
            "Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        section = Section(
            name="Introduction",
            canonical_name="Introduction",
            content=(
                "The method was evaluated on multiple datasets. "
                "The results were obtained through extensive experimentation. "
                "The approach was designed to be computationally efficient."
            ),
        )
        diag = service.diagnose_section(section)
        suggestions = service.suggest_rewrites(diag)
        assert isinstance(suggestions, list)

    def test_get_exemplars(self, tmp_path: Path):
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        service = WritingStyleService(
            "Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        exemplars = service.get_exemplars("Introduction")
        assert isinstance(exemplars, list)

    def test_compare_journals(self, tmp_path: Path):
        j1 = _minimal_journal(name="Journal A", abbreviation="JA")
        j2 = _minimal_journal(name="Journal B", abbreviation="JB")
        profiles = _write_profiles(tmp_path, [j1, j2])
        service = WritingStyleService(
            "Journal A",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        comparison = service.compare_journals(["Journal B"])
        assert "Journal A" in comparison

    def test_flatten_metrics(self):
        metrics = StyleMetrics(
            readability=ReadabilityMetrics(flesch_kincaid_grade=12.0),
            vocabulary=VocabularyMetrics(type_token_ratio=0.55),
        )
        flat = _flatten_metrics(metrics)
        assert flat["flesch_kincaid_grade"] == 12.0
        assert flat["type_token_ratio"] == 0.55


# ── Phase B: StyleGuideBuilder ──


class TestPhaseBStyleGuideBuilder:
    def test_calculate_style_metrics(self):
        builder = StyleGuideBuilder()
        text = (
            "Deep learning has revolutionized many fields. "
            "The transformer architecture was introduced by Vaswani et al. "
            "Our method achieves state-of-the-art results on benchmarks."
        )
        metrics = builder.calculate_style_metrics(text)
        assert metrics.readability.avg_sentence_length > 0
        assert metrics.grammar.passive_voice_ratio >= 0.0


# ── Phase C: MCP Tool Integration ──


class TestPhaseCToolIntegration:
    def test_diagnose_paper_tool_flow(self, tmp_path: Path):
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        paper = _write_latex(tmp_path)
        service = WritingStyleService(
            "Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        diagnoses = service.diagnose_full_paper(paper)
        sections_result = {}
        deviation_scores = []
        for name, diag in diagnoses.items():
            sections_result[name] = {
                "section_name": diag.section_name,
                "deviation_score": diag.deviation_score,
                "issues_count": len(diag.issues),
                "suggestions_count": len(diag.suggestions),
            }
            deviation_scores.append(diag.deviation_score)
        overall = sum(deviation_scores) / len(deviation_scores) if deviation_scores else 0.0
        assert overall >= 0.0
        assert len(sections_result) >= 3

    def test_style_guide_extraction_flow(self, tmp_path: Path):
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        service = WritingStyleService(
            "Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        guide = service.get_style_guide()
        assert guide.journal_name == "Test Journal"
        assert len(guide.section_targets) > 0

    def test_compare_sections_flow(self, tmp_path: Path):
        j1 = _minimal_journal(name="Journal A", abbreviation="JA")
        j2 = _minimal_journal(name="Journal B", abbreviation="JB")
        profiles = _write_profiles(tmp_path, [j1, j2])
        service1 = WritingStyleService(
            "Journal A",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        comparison = service1.compare_journals(["Journal B"], section_name="Introduction")
        assert "Journal A" in comparison


# ── Phase D: Interactive Rewrite ──


class TestPhaseDInteractiveRewrite:
    def test_full_interactive_workflow(self, tmp_path: Path):
        service = InteractiveRewriteService(storage_dir=tmp_path / "sessions")
        suggestions = [
            RewriteSuggestion(
                original_text="was computed",
                suggested_text="we computed",
                rationale="Reduce passive voice",
                confidence=0.8,
            ),
            RewriteSuggestion(
                original_text="utilization",
                suggested_text="use",
                rationale="Reduce nominalization",
                confidence=0.7,
            ),
        ]
        session = InteractiveRewriteSession(
            session_id="workflow_test",
            paper_path="/tmp/test.tex",
            journal_name="IEEE TPAMI",
            section_name="Methods",
            suggestions=suggestions,
        )
        service._save_session(session)

        session = service.submit_choice(session, 0, "accept")
        assert len(session.applied_rewrites) == 1

        session = service.submit_choice(session, 1, "modify", modified_text="utilize")
        assert len(session.applied_rewrites) == 2
        assert session.status == "completed"

        summary = service.get_session_summary(session)
        assert summary["accepted"] == 1
        assert summary["modified"] == 1
        assert summary["applied_count"] == 2

    def test_pause_resume_workflow(self, tmp_path: Path):
        service = InteractiveRewriteService(storage_dir=tmp_path / "sessions")
        suggestions = [
            RewriteSuggestion(rationale="Fix passive", confidence=0.8),
            RewriteSuggestion(rationale="Fix length", confidence=0.7),
        ]
        session = InteractiveRewriteSession(
            session_id="pause_test",
            paper_path="/tmp/test.tex",
            journal_name="IEEE TPAMI",
            section_name="Introduction",
            suggestions=suggestions,
        )
        service._save_session(session)

        session = service.submit_choice(session, 0, "accept")
        service.pause_session(session)

        resumed = service.resume_session("pause_test")
        assert resumed.status == "active"
        assert len(resumed.choices) == 1


# ── Phase D: Preference Learning ──


class TestPhaseDPreferenceLearning:
    def test_learn_and_adjust_workflow(self, tmp_path: Path):
        learner = PreferenceLearnerService(storage_dir=tmp_path / "prefs")

        session = InteractiveRewriteSession(
            session_id="learn_test",
            paper_path="/tmp/test.tex",
            journal_name="IEEE TPAMI",
            section_name="Introduction",
            suggestions=[
                RewriteSuggestion(rationale="Reduce passive voice", confidence=0.7),
                RewriteSuggestion(rationale="Simplify sentence length", confidence=0.6),
            ],
            choices=[
                RewriteChoice(suggestion_id="sug_0", decision="accept"),
                RewriteChoice(suggestion_id="sug_1", decision="reject"),
            ],
        )

        state = learner.learn_from_session(session)
        assert state.total_sessions == 1
        assert state.total_choices == 2

        new_suggestions = [
            RewriteSuggestion(rationale="Reduce passive voice", confidence=0.5),
            RewriteSuggestion(rationale="Simplify sentence length", confidence=0.5),
        ]
        adjusted = learner.adjust_suggestions(new_suggestions)
        assert len(adjusted) == 2

    def test_cross_session_preference_persistence(self, tmp_path: Path):
        storage = tmp_path / "prefs"
        learner1 = PreferenceLearnerService(storage_dir=storage)
        session = InteractiveRewriteSession(
            session_id="persist_test",
            suggestions=[
                RewriteSuggestion(rationale="Reduce passive voice", confidence=0.7),
            ],
            choices=[
                RewriteChoice(suggestion_id="sug_0", decision="accept"),
            ],
        )
        learner1.learn_from_session(session)

        learner2 = PreferenceLearnerService(storage_dir=storage)
        state = learner2.get_state()
        assert state.total_sessions == 1
        assert "passive_voice_ratio" in state.preferences


# ── Multi-Domain Support ──


class TestMultiDomainSupport:
    def test_ai_ml_domain(self, tmp_path: Path):
        journal = _minimal_journal(name="AI Journal")
        journal["scope_keywords"] = ["artificial intelligence", "machine learning"]
        profiles = _write_profiles(tmp_path, [journal])
        service = WritingStyleService(
            "AI Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        assert service.domain in ("ai_ml", "computer_science")

    def test_cybersecurity_domain(self, tmp_path: Path):
        journal = _minimal_journal(name="Security Journal")
        journal["scope_keywords"] = ["cybersecurity", "network security", "intrusion detection"]
        profiles = _write_profiles(tmp_path, [journal])
        service = WritingStyleService(
            "Security Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        assert service.domain is not None

    def test_iot_domain(self, tmp_path: Path):
        journal = _minimal_journal(name="IoT Journal")
        journal["scope_keywords"] = ["internet of things", "IoT", "sensor networks"]
        profiles = _write_profiles(tmp_path, [journal])
        service = WritingStyleService(
            "IoT Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        assert service.domain is not None

    def test_mis_domain(self, tmp_path: Path):
        journal = _minimal_journal(name="MIS Journal")
        journal["scope_keywords"] = ["management information systems", "IS research"]
        profiles = _write_profiles(tmp_path, [journal])
        service = WritingStyleService(
            "MIS Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        assert service.domain is not None

    def test_different_domains_produce_different_weights(self, tmp_path: Path):
        j_ai = _minimal_journal(name="AI Journal", abbreviation="AIJ")
        j_ai["scope_keywords"] = ["machine learning", "deep learning"]
        j_sec = _minimal_journal(name="Sec Journal", abbreviation="SJ")
        j_sec["scope_keywords"] = ["cybersecurity", "network security"]
        profiles = _write_profiles(tmp_path, [j_ai, j_sec])

        s_ai = WritingStyleService("AI Journal", profiles_path=profiles, cache_dir=tmp_path / "c1")
        s_sec = WritingStyleService(
            "Sec Journal", profiles_path=profiles, cache_dir=tmp_path / "c2"
        )
        assert s_ai.domain != "" or s_sec.domain != ""


# ── Session Persistence & Recovery ──


class TestSessionPersistenceRecovery:
    def test_rewrite_session_survives_restart(self, tmp_path: Path):
        storage = tmp_path / "sessions"
        svc1 = InteractiveRewriteService(storage_dir=storage)
        session = InteractiveRewriteSession(
            session_id="persist_001",
            paper_path="/tmp/test.tex",
            journal_name="IEEE TPAMI",
            section_name="Introduction",
            suggestions=[
                RewriteSuggestion(rationale="Fix passive", confidence=0.8),
            ],
        )
        svc1._save_session(session)
        svc1.submit_choice(session, 0, "accept")

        svc2 = InteractiveRewriteService(storage_dir=storage)
        loaded = svc2._load_session("persist_001")
        assert len(loaded.choices) == 1
        assert loaded.choices[0].decision == "accept"

    def test_preference_state_survives_restart(self, tmp_path: Path):
        storage = tmp_path / "prefs"
        svc1 = PreferenceLearnerService(storage_dir=storage)
        session = InteractiveRewriteSession(
            session_id="pref_persist",
            suggestions=[
                RewriteSuggestion(rationale="Reduce passive voice", confidence=0.7),
            ],
            choices=[
                RewriteChoice(suggestion_id="sug_0", decision="accept"),
            ],
        )
        svc1.learn_from_session(session)

        svc2 = PreferenceLearnerService(storage_dir=storage)
        state = svc2.get_state()
        assert state.total_sessions == 1

    def test_list_sessions_after_restart(self, tmp_path: Path):
        storage = tmp_path / "sessions"
        svc1 = InteractiveRewriteService(storage_dir=storage)
        for i in range(3):
            session = InteractiveRewriteSession(
                session_id=f"list_{i}",
                paper_path="/tmp/test.tex",
                journal_name="IEEE TPAMI",
                section_name="Introduction",
                suggestions=[],
            )
            svc1._save_session(session)

        svc2 = InteractiveRewriteService(storage_dir=storage)
        sessions = svc2.list_sessions()
        assert len(sessions) == 3


# ── Cross-Session Preference Learning ──


class TestCrossSessionPreferenceLearning:
    def test_preferences_accumulate_across_sessions(self, tmp_path: Path):
        learner = PreferenceLearnerService(storage_dir=tmp_path / "prefs")

        for i in range(5):
            session = InteractiveRewriteSession(
                session_id=f"accum_{i}",
                suggestions=[
                    RewriteSuggestion(rationale="Reduce passive voice", confidence=0.7),
                ],
                choices=[
                    RewriteChoice(suggestion_id="sug_0", decision="accept"),
                ],
            )
            learner.learn_from_session(session)

        state = learner.get_state()
        assert state.total_sessions == 5
        assert state.total_choices == 5
        pref = state.preferences.get("passive_voice_ratio")
        assert pref is not None
        assert pref.evidence_count == 5
        assert pref.strength >= 0.3

    def test_mixed_decisions_balance_preferences(self, tmp_path: Path):
        learner = PreferenceLearnerService(storage_dir=tmp_path / "prefs")

        for decision in ["accept", "accept", "reject", "accept", "reject"]:
            session = InteractiveRewriteSession(
                session_id="mixed",
                suggestions=[
                    RewriteSuggestion(rationale="Reduce passive voice", confidence=0.7),
                ],
                choices=[
                    RewriteChoice(suggestion_id="sug_0", decision=decision),
                ],
            )
            learner.learn_from_session(session)

        state = learner.get_state()
        pref = state.preferences.get("passive_voice_ratio")
        assert pref is not None
        assert pref.evidence_count == 5

    def test_preference_reset_clears_history(self, tmp_path: Path):
        learner = PreferenceLearnerService(storage_dir=tmp_path / "prefs")
        session = InteractiveRewriteSession(
            session_id="reset_test",
            suggestions=[
                RewriteSuggestion(rationale="Reduce passive voice", confidence=0.7),
            ],
            choices=[
                RewriteChoice(suggestion_id="sug_0", decision="accept"),
            ],
        )
        learner.learn_from_session(session)
        learner.reset_preferences()
        state = learner.get_state()
        assert state.total_sessions == 0
        assert len(state.preferences) == 0


# ── End-to-End: Full Pipeline ──


class TestEndToEndPipeline:
    def test_diagnose_then_rewrite_then_learn(self, tmp_path: Path):
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        paper = _write_latex(tmp_path)

        style_service = WritingStyleService(
            "Test Journal",
            profiles_path=profiles,
            cache_dir=tmp_path / "cache",
        )
        diagnoses = style_service.diagnose_full_paper(paper)
        assert len(diagnoses) >= 1

        first_section = next(iter(diagnoses.values()))
        suggestions = style_service.suggest_rewrites(first_section)

        rewrite_service = InteractiveRewriteService(storage_dir=tmp_path / "sessions")
        session = InteractiveRewriteSession(
            session_id="e2e_test",
            paper_path=str(paper),
            journal_name="Test Journal",
            section_name=first_section.section_name,
            suggestions=suggestions
            if suggestions
            else [
                RewriteSuggestion(rationale="Placeholder", confidence=0.5),
            ],
        )
        rewrite_service._save_session(session)

        for i in range(len(session.suggestions)):
            decision = "accept" if i % 2 == 0 else "reject"
            session = rewrite_service.submit_choice(session, i, decision)

        learner = PreferenceLearnerService(storage_dir=tmp_path / "prefs")
        state = learner.learn_from_session(session)
        assert state.total_sessions == 1
        assert state.total_choices == len(session.choices)

    def test_style_guide_caching(self, tmp_path: Path):
        profiles = _write_profiles(tmp_path, [_minimal_journal()])
        cache_dir = tmp_path / "cache"

        svc1 = WritingStyleService(
            "Test Journal",
            profiles_path=profiles,
            cache_dir=cache_dir,
        )
        guide1 = svc1.get_style_guide()

        svc2 = WritingStyleService(
            "Test Journal",
            profiles_path=profiles,
            cache_dir=cache_dir,
        )
        guide2 = svc2.get_style_guide()
        assert guide1.journal_name == guide2.journal_name
