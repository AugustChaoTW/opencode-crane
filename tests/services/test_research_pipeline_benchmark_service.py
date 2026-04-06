# pyright: reportMissingImports=false

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

SERVICE_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "crane"
    / "services"
    / "research_pipeline_benchmark_service.py"
)
SERVICE_SPEC = importlib.util.spec_from_file_location(
    "research_pipeline_benchmark_service_local", SERVICE_PATH
)
if SERVICE_SPEC is None or SERVICE_SPEC.loader is None:
    raise RuntimeError("Unable to load research_pipeline_benchmark_service module")
SERVICE_MODULE = importlib.util.module_from_spec(SERVICE_SPEC)
sys.modules[SERVICE_SPEC.name] = SERVICE_MODULE
SERVICE_SPEC.loader.exec_module(SERVICE_MODULE)
ResearchPipelineBenchmarkService = SERVICE_MODULE.ResearchPipelineBenchmarkService


def _accepted_manuscript(title: str) -> str:
    return rf"""
\\section{{Introduction}}
In this paper we introduce a novel method titled {title}. The motivation and
problem statement highlight a core challenge and research question with practical value.
Our significance and impact are broad and we define a new paradigm.

\\section{{Related Work}}
We compare with prior work and related work across state-of-the-art benchmark families
\\cite{{a1,a2,a3,a4,a5,a6,a7,a8,a9,a10,a11,a12}}.
Unlike previous work, in contrast to prior baselines, our method differs from
existing benchmark assumptions and uses recent OpenReview reports.

\\section{{Method}}
We hypothesize that the objective loss improves generalization and test whether
this holds under control conditions. The methodology includes comprehensive evaluation.
\\begin{{equation}} f(x)=x^2 \\end{{equation}}
\\begin{{equation}} y=mx+b \\end{{equation}}

\\section{{Experiments}}
We run ablation, statistical significance analysis, and strong baseline comparison.
The experimental setup includes robustness and comprehensive evaluation.

\\section{{Implementation Details}}
Code is available in open-source repository at github.com/example/project.
We provide random seed, hyperparameter tuning, implementation details, compute budget,
artifact evaluation, reproducibility checklist, docker setup, scripts, and requirements.txt.

\\begin{{figure}}
\\caption{{Visualization with error bar for benchmark metrics.}}
\\end{{figure}}

\\section{{Conclusion}}
We demonstrate improved results and discuss limitation, ethics, future work,
appendix, supplementary material, and camera-ready checklist for NeurIPS conference track.
"""


def _rejected_manuscript(title: str) -> str:
    return rf"""
\\section{{Intro}}
This is a cool thing about {title}. Nice stuff maybe works.

\\section{{Method}}
We tried something and it could be better. No baseline discussion.

\\section{{Results}}
Some numbers look good but maybe not always.
"""


def _auc(scores: list[float], labels: list[int]) -> float:
    positives = [score for score, label in zip(scores, labels) if label == 1]
    negatives = [score for score, label in zip(scores, labels) if label == 0]
    if not positives or not negatives:
        return 0.0

    wins = 0.0
    for pos in positives:
        for neg in negatives:
            if pos > neg:
                wins += 1.0
            elif pos == neg:
                wins += 0.5

    return wins / (len(positives) * len(negatives))


@pytest.fixture
def service(tmp_path: Path) -> ResearchPipelineBenchmarkService:
    refs_dir = tmp_path / "references"
    refs_dir.mkdir(parents=True, exist_ok=True)
    return ResearchPipelineBenchmarkService(refs_dir=str(refs_dir))


def _write_manuscript(tmp_path: Path, content: str, name: str = "paper.tex") -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_constructor_sets_refs_dir(service: ResearchPipelineBenchmarkService) -> None:
    assert "references" in service.refs_dir


def test_evaluate_pipeline_returns_expected_structure(
    service: ResearchPipelineBenchmarkService, tmp_path: Path
) -> None:
    paper_path = _write_manuscript(tmp_path, _accepted_manuscript("Test Paper"))
    result = service.evaluate_pipeline(str(paper_path))

    assert set(result.keys()) == {
        "paper_path",
        "stages",
        "coherence_scores",
        "health_score",
        "prediction",
    }
    assert len(result["stages"]) == 6
    assert 0.0 <= float(result["health_score"]) <= 100.0


def test_calculate_stage_scores_raises_on_unknown_stage(
    service: ResearchPipelineBenchmarkService,
) -> None:
    with pytest.raises(ValueError):
        service.calculate_stage_scores({"text": "hello"}, "unknown")


def test_stage_scores_are_bounded(
    service: ResearchPipelineBenchmarkService,
) -> None:
    score = service.calculate_stage_scores(
        {"text": _accepted_manuscript("Bounded Score")},
        "ideation",
    )
    assert 0.0 <= score <= 100.0


def test_check_stage_coherence_high_when_outputs_align(
    service: ResearchPipelineBenchmarkService,
) -> None:
    stage1 = {"score": 88.0, "key_terms": ["novel", "motivation", "benchmark"]}
    stage2 = {"score": 84.0, "key_terms": ["novel", "benchmark", "methodology"]}
    coherence = service.check_stage_coherence(stage1, stage2)
    assert coherence >= 70.0


