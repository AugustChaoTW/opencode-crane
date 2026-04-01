"""測試 submission_check MCP 工具"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from crane.tools.submission_check import register_tools


class MockMCP:
    """模擬 MCP server"""

    def __init__(self):
        self.tools = {}

    def tool(self):
        """裝飾器：註冊工具"""

        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator

    def get_tool(self, name):
        """取得已註冊的工具"""
        return self.tools.get(name)


@pytest.fixture
def mock_mcp_server():
    """建立模擬 MCP server"""
    mcp = MockMCP()
    register_tools(mcp)
    return mcp


@pytest.fixture
def temp_project_with_paper():
    """建立臨時專案與論文"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)

        papers_dir = repo / "papers" / "TEST"
        papers_dir.mkdir(parents=True)

        paper_path = papers_dir / "TEST-MAIN.tex"
        paper_path.write_text(
            r"""
\documentclass{article}
\title{Test Paper}
\begin{document}
\section{Introduction}
Novel approach proposed.
\end{document}
""",
            encoding="utf-8",
        )

        references_dir = repo / "references"
        references_dir.mkdir()
        (references_dir / "papers").mkdir()
        (references_dir / "pdfs").mkdir()

        data_dir = repo / "data"
        data_dir.mkdir()
        (data_dir / "results.csv").write_text(
            "metric,value\naccuracy,0.95\n",
            encoding="utf-8",
        )

        yield repo


def test_run_submission_check_registered(mock_mcp_server):
    """測試工具是否已註冊"""
    assert "run_submission_check" in mock_mcp_server.tools
    tool = mock_mcp_server.get_tool("run_submission_check")
    assert tool is not None
    assert callable(tool)


def test_run_submission_check_with_explicit_paths(mock_mcp_server, temp_project_with_paper):
    """測試顯式提供論文路徑的檢查"""
    repo = temp_project_with_paper
    paper_path = repo / "papers" / "TEST" / "TEST-MAIN.tex"

    tool = mock_mcp_server.get_tool("run_submission_check")
    result = tool(
        paper_path=str(paper_path),
        project_dir=str(repo),
    )

    assert result["status"] == "completed"
    assert result["version"] == 1
    assert "submission_dir" in result
    assert "checkpoints" in result
    assert "reports" in result
    assert len(result["checkpoints"]) == 4


def test_run_submission_check_auto_detect_paper(mock_mcp_server, temp_project_with_paper):
    """測試自動偵測論文路徑"""
    repo = temp_project_with_paper

    tool = mock_mcp_server.get_tool("run_submission_check")
    result = tool(paper_path="", project_dir=str(repo))

    assert result["status"] == "completed"
    assert result["version"] == 1
    assert Path(result["submission_dir"]).exists()


def test_run_submission_check_default_project_dir(mock_project_dir):
    """測試預設專案目錄"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)

        papers_dir = repo / "papers" / "TEST"
        papers_dir.mkdir(parents=True)

        paper_path = papers_dir / "TEST-MAIN.tex"
        paper_path.write_text(r"\documentclass{article}\begin{document}\end{document}")

        references_dir = repo / "references"
        references_dir.mkdir()
        (references_dir / "papers").mkdir()
        (references_dir / "pdfs").mkdir()

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(repo)

            mcp = MockMCP()
            register_tools(mcp)
            tool = mcp.get_tool("run_submission_check")

            result = tool(paper_path=str(paper_path))

            assert result["status"] == "completed"
        finally:
            os.chdir(original_cwd)


def test_run_submission_check_missing_papers_dir(mock_mcp_server):
    """測試缺失 papers 目錄"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = mock_mcp_server.get_tool("run_submission_check")
        result = tool(paper_path="", project_dir=tmpdir)

        assert result["status"] == "failed"
        assert "error" in result
        assert "papers" in result["error"].lower()


def test_run_submission_check_invalid_paper_path(mock_mcp_server, temp_project_with_paper):
    """測試無效論文路徑"""
    repo = temp_project_with_paper

    tool = mock_mcp_server.get_tool("run_submission_check")
    result = tool(
        paper_path="/nonexistent/paper.tex",
        project_dir=str(repo),
    )

    assert result["status"] == "failed"
    assert "error" in result


def test_submission_check_report_structure(mock_mcp_server, temp_project_with_paper):
    """測試報告結構完整性"""
    repo = temp_project_with_paper
    paper_path = repo / "papers" / "TEST" / "TEST-MAIN.tex"

    tool = mock_mcp_server.get_tool("run_submission_check")
    result = tool(
        paper_path=str(paper_path),
        project_dir=str(repo),
    )

    assert result["status"] == "completed"

    reports = result["reports"]
    assert "literature" in reports
    assert "experiments" in reports
    assert "framing" in reports
    assert "health" in reports

    for key, report in reports.items():
        assert "file" in report


def test_submission_check_version_increment(mock_mcp_server, temp_project_with_paper):
    """測試版本號遞增"""
    repo = temp_project_with_paper
    paper_path = repo / "papers" / "TEST" / "TEST-MAIN.tex"

    tool = mock_mcp_server.get_tool("run_submission_check")

    result1 = tool(paper_path=str(paper_path), project_dir=str(repo))
    assert result1["version"] == 1

    result2 = tool(paper_path=str(paper_path), project_dir=str(repo))
    assert result2["version"] == 2

    assert result1["submission_dir"] != result2["submission_dir"]


@pytest.fixture
def mock_project_dir():
    """建立模擬專案目錄"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir
