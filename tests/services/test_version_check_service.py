from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crane.services.version_check_service import Compatibility, VersionCheckService


def _write_pyproject(root: Path, content: str) -> None:
    (root / "pyproject.toml").write_text(content, encoding="utf-8")


class TestGetLocalVersion:
    def test_reads_valid_version_from_pyproject(self, tmp_path: Path):
        _write_pyproject(tmp_path, '[project]\nname = "crane"\nversion = "1.2.3"\n')
        service = VersionCheckService(tmp_path)
        assert service.get_local_version() == "1.2.3"

    def test_returns_unknown_when_pyproject_missing(self, tmp_path: Path):
        service = VersionCheckService(tmp_path)
        assert service.get_local_version() == "unknown"

    def test_returns_unknown_when_version_not_present(self, tmp_path: Path):
        _write_pyproject(tmp_path, '[project]\nname = "crane"\n')
        service = VersionCheckService(tmp_path)
        assert service.get_local_version() == "unknown"

    def test_reads_version_with_spaces(self, tmp_path: Path):
        _write_pyproject(tmp_path, '[project]\nname="crane"\nversion   =   "2.0.1"\n')
        service = VersionCheckService(tmp_path)
        assert service.get_local_version() == "2.0.1"

    def test_ignores_non_matching_key(self, tmp_path: Path):
        _write_pyproject(tmp_path, '[project]\nname = "crane"\napp_version = "9.9.9"\n')
        service = VersionCheckService(tmp_path)
        assert service.get_local_version() == "unknown"


class TestGetLatestVersion:
    def test_success_strips_v_prefix(self, tmp_path: Path):
        service = VersionCheckService(tmp_path)
        response = MagicMock(status_code=200)
        response.json.return_value = {"tag_name": "v1.4.0"}
        with patch("requests.get", return_value=response):
            assert service.get_latest_version() == "1.4.0"

    def test_success_without_v_prefix(self, tmp_path: Path):
        service = VersionCheckService(tmp_path)
        response = MagicMock(status_code=200)
        response.json.return_value = {"tag_name": "1.4.0"}
        with patch("requests.get", return_value=response):
            assert service.get_latest_version() == "1.4.0"

    def test_returns_empty_on_404(self, tmp_path: Path):
        service = VersionCheckService(tmp_path)
        response = MagicMock(status_code=404)
        with patch("requests.get", return_value=response):
            assert service.get_latest_version() == ""

    def test_returns_empty_when_tag_name_missing(self, tmp_path: Path):
        service = VersionCheckService(tmp_path)
        response = MagicMock(status_code=200)
        response.json.return_value = {}
        with patch("requests.get", return_value=response):
            assert service.get_latest_version() == ""

    def test_returns_empty_on_network_error(self, tmp_path: Path):
        service = VersionCheckService(tmp_path)
        with patch("requests.get", side_effect=Exception("network")):
            assert service.get_latest_version() == ""


class TestGetReleaseNotes:
    def test_returns_body_for_release(self, tmp_path: Path):
        service = VersionCheckService(tmp_path)
        response = MagicMock(status_code=200)
        response.json.return_value = {"body": "bug fixes"}
        with patch("requests.get", return_value=response):
            assert service.get_release_notes("1.2.0") == "bug fixes"

    def test_returns_empty_when_body_missing(self, tmp_path: Path):
        service = VersionCheckService(tmp_path)
        response = MagicMock(status_code=200)
        response.json.return_value = {}
        with patch("requests.get", return_value=response):
            assert service.get_release_notes("1.2.0") == ""

    def test_returns_empty_on_non_200(self, tmp_path: Path):
        service = VersionCheckService(tmp_path)
        response = MagicMock(status_code=500)
        with patch("requests.get", return_value=response):
            assert service.get_release_notes("1.2.0") == ""

    def test_returns_empty_on_exception(self, tmp_path: Path):
        service = VersionCheckService(tmp_path)
        with patch("requests.get", side_effect=Exception("boom")):
            assert service.get_release_notes("1.2.0") == ""


class TestGetGitStatus:
    def test_parses_ahead_behind_counts(self, tmp_path: Path):
        service = VersionCheckService(tmp_path)
        result = MagicMock(returncode=0, stdout="3 4\n")
        with patch("subprocess.run", return_value=result):
            assert service.get_git_status() == {"ahead": 3, "behind": 4}

    def test_returns_zeroes_on_nonzero_return(self, tmp_path: Path):
        service = VersionCheckService(tmp_path)
        result = MagicMock(returncode=1, stdout="", stderr="error")
        with patch("subprocess.run", return_value=result):
            assert service.get_git_status() == {"ahead": 0, "behind": 0}

    def test_returns_zeroes_on_malformed_output(self, tmp_path: Path):
        service = VersionCheckService(tmp_path)
        result = MagicMock(returncode=0, stdout="abc def\n")
        with patch("subprocess.run", return_value=result):
            assert service.get_git_status() == {"ahead": 0, "behind": 0}

    def test_returns_zeroes_on_subprocess_exception(self, tmp_path: Path):
        service = VersionCheckService(tmp_path)
        with patch("subprocess.run", side_effect=Exception("no git")):
            assert service.get_git_status() == {"ahead": 0, "behind": 0}


