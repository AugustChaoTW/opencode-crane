# pyright: reportMissingImports=false

from __future__ import annotations

from pathlib import Path

import pytest

from crane.models.paper_profile import (
    DimensionScore,
    EvidenceItem,
    EvidenceLedger,
    EvidencePattern,
    EvidenceSignal,
    NoveltyShape,
    PaperProfile,
    RevisionEffort,
    RevisionPlan,
    RevisionPriority,
)
from crane.services.evidence_evaluation_service import EvidenceEvaluation, EvidenceEvaluationService


def _write_tex(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _rich_profile() -> PaperProfile:
    return PaperProfile(
        method_family="deep learning",
        evidence_pattern=EvidencePattern.BENCHMARK_HEAVY,
        validation_scale="large",
        citation_neighborhood=["NeurIPS", "ICML"],
        novelty_shape=NoveltyShape.NEW_METHOD,
        reproducibility_maturity=0.9,
        problem_domain="natural language processing",
        keywords=["transformer", "benchmark"],
        word_count=7000,
        has_code=True,
        has_appendix=True,
        num_figures=4,
        num_tables=4,
        num_equations=6,
        num_references=45,
    )


def _minimal_profile() -> PaperProfile:
    return PaperProfile(
        method_family="",
        evidence_pattern=EvidencePattern.UNKNOWN,
        validation_scale="",
        citation_neighborhood=[],
        novelty_shape=NoveltyShape.UNKNOWN,
        reproducibility_maturity=0.0,
        problem_domain="",
        keywords=[],
        word_count=100,
        has_code=False,
        has_appendix=False,
        num_figures=0,
        num_tables=0,
        num_equations=0,
        num_references=0,
    )


def _rich_evidence() -> EvidenceLedger:
    return EvidenceLedger(
        items=[
            EvidenceItem(
                claim="we propose a novel method",
                section="Method",
                span="We propose a novel method with algorithmic guarantees.",
                signal=EvidenceSignal.OBSERVED,
                confidence=0.9,
            ),
            EvidenceItem(
                claim="our results improve benchmarks",
                section="Experiments",
                span="Our results improve benchmark accuracy by 12% compared to baselines.",
                signal=EvidenceSignal.OBSERVED,
                confidence=0.9,
            ),
            EvidenceItem(
                claim="our analysis is robust",
                section="Results",
                span="Our analysis shows robustness under distribution shift.",
                signal=EvidenceSignal.OBSERVED,
                confidence=0.8,
            ),
            EvidenceItem(
                claim="limitations are discussed",
                section="Limitations",
                span="A key limitation is sensitivity to noisy labels.",
                signal=EvidenceSignal.OBSERVED,
                confidence=0.9,
            ),
            EvidenceItem(
                claim="future work",
                section="Conclusion",
                span="Future work includes stronger calibration and larger datasets.",
                signal=EvidenceSignal.INFERRED,
                confidence=0.6,
            ),
        ]
    )


def _minimal_evidence() -> EvidenceLedger:
    return EvidenceLedger(
        items=[
            EvidenceItem(
                claim="expected empirical support",
                section="global",
                span="missing benchmark or dataset details",
                signal=EvidenceSignal.MISSING,
                confidence=1.0,
            )
        ]
    )


def _seed_service_for_scoring(service: EvidenceEvaluationService) -> None:
    service._section_names = {
        "introduction",
        "method",
        "experiments",
        "results",
        "limitations",
        "conclusion",
    }
    service._raw_text = (
        "we define the optimization problem and objective. "
        "algorithm 1 shows the pseudocode. "
        "compared to prior work we improve baselines. "
        "p < 0.05 with confidence interval. "
        "future work and threats to validity are discussed. "
        "hyperparameter random seed and implementation details are provided."
    )


def test_evidence_evaluation_dataclass_access() -> None:
    profile = _rich_profile()
    evidence = _rich_evidence()
    scores = [
        DimensionScore(dimension="methodology", score=85.0, confidence=0.8, suggestions=["x"]),
    ]
    plan = RevisionPlan(current_score=85.0)
    result = EvidenceEvaluation(
        paper_path="paper.tex",
        profile=profile,
        evidence=evidence,
        dimension_scores=scores,
        overall_score=85.0,
        gates_passed=True,
        readiness="ready",
        revision_plan=plan,
    )
    assert result.paper_path == "paper.tex"
    assert result.profile.method_family == "deep learning"
    assert result.evidence.observed_count >= 1
    assert result.dimension_scores[0].dimension == "methodology"
    assert result.revision_plan.current_score == 85.0


def test_init_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError):
        EvidenceEvaluationService(mode="unknown")


