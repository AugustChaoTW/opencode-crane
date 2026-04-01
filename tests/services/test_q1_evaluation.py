"""Tests for Q1 evaluation service."""

from __future__ import annotations

import importlib

from crane.models.paper import AiAnnotations, Paper


def _load_eval():
    return importlib.import_module("crane.services.q1_evaluation_service")


class TestQ1EvaluationService:
    def test_evaluate_returns_q1_evaluation(self, tmp_path):
        eval_mod = _load_eval()
        tex_file = tmp_path / "test.tex"
        tex_file.write_text(r"""
\title{Test Paper}
\section{Introduction}
Our contribution is significant.
\section{Methodology}
We propose a novel approach.
\section{Experiments}
Compared to baselines, we achieve 15% improvement.
\section{Limitations}
This work has limitations.
\section{Future Work}
Future work includes...
""")
        service = eval_mod.Q1EvaluationService()
        result = service.evaluate(tex_file)

        assert result.overall_score >= 0.0
        assert result.overall_score <= 1.0
        assert len(result.criteria) > 0
        assert result.readiness in [
            "READY: Meets Q1 standards",
            "NEARLY READY: Minor improvements needed",
            "NEEDS WORK: Significant improvements required",
            "NOT READY: Critical issues must be addressed",
            "NEEDS WORK: Multiple weak areas require improvement",
        ]

    def test_evaluate_detects_weak_areas(self, tmp_path):
        eval_mod = _load_eval()
        tex_file = tmp_path / "test.tex"
        tex_file.write_text(r"""
\title{Test Paper}
\section{Introduction}
This is a cool paper.
\section{Methodology}
We do stuff.
""")
        service = eval_mod.Q1EvaluationService()
        result = service.evaluate(tex_file)

        weak_criteria = [
            c
            for c in result.criteria
            if c.score in [eval_mod.Q1Score.WEAK, eval_mod.Q1Score.CRITICAL]
        ]
        assert len(weak_criteria) > 0

    def test_evaluate_excellent_paper(self, tmp_path):
        eval_mod = _load_eval()
        tex_file = tmp_path / "test.tex"
        tex_file.write_text(r"""
\title{Test Paper}
\section{Introduction}
Our main contributions are:
\begin{itemize}
\item Contribution 1
\item Contribution 2
\end{itemize}
Compared to existing methods, our approach differs in several ways.
\section{Methodology}
\begin{equation}
E = mc^2
\end{equation}
The hyperparameters were selected via cross-validation.
\section{Experiments}
We compare with several baselines including SOTA methods.
Results show statistical significance (p < 0.05).
\section{Limitations}
This study has several limitations.
\section{Future Work}
Future work will address these limitations.
Code is available at github.com/example.
""")
        service = eval_mod.Q1EvaluationService()
        result = service.evaluate(tex_file)

        assert result.overall_score >= 0.6

    def test_evaluate_uses_ai_annotations_when_paper_provided(self, tmp_path):
        eval_mod = _load_eval()
        tex_file = tmp_path / "test.tex"
        tex_file.write_text(r"""
\title{Test Paper}
\section{Introduction}
This section is intentionally terse.
""")
        paper = Paper(
            key="k",
            title="T",
            authors=["A"],
            year=2026,
            ai_annotations=AiAnnotations(
                summary="Our contributions are: we propose a robust method and reduce error by 10% compared to baselines."
            ),
        )

        service = eval_mod.Q1EvaluationService()
        result = service.evaluate(tex_file, paper=paper)
        contribution = next(c for c in result.criteria if c.name == "Contribution Statement")

        assert contribution.score != eval_mod.Q1Score.WEAK
        assert result.summary["annotation_context_used"] is True
