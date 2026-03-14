"""
TDD tests for gh CLI subprocess wrapper.
RED phase: define expected behavior before implementation.
"""

import json
from unittest.mock import patch, MagicMock

import pytest

from crane.utils.gh import gh, gh_json


class TestGhCommand:
    """Basic gh CLI execution."""

    def test_gh_returns_stdout(self):
        mock_result = MagicMock()
        mock_result.stdout = "output text\n"
        mock_result.returncode = 0
        with patch("crane.utils.gh.subprocess.run", return_value=mock_result) as mock_run:
            result = gh(["issue", "list"])
            mock_run.assert_called_once_with(
                ["gh", "issue", "list"],
                capture_output=True,
                text=True,
                check=True,
            )
            assert result == "output text"

    def test_gh_strips_whitespace(self):
        mock_result = MagicMock()
        mock_result.stdout = "  trimmed  \n"
        with patch("crane.utils.gh.subprocess.run", return_value=mock_result):
            assert gh(["version"]) == "trimmed"

    def test_gh_raises_on_failure(self):
        import subprocess

        with patch(
            "crane.utils.gh.subprocess.run", side_effect=subprocess.CalledProcessError(1, "gh")
        ):
            with pytest.raises(subprocess.CalledProcessError):
                gh(["bad", "command"])


class TestGhJson:
    """gh commands that return JSON."""

    def test_gh_json_parses_dict(self):
        mock_result = MagicMock()
        mock_result.stdout = json.dumps({"number": 1, "title": "Test"})
        with patch("crane.utils.gh.subprocess.run", return_value=mock_result):
            result = gh_json(["issue", "view", "1", "--json", "number,title"])
            assert result["number"] == 1
            assert result["title"] == "Test"

    def test_gh_json_parses_list(self):
        mock_result = MagicMock()
        mock_result.stdout = json.dumps([{"number": 1}, {"number": 2}])
        with patch("crane.utils.gh.subprocess.run", return_value=mock_result):
            result = gh_json(["issue", "list", "--json", "number"])
            assert len(result) == 2

    def test_gh_json_empty_returns_dict(self):
        mock_result = MagicMock()
        mock_result.stdout = ""
        with patch("crane.utils.gh.subprocess.run", return_value=mock_result):
            result = gh_json(["issue", "list"])
            assert result == {}
