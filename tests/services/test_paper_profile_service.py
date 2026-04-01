# pyright: reportMissingImports=false

from __future__ import annotations

from pathlib import Path

import pytest

from crane.models.paper_profile import EvidencePattern, EvidenceSignal, NoveltyShape, PaperType
from crane.services.paper_profile_service import PaperProfileService


def _write_tex(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_extract_profile_empirical(tmp_path: Path) -> None:
    tex = r"""
\title{A Strong Empirical Study}
\keywords{transformer, benchmark, reproducibility}
\section{Introduction}
We propose a novel method for NLP tasks.
\section{Method}
Neural network architecture with transformer blocks.
\begin{equation} a=b \end{equation}
\section{Experiments}
We evaluate on benchmark dataset with baseline comparisons and ablation.
Data split uses 100000 samples. Hyperparameter search and random seed are provided.
Code available at https://github.com/example/repo
\begin{figure}x\end{figure}
\begin{table}y\end{table}
\cite{a,b,c}
\appendix
\section{Extra}
More details.
"""
    path = _write_tex(tmp_path / "empirical.tex", tex)
    svc = PaperProfileService()

    profile = svc.extract_profile(path)

    assert profile.paper_type == PaperType.EMPIRICAL
    assert profile.method_family in {"deep learning", "nlp"}
    assert profile.evidence_pattern == EvidencePattern.BENCHMARK_HEAVY
    assert profile.novelty_shape == NoveltyShape.NEW_METHOD
    assert profile.reproducibility_maturity > 0.5
    assert profile.has_code is True
    assert profile.has_appendix is True
    assert profile.num_figures == 1
    assert profile.num_tables == 1
    assert profile.num_equations == 1
    assert profile.num_references == 3
    assert profile.validation_scale == "large"
    assert "transformer" in profile.keywords


def test_extract_profile_unknown_with_empty_text(tmp_path: Path) -> None:
    path = _write_tex(tmp_path / "empty.tex", "")
    svc = PaperProfileService()

    profile = svc.extract_profile(path)

    assert profile.paper_type == PaperType.UNKNOWN
    assert profile.method_family == ""
    assert profile.evidence_pattern == EvidencePattern.UNKNOWN
    assert profile.novelty_shape == NoveltyShape.UNKNOWN
    assert profile.reproducibility_maturity == 0.0
    assert profile.word_count == 0


def test_extract_evidence_observed_and_inferred(tmp_path: Path) -> None:
    tex = r"""
\section{Introduction}
We show strong gains on benchmark tasks. This may suggest better robustness.
\section{Results}
Our analysis confirms the trend.
"""
    path = _write_tex(tmp_path / "evidence.tex", tex)
    svc = PaperProfileService()

    ledger = svc.extract_evidence(path)

    assert len(ledger.items) >= 2
    assert any(item.signal == EvidenceSignal.OBSERVED for item in ledger.items)
    assert any(item.signal == EvidenceSignal.INFERRED for item in ledger.items)


def test_extract_evidence_adds_missing_signal(tmp_path: Path) -> None:
    tex = r"""
\section{Evaluation}
We report experiment results extensively.
"""
    path = _write_tex(tmp_path / "missing.tex", tex)
    svc = PaperProfileService()

    ledger = svc.extract_evidence(path)

    assert any(item.signal == EvidenceSignal.MISSING for item in ledger.items)


def test_extract_evidence_empty_sections(tmp_path: Path) -> None:
    path = _write_tex(tmp_path / "none.tex", r"\section{A}")
    svc = PaperProfileService()
    ledger = svc.extract_evidence(path)
    assert ledger.items == []


def test_classify_paper_type_empirical() -> None:
    text = r"""
\section{Experiments}
benchmark dataset accuracy baseline ablation
"""
    sections = {"experiments": "x"}
    svc = PaperProfileService()
    assert svc.classify_paper_type(text, sections) == PaperType.EMPIRICAL


def test_classify_paper_type_system() -> None:
    text = r"""
\section{System Architecture}
deployment in production with low latency serving
"""
    sections = {"system architecture": "x"}
    svc = PaperProfileService()
    assert svc.classify_paper_type(text, sections) == PaperType.SYSTEM


def test_classify_paper_type_theoretical() -> None:
    text = r"""
\section{Method}
Theorem 1 and proof are provided.
\begin{equation} x = y \end{equation}
"""
    sections = {"method": "x"}
    svc = PaperProfileService()
    assert svc.classify_paper_type(text, sections) == PaperType.THEORETICAL


def test_classify_paper_type_survey() -> None:
    cites = " ".join([f"\\cite{{k{i}}}" for i in range(60)])
    text = "\\title{A Survey of Methods}\n" + cites
    sections = {"introduction": "x"}
    svc = PaperProfileService()
    assert svc.classify_paper_type(text, sections) == PaperType.SURVEY


def test_classify_paper_type_unknown() -> None:
    svc = PaperProfileService()
    assert svc.classify_paper_type("plain text", {"intro": "x"}) == PaperType.UNKNOWN


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("transformer neural network deep learning", "deep learning"),
        ("convex optimization with gradient descent", "optimization"),
        ("graph neural network with message passing", "graph learning"),
        ("policy optimization actor-critic", "reinforcement learning"),
        ("bayesian variational inference", "probabilistic modeling"),
        ("machine translation for language model", "nlp"),
    ],
)
def test_detect_method_family(text: str, expected: str) -> None:
    svc = PaperProfileService()
    assert svc.detect_method_family(text) == expected


