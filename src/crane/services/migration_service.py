from __future__ import annotations

import datetime
import importlib.util
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MigrationRecord:
    """Record of a single migration execution."""

    version: str
    applied_at: str
    status: str  # success / failed / skipped
    output: str


@dataclass
class MigrationState:
    """Persistent state of all migrations."""

    applied_migrations: list[MigrationRecord] = field(default_factory=list)
    skipped_versions: list[str] = field(default_factory=list)
    last_applied: str = ""

    def save(self, path: Path) -> None:
        """Save state to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "applied_migrations": [
                        {
                            "version": m.version,
                            "applied_at": m.applied_at,
                            "status": m.status,
                            "output": m.output,
                        }
                        for m in self.applied_migrations
                    ],
                    "skipped_versions": self.skipped_versions,
                    "last_applied": self.last_applied,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> MigrationState:
        """Load state from JSON file."""
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        state = cls()
        state.applied_migrations = [
            MigrationRecord(**m) for m in data.get("applied_migrations", [])
        ]
        state.skipped_versions = data.get("skipped_versions", [])
        state.last_applied = data.get("last_applied", "")
        return state


class MigrationService:
    """Manage database/schema migrations for CRANE."""

    def __init__(self, crane_dir: str | Path | None = None):
        self.crane_dir = Path(crane_dir) if crane_dir else Path(__file__).resolve().parents[3]
        self.migrations_dir = self.crane_dir / "scripts" / "migrations"
        self.state_file = self.crane_dir / ".crane_migration_state.json"

    def get_pending_migrations(self, current_version: str) -> list[str]:
        """Get list of pending migration versions."""
        state = MigrationState.load(self.state_file)
        if not self.migrations_dir.exists():
            return []
        pending = []
        for f in sorted(self.migrations_dir.glob("*.py")):
            if f.name in ("__init__.py",):
                continue
            version = f.stem.lstrip("v")
            # Check if already applied successfully
            if version not in [
                m.version for m in state.applied_migrations if m.status == "success"
            ]:
                # Check if not skipped
                if version not in state.skipped_versions:
                    # Check if version is greater than current
                    if self._version_gt(version, current_version):
                        pending.append(version)
        return pending

    def apply_migration(self, version: str) -> MigrationRecord:
        """Apply a specific migration."""
        migration_path = self.migrations_dir / f"v{version}.py"
        if not migration_path.exists():
            return MigrationRecord(
                version, "", "failed", f"Migration file not found: {migration_path}"
            )

        try:
            spec = importlib.util.spec_from_file_location(f"migration_{version}", migration_path)
            if spec is None or spec.loader is None:
                return MigrationRecord(version, "", "failed", "Could not load migration module")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            migrate_func = getattr(mod, "migrate", None)
            if migrate_func:
                output = migrate_func(str(self.crane_dir))
            else:
                output = "No migrate() function found"
            record = MigrationRecord(version, "", "success", str(output))
        except Exception as e:
            record = MigrationRecord(version, "", "failed", str(e))

        record.applied_at = self._now_iso()
        state = MigrationState.load(self.state_file)
        state.applied_migrations.append(record)
        if record.status == "success":
            state.last_applied = version
        state.save(self.state_file)
        return record

    def apply_all_pending(self, current_version: str) -> list[MigrationRecord]:
        """Apply all pending migrations in order."""
        pending = self.get_pending_migrations(current_version)
        return [self.apply_migration(v) for v in pending]

    def skip_version(self, version: str) -> None:
        """Mark a version as skipped."""
        state = MigrationState.load(self.state_file)
        if version not in state.skipped_versions:
            state.skipped_versions.append(version)
            state.save(self.state_file)

    def unskip_version(self, version: str) -> None:
        """Unmark a skipped version."""
        state = MigrationState.load(self.state_file)
        if version in state.skipped_versions:
            state.skipped_versions.remove(version)
            state.save(self.state_file)

    @staticmethod
    def _version_gt(a: str, b: str) -> bool:
        """Check if version a > version b (semantic versioning)."""

        def parse(v: str) -> tuple[int, ...]:
            try:
                return tuple(int(x) for x in v.split(".")[:3])
            except (ValueError, IndexError):
                return ()

        try:
            a_parts = parse(a)
            b_parts = parse(b)
            if not a_parts or not b_parts:
                return False
            return a_parts > b_parts
        except (ValueError, IndexError):
            return False

    @staticmethod
    def _now_iso() -> str:
        """Get current time in ISO format."""
        return datetime.datetime.now(datetime.timezone.utc).isoformat()