class TestCheckUpdate:
    def test_no_latest_version_returns_unknown_latest(self, tmp_path: Path):
        service = VersionCheckService(tmp_path)
        with (
            patch.object(service, "get_local_version", return_value="1.0.0"),
            patch.object(service, "get_latest_version", return_value=""),
            patch.object(service, "get_git_status", return_value={"ahead": 1, "behind": 2}),
        ):
            info = service.check_update()
        assert info.local_version == "1.0.0"
        assert info.latest_version == "unknown"
        assert info.update_type == "none"
        assert info.is_update_available is False
        assert info.commits_ahead == 1
        assert info.commits_behind == 2

    @pytest.mark.parametrize(
        ("local", "latest", "expected_type"),
        [
            ("1.0.0", "2.0.0", "major"),
            ("1.0.0", "1.1.0", "minor"),
            ("1.0.0", "1.0.1", "patch"),
            ("1.0.0", "1.0.0", "none"),
            ("unknown", "1.0.0", "none"),
        ],
    )
    def test_check_update_version_scenarios(
        self,
        tmp_path: Path,
        local: str,
        latest: str,
        expected_type: str,
    ):
        service = VersionCheckService(tmp_path)
        with (
            patch.object(service, "get_local_version", return_value=local),
            patch.object(service, "get_latest_version", return_value=latest),
            patch.object(service, "get_git_status", return_value={"ahead": 0, "behind": 0}),
            patch.object(service, "get_release_notes", return_value="release notes") as notes_mock,
        ):
            info = service.check_update()

        assert info.update_type == expected_type
        assert info.is_update_available is (expected_type != "none")
        if expected_type == "none":
            notes_mock.assert_not_called()
            assert info.release_notes == ""
        else:
            notes_mock.assert_called_once_with(latest)
            assert info.release_notes == "release notes"


class TestAssessCompatibility:
    @pytest.mark.parametrize(
        ("current", "target", "expected"),
        [
            (
                "unknown",
                "1.0.0",
                Compatibility(False, True, True, "high", "Cannot determine compatibility"),
            ),
            (
                "1.0.0",
                "unknown",
                Compatibility(False, True, True, "high", "Cannot determine compatibility"),
            ),
            (
                "bad",
                "1.0.0",
                Compatibility(False, True, True, "high", "Invalid version format"),
            ),
            (
                "1.0.0",
                "2.0.0",
                Compatibility(
                    True,
                    True,
                    True,
                    "high",
                    "Major version change (1.0.0 → 2.0.0). Review breaking changes before upgrading.",
                ),
            ),
            (
                "1.0.0",
                "1.1.0",
                Compatibility(
                    True,
                    False,
                    False,
                    "low",
                    "Minor version update (1.0.0 → 1.1.0). New features, backward compatible.",
                ),
            ),
            (
                "1.0.0",
                "1.0.1",
                Compatibility(
                    True,
                    False,
                    False,
                    "low",
                    "Patch update (1.0.0 → 1.0.1). Bug fixes and improvements.",
                ),
            ),
            (
                "1.1.1",
                "1.1.1",
                Compatibility(True, False, False, "low", "Already up to date"),
            ),
            (
                "2.0.0",
                "1.9.9",
                Compatibility(
                    True,
                    False,
                    False,
                    "low",
                    "Minor version update (2.0.0 → 1.9.9). New features, backward compatible.",
                ),
            ),
        ],
    )
    def test_assess_compatibility_cases(
        self,
        tmp_path: Path,
        current: str,
        target: str,
        expected: Compatibility,
    ):
        service = VersionCheckService(tmp_path)
        assert service.assess_compatibility(current, target) == expected


class TestCompareVersions:
    @pytest.mark.parametrize(
        ("current", "latest", "expected"),
        [
            ("1.0.0", "2.0.0", "major"),
            ("1.0.0", "1.2.0", "minor"),
            ("1.0.0", "1.0.1", "patch"),
            ("1.0.0", "1.0.0", "none"),
            ("1.2.3", "1.2.2", "none"),
            ("invalid", "1.0.0", "none"),
            ("1.0.0", "invalid", "none"),
            ("1.0", "1.0.1", "none"),
        ],
    )
    def test_compare_versions_cases(self, current: str, latest: str, expected: str):
        assert VersionCheckService._compare_versions(current, latest) == expected


class TestParseVersion:
    @pytest.mark.parametrize(
        ("version", "expected"),
        [
            ("1.2.3", (1, 2, 3)),
            ("0.0.1", (0, 0, 1)),
            ("12.34.56", (12, 34, 56)),
            ("1.2", None),
            ("1.2.3.4", (1, 2, 3)),
            ("v1.2.3", None),
            ("a.b.c", None),
            ("", None),
        ],
    )
    def test_parse_version_cases(self, version: str, expected: tuple[int, int, int] | None):
        assert VersionCheckService._parse_version(version) == expected


def test_get_git_status_handles_timeout(tmp_path: Path):
    service = VersionCheckService(tmp_path)
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=10)):
        assert service.get_git_status() == {"ahead": 0, "behind": 0}
