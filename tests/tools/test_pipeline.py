"""TDD tests for run_pipeline tool."""

from unittest.mock import MagicMock, patch

import pytest

from crane.tools.pipeline import register_tools


class _ToolCollector:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


@pytest.fixture
def pipe(self=None):
    collector = _ToolCollector()
    register_tools(collector)
    return collector.tools["run_pipeline"]


def _mock_subprocess_for_gh(mock_gh):
    def side_effect(cmd, **kwargs):
        m = MagicMock()
        m.returncode = 0
        m.stderr = ""
        cmd_str = " ".join(cmd[1:3]) if len(cmd) >= 3 else ""
        if "issue create" in cmd_str:
            m.stdout = "https://github.com/test/repo/issues/42\n"
        elif "issue list" in cmd_str:
            m.stdout = "[]"
        elif "label create" in cmd_str:
            m.stdout = ""
        elif cmd[0] == "git":
            if "remote" in cmd_str:
                m.stdout = "git@github.com:test/repo.git\n"
            elif "rev-parse --abbrev" in " ".join(cmd):
                m.stdout = "main\n"
            elif "log" in cmd_str:
                m.stdout = "abc123 test\n"
            elif "rev-parse --show" in " ".join(cmd):
                m.stdout = "/tmp/test\n"
            else:
                m.stdout = "\n"
        else:
            m.stdout = mock_gh.responses.get(cmd_str, "") + "\n"
        return m

    return side_effect


class TestRegistration:
    def test_registered(self):
        collector = _ToolCollector()
        register_tools(collector)
        assert "run_pipeline" in collector.tools


class TestDryRun:
    def test_dry_run_returns_planned_steps(self, pipe):
        result = pipe(pipeline="literature-review", topic="transformers", dry_run=True)
        assert result["status"] == "dry_run"
        assert result["pipeline"] == "literature-review"
        assert len(result["planned_steps"]) > 0
        assert "search" in result["planned_steps"]

    def test_dry_run_respects_skip_steps(self, pipe):
        result = pipe(
            pipeline="literature-review",
            topic="test",
            dry_run=True,
            skip_steps=["download", "annotate"],
        )
        assert "download" not in result["planned_steps"]
        assert "annotate" not in result["planned_steps"]
        assert "search" in result["planned_steps"]

    def test_dry_run_respects_stop_after(self, pipe):
        result = pipe(
            pipeline="literature-review",
            topic="test",
            dry_run=True,
            stop_after="search",
        )
        assert result["planned_steps"] == ["search"]

    def test_dry_run_no_side_effects(self, pipe, tmp_project):
        result = pipe(
            pipeline="literature-review",
            topic="test",
            dry_run=True,
            refs_dir=str(tmp_project / "references"),
        )
        assert result["artifacts_created"] == []


class TestInvalidPipeline:
    def test_unknown_pipeline_returns_error(self, pipe):
        result = pipe(pipeline="nonexistent", topic="test")
        assert result["status"] == "failed"
        assert "error" in result
        assert "nonexistent" in result["error"]


