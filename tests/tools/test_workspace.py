import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from crane.server import mcp  # pyright: ignore[reportMissingImports]
from crane.tools.workspace import register_tools  # pyright: ignore[reportMissingImports]
from crane.workspace import WorkspaceContext  # pyright: ignore[reportMissingImports]


class _ToolCollector:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


def _gh_run(cmd, **kwargs):
    cmd_str = " ".join(cmd)
    result = MagicMock()
    result.returncode = 0
    result.stderr = ""

    if "issue list" in cmd_str and "--label kind:task" in cmd_str:
        result.stdout = json.dumps(
            [
                {
                    "number": 11,
                    "title": "Draft experiment plan",
                    "url": "https://github.com/test/repo/issues/11",
                    "labels": [{"name": "kind:task"}, {"name": "phase:experiment"}],
                    "milestone": {"title": "Phase 3: Experiment"},
                }
            ]
        )
    elif "issue list" in cmd_str and "--label kind:todo" in cmd_str:
        result.stdout = json.dumps(
            [
                {
                    "number": 12,
                    "title": "Read appendix",
                    "url": "https://github.com/test/repo/issues/12",
                    "labels": [{"name": "kind:todo"}],
                    "milestone": None,
                }
            ]
        )
    elif "api repos/testuser/test-research/milestones?state=all" in cmd_str:
        result.stdout = json.dumps(
            [
                {
                    "title": "Phase 1: Literature Review",
                    "open_issues": 2,
                    "closed_issues": 3,
                }
            ]
        )
    else:
        result.stdout = "[]"

    return result


def _workspace_context(tmp_project: Path) -> WorkspaceContext:
    return WorkspaceContext(
        project_root=str(tmp_project),
        owner="testuser",
        repo="test-research",
        references_dir=str(tmp_project / "references"),
    )


def test_workspace_status_registered():
    collector = _ToolCollector()
    register_tools(collector)

    assert "workspace_status" in collector.tools


def test_workspace_status_registered_in_server():
    tools = mcp._tool_manager._tools if hasattr(mcp, "_tool_manager") else {}
    assert "workspace_status" in tools


def test_workspace_status_returns_workspace_overview(tmp_project):
    collector = _ToolCollector()
    register_tools(collector)

    papers_dir = tmp_project / "references" / "papers"
    (papers_dir / "paper-one.yaml").write_text("key: paper-one\n", encoding="utf-8")
    (papers_dir / "paper-two.yaml").write_text("key: paper-two\n", encoding="utf-8")
    pdfs_dir = tmp_project / "references" / "pdfs"
    (pdfs_dir / "paper-one.pdf").write_bytes(b"%PDF-1.4")
    (pdfs_dir / "paper-two.pdf").write_bytes(b"%PDF-1.4")

    with (
        patch(
            "crane.tools.workspace.resolve_workspace", return_value=_workspace_context(tmp_project)
        ),
        patch(
            "crane.services.task_service.get_owner_repo", return_value=("testuser", "test-research")
        ),
        patch("crane.utils.gh.subprocess.run", side_effect=_gh_run),
    ):
        status = collector.tools["workspace_status"](project_dir=str(tmp_project))

    assert status["workspace"] == {
        "project_root": str(tmp_project),
        "repo": "testuser/test-research",
        "references_dir": str(tmp_project / "references"),
    }
    assert status["references"] == {"papers": 2, "pdfs": 2, "bibliography": True}
    assert status["tasks"] == [
        {
            "number": 11,
            "title": "Draft experiment plan",
            "url": "https://github.com/test/repo/issues/11",
            "milestone": "Phase 3: Experiment",
            "labels": ["kind:task", "phase:experiment"],
        }
    ]
    assert status["todos"] == [
        {
            "number": 12,
            "title": "Read appendix",
            "url": "https://github.com/test/repo/issues/12",
            "milestone": "",
            "labels": ["kind:todo"],
        }
    ]
    assert status["milestones"] == [
        {
            "title": "Phase 1: Literature Review",
            "open": 2,
            "closed": 3,
            "progress": 60.0,
        }
    ]


def test_workspace_status_auto_detects_workspace(tmp_project):
    collector = _ToolCollector()
    register_tools(collector)

    with (
        patch(
            "crane.tools.workspace.resolve_workspace", return_value=_workspace_context(tmp_project)
        ) as mock_resolve,
        patch(
            "crane.services.task_service.get_owner_repo", return_value=("testuser", "test-research")
        ),
        patch("crane.utils.gh.subprocess.run", side_effect=_gh_run),
    ):
        collector.tools["workspace_status"]()

    assert mock_resolve.call_args.args == (None,)


def test_workspace_status_uses_kind_labels_for_issue_queries(tmp_project):
    collector = _ToolCollector()
    register_tools(collector)
    calls: list[list[str]] = []

    def _recording_run(cmd, **kwargs):
        calls.append(cmd)
        return _gh_run(cmd, **kwargs)

    with (
        patch(
            "crane.tools.workspace.resolve_workspace", return_value=_workspace_context(tmp_project)
        ),
        patch(
            "crane.services.task_service.get_owner_repo", return_value=("testuser", "test-research")
        ),
        patch("crane.utils.gh.subprocess.run", side_effect=_recording_run),
    ):
        collector.tools["workspace_status"](project_dir=str(tmp_project))

    commands = [" ".join(cmd) for cmd in calls]
    assert any("issue list --state open --label kind:task" in cmd for cmd in commands)
    assert any("issue list --state open --label kind:todo" in cmd for cmd in commands)
