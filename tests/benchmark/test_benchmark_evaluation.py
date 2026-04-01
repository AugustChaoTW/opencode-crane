# pyright: reportMissingImports=false

from __future__ import annotations

from pathlib import Path

import pytest

from crane.models.paper_profile import EvidenceSignal, PaperType, RevisionPriority
from crane.services.evidence_evaluation_service import EvidenceEvaluation, EvidenceEvaluationService
from crane.services.journal_matching_service import JournalMatchingService
from crane.services.paper_profile_service import PaperProfileService
from crane.services.revision_planning_service import RevisionPlanningService


def _write_tex(tmp_path: Path, filename: str, content: str) -> Path:
    path = tmp_path / filename
    path.write_text(content, encoding="utf-8")
    return path


STRONG_PAPER_TEX = r"""
\title{Robust Hybrid Evaluation for Reliable Language Model Adaptation}
\begin{abstract}
This paper presents a robust hybrid evaluation pipeline for adaptation of transformer systems in
high-stakes text analytics. We formalize objective functions, compare calibrated baselines, and
report reproducible experiments over large public corpora. The design includes clear methodology,
multiple ablations, and explicit limitations analysis.
\end{abstract}
\section{Introduction}
Modern NLP systems often fail when distribution shifts appear across domains such as legal text,
clinical narratives, and financial filings. We propose a hybrid evaluation protocol that couples
quantitative benchmark validation with qualitative error tracing. Our results show stable gains in
accuracy and robustness while reducing variance across seeds. Compared to prior work, our method
introduces a tighter bridge between model diagnostics and decision-ready evidence. We ground the
motivation in established literature from NeurIPS, ICML, ACL, and IEEE venues and explain why
benchmark-only reporting can hide meaningful failure modes. We report claims in a traceable way so
that reviewers can map each contribution to empirical support, implementation choices, and explicit
risk statements.
\section{Methodology}
We define the optimization objective with regularization and calibration constraints. Let model
parameters be \(\theta\). We optimize a weighted objective balancing task loss and consistency.
\begin{equation}
\mathcal{L}(\theta) = \mathcal{L}_{task}(\theta) + \lambda \mathcal{L}_{cal}(\theta) + \gamma \lVert\theta\rVert_2^2
\end{equation}
Algorithm 1 outlines the full pipeline: data curation, train/validation split, hyperparameter
search, ablation schedule, and robustness probes. We detail learning rate, batch size, epoch
budget, and deterministic random seed settings. We also provide implementation details for
tokenization, hardware configuration, and runtime constraints. The method family is transformer-
based deep learning with explicit error decomposition and confidence-aware post-processing.
\section{Experiments and Results}
We evaluate on five benchmark datasets with over 120000 instances in total and compare against
strong baseline systems including prompt-only adaptation, LoRA fine-tuning, and retrieval-augmented
variants. Our analysis shows statistically significant improvements with p < 0.05 and confidence
intervals across repeated runs. We demonstrate that our method improves macro-F1, calibration, and
shift robustness while maintaining acceptable latency in practical workflows.
\begin{table}
\centering
\begin{tabular}{lcc}
Model & F1 & Robustness \\
Baseline-A & 81.2 & 72.4 \\
HybridEval & 88.9 & 84.1 \\
\end{tabular}
\caption{Benchmark comparison with baselines and ablations.}
\end{table}
\begin{table}
\centering
\begin{tabular}{lcc}
Variant & ECE & Latency \\
No calibration & 0.112 & 38 \\
Full method & 0.041 & 42 \\
\end{tabular}
\caption{Calibration and efficiency trade-offs.}
\end{table}
\begin{figure}
\caption{Architecture and evaluation workflow.}
\end{figure}
\section{Limitations and Future Work}
A current limitation is sensitivity to noisy labels in low-resource slices, and another limitation is
that domain adaptation still depends on curated prompts. We discuss threats to validity, data bias,
and external validity boundaries. Future work includes broader multilingual evaluation and stronger
causal diagnostics. Code available at https://github.com/example/hybrid-eval with scripts,
configuration files, and reproducibility checklist.
\appendix
\section{Appendix}
Additional implementation details, hyperparameter grids, and seed-wise variance tables are provided.
\cite{vaswani2017attention,devlin2019bert,brown2020language,raffel2020t5,li2022survey,liu2021roberta,wang2023robust,lin2020focal,radford2019gpt,he2016resnet,kingma2015adam,chen2021simcse,zhou2022calibration,gao2021simcse,beltagy2020longformer,dua2019uci,paszke2019pytorch,wolf2020transformers,yu2023adapter,hendrycks2020many}
"""


