from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crane.services.version_check_service import Compatibility, VersionInfo
from crane.tools.version_tools import register_tools


class _ToolCollector:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


@pytest.fixture
def version_tools() -> dict[str, object]:
    collector = _ToolCollector()
    register_tools(collector)
    return collector.tools


def _ok_result(stdout: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = 0
    result.stdout = stdout
    result.stderr = ""
    return result


class TestRegisterTools:
    def test_registers_all_version_tools(self):
        collector = _ToolCollector()
        register_tools(collector)
        assert "check_crane_version" in collector.tools
        assert "upgrade_crane" in collector.tools
        assert "rollback_crane" in collector.tools


class TestCheckCraneVersion:
    def test_returns_expected_payload(self, version_tools):
        info = VersionInfo("1.0.0", "1.1.0", "minor", True, "notes", 1, 2)
        compat = Compatibility(True, False, False, "low", "safe")
        mock_service = MagicMock()
        mock_service.check_update.return_value = info
        mock_service.assess_compatibility.return_value = compat

        with patch("crane.tools.version_tools.VersionCheckService", return_value=mock_service):
            result = version_tools["check_crane_version"](project_dir="/tmp/test")

        assert result["current_version"] == "1.0.0"
        assert result["latest_version"] == "1.1.0"
        assert result["update_type"] == "minor"
        assert result["is_update_available"] is True
        assert result["commits_ahead"] == 1
        assert result["commits_behind"] == 2
        assert result["compatibility"]["risk_level"] == "low"

    def test_truncates_release_notes_to_500(self, version_tools):
        info = VersionInfo("1.0.0", "1.1.0", "minor", True, "x" * 600, 0, 0)
        compat = Compatibility(True, False, False, "low", "safe")
        mock_service = MagicMock()
        mock_service.check_update.return_value = info
        mock_service.assess_compatibility.return_value = compat

        with patch("crane.tools.version_tools.VersionCheckService", return_value=mock_service):
            result = version_tools["check_crane_version"]()

        assert len(result["release_notes"]) == 500

    def test_uses_crane_dir_env_when_project_dir_missing(self, version_tools, monkeypatch):
        info = VersionInfo("1.0.0", "1.0.0", "none", False, "", 0, 0)
        compat = Compatibility(True, False, False, "low", "Already up to date")
        mock_service = MagicMock()
        mock_service.check_update.return_value = info
        mock_service.assess_compatibility.return_value = compat
        monkeypatch.setenv("CRANE_DIR", "/opt/crane")

        with patch(
            "crane.tools.version_tools.VersionCheckService", return_value=mock_service
        ) as cls:
            result = version_tools["check_crane_version"]()

        assert cls.call_args.args == ("/opt/crane",)
        assert result["is_update_available"] is False

    def test_handles_unknown_version_and_network_failure(self, version_tools):
        info = VersionInfo("unknown", "unknown", "none", False, "", 0, 0)
        compat = Compatibility(False, True, True, "high", "Cannot determine compatibility")
        mock_service = MagicMock()
        mock_service.check_update.return_value = info
        mock_service.assess_compatibility.return_value = compat

        with patch("crane.tools.version_tools.VersionCheckService", return_value=mock_service):
            result = version_tools["check_crane_version"]()

        assert result["current_version"] == "unknown"
        assert result["latest_version"] == "unknown"
        assert result["compatibility"]["breaking_changes"] is True


class TestUpgradeCrane:
    def test_success_path_with_verify(self, version_tools, tmp_project: Path):
        (tmp_project / "src").mkdir()
        (tmp_project / "scripts").mkdir()
        (tmp_project / "data").mkdir()
        (tmp_project / "pyproject.toml").write_text('version = "1.0.0"\n', encoding="utf-8")

        mock_service = MagicMock()
        mock_service.get_local_version.side_effect = ["1.0.0", "1.1.0"]
        mock_service.get_latest_version.return_value = "1.1.0"

        subprocess_results = [
            _ok_result(),
            _ok_result(),
            _ok_result("10 passed"),
        ]

        with (
            patch("crane.tools.version_tools.VersionCheckService", return_value=mock_service),
            patch("subprocess.run", side_effect=subprocess_results),
        ):
            result = version_tools["upgrade_crane"](
                project_dir=str(tmp_project), backup=True, verify=True
            )

        assert result["status"] == "success"
        assert result["from_version"] == "1.0.0"
        assert result["to_version"] == "1.1.0"
        step_names = [s["step"] for s in result["steps_completed"]]
        assert step_names == [
            "check",
            "target",
            "backup",
            "git_pull",
            "uv_sync",
            "verify",
            "confirm",
        ]

    def test_success_path_without_backup_or_verify(self, version_tools, tmp_project: Path):
        (tmp_project / "pyproject.toml").write_text('version = "1.0.0"\n', encoding="utf-8")
        mock_service = MagicMock()
        mock_service.get_local_version.side_effect = ["1.0.0", "1.0.1"]
        mock_service.get_latest_version.return_value = "1.0.1"

        with (
            patch("crane.tools.version_tools.VersionCheckService", return_value=mock_service),
            patch("subprocess.run", side_effect=[_ok_result(), _ok_result()]),
        ):
            result = version_tools["upgrade_crane"](
                project_dir=str(tmp_project), backup=False, verify=False
            )

        assert result["status"] == "success"
        step_names = [s["step"] for s in result["steps_completed"]]
        assert "backup" not in step_names
        assert "verify" not in step_names

    def test_errors_when_latest_version_unavailable(self, version_tools, tmp_project: Path):
        mock_service = MagicMock()
        mock_service.get_local_version.return_value = "1.0.0"
        mock_service.get_latest_version.return_value = ""

        with patch("crane.tools.version_tools.VersionCheckService", return_value=mock_service):
            result = version_tools["upgrade_crane"](
                project_dir=str(tmp_project), target_version="latest"
            )

        assert result == {"status": "error", "message": "Cannot fetch latest version from GitHub"}

    def test_git_pull_failure(self, version_tools, tmp_project: Path):
        mock_service = MagicMock()
        mock_service.get_local_version.return_value = "1.0.0"
        mock_service.get_latest_version.return_value = "1.0.1"

        failed = MagicMock(returncode=1, stderr="pull failed", stdout="")
        with (
            patch("crane.tools.version_tools.VersionCheckService", return_value=mock_service),
            patch("subprocess.run", return_value=failed),
        ):
            result = version_tools["upgrade_crane"](project_dir=str(tmp_project), backup=False)

        assert result["status"] == "error"
        assert result["step"] == "git_pull"
        assert "pull failed" in result["message"]

    def test_uv_sync_failure(self, version_tools, tmp_project: Path):
        mock_service = MagicMock()
        mock_service.get_local_version.return_value = "1.0.0"
        mock_service.get_latest_version.return_value = "1.0.1"

        ok = _ok_result()
        failed = MagicMock(returncode=2, stderr="uv failed", stdout="")
        with (
            patch("crane.tools.version_tools.VersionCheckService", return_value=mock_service),
            patch("subprocess.run", side_effect=[ok, failed]),
        ):
            result = version_tools["upgrade_crane"](project_dir=str(tmp_project), backup=False)

        assert result["status"] == "error"
        assert result["step"] == "uv_sync"

    def test_verify_step_warning_when_tests_fail(self, version_tools, tmp_project: Path):
        mock_service = MagicMock()
        mock_service.get_local_version.side_effect = ["1.0.0", "1.0.1"]
        mock_service.get_latest_version.return_value = "1.0.1"

        verify_fail = MagicMock(returncode=1, stdout="2 failed", stderr="")
        with (
            patch("crane.tools.version_tools.VersionCheckService", return_value=mock_service),
            patch("subprocess.run", side_effect=[_ok_result(), _ok_result(), verify_fail]),
        ):
            result = version_tools["upgrade_crane"](
                project_dir=str(tmp_project), backup=False, verify=True
            )

        verify_step = [s for s in result["steps_completed"] if s["step"] == "verify"][0]
        assert verify_step["status"] == "warning"

    def test_timeout_error(self, version_tools, tmp_project: Path):
        mock_service = MagicMock()
        mock_service.get_local_version.return_value = "1.0.0"
        mock_service.get_latest_version.return_value = "1.0.1"

        with (
            patch("crane.tools.version_tools.VersionCheckService", return_value=mock_service),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=60)),
        ):
            result = version_tools["upgrade_crane"](project_dir=str(tmp_project), backup=False)

        assert result["status"] == "error"
        assert result["step"] == "timeout"

    def test_unexpected_error_is_reported(self, version_tools, tmp_project: Path):
        with patch(
            "crane.tools.version_tools.VersionCheckService",
            side_effect=RuntimeError("init failed"),
        ):
            result = version_tools["upgrade_crane"](project_dir=str(tmp_project), backup=False)

        assert result["status"] == "error"
        assert result["step"] == "unexpected"


