from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VersionInfo:
    local_version: str
    latest_version: str
    update_type: str
    is_update_available: bool
    release_notes: str
    commits_ahead: int
    commits_behind: int


@dataclass
class Compatibility:
    is_compatible: bool
    breaking_changes: bool
    migration_required: bool
    risk_level: str
    notes: str


class VersionCheckService:
    """Check CRANE version updates and compatibility."""

    REPO_URL = "https://github.com/AugustChaoTW/opencode-crane"
    API_URL = "https://api.github.com/repos/AugustChaoTW/opencode-crane"

    def __init__(self, crane_dir: str | Path | None = None):
        self.crane_dir = Path(crane_dir) if crane_dir else Path(__file__).resolve().parents[3]
        self.pyproject = self.crane_dir / "pyproject.toml"

    def get_local_version(self) -> str:
        """Read version from pyproject.toml."""
        if not self.pyproject.exists():
            return "unknown"
        content = self.pyproject.read_text(encoding="utf-8")
        match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
        return match.group(1) if match else "unknown"

    def get_latest_version(self) -> str:
        """Get latest release tag from GitHub API."""
        import requests

        try:
            resp = requests.get(
                f"{self.API_URL}/releases/latest",
                headers={"Accept": "application/vnd.github.v3+json"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("tag_name", "").lstrip("v")
        except Exception:
            pass
        return ""

    def get_release_notes(self, version: str) -> str:
        """Get release notes for a specific version."""
        import requests

        try:
            resp = requests.get(
                f"{self.API_URL}/releases/tags/v{version}",
                headers={"Accept": "application/vnd.github.v3+json"},
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json().get("body", "")
        except Exception:
            pass
        return ""

    def get_git_status(self) -> dict[str, int]:
        """Get commits ahead/behind remote."""
        try:
            result = subprocess.run(
                ["git", "rev-list", "--left-right", "--count", "HEAD...origin/main"],
                capture_output=True,
                text=True,
                cwd=str(self.crane_dir),
                timeout=10,
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                return {"ahead": int(parts[0]), "behind": int(parts[1])}
        except Exception:
            pass
        return {"ahead": 0, "behind": 0}

    def check_update(self) -> VersionInfo:
        """Compare local and remote versions."""
        local = self.get_local_version()
        latest = self.get_latest_version()
        git_status = self.get_git_status()

        if not latest:
            return VersionInfo(
                local_version=local,
                latest_version="unknown",
                update_type="none",
                is_update_available=False,
                release_notes="",
                commits_ahead=git_status["ahead"],
                commits_behind=git_status["behind"],
            )

        update_type = self._compare_versions(local, latest)
        notes = self.get_release_notes(latest) if update_type != "none" else ""

        return VersionInfo(
            local_version=local,
            latest_version=latest,
            update_type=update_type,
            is_update_available=update_type != "none",
            release_notes=notes,
            commits_ahead=git_status["ahead"],
            commits_behind=git_status["behind"],
        )

    def assess_compatibility(self, current: str, target: str) -> Compatibility:
        """Assess version compatibility."""
        if current == "unknown" or target == "unknown":
            return Compatibility(False, True, True, "high", "Cannot determine compatibility")

        curr_parts = self._parse_version(current)
        tgt_parts = self._parse_version(target)

        if not curr_parts or not tgt_parts:
            return Compatibility(False, True, True, "high", "Invalid version format")

        if tgt_parts[0] > curr_parts[0]:
            return Compatibility(
                True,
                True,
                True,
                "high",
                f"Major version change ({current} → {target}). Review breaking changes before upgrading.",
            )

        if tgt_parts[1] > curr_parts[1]:
            return Compatibility(
                True,
                False,
                False,
                "low",
                f"Minor version update ({current} → {target}). New features, backward compatible.",
            )

        if tgt_parts[2] > curr_parts[2]:
            return Compatibility(
                True,
                False,
                False,
                "low",
                f"Patch update ({current} → {target}). Bug fixes and improvements.",
            )

        return Compatibility(True, False, False, "low", "Already up to date")

    @staticmethod
    def _compare_versions(current: str, latest: str) -> str:
        """Compare two version strings. Return 'major'/'minor'/'patch'/'none'."""
        curr = VersionCheckService._parse_version(current)
        tgt = VersionCheckService._parse_version(latest)
        if not curr or not tgt:
            return "none"
        if tgt[0] > curr[0]:
            return "major"
        if tgt[1] > curr[1]:
            return "minor"
        if tgt[2] > curr[2]:
            return "patch"
        return "none"

    @staticmethod
    def _parse_version(version: str) -> tuple[int, int, int] | None:
        """Parse version string to tuple."""
        match = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
        if match:
            return int(match.group(1)), int(match.group(2)), int(match.group(3))
        return None
