from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crane.services.migration_service import (
    MigrationRecord,
    MigrationService,
    MigrationState,
)


class TestMigrationRecord:
    def test_creates_record_with_all_fields(self):
        record = MigrationRecord(
            version="1.0.0", applied_at="2025-01-01T00:00:00", status="success", output="ok"
        )
        assert record.version == "1.0.0"
        assert record.applied_at == "2025-01-01T00:00:00"
        assert record.status == "success"
        assert record.output == "ok"

    def test_record_status_can_be_failed(self):
        record = MigrationRecord(
            version="1.0.0", applied_at="2025-01-01T00:00:00", status="failed", output="error"
        )
        assert record.status == "failed"

    def test_record_status_can_be_skipped(self):
        record = MigrationRecord(
            version="1.0.0", applied_at="2025-01-01T00:00:00", status="skipped", output=""
        )
        assert record.status == "skipped"


class TestMigrationState:
    def test_creates_empty_state(self):
        state = MigrationState()
        assert state.applied_migrations == []
        assert state.skipped_versions == []
        assert state.last_applied == ""

    def test_saves_empty_state_to_json(self, tmp_path: Path):
        state = MigrationState()
        state_file = tmp_path / "state.json"
        state.save(state_file)
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["applied_migrations"] == []
        assert data["skipped_versions"] == []
        assert data["last_applied"] == ""

    def test_saves_state_with_migrations(self, tmp_path: Path):
        state = MigrationState()
        state.applied_migrations = [
            MigrationRecord("1.0.0", "2025-01-01T00:00:00", "success", "ok")
        ]
        state.last_applied = "1.0.0"
        state_file = tmp_path / "state.json"
        state.save(state_file)
        data = json.loads(state_file.read_text())
        assert len(data["applied_migrations"]) == 1
        assert data["applied_migrations"][0]["version"] == "1.0.0"
        assert data["last_applied"] == "1.0.0"

    def test_saves_state_with_skipped_versions(self, tmp_path: Path):
        state = MigrationState()
        state.skipped_versions = ["1.0.0", "1.1.0"]
        state_file = tmp_path / "state.json"
        state.save(state_file)
        data = json.loads(state_file.read_text())
        assert data["skipped_versions"] == ["1.0.0", "1.1.0"]

    def test_loads_empty_state_when_file_missing(self, tmp_path: Path):
        state_file = tmp_path / "nonexistent.json"
        state = MigrationState.load(state_file)
        assert state.applied_migrations == []
        assert state.skipped_versions == []
        assert state.last_applied == ""

    def test_loads_state_from_json(self, tmp_path: Path):
        state_file = tmp_path / "state.json"
        state_file.write_text(
            json.dumps(
                {
                    "applied_migrations": [
                        {
                            "version": "1.0.0",
                            "applied_at": "2025-01-01T00:00:00",
                            "status": "success",
                            "output": "ok",
                        }
                    ],
                    "skipped_versions": ["1.1.0"],
                    "last_applied": "1.0.0",
                }
            )
        )
        state = MigrationState.load(state_file)
        assert len(state.applied_migrations) == 1
        assert state.applied_migrations[0].version == "1.0.0"
        assert state.skipped_versions == ["1.1.0"]
        assert state.last_applied == "1.0.0"

    def test_loads_state_with_missing_fields(self, tmp_path: Path):
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"applied_migrations": []}))
        state = MigrationState.load(state_file)
        assert state.applied_migrations == []
        assert state.skipped_versions == []
        assert state.last_applied == ""

    def test_save_creates_parent_directories(self, tmp_path: Path):
        state = MigrationState()
        state_file = tmp_path / "deep" / "nested" / "state.json"
        state.save(state_file)
        assert state_file.exists()