def test_check_stage_coherence_low_when_outputs_diverge(
    service: ResearchPipelineBenchmarkService,
) -> None:
    stage1 = {"score": 95.0, "key_terms": ["novel", "motivation", "impact"]}
    stage2 = {"score": 20.0, "key_terms": ["random", "casual"]}
    coherence = service.check_stage_coherence(stage1, stage2)
    assert coherence < 50.0


def test_calculate_pipeline_health_score_uses_weights(
    service: ResearchPipelineBenchmarkService,
) -> None:
    all_stages = {
        "ideation": {"score": 80.0},
        "literature": {"score": 75.0},
        "design": {"score": 70.0},
        "implementation": {"score": 65.0},
        "writing": {"score": 60.0},
        "submission": {"score": 55.0},
    }
    score = service.calculate_pipeline_health_score(all_stages)
    expected = 80.0 * 0.14 + 75.0 * 0.16 + 70.0 * 0.18 + 65.0 * 0.17 + 60.0 * 0.17 + 55.0 * 0.18
    assert score == round(expected, 2)


def test_evaluate_pipeline_predicts_accept_for_strong_manuscript(
    service: ResearchPipelineBenchmarkService, tmp_path: Path
) -> None:
    paper_path = _write_manuscript(tmp_path, _accepted_manuscript("Strong Paper"), "acc.tex")
    result = service.evaluate_pipeline(str(paper_path))
    assert result["prediction"]["label"] == "accept"
    assert float(result["health_score"]) >= 70.0


def test_evaluate_pipeline_predicts_reject_for_weak_manuscript(
    service: ResearchPipelineBenchmarkService, tmp_path: Path
) -> None:
    paper_path = _write_manuscript(tmp_path, _rejected_manuscript("Weak Paper"), "rej.tex")
    result = service.evaluate_pipeline(str(paper_path))
    assert result["prediction"]["label"] == "reject"


def test_stage_outputs_include_sub_dimensions_and_signals(
    service: ResearchPipelineBenchmarkService, tmp_path: Path
) -> None:
    paper_path = _write_manuscript(tmp_path, _accepted_manuscript("Signals"), "signals.tex")
    result = service.evaluate_pipeline(str(paper_path))
    ideation = result["stages"]["ideation"]
    assert "sub_dimensions" in ideation
    assert "signal_counts" in ideation
    assert isinstance(ideation["key_terms"], list)


def test_missing_paper_path_raises_file_not_found(
    service: ResearchPipelineBenchmarkService,
) -> None:
    with pytest.raises(FileNotFoundError):
        service.evaluate_pipeline("/tmp/does-not-exist-9999.tex")


def test_dataset_fixture_has_100_balanced_records() -> None:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "benchmark_dataset.yaml"
    payload = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))

    papers = payload["papers"]
    accepted = [p for p in papers if p["label"] == "accept"]
    rejected = [p for p in papers if p["label"] == "reject"]

    assert payload["paper_count"] == 100
    assert len(papers) == 100
    assert len(accepted) == 50
    assert len(rejected) == 50


def test_benchmark_dataset_auc_exceeds_target(
    service: ResearchPipelineBenchmarkService, tmp_path: Path
) -> None:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "benchmark_dataset.yaml"
    payload = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))

    scores: list[float] = []
    labels: list[int] = []

    for index, paper in enumerate(payload["papers"]):
        profile = paper["profile"]
        title = paper["title"]
        manuscript = (
            _accepted_manuscript(title) if profile == "accepted" else _rejected_manuscript(title)
        )
        paper_path = _write_manuscript(tmp_path, manuscript, f"sample_{index}.tex")
        report = service.evaluate_pipeline(str(paper_path))
        scores.append(float(report["health_score"]))
        labels.append(1 if paper["label"] == "accept" else 0)

    auc = _auc(scores, labels)
    assert auc > 0.8


def test_accepted_group_health_higher_than_rejected_group(
    service: ResearchPipelineBenchmarkService, tmp_path: Path
) -> None:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "benchmark_dataset.yaml"
    payload = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))

    accepted_scores: list[float] = []
    rejected_scores: list[float] = []

    for index, paper in enumerate(payload["papers"]):
        manuscript = (
            _accepted_manuscript(paper["title"])
            if paper["label"] == "accept"
            else _rejected_manuscript(paper["title"])
        )
        paper_path = _write_manuscript(tmp_path, manuscript, f"grp_{index}.tex")
        health = float(service.evaluate_pipeline(str(paper_path))["health_score"])
        if paper["label"] == "accept":
            accepted_scores.append(health)
        else:
            rejected_scores.append(health)

    assert sum(accepted_scores) / len(accepted_scores) > sum(rejected_scores) / len(rejected_scores)


def test_coherence_scores_include_overall(
    service: ResearchPipelineBenchmarkService, tmp_path: Path
) -> None:
    paper_path = _write_manuscript(tmp_path, _accepted_manuscript("Coherence"), "coh.tex")
    report = service.evaluate_pipeline(str(paper_path))

    coherence = report["coherence_scores"]
    assert "overall" in coherence
    assert 0.0 <= float(coherence["overall"]) <= 100.0


def test_submission_stage_has_q1_readiness_dimension(
    service: ResearchPipelineBenchmarkService,
) -> None:
    score = service.calculate_stage_scores(
        {"text": "q1 readiness strong baseline statistical test comprehensive evaluation neurips"},
        "submission",
    )
    assert score > 0.0