class TestLiteratureReviewPipeline:
    def _patch_all(self, mock_gh, mock_arxiv_xml):
        """Return a context manager patching subprocess + requests for lit review."""
        import contextlib

        @contextlib.contextmanager
        def patches():
            def mock_get(url, **kwargs):
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.raise_for_status = MagicMock()
                if "export.arxiv.org" in url:
                    # Search request - return XML
                    mock_response.text = mock_arxiv_xml
                    mock_response.content = mock_arxiv_xml.encode("utf-8")
                else:
                    # Download request - return PDF bytes
                    mock_response.text = ""
                    mock_response.content = b"%PDF-fake"
                return mock_response

            mock_pdf_reader = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Extracted paper text content."
            mock_pdf_reader.pages = [mock_page]

            with (
                patch(
                    "crane.utils.gh.subprocess.run",
                    side_effect=_mock_subprocess_for_gh(mock_gh),
                ),
                patch(
                    "crane.utils.git.subprocess.run",
                    side_effect=_mock_subprocess_for_gh(mock_gh),
                ),
                patch(
                    "crane.services.paper_service.requests.get",
                    side_effect=mock_get,
                ),
                patch(
                    "crane.services.paper_service.PyPDF2.PdfReader",
                    return_value=mock_pdf_reader,
                ),
            ):
                yield

        return patches()

    def test_full_pipeline_completes(self, pipe, tmp_project, mock_gh, mock_arxiv_response):
        refs = str(tmp_project / "references")
        with self._patch_all(mock_gh, mock_arxiv_response):
            result = pipe(
                pipeline="literature-review",
                topic="attention",
                max_papers=1,
                refs_dir=refs,
                project_dir=str(tmp_project),
            )

        assert result["status"] in ("completed", "stopped")
        assert "search" in result["completed_steps"]
        assert len(result["artifacts_created"]) > 0

    def test_stop_after_search(self, pipe, tmp_project, mock_gh, mock_arxiv_response):
        refs = str(tmp_project / "references")
        with self._patch_all(mock_gh, mock_arxiv_response):
            result = pipe(
                pipeline="literature-review",
                topic="attention",
                max_papers=1,
                stop_after="search",
                refs_dir=refs,
            )

        assert result["status"] == "stopped"
        assert result["completed_steps"] == ["search"]
        papers_dir = tmp_project / "references" / "papers"
        assert len(list(papers_dir.glob("*.yaml"))) == 0

    def test_skip_download_and_annotate(self, pipe, tmp_project, mock_gh, mock_arxiv_response):
        refs = str(tmp_project / "references")
        with self._patch_all(mock_gh, mock_arxiv_response):
            result = pipe(
                pipeline="literature-review",
                topic="attention",
                max_papers=1,
                skip_steps=["download", "read", "annotate"],
                refs_dir=refs,
                project_dir=str(tmp_project),
            )

        assert "download" not in result["completed_steps"]
        assert "read" not in result["completed_steps"]
        assert "annotate" not in result["completed_steps"]
        assert "add" in result["completed_steps"]

    def test_partial_failure_reports_error(self, pipe, tmp_project, mock_gh):
        refs = str(tmp_project / "references")
        bad_xml = "<feed></feed>"
        with self._patch_all(mock_gh, bad_xml):
            result = pipe(
                pipeline="literature-review",
                topic="attention",
                max_papers=1,
                refs_dir=refs,
            )

        assert result["status"] in ("failed", "completed")
        if result["status"] == "failed":
            assert result["failed_step"] is not None
            assert result["error"] != ""

    def test_result_has_next_recommended_action(
        self, pipe, tmp_project, mock_gh, mock_arxiv_response
    ):
        refs = str(tmp_project / "references")
        with self._patch_all(mock_gh, mock_arxiv_response):
            result = pipe(
                pipeline="literature-review",
                topic="attention",
                max_papers=1,
                stop_after="search",
                refs_dir=refs,
            )

        assert "next_recommended_action" in result
        assert result["next_recommended_action"] != ""


class TestFullSetupPipeline:
    def test_creates_labels_and_tasks(self, pipe, tmp_project, mock_gh):
        with (
            patch(
                "crane.utils.gh.subprocess.run",
                side_effect=_mock_subprocess_for_gh(mock_gh),
            ),
            patch(
                "crane.utils.git.subprocess.run",
                side_effect=_mock_subprocess_for_gh(mock_gh),
            ),
        ):
            result = pipe(
                pipeline="full-setup",
                project_dir=str(tmp_project),
                refs_dir=str(tmp_project / "references"),
            )

        assert result["status"] == "completed"
        assert "init" in result["completed_steps"]
        assert len(result["artifacts_created"]) > 0


class TestResultStructure:
    def test_result_keys_always_present(self, pipe):
        result = pipe(pipeline="literature-review", topic="test", dry_run=True)
        required_keys = [
            "pipeline",
            "status",
            "completed_steps",
            "artifacts_created",
            "planned_steps",
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_failed_result_has_error_fields(self, pipe):
        result = pipe(pipeline="bad-name", topic="test")
        assert "failed_step" in result
        assert "error" in result
        assert "next_recommended_action" in result