class TestMigrationServiceInit:
    def test_initializes_with_default_crane_dir(self):
        service = MigrationService()
        assert service.crane_dir.exists()
        assert service.migrations_dir.name == "migrations"

    def test_initializes_with_custom_crane_dir(self, tmp_path: Path):
        service = MigrationService(tmp_path)
        assert service.crane_dir == tmp_path
        assert service.migrations_dir == tmp_path / "scripts" / "migrations"

    def test_initializes_with_string_crane_dir(self, tmp_path: Path):
        service = MigrationService(str(tmp_path))
        assert service.crane_dir == tmp_path

    def test_state_file_path_is_correct(self, tmp_path: Path):
        service = MigrationService(tmp_path)
        assert service.state_file == tmp_path / ".crane_migration_state.json"


class TestGetPendingMigrations:
    def test_returns_empty_when_migrations_dir_missing(self, tmp_path: Path):
        service = MigrationService(tmp_path)
        pending = service.get_pending_migrations("0.0.0")
        assert pending == []

    def test_returns_empty_when_no_migrations_exist(self, tmp_path: Path):
        migrations_dir = tmp_path / "scripts" / "migrations"
        migrations_dir.mkdir(parents=True)
        service = MigrationService(tmp_path)
        pending = service.get_pending_migrations("0.0.0")
        assert pending == []

    def test_returns_migrations_greater_than_current_version(self, tmp_path: Path):
        migrations_dir = tmp_path / "scripts" / "migrations"
        migrations_dir.mkdir(parents=True)
        (migrations_dir / "v1.0.0.py").write_text("def migrate(crane_dir): pass")
        (migrations_dir / "v1.1.0.py").write_text("def migrate(crane_dir): pass")
        (migrations_dir / "v0.9.0.py").write_text("def migrate(crane_dir): pass")
        service = MigrationService(tmp_path)
        pending = service.get_pending_migrations("0.9.0")
        assert "1.0.0" in pending
        assert "1.1.0" in pending
        assert "0.9.0" not in pending

    def test_excludes_already_applied_migrations(self, tmp_path: Path):
        migrations_dir = tmp_path / "scripts" / "migrations"
        migrations_dir.mkdir(parents=True)
        (migrations_dir / "v1.0.0.py").write_text("def migrate(crane_dir): pass")
        (migrations_dir / "v1.1.0.py").write_text("def migrate(crane_dir): pass")
        service = MigrationService(tmp_path)
        state = MigrationState()
        state.applied_migrations = [
            MigrationRecord("1.0.0", "2025-01-01T00:00:00", "success", "ok")
        ]
        state.save(service.state_file)
        pending = service.get_pending_migrations("0.0.0")
        assert "1.0.0" not in pending
        assert "1.1.0" in pending

    def test_excludes_skipped_versions(self, tmp_path: Path):
        migrations_dir = tmp_path / "scripts" / "migrations"
        migrations_dir.mkdir(parents=True)
        (migrations_dir / "v1.0.0.py").write_text("def migrate(crane_dir): pass")
        (migrations_dir / "v1.1.0.py").write_text("def migrate(crane_dir): pass")
        service = MigrationService(tmp_path)
        state = MigrationState()
        state.skipped_versions = ["1.0.0"]
        state.save(service.state_file)
        pending = service.get_pending_migrations("0.0.0")
        assert "1.0.0" not in pending
        assert "1.1.0" in pending

    def test_ignores_init_py_file(self, tmp_path: Path):
        migrations_dir = tmp_path / "scripts" / "migrations"
        migrations_dir.mkdir(parents=True)
        (migrations_dir / "__init__.py").write_text("")
        (migrations_dir / "v1.0.0.py").write_text("def migrate(crane_dir): pass")
        service = MigrationService(tmp_path)
        pending = service.get_pending_migrations("0.0.0")
        assert "__init__" not in str(pending)
        assert "1.0.0" in pending

    def test_returns_migrations_in_sorted_order(self, tmp_path: Path):
        migrations_dir = tmp_path / "scripts" / "migrations"
        migrations_dir.mkdir(parents=True)
        (migrations_dir / "v1.2.0.py").write_text("def migrate(crane_dir): pass")
        (migrations_dir / "v1.0.0.py").write_text("def migrate(crane_dir): pass")
        (migrations_dir / "v1.1.0.py").write_text("def migrate(crane_dir): pass")
        service = MigrationService(tmp_path)
        pending = service.get_pending_migrations("0.0.0")
        assert pending == ["1.0.0", "1.1.0", "1.2.0"]