class TestRollbackCrane:
    def test_returns_error_when_no_arguments(self, version_tools, tmp_project: Path):
        result = version_tools["rollback_crane"](project_dir=str(tmp_project))
        assert result["status"] == "error"
        assert "Provide either" in result["message"]

    def test_returns_error_for_missing_backup(self, version_tools, tmp_project: Path):
        result = version_tools["rollback_crane"](
            project_dir=str(tmp_project),
            backup_path=str(tmp_project / "missing"),
        )
        assert result["status"] == "error"
        assert "Backup not found" in result["message"]

    def test_restores_from_backup_directory(self, version_tools, tmp_path: Path):
        crane_dir = tmp_path / "crane"
        backup = tmp_path / "backup"
        (crane_dir / "src").mkdir(parents=True)
        (crane_dir / "src" / "a.txt").write_text("new", encoding="utf-8")
        (backup / "src").mkdir(parents=True)
        (backup / "src" / "a.txt").write_text("old", encoding="utf-8")

        result = version_tools["rollback_crane"](
            project_dir=str(crane_dir),
            backup_path=str(backup),
        )

        assert result["status"] == "success"
        assert (crane_dir / "src" / "a.txt").read_text(encoding="utf-8") == "old"

    def test_restores_pyproject_from_backup(self, version_tools, tmp_path: Path):
        crane_dir = tmp_path / "crane"
        backup = tmp_path / "backup"
        crane_dir.mkdir()
        backup.mkdir()
        (crane_dir / "pyproject.toml").write_text('version = "9.9.9"\n', encoding="utf-8")
        (backup / "pyproject.toml").write_text('version = "1.0.0"\n', encoding="utf-8")

        result = version_tools["rollback_crane"](
            project_dir=str(crane_dir),
            backup_path=str(backup),
        )
        assert result["status"] == "success"
        assert "1.0.0" in (crane_dir / "pyproject.toml").read_text(encoding="utf-8")

    def test_rollback_from_git_tag_success(self, version_tools, tmp_project: Path):
        mock_service = MagicMock()
        mock_service.get_local_version.return_value = "0.9.0"

        with (
            patch("subprocess.run", side_effect=[_ok_result(), _ok_result()]),
            patch("crane.tools.version_tools.VersionCheckService", return_value=mock_service),
        ):
            result = version_tools["rollback_crane"](
                project_dir=str(tmp_project), to_version="v0.9.0"
            )

        assert result["status"] == "success"
        assert result["method"] == "git_checkout"
        assert result["version"] == "0.9.0"

    def test_rollback_from_git_tag_failure(self, version_tools, tmp_project: Path):
        failed = MagicMock(returncode=1, stderr="bad tag", stdout="")
        with patch("subprocess.run", return_value=failed):
            result = version_tools["rollback_crane"](
                project_dir=str(tmp_project), to_version="v0.9.0"
            )
        assert result["status"] == "error"
        assert "bad tag" in result["message"]

    def test_rollback_exception_is_reported(self, version_tools, tmp_project: Path):
        with patch("subprocess.run", side_effect=RuntimeError("boom")):
            result = version_tools["rollback_crane"](
                project_dir=str(tmp_project), to_version="v0.9.0"
            )
        assert result["status"] == "error"
        assert "boom" in result["message"]