WEAK_PAPER_TEX = r"""
\title{Notes on an Initial Idea for Text Processing}
\begin{abstract}
We describe an early concept and some observations. The manuscript is intentionally lightweight and
does not yet include structured empirical validation.
\end{abstract}
\section{Introduction}
This draft discusses a general idea about improving text processing systems, but the discussion
remains broad and narrative. We describe motivation and use several informal statements about why
the idea may be useful in practice. The writing includes high-level claims without measurable
targets, no clear objective definition, and no detailed assumptions. We mention that previous work
exists and provide a few citations, but we do not present explicit comparisons or rigorous framing.
The purpose of this draft is to document intuition and context before formal experiments are run.
\section{Background}
The background reviews classic language modeling and related tools in a descriptive style. We outline
possible directions for future implementation but omit algorithmic details and method breakdown.
There is no standalone methodology section, no clear specification of training setup, and no
reproducibility package. We include one symbolic expression for notation only.
\begin{equation}
z = x + y
\end{equation}
\section{Discussion}
We report anecdotal observations from internal trials and informal checks. The manuscript does not
include benchmark datasets, baseline systems, ablation analysis, significance testing, or confidence
intervals. We provide a small descriptive table to summarize rough impressions instead of validated
results.
\begin{table}
\centering
\begin{tabular}{lc}
Aspect & Note \\
Speed & acceptable \\
Quality & promising \\
\end{tabular}
\caption{Informal notes without benchmark validation.}
\end{table}
The paper currently has no code link, no explicit limitations section, and no deployment evidence.
Further work is required to convert this idea into a Q1-ready manuscript.
\cite{manning1999foundations,jurafsky2000speech,russell2010ai,goodfellow2016dl,vaswani2017attention,devlin2019bert}
"""


METHODOLOGY_WEAK_PAPER_TEX = r"""
\title{Comprehensive Evaluation of Prompt Calibration Strategies}
\begin{abstract}
We provide broad evaluation and polished writing for prompt calibration strategies, but the core
method description remains shallow and intentionally under-specified.
\end{abstract}
\section{Introduction}
Reliable calibration is central to safe deployment of language models. We present a careful
evaluation narrative with strong organization and clear argument flow. Compared to prior work, our
paper reports broad result coverage and practical reporting structure. We emphasize reproducibility
assets and transparency. However, this version intentionally avoids deep method derivations and does
not include a dedicated approach section with technical pipeline details.
\section{Experimental Setup}
We evaluate on benchmark datasets spanning sentiment, intent classification, and retrieval reranking.
Across 60000 evaluation instances, we compare against strong baseline prompts and lightweight tuning
variants. We report accuracy, macro-F1, and calibration error with confidence intervals. Results are
statistically stable with p < 0.05 over repeated runs. We provide multiple tables and visual summaries
to support interpretation.
\begin{table}
\centering
\begin{tabular}{lcc}
Model & F1 & ECE \\
Baseline Prompt & 80.4 & 0.121 \\
Calibrated Prompt & 85.7 & 0.058 \\
\end{tabular}
\caption{Main benchmark evaluation with baselines.}
\end{table}
\section{Results and Analysis}
Our analysis shows that calibration improves robustness under shift and reduces overconfidence. We
present error slices, sensitivity trends, and confidence diagnostics in structured prose. We discuss
limitations and future work, including data drift adaptation and annotation quality constraints. The
paper includes a public repository at github.com/example/calibration-study and complete seed
controls for reproducibility. Despite the strong evaluation, the manuscript lacks algorithmic depth,
formal objective definition, pseudocode, and explicit method decomposition required for strong
methodology scoring.
\section{Limitations}
A limitation is dependence on manually curated prompts in domain-specific settings, and future work
will improve automation and causal attribution.
\cite{guo2017calibration,naeini2015obtaining,minderer2021revisiting,desai2021calibration,zhou2022calibration,wang2023robust,kumar2019verified,brown2020language,ouyang2022training}
"""