def test_evaluate_hybrid_end_to_end(tmp_path: Path) -> None:
    tex = r"""
\title{Strong Paper}
\section{Introduction}
We propose a novel method and compared to prior work we improve by 10\%.
\section{Method}
We define an objective and present Algorithm 1.
\begin{equation}a=b\end{equation}
\begin{equation}a=b\end{equation}
\begin{equation}a=b\end{equation}
\begin{equation}a=b\end{equation}
\section{Experiments}
Benchmark baseline dataset with p < 0.05 confidence interval.
\begin{table}x\end{table}
\begin{table}x\end{table}
\begin{figure}x\end{figure}
\begin{figure}x\end{figure}
\section{Limitations}
A limitation is data noise; future work explores larger settings.
Code available at github.com/example/repo with hyperparameter and random seed details.
\appendix
\section{Appendix}
Extra implementation details.
\cite{a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t}
"""
    path = _write_tex(tmp_path / "hybrid.tex", tex)
    service = EvidenceEvaluationService(mode="hybrid")

    result = service.evaluate(path)

    assert result.paper_path.endswith("hybrid.tex")
    assert len(result.dimension_scores) == 7
    assert 0.0 <= result.overall_score <= 100.0
    assert result.readiness in {"ready", "ready_with_revisions", "not_ready"}


def test_evaluate_heuristic_end_to_end(tmp_path: Path) -> None:
    tex = r"""
\title{Heuristic Paper}
\section{Introduction}
Our contribution is clear and compared to prior work we differ significantly.
\section{Method}
\begin{equation} a=b \end{equation}
\section{Experiments}
baseline benchmark p < 0.05
\section{Limitations}
This work has limitations and future work is planned.
"""
    path = _write_tex(tmp_path / "heuristic.tex", tex)
    service = EvidenceEvaluationService(mode="heuristic")

    result = service.evaluate(path)

    assert len(result.dimension_scores) == 7
    assert 0.0 <= result.overall_score <= 100.0
    assert result.readiness in {"ready", "ready_with_revisions", "not_ready"}


@pytest.mark.parametrize(
    ("dimension", "expected_min", "expected_max"),
    [
        ("writing_quality", 60.0, 100.0),
        ("methodology", 80.0, 100.0),
        ("novelty", 70.0, 100.0),
        ("evaluation", 70.0, 100.0),
        ("presentation", 75.0, 100.0),
        ("limitations", 70.0, 100.0),
        ("reproducibility", 70.0, 100.0),
    ],
)
def test_score_dimension_strong_inputs(
    dimension: str,
    expected_min: float,
    expected_max: float,
) -> None:
    service = EvidenceEvaluationService(mode="hybrid")
    _seed_service_for_scoring(service)

    score = service._score_dimension(dimension, _rich_profile(), _rich_evidence())

    assert score.dimension == dimension
    assert expected_min <= score.score <= expected_max
    assert 0.0 <= score.confidence <= 1.0


@pytest.mark.parametrize(
    ("dimension", "expected_max"),
    [
        ("writing_quality", 65.0),
        ("methodology", 20.0),
        ("novelty", 20.0),
        ("evaluation", 20.0),
        ("presentation", 15.0),
        ("limitations", 10.0),
        ("reproducibility", 10.0),
    ],
)
def test_score_dimension_weak_inputs(dimension: str, expected_max: float) -> None:
    service = EvidenceEvaluationService(mode="hybrid")
    service._section_names = {"introduction"}
    service._raw_text = ""

    score = service._score_dimension(dimension, _minimal_profile(), _minimal_evidence())

    assert score.dimension == dimension
    assert 0.0 <= score.score <= expected_max
    assert score.missing_evidence


@pytest.mark.parametrize(
    "scores,expected",
    [
        (
            [
                DimensionScore("methodology", 60, 0.9),
                DimensionScore("novelty", 60, 0.9),
                DimensionScore("evaluation", 60, 0.9),
            ],
            True,
        ),
        (
            [
                DimensionScore("methodology", 59.9, 0.9),
                DimensionScore("novelty", 90, 0.9),
                DimensionScore("evaluation", 90, 0.9),
            ],
            False,
        ),
        (
            [
                DimensionScore("methodology", 90, 0.9),
                DimensionScore("novelty", 59.9, 0.9),
                DimensionScore("evaluation", 90, 0.9),
            ],
            False,
        ),
        (
            [
                DimensionScore("methodology", 90, 0.9),
                DimensionScore("novelty", 90, 0.9),
                DimensionScore("evaluation", 59.9, 0.9),
            ],
            False,
        ),
    ],
)
def test_check_gates(scores: list[DimensionScore], expected: bool) -> None:
    service = EvidenceEvaluationService()
    assert service._check_gates(scores) is expected


@pytest.mark.parametrize(
    ("overall", "gates", "expected"),
    [
        (85.0, True, "ready"),
        (70.0, True, "ready_with_revisions"),
        (59.9, True, "not_ready"),
        (95.0, False, "not_ready"),
    ],
)
def test_determine_readiness(overall: float, gates: bool, expected: str) -> None:
    service = EvidenceEvaluationService()
    assert service._determine_readiness(overall, gates, []) == expected