class TestApplyMigration:
    def test_returns_failed_when_migration_file_missing(self, tmp_path: Path):
        migrations_dir = tmp_path / "scripts" / "migrations"
        migrations_dir.mkdir(parents=True)
        service = MigrationService(tmp_path)
        record = service.apply_migration("1.0.0")
        assert record.status == "failed"
        assert "not found" in record.output

    def test_applies_migration_successfully(self, tmp_path: Path):
        migrations_dir = tmp_path / "scripts" / "migrations"
        migrations_dir.mkdir(parents=True)
        (migrations_dir / "v1.0.0.py").write_text("def migrate(crane_dir):\n    return 'success'")
        service = MigrationService(tmp_path)
        record = service.apply_migration("1.0.0")
        assert record.status == "success"
        assert record.version == "1.0.0"
        assert record.output == "success"

    def test_records_applied_at_timestamp(self, tmp_path: Path):
        migrations_dir = tmp_path / "scripts" / "migrations"
        migrations_dir.mkdir(parents=True)
        (migrations_dir / "v1.0.0.py").write_text("def migrate(crane_dir):\n    return 'ok'")
        service = MigrationService(tmp_path)
        record = service.apply_migration("1.0.0")
        assert record.applied_at != ""
        assert "T" in record.applied_at

    def test_saves_state_after_successful_migration(self, tmp_path: Path):
        migrations_dir = tmp_path / "scripts" / "migrations"
        migrations_dir.mkdir(parents=True)
        (migrations_dir / "v1.0.0.py").write_text("def migrate(crane_dir):\n    return 'ok'")
        service = MigrationService(tmp_path)
        service.apply_migration("1.0.0")
        state = MigrationState.load(service.state_file)
        assert len(state.applied_migrations) == 1
        assert state.applied_migrations[0].version == "1.0.0"
        assert state.last_applied == "1.0.0"

    def test_saves_state_after_failed_migration(self, tmp_path: Path):
        migrations_dir = tmp_path / "scripts" / "migrations"
        migrations_dir.mkdir(parents=True)
        (migrations_dir / "v1.0.0.py").write_text(
            "def migrate(crane_dir):\n    raise ValueError('boom')"
        )
        service = MigrationService(tmp_path)
        service.apply_migration("1.0.0")
        state = MigrationState.load(service.state_file)
        assert len(state.applied_migrations) == 1
        assert state.applied_migrations[0].status == "failed"
        assert state.last_applied == ""

    def test_handles_migration_without_migrate_function(self, tmp_path: Path):
        migrations_dir = tmp_path / "scripts" / "migrations"
        migrations_dir.mkdir(parents=True)
        (migrations_dir / "v1.0.0.py").write_text("x = 1")
        service = MigrationService(tmp_path)
        record = service.apply_migration("1.0.0")
        assert record.status == "success"
        assert "No migrate()" in record.output

    def test_passes_crane_dir_to_migrate_function(self, tmp_path: Path):
        migrations_dir = tmp_path / "scripts" / "migrations"
        migrations_dir.mkdir(parents=True)
        (migrations_dir / "v1.0.0.py").write_text(
            "def migrate(crane_dir):\n    return f'dir={crane_dir}'"
        )
        service = MigrationService(tmp_path)
        record = service.apply_migration("1.0.0")
        assert str(tmp_path) in record.output


