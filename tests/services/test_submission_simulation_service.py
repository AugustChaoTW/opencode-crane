# pyright: reportMissingImports=false

from __future__ import annotations

import math
from pathlib import Path

from crane.services.submission_simulation_service import SubmissionSimulationService


def _write_tex(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_simulate_outcomes_returns_expected_shape(tmp_path: Path) -> None:
    tex = r"""
\title{World Model Driven Submission}
\begin{abstract}
We propose a machine learning method.
\end{abstract}
\section{Introduction}
This work studies machine learning.
\section{Related Work}
Prior studies are discussed.
\section{Method}
Our method is described.
\section{Evaluation}
We evaluate with benchmark and ablation studies.
\begin{figure}x\end{figure}
\begin{table}y\end{table}
\section{Limitations}
Threats to validity are discussed.
\section{Conclusion}
Summary.
\cite{k1,k2,k3,k4,k5,k6,k7,k8,k9,k10,k11,k12,k13,k14,k15,k16,k17,k18,k19,k20,k21}
"""
    paper_path = _write_tex(tmp_path / "paper.tex", tex)
    service = SubmissionSimulationService(project_dir=str(_repo_root()))

    result = service.simulate_outcomes(
        paper_path=str(paper_path),
        target_journal="IEEE TPAMI",
        revision_status="current",
        num_scenarios=5,
    )

    assert "paper_profile" in result
    assert "scenarios" in result
    assert "world_model_analysis" in result
    assert "recommendation" in result
    assert len(result["scenarios"]) == 5

    total_probability = sum(item["probability"] for item in result["scenarios"])
    assert math.isclose(total_probability, 1.0, rel_tol=1e-9, abs_tol=1e-9)


def test_missing_sections_reduce_acceptance_probability(tmp_path: Path) -> None:
    strong_tex = r"""
\title{Strong Draft}
\begin{abstract}A\end{abstract}
\section{Introduction}x
\section{Related Work}x
\section{Method}x
\section{Evaluation}benchmark ablation
\section{Limitations}x
\section{Conclusion}x
\cite{a1,a2,a3,a4,a5,a6,a7,a8,a9,a10,a11,a12,a13,a14,a15,a16,a17,a18,a19,a20,a21,a22,a23,a24,a25}
"""
    weak_tex = r"""
\title{Weak Draft}
\section{Introduction}x
\section{Method}x
\section{Conclusion}x
\cite{a1,a2,a3,a4,a5}
"""

    strong_path = _write_tex(tmp_path / "strong.tex", strong_tex)
    weak_path = _write_tex(tmp_path / "weak.tex", weak_tex)

    service = SubmissionSimulationService(project_dir=str(_repo_root()))
    journal = service._find_target_journal("IEEE TPAMI")

    strong_profile = service._build_paper_profile(strong_path)
    weak_profile = service._build_paper_profile(weak_path)

    strong_fit = service._score_journal_fit(strong_profile, journal)
    weak_fit = service._score_journal_fit(weak_profile, journal)

    strong_acceptance = service._estimate_acceptance_probability(
        paper_profile=strong_profile,
        journal=journal,
        fit_score=strong_fit,
        revision_status="current",
    )
    weak_acceptance = service._estimate_acceptance_probability(
        paper_profile=weak_profile,
        journal=journal,
        fit_score=weak_fit,
        revision_status="current",
    )

    assert strong_acceptance > weak_acceptance


def test_num_scenarios_is_clamped_to_valid_range(tmp_path: Path) -> None:
    tex = r"""
\title{Scenario Range}
\section{Introduction}x
\section{Method}x
\section{Evaluation}x
\section{Related Work}x
\section{Limitations}x
\section{Conclusion}x
\cite{a1,a2,a3,a4,a5,a6,a7,a8,a9,a10,a11,a12,a13,a14,a15,a16,a17,a18,a19,a20}
"""
    paper_path = _write_tex(tmp_path / "range.tex", tex)
    service = SubmissionSimulationService(project_dir=str(_repo_root()))

    low_result = service.simulate_outcomes(
        paper_path=str(paper_path),
        target_journal="IEEE TPAMI",
        num_scenarios=1,
    )
    high_result = service.simulate_outcomes(
        paper_path=str(paper_path),
        target_journal="IEEE TPAMI",
        num_scenarios=20,
    )

    assert len(low_result["scenarios"]) == 3
    assert len(high_result["scenarios"]) == 7


def test_unknown_target_journal_uses_fallback_profile(tmp_path: Path) -> None:
    tex = r"""
\title{Fallback Journal}
\section{Introduction}x
\section{Method}x
\section{Evaluation}x
\section{Conclusion}x
\cite{a1,a2,a3,a4,a5,a6,a7,a8,a9,a10,a11,a12,a13,a14,a15,a16,a17,a18,a19,a20}
"""
    paper_path = _write_tex(tmp_path / "fallback.tex", tex)
    service = SubmissionSimulationService(project_dir=str(_repo_root()))

    result = service.simulate_outcomes(
        paper_path=str(paper_path),
        target_journal="Imaginary Journal of Future Science",
        num_scenarios=5,
    )

    assert result["target_journal"] == "Imaginary Journal of Future Science"
    assert result["world_model_analysis"]["default_trajectory"] in {
        scenario["name"] for scenario in result["scenarios"]
    }