def test_generate_revision_plan_low_scores() -> None:
    service = EvidenceEvaluationService()
    scores = [
        DimensionScore(
            dimension="methodology",
            score=35.0,
            confidence=0.8,
            suggestions=["Add method details", "Add equations"],
        ),
        DimensionScore(
            dimension="novelty",
            score=50.0,
            confidence=0.8,
            suggestions=["Clarify contributions", "Compare prior work"],
        ),
    ]
    plan = service._generate_revision_plan(scores)
    assert len(plan.items) == 4
    assert all(item.priority == RevisionPriority.IMMEDIATE for item in plan.items)
    assert all(item.effort in {RevisionEffort.HIGH, RevisionEffort.MEDIUM} for item in plan.items)
    assert plan.current_score > 0.0


def test_generate_revision_plan_high_scores_empty() -> None:
    service = EvidenceEvaluationService()
    scores = [
        DimensionScore("methodology", 90.0, 0.9, suggestions=["x"]),
        DimensionScore("novelty", 85.0, 0.9, suggestions=["x"]),
    ]
    plan = service._generate_revision_plan(scores)
    assert plan.items == []


def test_generate_revision_plan_mixed_scores() -> None:
    service = EvidenceEvaluationService()
    scores = [
        DimensionScore("evaluation", 58.0, 0.8, suggestions=["A", "B", "C"]),
        DimensionScore("presentation", 72.0, 0.8, suggestions=["D", "E"]),
        DimensionScore("writing_quality", 81.0, 0.8, suggestions=["F"]),
    ]
    plan = service._generate_revision_plan(scores)
    assert len(plan.items) == 4
    assert plan.items[0].expected_impact >= plan.items[-1].expected_impact
    assert any(item.priority == RevisionPriority.IMMEDIATE for item in plan.items)
    assert any(item.priority == RevisionPriority.MEDIUM_TERM for item in plan.items)


def test_evaluate_empty_paper_edge_case(tmp_path: Path) -> None:
    path = _write_tex(tmp_path / "empty.tex", "")
    service = EvidenceEvaluationService(mode="hybrid")
    result = service.evaluate(path)
    assert len(result.dimension_scores) == 7
    assert result.overall_score <= 30.0


def test_evaluate_no_sections_edge_case(tmp_path: Path) -> None:
    content = "Just plain text with no section markers and no structure"
    path = _write_tex(tmp_path / "nosections.tex", content)
    service = EvidenceEvaluationService(mode="hybrid")
    result = service.evaluate(path)
    assert len(result.dimension_scores) == 7
    assert result.readiness == "not_ready"


def test_evaluate_minimal_content_edge_case(tmp_path: Path) -> None:
    content = r"""
\section{Introduction}
We show something.
"""
    path = _write_tex(tmp_path / "minimal.tex", content)
    service = EvidenceEvaluationService(mode="hybrid")
    result = service.evaluate(path)
    assert result.overall_score < 60.0
    assert result.gates_passed is False


@pytest.mark.parametrize(
    ("template_file", "placeholders"),
    [
        (
            "evidence_extraction.txt",
            ["{section_name}", "{section_text}", "claim", "signal", "confidence"],
        ),
        (
            "dimension_scoring.txt",
            ["{dimension}", "{evidence_items}", "reason_codes", "suggestions"],
        ),
        (
            "revision_planning.txt",
            ["{dimension_scores}", "priority", "expected_impact", "effort"],
        ),
    ],
)
def test_prompt_templates_exist_and_have_placeholders(
    template_file: str,
    placeholders: list[str],
) -> None:
    template_dir = Path("src/crane/templates/llm")
    file_path = template_dir / template_file
    assert file_path.exists()
    content = file_path.read_text(encoding="utf-8")
    for token in placeholders:
        assert token in content


@pytest.mark.parametrize(
    "dimension",
    [
        "writing_quality",
        "methodology",
        "novelty",
        "evaluation",
        "presentation",
        "limitations",
        "reproducibility",
    ],
)
def test_dimension_score_contains_expected_fields(dimension: str) -> None:
    service = EvidenceEvaluationService()
    _seed_service_for_scoring(service)
    score = service._score_dimension(dimension, _rich_profile(), _rich_evidence())
    assert isinstance(score.reason_codes, list)
    assert isinstance(score.evidence_spans, list)
    assert isinstance(score.missing_evidence, list)
    assert isinstance(score.suggestions, list)


def test_heuristic_mode_converts_legacy_suggestions(tmp_path: Path) -> None:
    tex = r"""
\title{Sparse Paper}
\section{Introduction}
This is a cool thing.
"""
    path = _write_tex(tmp_path / "legacy.tex", tex)
    service = EvidenceEvaluationService(mode="heuristic")
    result = service.evaluate(path)
    assert any(score.suggestions for score in result.dimension_scores)
    assert isinstance(result.revision_plan, RevisionPlan)
