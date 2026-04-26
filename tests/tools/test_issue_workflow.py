"""
TDD Test Cases for Issue Workflow (Feynman + Le Chun Review)

Tests the workflow: fetch closed issues → batch → dual analysis → verdict → write back

Run with:
  pytest tests/tools/test_issue_workflow.py -v
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def sample_closed_issues():
    return [
        {
            "number": 42,
            "title": "[P1] Fix authentication flow",
            "body": "## 背景\n登入 API 回傳 500 錯誤。\n\n## 重現步驟\n1. 呼叫 POST /auth/login\n2. 傳入有效 credentials\n3. 獲得 500 錯誤\n\n## 預期\n返回 200 + JWT token\n\n## 實際\n500 Internal Server Error",
            "state": "closed",
            "labels": ["bug", "backend"],
            "comments": [],
        },
        {
            "number": 43,
            "title": "[P2] Add caching layer",
            "body": "## 背景\n需快取減少 API 延遲。\n\n## 目標\n加入 Redis 快取層\n\n## 影響\n所有 GET 請求",
            "state": "closed",
            "labels": ["feature", "performance"],
            "comments": [],
        },
    ]


@pytest.fixture
def batch_config():
    return {
        "batch_size": 3,
        "group_by": "pipeline",
    }


class TestRunReview:
    @patch("subprocess.run")
    def test_generate_feynman_session_called(self, mock_run, sample_closed_issues):
        mock_run.return_value = MagicMock(
            stdout=json.dumps({"questions": ["Q1", "Q2", "Q3"]}),
            returncode=0,
        )

        from scripts.issue_workflow import run_review

        issue = sample_closed_issues[0]

        result = run_review.run_feynman_analysis(
            issue_body=issue["body"],
            paper_path="/fake/paper.tex",
        )

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "generate_feynman_session" in str(call_args)

    def test_le_chun_checks_applied(self):
        from scripts.issue_workflow import run_review

        issue_missing_repro = {
            "body": "## 背景\n系統壞了",
        }

        checks = run_review.le_chun_validate(issue_missing_repro)

        assert "reproducible_steps" in checks
        assert checks["reproducible_steps"] is False

    def test_le_chun_all_pass(self):
        from scripts.issue_workflow import run_review

        valid_issue = {
            "body": """## 背景
API 回傳錯誤

## 重現步驟
1. 呼叫 POST /auth
2. 獲得 500

## 預期
返回 200

## 實際
500 錯誤

## 量化差異
期望: 200, 實際: 500 (delta 300)

## 依賴
需要 Redis
"""
        }

        checks = run_review.le_chun_validate(valid_issue)

        assert all(checks.values())

    def test_pass_verdict(self):
        from scripts.issue_workflow import run_review

        feynman_result = {"verdict": "PASS", "questions": []}
        le_chun_result = {"verdict": "PASS"}

        verdict = run_review.compute_verdict(feynman_result, le_chun_result)

        assert verdict == "PASS"

    def test_needs_work_verdict_feynman(self):
        from scripts.issue_workflow import run_review

        feynman_result = {"verdict": "NEEDS_WORK", "questions": ["Why assumption holds?"]}
        le_chun_result = {"verdict": "PASS"}

        verdict = run_review.compute_verdict(feynman_result, le_chun_result)

        assert verdict == "NEEDS_WORK"

    def test_needs_work_verdict_le_chun(self):
        from scripts.issue_workflow import run_review

        feynman_result = {"verdict": "PASS"}
        le_chun_result = {"verdict": "NEEDS_WORK", "missing": ["reproducible_steps"]}

        verdict = run_review.compute_verdict(feynman_result, le_chun_result)

        assert verdict == "NEEDS_WORK"


class TestGhIntegration:
    @patch("subprocess.run")
    def test_gh_comment_called(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        from scripts.issue_workflow import gh_integration

        gh_integration.post_comment(
            issue_number=42,
            body="## Feynman 審查報告\n### 結論: PASS",
        )

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "issue" in call_args
        assert "comment" in call_args

    @patch("subprocess.run")
    def test_gh_reopen_called_on_needs_work(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        from scripts.issue_workflow import gh_integration

        gh_integration.reopen_if_needed(issue_number=42, verdict="NEEDS_WORK")

        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert "reopen" in call_args

    @patch("subprocess.run")
    def test_dry_run_skips_gh_calls(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        from scripts.issue_workflow import gh_integration

        gh_integration.post_comment(
            issue_number=42,
            body="test",
            dry_run=True,
        )

        assert not mock_run.called


class TestPromptTemplate:
    def test_variable_substitution(self):
        from scripts.issue_workflow import prompt_template

        template = "{{issue_body}}|{{issue_number}}|{{paper_path}}"
        variables = {
            "issue_body": "test body",
            "issue_number": "42",
            "paper_path": "/fake/paper.tex",
        }

        result = prompt_template.substitute(template, variables)

        assert "test body" in result
        assert "42" in result
        assert "/fake/paper.tex" in result

    def test_missing_variable_raises(self):
        from scripts.issue_workflow import prompt_template

        template = "{{issue_body}}|{{missing}}"

        with pytest.raises(ValueError):
            prompt_template.substitute(template, {"issue_body": "test"})


class TestIntegration:
    @patch("subprocess.run")
    def test_full_flow_mocked(self, mock_run, sample_closed_issues, tmp_path):
        mock_run.return_value = MagicMock(
            stdout=json.dumps(sample_closed_issues),
            returncode=0,
        )

        from scripts.issue_workflow import orchestrator, run_review, gh_integration

        issues = orchestrator.fetch_closed_issues(label="to-review")
        groups = orchestrator.group_issues(issues, batch_size=2)

        feynman = run_review.run_feynman_analysis(groups[0][0]["body"])
        le_chun = run_review.le_chun_validate(groups[0][0])

        verdict = run_review.compute_verdict(feynman, le_chun)

        gh_integration.post_comment(
            issue_number=groups[0][0]["number"],
            body=f"## 審查結論: {verdict}",
            dry_run=True,
        )

        assert len(issues) == 2
        assert len(groups) == 1
        assert verdict in ["PASS", "NEEDS_WORK"]

    def test_review_log_created(self, tmp_path):
        from scripts.issue_workflow import run_review

        log_entry = {
            "issue_number": 42,
            "verdict": "PASS",
            "feynman_questions": ["Q1", "Q2"],
            "le_chun_checks": {
                "reproducible_steps": True,
                "quantified_metrics": True,
            },
            "reasoning": "All checks passed",
        }

        output_file = tmp_path / "review_log.json"

        run_review.write_log([log_entry], output_file)

        assert output_file.exists()
        loaded = json.loads(output_file.read_text())
        assert loaded[0]["verdict"] == "PASS"


@pytest.fixture(autouse=True)
def setup_scripts_import():
    import sys
    script_dir = str(Path(__file__).parent.parent / "scripts")
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)