class TestApplyAllPending:
    def test_applies_all_pending_migrations_in_order(self, tmp_path: Path):
        migrations_dir = tmp_path / "scripts" / "migrations"
        migrations_dir.mkdir(parents=True)
        (migrations_dir / "v1.0.0.py").write_text("def migrate(crane_dir):\n    return 'v1.0.0'")
        (migrations_dir / "v1.1.0.py").write_text("def migrate(crane_dir):\n    return 'v1.1.0'")
        service = MigrationService(tmp_path)
        records = service.apply_all_pending("0.0.0")
        assert len(records) == 2
        assert records[0].version == "1.0.0"
        assert records[1].version == "1.1.0"
        assert all(r.status == "success" for r in records)

    def test_returns_empty_when_no_pending_migrations(self, tmp_path: Path):
        migrations_dir = tmp_path / "scripts" / "migrations"
        migrations_dir.mkdir(parents=True)
        service = MigrationService(tmp_path)
        records = service.apply_all_pending("2.0.0")
        assert records == []

    def test_stops_on_first_failure_but_records_all(self, tmp_path: Path):
        migrations_dir = tmp_path / "scripts" / "migrations"
        migrations_dir.mkdir(parents=True)
        (migrations_dir / "v1.0.0.py").write_text(
            "def migrate(crane_dir):\n    raise ValueError('fail')"
        )
        (migrations_dir / "v1.1.0.py").write_text("def migrate(crane_dir):\n    return 'ok'")
        service = MigrationService(tmp_path)
        records = service.apply_all_pending("0.0.0")
        assert len(records) == 2
        assert records[0].status == "failed"
        assert records[1].status == "success"


class TestSkipVersion:
    def test_adds_version_to_skipped_list(self, tmp_path: Path):
        service = MigrationService(tmp_path)
        service.skip_version("1.0.0")
        state = MigrationState.load(service.state_file)
        assert "1.0.0" in state.skipped_versions

    def test_does_not_duplicate_skipped_version(self, tmp_path: Path):
        service = MigrationService(tmp_path)
        service.skip_version("1.0.0")
        service.skip_version("1.0.0")
        state = MigrationState.load(service.state_file)
        assert state.skipped_versions.count("1.0.0") == 1

    def test_skips_multiple_versions(self, tmp_path: Path):
        service = MigrationService(tmp_path)
        service.skip_version("1.0.0")
        service.skip_version("1.1.0")
        state = MigrationState.load(service.state_file)
        assert "1.0.0" in state.skipped_versions
        assert "1.1.0" in state.skipped_versions


class TestUnskipVersion:
    def test_removes_version_from_skipped_list(self, tmp_path: Path):
        service = MigrationService(tmp_path)
        service.skip_version("1.0.0")
        service.unskip_version("1.0.0")
        state = MigrationState.load(service.state_file)
        assert "1.0.0" not in state.skipped_versions

    def test_does_nothing_when_version_not_skipped(self, tmp_path: Path):
        service = MigrationService(tmp_path)
        service.unskip_version("1.0.0")
        state = MigrationState.load(service.state_file)
        assert state.skipped_versions == []

    def test_unSkips_one_version_preserves_others(self, tmp_path: Path):
        service = MigrationService(tmp_path)
        service.skip_version("1.0.0")
        service.skip_version("1.1.0")
        service.unskip_version("1.0.0")
        state = MigrationState.load(service.state_file)
        assert "1.0.0" not in state.skipped_versions
        assert "1.1.0" in state.skipped_versions


