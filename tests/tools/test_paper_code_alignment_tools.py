# pyright: reportMissingImports=false

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from crane.tools.paper_code_alignment import register_tools
from crane.workspace import WorkspaceContext


class _ToolCollector:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


@pytest.fixture
def alignment_tools():
    collector = _ToolCollector()
    register_tools(collector)
    return collector.tools


def _workspace_context(tmp_project: Path) -> WorkspaceContext:
    return WorkspaceContext(
        project_root=str(tmp_project),
        owner="testowner",
        repo="testrepo",
        references_dir=str(tmp_project / "references"),
    )


def test_verify_paper_code_alignment_registered(alignment_tools) -> None:
    assert "verify_paper_code_alignment" in alignment_tools


def test_verify_paper_code_alignment_requires_inputs(alignment_tools) -> None:
    tool = alignment_tools["verify_paper_code_alignment"]

    with pytest.raises(ValueError):
        tool(paper_path="", code_path="src")

    with pytest.raises(ValueError):
        tool(paper_path="paper.tex", code_path="")


def test_verify_paper_code_alignment_invokes_service_with_resolved_paths(
    alignment_tools, tmp_path: Path
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "references").mkdir()

    report = {
        "aligned": True,
        "matches": [],
        "mismatches": [],
        "alignment_score": 1.0,
    }

    with (
        patch(
            "crane.tools.paper_code_alignment.resolve_workspace",
            return_value=_workspace_context(project),
        ),
        patch(
            "crane.tools.paper_code_alignment.PaperCodeAlignmentService.generate_alignment_report",
            return_value=report,
        ) as mock_report,
    ):
        result = alignment_tools["verify_paper_code_alignment"](
            paper_path="papers/main.tex",
            code_path="src/train.py",
            project_dir=str(project),
        )

    assert result["aligned"] is True
    assert mock_report.call_args.kwargs["latex_path"] == str(project / "papers" / "main.tex")
    assert mock_report.call_args.kwargs["code_path"] == str(project / "src" / "train.py")


def test_verify_paper_code_alignment_uses_custom_relative_refs_dir(
    alignment_tools, tmp_path: Path
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "artifacts").mkdir()

    with (
        patch(
            "crane.tools.paper_code_alignment.resolve_workspace",
            return_value=_workspace_context(project),
        ),
        patch(
            "crane.tools.paper_code_alignment.PaperCodeAlignmentService.__init__",
            return_value=None,
        ) as mock_init,
        patch(
            "crane.tools.paper_code_alignment.PaperCodeAlignmentService.generate_alignment_report",
            return_value={
                "aligned": False,
                "matches": [],
                "mismatches": [],
                "alignment_score": 0.0,
            },
        ),
    ):
        alignment_tools["verify_paper_code_alignment"](
            paper_path="paper.tex",
            code_path="code.py",
            refs_dir="artifacts/refs",
            project_dir=str(project),
        )

    assert mock_init.call_args.args == (str(project / "artifacts" / "refs"),)


def test_verify_paper_code_alignment_keeps_absolute_paths(alignment_tools, tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    paper = tmp_path / "absolute.tex"
    code = tmp_path / "absolute.py"

    with (
        patch(
            "crane.tools.paper_code_alignment.resolve_workspace",
            return_value=_workspace_context(project),
        ),
        patch(
            "crane.tools.paper_code_alignment.PaperCodeAlignmentService.generate_alignment_report",
            return_value={
                "aligned": True,
                "matches": [],
                "mismatches": [],
                "alignment_score": 1.0,
            },
        ) as mock_report,
    ):
        alignment_tools["verify_paper_code_alignment"](
            paper_path=str(paper),
            code_path=str(code),
            project_dir=str(project),
        )

    assert mock_report.call_args.kwargs["latex_path"] == str(paper)
    assert mock_report.call_args.kwargs["code_path"] == str(code)