SYSTEM_PAPER_TEX = r"""
\title{A Production-Grade Retrieval System for Continual Research Assistance}
\begin{abstract}
This paper describes a deployable architecture for retrieval and ranking in a research assistant,
including implementation details, serving constraints, and operational benchmark analysis.
\end{abstract}
\section{Introduction}
Practical assistant systems require robust architecture, predictable latency, and monitored
throughput under evolving workloads. We present an end-to-end system that combines indexing,
reranking, and quality control for literature workflows. The paper focuses on system design and
deployment realism rather than theoretical guarantees.
\section{System Architecture}
The architecture contains ingestion workers, a vector index service, a reranker gateway, and an
observability control plane. We document interfaces, fallback paths, and failure handling. A core
objective balances relevance and operational constraints.
\begin{equation}
S = \alpha \cdot Rel + \beta \cdot Freshness - \gamma \cdot Cost
\end{equation}
We describe implementation details, resource scheduling, and autoscaling policy for peak load
periods. The deployment target is a production-like environment with staged rollout and canary
checks.
\section{Deployment and Operations}
We deploy the service using containerized components and measure latency, throughput, and cost over
month-long traces. The deployment section includes incident-response protocol, SLO tracking, and
monitoring dashboards. We report that p95 latency remains below 180 ms under sustained traffic.
\section{Benchmarks}
We benchmark the full system against two service baselines and one retrieval-only variant. Results
show improved throughput and lower cost while preserving retrieval quality.
\begin{table}
\centering
\begin{tabular}{lcc}
System & p95 Latency(ms) & Throughput(req/s) \\
Baseline Service & 240 & 420 \\
Our System & 178 & 590 \\
\end{tabular}
\caption{System benchmark under production-like workload.}
\end{table}
\begin{figure}
\caption{Deployment topology and architecture modules.}
\end{figure}
We include limitations on cross-region replication and discuss future work for stronger fault
tolerance and security hardening. Repository and deployment scripts are available at
https://github.com/example/research-system.
\cite{dean2013tail,jeffrey2014dapper,zaharia2016spark,shapiro2019sre,kleppmann2017ddia,brewer2012cap,martin2021indexing,smith2020retrieval,wang2022serving}
"""


@pytest.fixture
def strong_paper_path(tmp_path: Path) -> Path:
    return _write_tex(tmp_path, "strong_paper.tex", STRONG_PAPER_TEX)


@pytest.fixture
def weak_paper_path(tmp_path: Path) -> Path:
    return _write_tex(tmp_path, "weak_paper.tex", WEAK_PAPER_TEX)


@pytest.fixture
def methodology_weak_paper_path(tmp_path: Path) -> Path:
    return _write_tex(tmp_path, "methodology_weak_paper.tex", METHODOLOGY_WEAK_PAPER_TEX)


@pytest.fixture
def survey_paper_path(tmp_path: Path) -> Path:
    survey_citations = ",".join(f"surveyref{i}" for i in range(1, 65))
    survey_tex = f"""
\\title{{A Survey of Validation Strategies for Trustworthy AI Systems}}
\\begin{{abstract}}
This survey synthesizes evidence across a wide body of literature on validation, reproducibility,
and benchmark methodology for AI systems in research and industry contexts.
\\end{{abstract}}
\\section{{Introduction}}
This survey maps the evolution of validation practices from early benchmark culture to modern
reproducibility standards. We summarize recurring gaps in reporting, fragmented evaluation metrics,
and inconsistent claims about robustness. The manuscript provides a taxonomy for benchmark design,
threats to validity, and practical checklist usage across disciplines. We discuss how citation
networks reveal conceptual clusters and where protocol choices create hidden comparability issues.
\\section{{Taxonomy of Validation Practices}}
We organize prior work into data-centric protocols, model-centric stress tests, human-centered
assessment, and deployment-time monitoring. For each category, we explain strengths, weaknesses,
and applicability boundaries. The narrative contrasts broad methodological families and clarifies
terminology for replication, reproducibility, and external validity. A formal notation section is
included for consistency across surveyed frameworks.
\\begin{{equation}}
R = f(coverage, rigor, transparency)
\\end{{equation}}
\\section{{Synthesis and Critical Analysis}}
We critically compare survey findings and identify unresolved conflicts in study design assumptions.
The paper emphasizes synthesis over new experimentation: no benchmark runs are executed in this
work, and no system deployment claims are made. Instead, we provide dense citation-backed analysis,
gap mapping, and recommendations for future empirical studies. A summary table groups representative
papers by domain, validation pattern, and evidence quality.
\\begin{{table}}
\\centering
\\begin{{tabular}}{{lll}}
Theme & Common Practice & Frequent Gap \\\\
Benchmarks & Leaderboard focus & Weak external validity \\\\
Reproducibility & Code release & Missing seeds/splits \\\\
Robustness & Stress testing & Limited domain shift coverage \\\\
\\end{{tabular}}
\\caption{{Survey taxonomy and recurring gaps.}}
\\end{{table}}
\\section{{Conclusion}}
This survey concludes with practical guidance for authors and reviewers, highlighting the need for
evidence traceability and transparent reporting artifacts. We also discuss limitations in coverage
and potential biases in available corpora. Future work should connect this synthesis with controlled
benchmark experiments.
\\cite{{{survey_citations}}}
"""
    return _write_tex(tmp_path, "survey_paper.tex", survey_tex)


@pytest.fixture
def system_paper_path(tmp_path: Path) -> Path:
    return _write_tex(tmp_path, "system_paper.tex", SYSTEM_PAPER_TEX)


def test_strong_paper_scores_high(strong_paper_path: Path) -> None:
    evaluation = EvidenceEvaluationService(mode="hybrid").evaluate(strong_paper_path)
    assert evaluation.overall_score > 70
    assert evaluation.gates_passed is True
    assert evaluation.readiness in {"ready", "ready_with_revisions"}


def test_weak_paper_scores_low(weak_paper_path: Path) -> None:
    evaluation = EvidenceEvaluationService(mode="hybrid").evaluate(weak_paper_path)
    assert evaluation.overall_score < 50
    assert evaluation.gates_passed is False


def test_methodology_gate_blocks(methodology_weak_paper_path: Path) -> None:
    evaluation = EvidenceEvaluationService(mode="hybrid").evaluate(methodology_weak_paper_path)
    methodology = next(
        score for score in evaluation.dimension_scores if score.dimension == "methodology"
    )
    assert methodology.score < 60
    assert evaluation.gates_passed is False


def test_paper_type_classification(
    strong_paper_path: Path,
    weak_paper_path: Path,
    methodology_weak_paper_path: Path,
    survey_paper_path: Path,
    system_paper_path: Path,
) -> None:
    profiler = PaperProfileService()
    assert profiler.extract_profile(strong_paper_path).paper_type == PaperType.EMPIRICAL
    assert profiler.extract_profile(weak_paper_path).paper_type == PaperType.UNKNOWN
    assert profiler.extract_profile(methodology_weak_paper_path).paper_type == PaperType.EMPIRICAL
    assert profiler.extract_profile(survey_paper_path).paper_type == PaperType.SURVEY
    assert profiler.extract_profile(system_paper_path).paper_type == PaperType.SYSTEM


def test_evidence_extraction_finds_signals(strong_paper_path: Path) -> None:
    evidence = PaperProfileService().extract_evidence(strong_paper_path)
    assert evidence.observed_count >= 3
    assert any(item.signal == EvidenceSignal.OBSERVED for item in evidence.items)


def test_revision_plan_generation(weak_paper_path: Path) -> None:
    evaluation = EvidenceEvaluationService(mode="hybrid").evaluate(weak_paper_path)
    assert evaluation.revision_plan.items
    assert any(
        item.priority == RevisionPriority.IMMEDIATE for item in evaluation.revision_plan.items
    )


def test_journal_matching_realistic(strong_paper_path: Path) -> None:
    profile = PaperProfileService().extract_profile(strong_paper_path)
    top3 = JournalMatchingService().recommend_top3(profile)
    assert top3["target"] is not None
    assert top3["backup"] is not None
    assert top3["safe"] is not None


def test_revision_report_generation(weak_paper_path: Path) -> None:
    evaluation = EvidenceEvaluationService(mode="hybrid").evaluate(weak_paper_path)
    report = RevisionPlanningService().generate_full_report(
        dimension_scores=evaluation.dimension_scores,
        gates_passed=evaluation.gates_passed,
        readiness=evaluation.readiness,
        plan=evaluation.revision_plan,
    )
    assert "# Q1 Readiness Scorecard" in report
    assert "# Evidence View" in report
    assert "# Revision Backlog" in report


def test_heuristic_mode_backward_compatible(strong_paper_path: Path) -> None:
    evaluation = EvidenceEvaluationService(mode="heuristic").evaluate(strong_paper_path)
    assert isinstance(evaluation, EvidenceEvaluation)
    assert len(evaluation.dimension_scores) == 7
    assert 0.0 <= evaluation.overall_score <= 100.0


def test_scoring_consistency(strong_paper_path: Path) -> None:
    service = EvidenceEvaluationService(mode="hybrid")
    first = service.evaluate(strong_paper_path)
    second = service.evaluate(strong_paper_path)
    assert first.overall_score == second.overall_score
    assert first.gates_passed == second.gates_passed
    assert first.readiness == second.readiness
    assert [score.score for score in first.dimension_scores] == [
        score.score for score in second.dimension_scores
    ]