class TestVersionGt:
    def test_returns_true_when_a_greater_than_b(self):
        assert MigrationService._version_gt("1.1.0", "1.0.0")
        assert MigrationService._version_gt("2.0.0", "1.9.9")
        assert MigrationService._version_gt("1.0.1", "1.0.0")

    def test_returns_false_when_a_less_than_b(self):
        assert not MigrationService._version_gt("1.0.0", "1.1.0")
        assert not MigrationService._version_gt("1.9.9", "2.0.0")
        assert not MigrationService._version_gt("1.0.0", "1.0.1")

    def test_returns_false_when_equal(self):
        assert not MigrationService._version_gt("1.0.0", "1.0.0")
        assert not MigrationService._version_gt("2.3.4", "2.3.4")

    def test_handles_single_digit_versions(self):
        assert MigrationService._version_gt("2", "1")
        assert not MigrationService._version_gt("1", "2")

    def test_handles_two_digit_versions(self):
        assert MigrationService._version_gt("1.1", "1.0")
        assert not MigrationService._version_gt("1.0", "1.1")

    def test_handles_invalid_version_format(self):
        assert not MigrationService._version_gt("invalid", "1.0.0")
        assert not MigrationService._version_gt("1.0.0", "invalid")
        assert not MigrationService._version_gt("abc", "def")

    def test_handles_empty_strings(self):
        assert not MigrationService._version_gt("", "1.0.0")
        assert not MigrationService._version_gt("1.0.0", "")

    def test_ignores_extra_version_parts(self):
        assert MigrationService._version_gt("1.0.1", "1.0.0")
        assert not MigrationService._version_gt("1.0.0", "1.0.1")


class TestNowIso:
    def test_returns_iso_format_string(self):
        iso_str = MigrationService._now_iso()
        assert "T" in iso_str
        assert "+" in iso_str or "Z" in iso_str

    def test_returns_valid_iso_timestamp(self):
        iso_str = MigrationService._now_iso()
        from datetime import datetime

        try:
            datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            valid = True
        except ValueError:
            valid = False
        assert valid


class TestIntegration:
    def test_full_migration_workflow(self, tmp_path: Path):
        migrations_dir = tmp_path / "scripts" / "migrations"
        migrations_dir.mkdir(parents=True)
        (migrations_dir / "v1.0.0.py").write_text(
            "def migrate(crane_dir):\n    return 'v1.0.0 applied'"
        )
        (migrations_dir / "v1.1.0.py").write_text(
            "def migrate(crane_dir):\n    return 'v1.1.0 applied'"
        )
        service = MigrationService(tmp_path)
        pending = service.get_pending_migrations("0.0.0")
        assert len(pending) == 2
        records = service.apply_all_pending("0.0.0")
        assert len(records) == 2
        assert all(r.status == "success" for r in records)
        pending_after = service.get_pending_migrations("0.0.0")
        assert len(pending_after) == 0

    def test_skip_and_unskip_workflow(self, tmp_path: Path):
        migrations_dir = tmp_path / "scripts" / "migrations"
        migrations_dir.mkdir(parents=True)
        (migrations_dir / "v1.0.0.py").write_text("def migrate(crane_dir):\n    return 'ok'")
        service = MigrationService(tmp_path)
        pending = service.get_pending_migrations("0.0.0")
        assert "1.0.0" in pending
        service.skip_version("1.0.0")
        pending = service.get_pending_migrations("0.0.0")
        assert "1.0.0" not in pending
        service.unskip_version("1.0.0")
        pending = service.get_pending_migrations("0.0.0")
        assert "1.0.0" in pending

    def test_mixed_success_and_failure(self, tmp_path: Path):
        migrations_dir = tmp_path / "scripts" / "migrations"
        migrations_dir.mkdir(parents=True)
        (migrations_dir / "v1.0.0.py").write_text("def migrate(crane_dir):\n    return 'success'")
        (migrations_dir / "v1.1.0.py").write_text(
            "def migrate(crane_dir):\n    raise RuntimeError('fail')"
        )
        (migrations_dir / "v1.2.0.py").write_text("def migrate(crane_dir):\n    return 'success'")
        service = MigrationService(tmp_path)
        records = service.apply_all_pending("0.0.0")
        assert records[0].status == "success"
        assert records[1].status == "failed"
        assert records[2].status == "success"
        state = MigrationState.load(service.state_file)
        assert state.last_applied == "1.2.0"
