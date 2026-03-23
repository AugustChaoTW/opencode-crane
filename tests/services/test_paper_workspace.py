"""Tests for paper workspace service."""

from __future__ import annotations

from pathlib import Path

import pytest

from crane.services.paper_workspace import (
    PaperWorkspace,
    create_workspace,
    get_workspace,
    list_workspaces,
)


class TestCreateWorkspace:
    def test_creates_directory_structure(self, tmp_path):
        ws = create_workspace("NIPS", tmp_path)

        assert (tmp_path / "papers" / "NIPS").exists()
        assert (tmp_path / "papers" / "NIPS" / "figures").exists()
        assert (tmp_path / "papers" / "NIPS" / "supplementary").exists()

    def test_creates_main_tex(self, tmp_path):
        ws = create_workspace("NIPS", tmp_path)

        assert ws.paper_path.exists()
        assert ws.paper_path.name == "NIPS-MAIN.tex"

    def test_creates_protected_zones_yaml(self, tmp_path):
        ws = create_workspace("NIPS", tmp_path)

        assert ws.protected_zones_path.exists()
        assert ws.protected_zones_path.name == "NIPS-protected-zones.yaml"

    def test_creates_report_files(self, tmp_path):
        ws = create_workspace("NIPS", tmp_path)

        assert ws.audit_report_path.exists()
        assert ws.detection_report_path.exists()
        assert ws.change_log_path.exists()
        assert ws.health_report_path.exists()

    def test_abbr_uppercase(self, tmp_path):
        ws = create_workspace("nips", tmp_path)

        assert ws.journal_abbr == "NIPS"

    def test_abbr_too_long_raises(self, tmp_path):
        with pytest.raises(ValueError, match="5 characters"):
            create_workspace("toolong", tmp_path)


class TestGetWorkspace:
    def test_returns_workspace_if_exists(self, tmp_path):
        create_workspace("NIPS", tmp_path)
        ws = get_workspace("NIPS", tmp_path)

        assert ws is not None
        assert ws.journal_abbr == "NIPS"

    def test_returns_none_if_not_exists(self, tmp_path):
        ws = get_workspace("NIPS", tmp_path)

        assert ws is None


class TestListWorkspaces:
    def test_lists_all_workspaces(self, tmp_path):
        create_workspace("NIPS", tmp_path)
        create_workspace("ICML", tmp_path)
        create_workspace("AAAI", tmp_path)

        workspaces = list_workspaces(tmp_path)

        assert len(workspaces) == 3
        assert set(workspaces) == {"NIPS", "ICML", "AAAI"}

    def test_empty_if_no_workspaces(self, tmp_path):
        workspaces = list_workspaces(tmp_path)

        assert workspaces == []


class TestPaperWorkspace:
    def test_main_tex_property(self, tmp_path):
        ws = create_workspace("NIPS", tmp_path)

        assert ws.main_tex == ws.paper_path

    def test_abbr_property(self, tmp_path):
        ws = create_workspace("NIPS", tmp_path)

        assert ws.abbr == "NIPS"
