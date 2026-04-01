"""測試 SubmissionPipelineService — 投稿前檢查流程"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from crane.services.submission_pipeline_service import SubmissionPipelineService


@pytest.fixture
def temp_project_with_paper():
    """建立臨時專案與論文結構"""
    import subprocess

    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        subprocess.run(["git", "init"], cwd=repo, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True
        )
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)

        papers_dir = repo / "papers" / "TEST"
        papers_dir.mkdir(parents=True)

        paper_path = papers_dir / "TEST-MAIN.tex"
        paper_path.write_text(
            r"""
\documentclass{article}
\usepackage{amsmath}

\title{Test Paper}
\author{Test Author}

\begin{document}

\section{Introduction}
This is the introduction. We propose a novel approach.

\section{Methodology}
\begin{equation}
x = y + z
\end{equation}

\section{Evaluation}
We compared with baseline methods. The results show improvements.

\section{Limitations}
The approach has limitations in scalability.

\end{document}
""",
            encoding="utf-8",
        )

        references_dir = repo / "references"
        references_dir.mkdir()
        (references_dir / "papers").mkdir()
        (references_dir / "pdfs").mkdir()

        paper_yaml = references_dir / "papers" / "test2020-example.yaml"
        paper_yaml.write_text(
            """
key: test2020-example
title: Example Paper
authors:
  - Test Author
year: 2020
doi: "10.1234/example"
url: "https://example.com/paper"
pdf_url: "https://example.com/paper.pdf"
""",
            encoding="utf-8",
        )

        data_dir = repo / "data"
        data_dir.mkdir()
        (data_dir / "results.csv").write_text(
            "metric,value\naccuracy,0.95\nprecision,0.92\n",
            encoding="utf-8",
        )

        yield repo, str(paper_path)


def test_detect_submission_run_version_initial(temp_project_with_paper):
    """測試初始版本號檢測"""
    repo, _ = temp_project_with_paper
    svc = SubmissionPipelineService(repo)

    version = svc.detect_submission_run_version()
    assert version == 1


def test_detect_submission_run_version_increment(temp_project_with_paper):
    """測試版本號遞增"""
    repo, _ = temp_project_with_paper
    svc = SubmissionPipelineService(repo)

    (repo / "BEFORE_SUBMISSION_RUN1").mkdir()
    (repo / "BEFORE_SUBMISSION_RUN2").mkdir()

    version = svc.detect_submission_run_version()
    assert version == 3


def test_create_submission_workspace(temp_project_with_paper):
    """測試創建投稿工作區"""
    repo, _ = temp_project_with_paper
    svc = SubmissionPipelineService(repo)

    workspace, version = svc.create_submission_workspace()

    assert workspace.exists()
    assert version == 1
    assert workspace.name == "BEFORE_SUBMISSION_RUN1"
    assert (workspace / "reports").exists()
    assert (workspace / "references").exists()


def test_generate_literature_review(temp_project_with_paper):
    """測試文獻回顧報告生成"""
    repo, _ = temp_project_with_paper
    svc = SubmissionPipelineService(repo)

    workspace, _ = svc.create_submission_workspace()
    result = svc.generate_literature_review(workspace)

    assert "file" in result
    assert "reference_count" in result
    assert result["reference_count"] >= 1

    report_path = Path(result["file"])
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "文獻回顧" in content


def test_generate_literature_review_includes_ai_annotation_summary(temp_project_with_paper):
    repo, _ = temp_project_with_paper
    paper_yaml = repo / "references" / "papers" / "test2020-example.yaml"
    paper_yaml.write_text(
        """
key: test2020-example
title: Example Paper
authors:
  - Test Author
year: 2020
ai_annotations:
  summary: "Annotation summary"
  key_contributions:
    - "Contribution A"
""",
        encoding="utf-8",
    )

    svc = SubmissionPipelineService(repo)
    workspace, _ = svc.create_submission_workspace()
    result = svc.generate_literature_review(workspace)

    report_path = Path(result["file"])
    content = report_path.read_text(encoding="utf-8")
    assert "AI 註解摘要" in content
    assert "Annotation summary" in content
    assert result["annotated_references"] == 1


def test_generate_experiment_results(temp_project_with_paper):
    """測試實驗結果報告生成"""
    repo, _ = temp_project_with_paper
    svc = SubmissionPipelineService(repo)

    workspace, _ = svc.create_submission_workspace()
    result = svc.generate_experiment_results(workspace)

    assert "file" in result
    assert "experiment_count" in result

    report_path = Path(result["file"])
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "實驗結果彙總" in content


def test_generate_framing_analysis(temp_project_with_paper):
    """測試 FRAMING 分析報告生成"""
    repo, paper_path = temp_project_with_paper
    svc = SubmissionPipelineService(repo)

    workspace, _ = svc.create_submission_workspace()
    result = svc.generate_framing_analysis(paper_path, workspace)

    assert "file" in result
    assert "total_issues" in result

    report_path = Path(result["file"])
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "Framing 分析" in content


def test_generate_paper_health_check(temp_project_with_paper):
    """測試論文健康檢查報告生成"""
    repo, paper_path = temp_project_with_paper
    svc = SubmissionPipelineService(repo)

    workspace, _ = svc.create_submission_workspace()
    result = svc.generate_paper_health_check(paper_path, workspace)

    assert "file" in result
    assert "overall_score" in result
    assert "readiness" in result

    report_path = Path(result["file"])
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "投稿前健康檢查報告" in content


def test_run_full_check(temp_project_with_paper):
    """測試完整的投稿前檢查流程"""
    repo, paper_path = temp_project_with_paper
    svc = SubmissionPipelineService(repo)

    result = svc.run_full_check(paper_path)

    assert result.status == "completed"
    assert result.version == 1
    assert Path(result.submission_dir).exists()
    assert len(result.checkpoints) == 4
    assert "literature" in result.reports
    assert "experiments" in result.reports
    assert "framing" in result.reports
    assert "health" in result.reports


def test_run_full_check_multiple_versions(temp_project_with_paper):
    """測試多版本管理"""
    repo, paper_path = temp_project_with_paper
    svc = SubmissionPipelineService(repo)

    result1 = svc.run_full_check(paper_path)
    assert result1.version == 1

    svc2 = SubmissionPipelineService(repo)
    result2 = svc2.run_full_check(paper_path)
    assert result2.version == 2
    assert result1.submission_dir != result2.submission_dir


def test_invalid_paper_path():
    """測試無效的論文路徑"""
    with tempfile.TemporaryDirectory() as tmpdir:
        svc = SubmissionPipelineService(tmpdir)

        result = svc.run_full_check("/nonexistent/paper.tex")

        assert result.status == "failed"
        assert result.error != ""
