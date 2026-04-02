from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from crane.services.version_check_service import VersionCheckService


def register_tools(mcp):
    """Register version management tools with the MCP server."""

    @mcp.tool()
    def check_crane_version(
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Check if CRANE has available updates.

        Returns:
        - current_version: Local version string
        - latest_version: Latest release version
        - update_type: major/minor/patch/none
        - is_update_available: bool
        - release_notes: Release notes summary
        - compatibility: Compatibility assessment
        - upgrade_command: Command to run for upgrade
        """
        crane_dir = project_dir or os.environ.get("CRANE_DIR")
        service = VersionCheckService(crane_dir)
        info = service.check_update()
        compat = service.assess_compatibility(info.local_version, info.latest_version)

        return {
            "current_version": info.local_version,
            "latest_version": info.latest_version,
            "update_type": info.update_type,
            "is_update_available": info.is_update_available,
            "release_notes": info.release_notes[:500] if info.release_notes else "",
            "commits_ahead": info.commits_ahead,
            "commits_behind": info.commits_behind,
            "compatibility": {
                "is_compatible": compat.is_compatible,
                "breaking_changes": compat.breaking_changes,
                "migration_required": compat.migration_required,
                "risk_level": compat.risk_level,
                "notes": compat.notes,
            },
            "upgrade_command": "cd ~/.opencode-crane && git pull && uv sync",
        }

    @mcp.tool()
    def upgrade_crane(
        target_version: str = "latest",
        backup: bool = True,
        verify: bool = True,
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Upgrade CRANE to specified version.

        Process:
        1. Backup current version
        2. Git pull/checkout
        3. uv sync
        4. Run verification tests

        Args:
            target_version: Version to upgrade to (default: latest)
            backup: Create backup before upgrade
            verify: Run tests after upgrade
        """
        crane_dir = Path(project_dir) if project_dir else Path(__file__).resolve().parents[3]
        backup_dir = crane_dir / "backups"
        steps: list[dict[str, Any]] = []

        try:
            service = VersionCheckService(crane_dir)
            current = service.get_local_version()
            steps.append({"step": "check", "status": "ok", "version": current})

            if target_version == "latest":
                target = service.get_latest_version()
                if not target:
                    return {"status": "error", "message": "Cannot fetch latest version from GitHub"}
            else:
                target = target_version.lstrip("v")

            steps.append({"step": "target", "status": "ok", "version": target})

            if backup:
                import datetime
                import shutil

                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = backup_dir / f"crane_{ts}"
                backup_dir.mkdir(parents=True, exist_ok=True)
                for subdir in ["src", "data", "scripts", "pyproject.toml"]:
                    src = crane_dir / subdir
                    if src.exists():
                        dst = backup_path / subdir
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        if src.is_dir():
                            shutil.copytree(src, dst, dirs_exist_ok=True)
                        else:
                            shutil.copy2(src, dst)
                steps.append({"step": "backup", "status": "ok", "path": str(backup_path)})

            result = subprocess.run(
                ["git", "pull", "origin", "main"],
                capture_output=True,
                text=True,
                cwd=str(crane_dir),
                timeout=60,
            )
            if result.returncode != 0:
                return {
                    "status": "error",
                    "step": "git_pull",
                    "message": result.stderr,
                    "steps_completed": steps,
                }
            steps.append({"step": "git_pull", "status": "ok"})

            result = subprocess.run(
                ["uv", "sync"],
                capture_output=True,
                text=True,
                cwd=str(crane_dir),
                timeout=120,
            )
            if result.returncode != 0:
                return {
                    "status": "error",
                    "step": "uv_sync",
                    "message": result.stderr,
                    "steps_completed": steps,
                }
            steps.append({"step": "uv_sync", "status": "ok"})

            if verify:
                result = subprocess.run(
                    [
                        "uv",
                        "run",
                        "pytest",
                        "tests/services/test_version_check_service.py",
                        "-q",
                        "--tb=no",
                    ],
                    capture_output=True,
                    text=True,
                    cwd=str(crane_dir),
                    timeout=60,
                )
                steps.append(
                    {
                        "step": "verify",
                        "status": "ok" if result.returncode == 0 else "warning",
                        "output": result.stdout.strip(),
                    }
                )

            new_version = service.get_local_version()
            steps.append({"step": "confirm", "status": "ok", "version": new_version})

            return {
                "status": "success",
                "from_version": current,
                "to_version": new_version,
                "steps_completed": steps,
            }

        except subprocess.TimeoutExpired:
            return {"status": "error", "step": "timeout", "message": "Operation timed out"}
        except Exception as e:
            return {
                "status": "error",
                "step": "unexpected",
                "message": str(e),
                "steps_completed": steps,
            }

    @mcp.tool()
    def rollback_crane(
        to_version: str = "",
        backup_path: str = "",
        project_dir: str | None = None,
    ) -> dict[str, Any]:
        """Rollback CRANE to a previous version.

        Args:
            to_version: Git tag or version to rollback to
            backup_path: Path to backup directory (alternative to git tag)
        """
        crane_dir = Path(project_dir) if project_dir else Path(__file__).resolve().parents[3]

        try:
            if backup_path:
                import shutil

                backup = Path(backup_path)
                if not backup.exists():
                    return {"status": "error", "message": f"Backup not found: {backup_path}"}

                for subdir in ["src", "data", "scripts", "pyproject.toml"]:
                    src = backup / subdir
                    dst = crane_dir / subdir
                    if src.exists():
                        if dst.exists():
                            if dst.is_dir():
                                shutil.rmtree(dst)
                            else:
                                dst.unlink()
                        if src.is_dir():
                            shutil.copytree(src, dst)
                        else:
                            shutil.copy2(src, dst)

                return {"status": "success", "method": "backup_restore", "backup_path": backup_path}

            if to_version:
                result = subprocess.run(
                    ["git", "checkout", to_version],
                    capture_output=True,
                    text=True,
                    cwd=str(crane_dir),
                    timeout=30,
                )
                if result.returncode != 0:
                    return {"status": "error", "message": result.stderr}

                subprocess.run(["uv", "sync"], capture_output=True, cwd=str(crane_dir), timeout=120)

                service = VersionCheckService(crane_dir)
                return {
                    "status": "success",
                    "method": "git_checkout",
                    "version": service.get_local_version(),
                }

            return {"status": "error", "message": "Provide either to_version or backup_path"}

        except Exception as e:
            return {"status": "error", "message": str(e)}