def test_detect_method_family_empty() -> None:
    svc = PaperProfileService()
    assert svc.detect_method_family("") == ""


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("benchmark baseline dataset ablation", EvidencePattern.BENCHMARK_HEAVY),
        ("real-world case study deployment user study", EvidencePattern.APPLICATION_HEAVY),
        ("theorem lemma proof proposition", EvidencePattern.THEOREM_HEAVY),
        ("benchmark theorem deployment", EvidencePattern.MIXED),
        ("none", EvidencePattern.UNKNOWN),
    ],
)
def test_detect_evidence_pattern(text: str, expected: EvidencePattern) -> None:
    svc = PaperProfileService()
    assert svc.detect_evidence_pattern(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("we propose a novel method", NoveltyShape.NEW_METHOD),
        ("we apply this model to healthcare", NoveltyShape.NEW_APPLICATION),
        ("we analyze failure cases", NoveltyShape.NEW_ANALYSIS),
        ("we improve existing baselines and build upon prior work", NoveltyShape.INCREMENTAL),
        ("nothing here", NoveltyShape.UNKNOWN),
    ],
)
def test_detect_novelty_shape(text: str, expected: NoveltyShape) -> None:
    svc = PaperProfileService()
    assert svc.detect_novelty_shape(text) == expected


def test_assess_reproducibility_all_signals() -> None:
    text = """
    github.com/x code available open-source repository
    hyperparameter learning rate batch size epoch
    train/test split validation split cross-validation data split
    random seed deterministic
    hardware gpu runtime implementation details
    """
    svc = PaperProfileService()
    assert svc.assess_reproducibility(text) == 1.0


def test_assess_reproducibility_no_signals() -> None:
    svc = PaperProfileService()
    assert svc.assess_reproducibility("plain text") == 0.0


def test_extract_profile_detects_domain_and_venues(tmp_path: Path) -> None:
    tex = r"""
\title{Vision Benchmarking}
\section{Introduction}
image detection segmentation with references to CVPR and ECCV and IEEE.
\section{Experiments}
dataset benchmark baseline
"""
    path = _write_tex(tmp_path / "domain.tex", tex)
    svc = PaperProfileService()
    profile = svc.extract_profile(path)

    assert profile.problem_domain == "computer vision"
    assert "CVPR" in profile.citation_neighborhood
    assert "ECCV" in profile.citation_neighborhood
    assert "IEEE" in profile.citation_neighborhood


def test_extract_profile_counts_bibitem_references(tmp_path: Path) -> None:
    tex = r"""
\title{Reference Counting}
\section{Intro}
\begin{thebibliography}{9}
\bibitem{a} A
\bibitem{b} B
\end{thebibliography}
"""
    path = _write_tex(tmp_path / "refs.tex", tex)
    svc = PaperProfileService()
    profile = svc.extract_profile(path)
    assert profile.num_references == 2


def test_extract_profile_handles_malformed_latex(tmp_path: Path) -> None:
    tex = r"""
\title{Broken
\section{Intro
We propose method and benchmark dataset.
"""
    path = _write_tex(tmp_path / "broken.tex", tex)
    svc = PaperProfileService()
    profile = svc.extract_profile(path)
    assert profile.word_count > 0
    assert profile.evidence_pattern in {
        EvidencePattern.BENCHMARK_HEAVY,
        EvidencePattern.MIXED,
        EvidencePattern.UNKNOWN,
    }


def test_extract_profile_equation_environment_variants(tmp_path: Path) -> None:
    tex = r"""
\section{Method}
\begin{align}
a &= b
\end{align}
\begin{multline}
x+y=z
\end{multline}
"""
    path = _write_tex(tmp_path / "equations.tex", tex)
    svc = PaperProfileService()
    profile = svc.extract_profile(path)
    assert profile.num_equations == 2
