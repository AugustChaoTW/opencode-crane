"""Journal submission workflow service - Main orchestrator for paper submission process."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from crane.workspace import resolve_workspace


class SubmissionConfig:
    """Configuration container for paper submission setup."""

    def __init__(
        self,
        field: str,
        target_journals: list[str],
        page_limit: int,
        figure_limit: int,
        timeline: str,
        acceptance_target: float,
        revision_tolerance: str,
        has_code: bool = True,
        has_dataset: bool = False,
        has_human_subjects: bool = False,
        ethics_approval_number: str | None = None,
        replicability_score: int = 7,
    ):
        self.field = field
        self.target_journals = target_journals
        self.page_limit = page_limit
        self.figure_limit = figure_limit
        self.timeline = timeline  # rush, normal, flexible
        self.acceptance_target = acceptance_target  # 0.5-0.95
        self.revision_tolerance = revision_tolerance  # none, minor, moderate, major
        self.has_code = has_code
        self.has_dataset = has_dataset
        self.has_human_subjects = has_human_subjects
        self.ethics_approval_number = ethics_approval_number
        self.replicability_score = replicability_score
        self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            "research_field": self.field,
            "target_journals": self.target_journals,
            "paper_constraints": {
                "page_limit": self.page_limit,
                "figure_limit": self.figure_limit,
            },
            "submission_strategy": {
                "timeline": self.timeline,
                "acceptance_target": self.acceptance_target,
                "revision_tolerance": self.revision_tolerance,
            },
            "paper_characteristics": {
                "has_code_release": self.has_code,
                "has_dataset_release": self.has_dataset,
                "has_human_subjects": self.has_human_subjects,
                "ethics_approval_number": self.ethics_approval_number,
                "replicability_score": self.replicability_score,
            },
            "created_at": self.created_at,
            "stage": "setup",
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SubmissionConfig:
        """Create from dictionary (YAML data)."""
        return cls(
            field=data.get("research_field", "other"),
            target_journals=data.get("target_journals", []),
            page_limit=data.get("paper_constraints", {}).get("page_limit", 16),
            figure_limit=data.get("paper_constraints", {}).get("figure_limit", 8),
            timeline=data.get("submission_strategy", {}).get("timeline", "normal"),
            acceptance_target=data.get("submission_strategy", {}).get("acceptance_target", 0.75),
            revision_tolerance=data.get("submission_strategy", {}).get(
                "revision_tolerance", "moderate"
            ),
            has_code=data.get("paper_characteristics", {}).get("has_code_release", True),
            has_dataset=data.get("paper_characteristics", {}).get("has_dataset_release", False),
            has_human_subjects=data.get("paper_characteristics", {}).get(
                "has_human_subjects", False
            ),
            ethics_approval_number=data.get("paper_characteristics", {}).get(
                "ethics_approval_number"
            ),
            replicability_score=data.get("paper_characteristics", {}).get("replicability_score", 7),
        )


class JournalSubmissionService:
    """Service for managing the complete journal submission workflow."""

    def __init__(self, project_dir: str | None = None):
        workspace = resolve_workspace(project_dir)
        self.project_root = Path(workspace.project_root)
        self.journal_system_dir = self.project_root / ".crane" / "journal-system"
        self.journal_system_dir.mkdir(parents=True, exist_ok=True)

        self.config_file = self.journal_system_dir / "submission-config.yaml"
        self.templates_dir = self.journal_system_dir / "templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def save_config(self, config: SubmissionConfig) -> dict[str, Any]:
        """Save submission configuration to YAML file."""
        config_dict = config.to_dict()

        with open(self.config_file, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

        return {
            "status": "success",
            "message": f"Configuration saved to {self.config_file}",
            "config": config_dict,
        }

    def load_config(self) -> SubmissionConfig | None:
        """Load submission configuration from YAML file."""
        if not self.config_file.exists():
            return None

        with open(self.config_file) as f:
            data = yaml.safe_load(f)

        if not data:
            return None

        return SubmissionConfig.from_dict(data)

    def load_journal_standard(self, journal_name: str) -> dict[str, Any] | None:
        """Load journal-specific evaluation standard."""
        templates_file = Path(__file__).parent.parent / "config" / "journal_standards"
        standard_file = templates_file / f"{journal_name.lower().replace(' ', '_')}.yaml"

        if not standard_file.exists():
            return None

        with open(standard_file) as f:
            return yaml.safe_load(f)

    def get_field_specific_checklist(self, field: str) -> dict[str, Any]:
        """Get field-specific checklist template."""
        checklist_file = self.project_root / ".crane" / "journal-system" / "chapter-checklist.yaml"

        if not checklist_file.exists():
            return {}

        with open(checklist_file) as f:
            full_checklist = yaml.safe_load(f)

        return full_checklist.get("chapter_templates", {})

    def initialize_submission_project(
        self,
        field: str,
        journals: list[str],
        page_limit: int = 16,
        figure_limit: int = 8,
        timeline: str = "normal",
        acceptance_target: float = 0.75,
        revision_tolerance: str = "moderate",
        has_code: bool = True,
        has_human_subjects: bool = False,
        replicability_score: int = 7,
    ) -> dict[str, Any]:
        """Initialize a new submission project with configuration."""
        config = SubmissionConfig(
            field=field,
            target_journals=journals,
            page_limit=page_limit,
            figure_limit=figure_limit,
            timeline=timeline,
            acceptance_target=acceptance_target,
            revision_tolerance=revision_tolerance,
            has_code=has_code,
            has_human_subjects=has_human_subjects,
            replicability_score=replicability_score,
        )

        result = self.save_config(config)

        loaded_standards = {}
        for journal in journals:
            try:
                standard = self.load_journal_standard(journal)
                if standard:
                    loaded_standards[journal] = "✅ loaded"
            except Exception:
                loaded_standards[journal] = "⚠️ not found (using defaults)"

        return {
            "status": "success",
            "message": "Submission project initialized",
            "config_saved": result,
            "journal_standards_loaded": loaded_standards,
            "next_step": "Run 'crane coach --chapter introduction' to start diagnosis",
        }

    def get_chapter_checklist(
        self, chapter: str, journal_name: str | None = None
    ) -> dict[str, Any]:
        """Get checklist for a specific chapter, optionally customized for a journal."""
        checklist = self.get_field_specific_checklist("all")
        chapter_checks = checklist.get(chapter, {})

        if journal_name:
            journal_standard = self.load_journal_standard(journal_name)
            if journal_standard:
                chapter_checks["journal_specific"] = journal_standard.get(chapter, {})

        return chapter_checks

    def get_submission_status(self) -> dict[str, Any]:
        """Get current submission project status."""
        config = self.load_config()

        if not config:
            return {"status": "no_project", "message": "No submission project initialized"}

        return {
            "status": "active",
            "field": config.field,
            "target_journals": config.target_journals,
            "timeline": config.timeline,
            "acceptance_target": config.acceptance_target,
            "page_limit": config.page_limit,
            "created_at": config.created_at,
            "stage": "setup",
        }
