"""Core traceability service: manage _paper_trace/ directory and documents."""
from __future__ import annotations

import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from crane.models.traceability import (
    TRACE_DIR_NAME,
    ArtifactEntry,
    BaselineSpec,
    ChangeLogEntry,
    ContributionItem,
    DatasetSpec,
    ExperimentEntry,
    FigureTableEntry,
    MustUpdateItem,
    ReferenceMapEntry,
    ResearchQuestion,
    ReviewerRisk,
    SectionEntry,
    TraceabilityIndex,
    is_active_paper_dir,
)
from crane.services.impact_graph_service import ImpactGraphService


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> Any:
    """Load a YAML file, returning {} on error or missing file."""
    try:
        text = path.read_text(encoding="utf-8")
        return yaml.safe_load(text) or {}
    except (FileNotFoundError, yaml.YAMLError):
        return {}


def _dump_yaml(path: Path, data: Any) -> None:
    """Write *data* as YAML to *path* (UTF-8, block style)."""
    path.write_text(
        yaml.dump(data, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Template directory
# ---------------------------------------------------------------------------

_TEMPLATE_DIR = Path(__file__).parent.parent / "config" / "templates" / "traceability"


class TraceabilityService:
    """Manage paper traceability documents in ``_paper_trace/v{n}/`` directories."""

    VERSION_CREATING_MODES: frozenset[str] = frozenset({"full", "init", "infer"})
    VERSION_READING_MODES: frozenset[str] = frozenset({"update", "status", "viz"})

    def __init__(
        self,
        paper_path: str,
        output_dir: str = "",
        project_dir: str = "",
    ) -> None:
        self.paper_path = Path(paper_path)
        self._output_dir = output_dir
        self._project_dir = project_dir
        self._trace_root: Path | None = None
        self._version_dir: Path | None = None

    # ------------------------------------------------------------------
    # Path resolution
    # ------------------------------------------------------------------

    def _resolve_trace_root(self) -> Path:
        """5-level fallback: output_dir → paper parent → project_dir → git root → cwd."""
        if self._output_dir:
            base = Path(self._output_dir)
        elif self.paper_path.parent.exists():
            base = self.paper_path.parent
        elif self._project_dir:
            base = Path(self._project_dir)
        else:
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--show-toplevel"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                base = Path(result.stdout.strip())
            except Exception:
                base = Path.cwd()
        return base / TRACE_DIR_NAME

    @property
    def trace_root(self) -> Path:
        if self._trace_root is None:
            self._trace_root = self._resolve_trace_root()
        return self._trace_root

    # ------------------------------------------------------------------
    # Version management
    # ------------------------------------------------------------------

    def _get_next_version(self) -> int:
        """Return next version number (max existing + 1, or 1 if none)."""
        if not self.trace_root.exists():
            return 1
        existing = [
            int(m.group(1))
            for d in self.trace_root.iterdir()
            if d.is_dir() and (m := re.fullmatch(r"v(\d+)", d.name))
        ]
        return max(existing, default=0) + 1

    def _get_latest_version(self) -> int | None:
        """Return the highest existing version number, or None."""
        if not self.trace_root.exists():
            return None
        existing = [
            int(m.group(1))
            for d in self.trace_root.iterdir()
            if d.is_dir() and (m := re.fullmatch(r"v(\d+)", d.name))
        ]
        return max(existing, default=None) if existing else None

    def get_version_dir(self, mode: str) -> Path:
        """Return the correct version directory for the given *mode*.

        Creating modes (``full``, ``init``, ``infer``) allocate a new version.
        Reading modes (``update``, ``status``, ``viz``) use the latest existing one.
        """
        if mode in self.VERSION_CREATING_MODES:
            version = self._get_next_version()
            vdir = self.trace_root / f"v{version}"
            vdir.mkdir(parents=True, exist_ok=True)
            return vdir
        else:
            latest = self._get_latest_version()
            if latest is None:
                raise FileNotFoundError(
                    f"No trace versions found in {self.trace_root}"
                )
            return self.trace_root / f"v{latest}"

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def init_documents(
        self,
        mode: str = "init",
        paper_stage: str = "draft",
    ) -> Path:
        """Create a new version directory and populate it with template YAML files.

        Returns the created version directory path.
        """
        version_dir = self.get_version_dir(mode)
        version_num = int(version_dir.name[1:])

        # Copy all template YAML files into the new version dir
        for template_file in sorted(_TEMPLATE_DIR.glob("*.yaml")):
            dest = version_dir / template_file.name
            if not dest.exists():
                shutil.copy2(template_file, dest)

        # Patch paper_path and paper_stage in 1_contribution.yaml
        contrib_path = version_dir / "1_contribution.yaml"
        if contrib_path.exists():
            data = _load_yaml(contrib_path)
            if isinstance(data, dict):
                data["paper_path"] = str(self.paper_path)
                data["paper_stage"] = paper_stage
                _dump_yaml(contrib_path, data)

        # Create/update README version history
        self._update_readme(version_num, mode, paper_stage)

        return version_dir

    def _update_readme(
        self,
        version: int,
        mode: str,
        paper_stage: str,
        trigger: str = "",
    ) -> None:
        """Update (or create) ``_paper_trace/README.md`` with a version history row."""
        self.trace_root.mkdir(parents=True, exist_ok=True)
        readme = self.trace_root / "README.md"
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        header = (
            "| 版次 | 建立時間 | 執行模式 | 論文階段 | 觸發指令 | 備註 |\n"
            "|------|----------|----------|----------|----------|------|\n"
        )
        row = f"| v{version} | {now} | {mode} | {paper_stage} | {trigger} |  |\n"

        if readme.exists():
            content = readme.read_text(encoding="utf-8")
            readme.write_text(content + row, encoding="utf-8")
        else:
            readme.write_text(
                f"# Paper Trace Version History\n\n{header}{row}",
                encoding="utf-8",
            )

    # ------------------------------------------------------------------
    # Add-* helpers  (read → append → write)
    # ------------------------------------------------------------------

    def add_research_question(
        self,
        version_dir: Path,
        rq_id: str,
        text: str,
        motivation: str = "",
        hypothesis: str = "",
    ) -> None:
        """Append a research question to ``6_research_question.yaml``."""
        path = version_dir / "6_research_question.yaml"
        data = _load_yaml(path) if path.exists() else {}
        rqs: list[dict] = data.get("research_questions", [])

        # Avoid duplicates
        if any(r.get("rq_id") == rq_id for r in rqs):
            return

        rqs.append(
            {
                "rq_id": rq_id,
                "text": text,
                "motivation": motivation,
                "hypothesis": hypothesis,
                "tested_by_experiments": [],
                "tested_by_figures": [],
                "tested_by_tables": [],
                "tested_by_sections": [],
                "related_contributions": [],
                "status": "draft",
            }
        )
        data["research_questions"] = rqs
        _dump_yaml(path, data)

    def add_contribution(self, version_dir: Path, **kwargs: Any) -> None:
        """Append a contribution to ``1_contribution.yaml``."""
        path = version_dir / "1_contribution.yaml"
        data = _load_yaml(path) if path.exists() else {}
        contributions: list[dict] = data.get("contributions", [])

        cid = kwargs.get("contribution_id", f"C{len(contributions) + 1}")
        if any(c.get("contribution_id") == cid for c in contributions):
            return

        entry: dict[str, Any] = {
            "contribution_id": cid,
            "claim": kwargs.get("claim", ""),
            "why_it_matters": kwargs.get("why_it_matters", ""),
            "strongest_defensible_wording": kwargs.get(
                "strongest_defensible_wording", ""
            ),
            "avoid_overclaiming": kwargs.get("avoid_overclaiming", []),
            "reviewer_risk": kwargs.get("reviewer_risk", ""),
            "response_strategy": kwargs.get("response_strategy", ""),
            "rq_ids": kwargs.get("rq_ids", []),
            "evidence_figures": kwargs.get("evidence_figures", []),
            "evidence_tables": kwargs.get("evidence_tables", []),
            "evidence_sections": kwargs.get("evidence_sections", []),
            "evidence_experiments": kwargs.get("evidence_experiments", []),
            "status": kwargs.get("status", "draft"),
        }
        if "inferred" in kwargs:
            entry["inferred"] = kwargs["inferred"]
        if "confidence" in kwargs:
            entry["confidence"] = kwargs["confidence"]

        contributions.append(entry)
        data["contributions"] = contributions
        _dump_yaml(path, data)

    def add_experiment(self, version_dir: Path, **kwargs: Any) -> None:
        """Append an experiment to ``2_experiment.yaml``."""
        path = version_dir / "2_experiment.yaml"
        data = _load_yaml(path) if path.exists() else {}
        experiments: list[dict] = data.get("experiments", [])

        eid = kwargs.get("exp_id", f"E{len(experiments) + 1}")
        if any(e.get("exp_id") == eid for e in experiments):
            return

        entry: dict[str, Any] = {
            "exp_id": eid,
            "goal": kwargs.get("goal", ""),
            "setting": kwargs.get("setting", {}),
            "final_numbers": kwargs.get("final_numbers", {}),
            "canonical_number": kwargs.get(
                "canonical_number", {"value": None, "locked": False, "locked_at": ""}
            ),
            "deprecated_numbers": kwargs.get("deprecated_numbers", []),
            "citation_needed": kwargs.get("citation_needed", []),
            "output_files": kwargs.get("output_files", []),
            "controlled_variables": kwargs.get("controlled_variables", {}),
            "used_in_paper": kwargs.get("used_in_paper", {}),
            "related_contributions": kwargs.get("related_contributions", []),
            "related_rqs": kwargs.get("related_rqs", []),
            "notes": kwargs.get("notes", ""),
            "status": kwargs.get("status", "pending"),
        }
        if "inferred" in kwargs:
            entry["inferred"] = kwargs["inferred"]
        if "confidence" in kwargs:
            entry["confidence"] = kwargs["confidence"]

        experiments.append(entry)
        data["experiments"] = experiments

        # Also update the compact experiment_registry
        registry: list[dict] = data.get("experiment_registry", [])
        if not any(r.get("exp_id") == eid for r in registry):
            registry.append(
                {
                    "exp_id": eid,
                    "goal": entry["goal"],
                    "canonical_metric": "",
                    "value": None,
                    "locked": False,
                }
            )
        data["experiment_registry"] = registry

        _dump_yaml(path, data)

    def add_figure_table(self, version_dir: Path, **kwargs: Any) -> None:
        """Append a figure/table entry to ``5_figure_table_map.yaml``."""
        path = version_dir / "5_figure_table_map.yaml"
        data = _load_yaml(path) if path.exists() else {}
        entries: list[dict] = data.get("entries", [])

        ft_id = kwargs.get("ft_id", f"Fig:{len(entries) + 1}")
        if any(e.get("ft_id") == ft_id for e in entries):
            return

        entry: dict[str, Any] = {
            "ft_id": ft_id,
            "type": kwargs.get("type", "figure"),
            "purpose": kwargs.get("purpose", ""),
            "claim_supported": kwargs.get("claim_supported", ""),
            "related_rqs": kwargs.get("related_rqs", []),
            "source_experiments": kwargs.get("source_experiments", []),
            "exact_numbers": kwargs.get("exact_numbers", []),
            "final_values": kwargs.get("final_values", {}),
            "visualization": kwargs.get("visualization", {}),
            "caption_draft": kwargs.get("caption_draft", ""),
            "presentation_rules": kwargs.get("presentation_rules", {}),
            "mentioned_in": kwargs.get("mentioned_in", []),
            "needs_update_if": kwargs.get("needs_update_if", []),
            "text_reference_rule": kwargs.get("text_reference_rule", ""),
        }
        if "inferred" in kwargs:
            entry["inferred"] = kwargs["inferred"]
        if "confidence" in kwargs:
            entry["confidence"] = kwargs["confidence"]

        entries.append(entry)
        data["entries"] = entries

        # Compact registry
        registry: list[dict] = data.get("figure_table_registry", [])
        if not any(r.get("ft_id") == ft_id for r in registry):
            registry.append(
                {
                    "ft_id": ft_id,
                    "type": entry["type"],
                    "purpose": entry["purpose"],
                    "locked_value": None,
                }
            )
        data["figure_table_registry"] = registry

        _dump_yaml(path, data)

    def add_reference(self, version_dir: Path, **kwargs: Any) -> None:
        """Append a reference to ``4_citation_map.yaml``."""
        path = version_dir / "4_citation_map.yaml"
        data = _load_yaml(path) if path.exists() else {}
        references: list[dict] = data.get("references", [])

        ref_key = kwargs.get("ref_key", "")
        if ref_key and any(r.get("ref_key") == ref_key for r in references):
            return

        entry: dict[str, Any] = {
            "ref_key": ref_key,
            "title": kwargs.get("title", ""),
            "purpose": kwargs.get("purpose", ""),
            "role": kwargs.get("role", "foundation"),
            "should_appear_in": kwargs.get("should_appear_in", []),
            "should_not_appear_in": kwargs.get("should_not_appear_in", []),
            "must_cite_before": kwargs.get("must_cite_before", []),
            "supports_contributions": kwargs.get("supports_contributions", []),
            "citation_needed_by": kwargs.get("citation_needed_by", []),
            "notes": kwargs.get("notes", ""),
        }
        references.append(entry)
        data["references"] = references
        _dump_yaml(path, data)

    def add_reviewer_risk(self, version_dir: Path, **kwargs: Any) -> None:
        """Append a reviewer risk to ``8_limitation_reviewer_risk.yaml``."""
        path = version_dir / "8_limitation_reviewer_risk.yaml"
        data = _load_yaml(path) if path.exists() else {}
        risks: list[dict] = data.get("risks", [])

        risk_id = kwargs.get("risk_id", f"R{len(risks) + 1}")
        if any(r.get("risk_id") == risk_id for r in risks):
            return

        entry: dict[str, Any] = {
            "risk_id": risk_id,
            "description": kwargs.get("description", ""),
            "severity": kwargs.get("severity", "medium"),
            "likely_appears_in": kwargs.get("likely_appears_in", ""),
            "response_strategy": kwargs.get("response_strategy", ""),
            "fallback_claim": kwargs.get("fallback_claim", ""),
            "related_contributions": kwargs.get("related_contributions", []),
            "related_sections": kwargs.get("related_sections", []),
            "status": kwargs.get("status", "open"),
            "mitigation_evidence": kwargs.get("mitigation_evidence", []),
        }
        if "inferred" in kwargs:
            entry["inferred"] = kwargs["inferred"]
        if "confidence" in kwargs:
            entry["confidence"] = kwargs["confidence"]

        risks.append(entry)
        data["risks"] = risks

        # Compact risk_register
        register: list[dict] = data.get("risk_register", [])
        if not any(r.get("risk_id") == risk_id for r in register):
            register.append(
                {
                    "risk_id": risk_id,
                    "description": entry["description"],
                    "severity": entry["severity"],
                    "status": entry["status"],
                }
            )
        data["risk_register"] = register

        _dump_yaml(path, data)

    def add_dataset(self, version_dir: Path, **kwargs: Any) -> None:
        """Append a dataset to ``9_dataset_baseline_protocol.yaml``."""
        path = version_dir / "9_dataset_baseline_protocol.yaml"
        data = _load_yaml(path) if path.exists() else {}
        datasets: list[dict] = data.get("dataset_registry", [])

        ds_id = kwargs.get("dataset_id", f"DS{len(datasets) + 1}")
        if any(d.get("dataset_id") == ds_id for d in datasets):
            return

        entry: dict[str, Any] = {
            "dataset_id": ds_id,
            "name": kwargs.get("name", ""),
            "description": kwargs.get("description", ""),
            "split": kwargs.get("split", ""),
            "split_source_citation": kwargs.get("split_source_citation", ""),
            "metrics": kwargs.get("metrics", []),
            "used_in_experiments": kwargs.get("used_in_experiments", []),
            "preprocessing": kwargs.get("preprocessing", {}),
            "download_url": kwargs.get("download_url", ""),
            "notes": kwargs.get("notes", ""),
        }
        datasets.append(entry)
        data["dataset_registry"] = datasets
        _dump_yaml(path, data)

    def add_baseline(self, version_dir: Path, **kwargs: Any) -> None:
        """Append a baseline to ``9_dataset_baseline_protocol.yaml``."""
        path = version_dir / "9_dataset_baseline_protocol.yaml"
        data = _load_yaml(path) if path.exists() else {}
        baselines: list[dict] = data.get("baseline_registry", [])

        bl_id = kwargs.get("baseline_id", f"BL{len(baselines) + 1}")
        if any(b.get("baseline_id") == bl_id for b in baselines):
            return

        entry: dict[str, Any] = {
            "baseline_id": bl_id,
            "name": kwargs.get("name", ""),
            "full_name": kwargs.get("full_name", ""),
            "source_citation": kwargs.get("source_citation", ""),
            "implementation_source": kwargs.get("implementation_source", "official"),
            "implementation_url": kwargs.get("implementation_url", ""),
            "configuration": kwargs.get("configuration", {}),
            "reproduced_by": kwargs.get("reproduced_by", ""),
            "reproduced_results": kwargs.get("reproduced_results", []),
            "used_in_experiments": kwargs.get("used_in_experiments", []),
            "notes": kwargs.get("notes", ""),
        }
        baselines.append(entry)
        data["baseline_registry"] = baselines
        _dump_yaml(path, data)

    def add_artifact(self, version_dir: Path, **kwargs: Any) -> None:
        """Append an artifact to ``10_artifact_index.yaml``."""
        path = version_dir / "10_artifact_index.yaml"
        data = _load_yaml(path) if path.exists() else {}
        artifacts: list[dict] = data.get("artifact_registry", [])

        artifact_id = kwargs.get("artifact_id", f"A{len(artifacts) + 1:03d}")
        if any(a.get("artifact_id") == artifact_id for a in artifacts):
            return

        entry: dict[str, Any] = {
            "artifact_id": artifact_id,
            "path": kwargs.get("artifact_path", ""),
            "type": kwargs.get("artifact_type", "other"),
            "purpose": kwargs.get("purpose", ""),
            "used_by": kwargs.get("used_by", []),
            "generated_by": kwargs.get("generated_by", ""),
            "git_tracked": kwargs.get("git_tracked", True),
            "created_at": datetime.now().strftime("%Y-%m-%d"),
            "last_modified": datetime.now().strftime("%Y-%m-%d"),
            "notes": kwargs.get("notes", ""),
        }
        artifacts.append(entry)
        data["artifact_registry"] = artifacts
        _dump_yaml(path, data)

    # ------------------------------------------------------------------
    # Change log
    # ------------------------------------------------------------------

    def log_change(
        self,
        version_dir: Path,
        change: str,
        why: str,
        changed_artifact: str,
        impact_severity: str = "low",
        must_update: list[dict] | None = None,
    ) -> str:
        """Append a change to ``7_change_log_impact.yaml``. Returns the new change_id."""
        path = version_dir / "7_change_log_impact.yaml"
        data = _load_yaml(path) if path.exists() else {}
        changes: list[dict] = data.get("changes", [])

        # Auto-increment ID: CH001, CH002, …
        next_num = len(changes) + 1
        change_id = f"CH{next_num:03d}"

        must_update_list: list[dict] = []
        for item in must_update or []:
            must_update_list.append(
                {
                    "artifact": item.get("artifact", ""),
                    "artifact_type": item.get("artifact_type", ""),
                    "reason": item.get("reason", ""),
                    "status": item.get("status", "pending"),
                    "resolved_at": item.get("resolved_at", ""),
                }
            )

        entry: dict[str, Any] = {
            "change_id": change_id,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "change": change,
            "why": why,
            "changed_artifact": changed_artifact,
            "impact_severity": impact_severity,
            "must_update": must_update_list,
        }
        changes.append(entry)
        data["changes"] = changes
        _dump_yaml(path, data)
        return change_id

    def get_change_impact(self, version_dir: Path, change_id: str) -> dict:
        """Return the must_update list for a given change_id."""
        path = version_dir / "7_change_log_impact.yaml"
        data = _load_yaml(path)
        for change in data.get("changes", []):
            if change.get("change_id") == change_id:
                return {
                    "change_id": change_id,
                    "must_update": change.get("must_update", []),
                }
        return {"change_id": change_id, "must_update": []}

    def get_pending_changes(self, version_dir: Path) -> list[dict]:
        """Return all must_update items with ``status=pending``."""
        path = version_dir / "7_change_log_impact.yaml"
        data = _load_yaml(path)
        pending: list[dict] = []
        for change in data.get("changes", []):
            for item in change.get("must_update", []):
                if item.get("status") == "pending":
                    pending.append(
                        {
                            "change_id": change.get("change_id"),
                            "changed_artifact": change.get("changed_artifact"),
                            **item,
                        }
                    )
        return pending

    def mark_change_resolved(
        self,
        version_dir: Path,
        change_id: str,
        artifact: str,
    ) -> bool:
        """Mark the must_update item for *artifact* in *change_id* as resolved.

        Returns True if the item was found and updated, False otherwise.
        """
        path = version_dir / "7_change_log_impact.yaml"
        data = _load_yaml(path)
        found = False
        for change in data.get("changes", []):
            if change.get("change_id") == change_id:
                for item in change.get("must_update", []):
                    if item.get("artifact") == artifact:
                        item["status"] = "resolved"
                        item["resolved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                        found = True
        if found:
            _dump_yaml(path, data)
        return found

    # ------------------------------------------------------------------
    # Verification / analysis
    # ------------------------------------------------------------------

    def verify_chain(self, version_dir: Path) -> dict:
        """Check RQ → Contribution → Experiment → Figure chain completeness.

        Returns a dict describing which nodes pass/fail chain checks.
        """
        rq_data = _load_yaml(version_dir / "6_research_question.yaml")
        contrib_data = _load_yaml(version_dir / "1_contribution.yaml")
        exp_data = _load_yaml(version_dir / "2_experiment.yaml")
        ft_data = _load_yaml(version_dir / "5_figure_table_map.yaml")

        rqs = rq_data.get("research_questions", [])
        contributions = contrib_data.get("contributions", [])
        experiments = exp_data.get("experiments", [])
        figures_tables = ft_data.get("entries", [])

        # Build lookup sets
        exp_ids: set[str] = {e.get("exp_id", "") for e in experiments}
        contrib_ids: set[str] = {c.get("contribution_id", "") for c in contributions}
        fig_ids: set[str] = {f.get("ft_id", "") for f in figures_tables}

        # Index: which experiments are linked to which RQs
        rq_to_exp: dict[str, list[str]] = {}
        for exp in experiments:
            for rq_id in exp.get("related_rqs", []):
                rq_to_exp.setdefault(rq_id, []).append(exp.get("exp_id", ""))
        # Also via tested_by_experiments in RQ
        for rq in rqs:
            rq_id = rq.get("rq_id", "")
            for eid in rq.get("tested_by_experiments", []):
                rq_to_exp.setdefault(rq_id, []).append(eid)

        # Index: which contributions have evidence
        contrib_evidence: dict[str, dict] = {}
        for c in contributions:
            cid = c.get("contribution_id", "")
            contrib_evidence[cid] = {
                "figures": c.get("evidence_figures", []),
                "tables": c.get("evidence_tables", []),
                "experiments": c.get("evidence_experiments", []),
                "sections": c.get("evidence_sections", []),
            }

        # Check 1: each RQ has ≥1 experiment
        rq_checks: list[dict] = []
        for rq in rqs:
            rq_id = rq.get("rq_id", "")
            linked_exps = list(set(rq_to_exp.get(rq_id, [])))
            rq_checks.append(
                {
                    "rq_id": rq_id,
                    "has_experiment": len(linked_exps) > 0,
                    "linked_experiments": linked_exps,
                }
            )

        # Check 2: each contribution has ≥1 evidence item
        contrib_checks: list[dict] = []
        for c in contributions:
            cid = c.get("contribution_id", "")
            ev = contrib_evidence.get(cid, {})
            all_ev = (
                ev.get("figures", [])
                + ev.get("tables", [])
                + ev.get("experiments", [])
                + ev.get("sections", [])
            )
            contrib_checks.append(
                {
                    "contribution_id": cid,
                    "has_evidence": len(all_ev) > 0,
                    "evidence_count": len(all_ev),
                }
            )

        # Check 3: each experiment links to ≥1 figure/table
        exp_checks: list[dict] = []
        for exp in experiments:
            eid = exp.get("exp_id", "")
            linked_fts = [
                ft.get("ft_id", "")
                for ft in figures_tables
                if eid in ft.get("source_experiments", [])
            ]
            exp_checks.append(
                {
                    "exp_id": eid,
                    "has_figure_table": len(linked_fts) > 0,
                    "linked_figure_tables": linked_fts,
                }
            )

        # Summary
        rq_ok = sum(1 for r in rq_checks if r["has_experiment"])
        contrib_ok = sum(1 for c in contrib_checks if c["has_evidence"])
        exp_ok = sum(1 for e in exp_checks if e["has_figure_table"])

        total_nodes = len(rqs) + len(contributions) + len(experiments)
        total_ok = rq_ok + contrib_ok + exp_ok
        chain_coverage = (total_ok / total_nodes) if total_nodes > 0 else 0.0

        return {
            "chain_coverage": round(chain_coverage, 3),
            "rq_checks": rq_checks,
            "contribution_checks": contrib_checks,
            "experiment_checks": exp_checks,
            "summary": {
                "rqs_with_experiments": f"{rq_ok}/{len(rqs)}",
                "contributions_with_evidence": f"{contrib_ok}/{len(contributions)}",
                "experiments_with_figures": f"{exp_ok}/{len(experiments)}",
            },
        }

    def find_orphans(self, version_dir: Path) -> dict:
        """Find nodes with no connections in the traceability chain."""
        graph = self.build_graph(version_dir)
        orphan_ids = graph.find_orphans()

        orphans_by_type: dict[str, list[str]] = {}
        for node_id in orphan_ids:
            node = graph.get_node(node_id)
            ntype = node.node_type if node else "unknown"
            orphans_by_type.setdefault(ntype, []).append(node_id)

        return {
            "total_orphans": len(orphan_ids),
            "orphans": orphan_ids,
            "orphans_by_type": orphans_by_type,
        }

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def build_graph(self, version_dir: Path) -> ImpactGraphService:
        """Build an :class:`ImpactGraphService` from all YAML files in *version_dir*."""
        graph = ImpactGraphService()

        # --- Research Questions (6_research_question.yaml) ---
        rq_data = _load_yaml(version_dir / "6_research_question.yaml")
        for rq in rq_data.get("research_questions", []):
            rq_id = rq.get("rq_id", "")
            if not rq_id:
                continue
            graph.add_node(rq_id, document_ref="6_research_question.yaml")
            for eid in rq.get("tested_by_experiments", []):
                graph.add_node(eid, document_ref="2_experiment.yaml")
                graph.add_edge(eid, rq_id)
            for fid in rq.get("tested_by_figures", []) + rq.get("tested_by_tables", []):
                graph.add_node(fid, document_ref="5_figure_table_map.yaml")
                graph.add_edge(fid, rq_id)
            for sid in rq.get("tested_by_sections", []):
                graph.add_node(sid, document_ref="3_section_outline.yaml")
                graph.add_edge(sid, rq_id)
            for cid in rq.get("related_contributions", []):
                graph.add_node(cid, document_ref="1_contribution.yaml")
                graph.add_edge(cid, rq_id)

        # --- Contributions (1_contribution.yaml) ---
        contrib_data = _load_yaml(version_dir / "1_contribution.yaml")
        for c in contrib_data.get("contributions", []):
            cid = c.get("contribution_id", "")
            if not cid:
                continue
            graph.add_node(cid, document_ref="1_contribution.yaml")
            for rq_id in c.get("rq_ids", []):
                graph.add_node(rq_id, document_ref="6_research_question.yaml")
                graph.add_edge(cid, rq_id)
            for fid in c.get("evidence_figures", []) + c.get("evidence_tables", []):
                graph.add_node(fid, document_ref="5_figure_table_map.yaml")
                graph.add_edge(fid, cid)
            for eid in c.get("evidence_experiments", []):
                graph.add_node(eid, document_ref="2_experiment.yaml")
                graph.add_edge(eid, cid)
            for sid in c.get("evidence_sections", []):
                graph.add_node(sid, document_ref="3_section_outline.yaml")
                graph.add_edge(sid, cid)

        # --- Experiments (2_experiment.yaml) ---
        exp_data = _load_yaml(version_dir / "2_experiment.yaml")
        for exp in exp_data.get("experiments", []):
            eid = exp.get("exp_id", "")
            if not eid:
                continue
            graph.add_node(eid, document_ref="2_experiment.yaml")
            for rq_id in exp.get("related_rqs", []):
                graph.add_node(rq_id, document_ref="6_research_question.yaml")
                graph.add_edge(eid, rq_id)
            for cid in exp.get("related_contributions", []):
                graph.add_node(cid, document_ref="1_contribution.yaml")
                graph.add_edge(eid, cid)
            used = exp.get("used_in_paper", {})
            for fid in used.get("figures", []) + used.get("tables", []):
                graph.add_node(fid, document_ref="5_figure_table_map.yaml")
                graph.add_edge(fid, eid)

        # --- Figures / Tables (5_figure_table_map.yaml) ---
        ft_data = _load_yaml(version_dir / "5_figure_table_map.yaml")
        for ft in ft_data.get("entries", []):
            ft_id = ft.get("ft_id", "")
            if not ft_id:
                continue
            graph.add_node(ft_id, document_ref="5_figure_table_map.yaml")
            for rq_id in ft.get("related_rqs", []):
                graph.add_node(rq_id, document_ref="6_research_question.yaml")
                graph.add_edge(ft_id, rq_id)
            for eid in ft.get("source_experiments", []):
                graph.add_node(eid, document_ref="2_experiment.yaml")
                graph.add_edge(ft_id, eid)

        # --- Sections (3_section_outline.yaml) ---
        sec_data = _load_yaml(version_dir / "3_section_outline.yaml")
        for sec in sec_data.get("sections", []):
            sid = sec.get("section_id", "")
            if not sid:
                continue
            graph.add_node(sid, document_ref="3_section_outline.yaml")
            for cid in sec.get("supports_contributions", []):
                graph.add_node(cid, document_ref="1_contribution.yaml")
                graph.add_edge(sid, cid)
            for rq_id in sec.get("related_rqs", []):
                graph.add_node(rq_id, document_ref="6_research_question.yaml")
                graph.add_edge(sid, rq_id)

        # --- References (4_citation_map.yaml) ---
        ref_data = _load_yaml(version_dir / "4_citation_map.yaml")
        for ref in ref_data.get("references", []):
            ref_key = ref.get("ref_key", "")
            if not ref_key:
                continue
            ref_id = f"Ref:{ref_key}"
            graph.add_node(ref_id, document_ref="4_citation_map.yaml")
            for cid in ref.get("supports_contributions", []):
                graph.add_node(cid, document_ref="1_contribution.yaml")
                graph.add_edge(ref_id, cid)

        # --- Risks (8_limitation_reviewer_risk.yaml) ---
        risk_data = _load_yaml(version_dir / "8_limitation_reviewer_risk.yaml")
        for risk in risk_data.get("risks", []):
            risk_id = risk.get("risk_id", "")
            if not risk_id:
                continue
            graph.add_node(risk_id, document_ref="8_limitation_reviewer_risk.yaml")
            for cid in risk.get("related_contributions", []):
                graph.add_node(cid, document_ref="1_contribution.yaml")
                graph.add_edge(risk_id, cid)

        # --- Artifacts (10_artifact_index.yaml) ---
        artifact_data = _load_yaml(version_dir / "10_artifact_index.yaml")
        for artifact in artifact_data.get("artifact_registry", []):
            aid = artifact.get("artifact_id", "")
            if not aid:
                continue
            graph.add_node(aid, document_ref="10_artifact_index.yaml")
            for dep_id in artifact.get("used_by", []):
                graph.add_node(dep_id)
                graph.add_edge(dep_id, aid)

        # --- Change log (7_change_log_impact.yaml) ---
        change_data = _load_yaml(version_dir / "7_change_log_impact.yaml")
        for change in change_data.get("changes", []):
            ch_id = change.get("change_id", "")
            if not ch_id:
                continue
            graph.add_node(ch_id, document_ref="7_change_log_impact.yaml")
            artifact = change.get("changed_artifact", "")
            if artifact:
                graph.add_node(artifact)
                graph.add_edge(ch_id, artifact)

        return graph

    # ------------------------------------------------------------------
    # Index generation
    # ------------------------------------------------------------------

    def generate_index(self, version_dir: Path) -> TraceabilityIndex:
        """Generate a summary :class:`TraceabilityIndex` for *version_dir*."""
        rq_data = _load_yaml(version_dir / "6_research_question.yaml")
        contrib_data = _load_yaml(version_dir / "1_contribution.yaml")
        exp_data = _load_yaml(version_dir / "2_experiment.yaml")
        ft_data = _load_yaml(version_dir / "5_figure_table_map.yaml")
        ref_data = _load_yaml(version_dir / "4_citation_map.yaml")
        risk_data = _load_yaml(version_dir / "8_limitation_reviewer_risk.yaml")
        artifact_data = _load_yaml(version_dir / "10_artifact_index.yaml")
        change_data = _load_yaml(version_dir / "7_change_log_impact.yaml")

        rq_count = len(rq_data.get("research_questions", []))
        contribution_count = len(contrib_data.get("contributions", []))
        experiment_count = len(exp_data.get("experiments", []))
        figure_table_count = len(ft_data.get("entries", []))
        reference_count = len(ref_data.get("references", []))
        risk_count = len(risk_data.get("risks", []))
        artifact_count = len(artifact_data.get("artifact_registry", []))

        # Pending changes
        pending_changes = 0
        for change in change_data.get("changes", []):
            for item in change.get("must_update", []):
                if item.get("status") == "pending":
                    pending_changes += 1

        # Chain coverage via verify_chain
        chain_result = self.verify_chain(version_dir)
        chain_coverage = chain_result.get("chain_coverage", 0.0)
        chain_completeness = chain_result

        # Orphan detection
        orphan_result = self.find_orphans(version_dir)

        return TraceabilityIndex(
            generated_at=datetime.now().isoformat(),
            paper_path=str(self.paper_path),
            trace_dir=str(version_dir),
            output_dir=str(self.trace_root),
            chain_coverage=chain_coverage,
            rq_count=rq_count,
            contribution_count=contribution_count,
            experiment_count=experiment_count,
            figure_table_count=figure_table_count,
            reference_count=reference_count,
            risk_count=risk_count,
            artifact_count=artifact_count,
            pending_changes=pending_changes,
            orphan_detection=orphan_result.get("orphans_by_type", {}),
            chain_completeness=chain_completeness,
        )

    # ------------------------------------------------------------------
    # Paper scanning
    # ------------------------------------------------------------------

    def list_active_papers(
        self,
        search_root: Path,
        max_depth: int = 3,
    ) -> list[dict]:
        """Scan *search_root* for active paper directories.

        Skips directories matching :data:`~crane.models.traceability.SKIP_KEYWORDS`.
        Returns a list of dicts: ``{dir_name, path, paper_files, has_trace, trace_version}``.
        """
        results: list[dict] = []
        self._scan_papers(search_root, results, current_depth=0, max_depth=max_depth)
        return results

    def _scan_papers(
        self,
        root: Path,
        results: list,
        current_depth: int,
        max_depth: int,
    ) -> None:
        if current_depth > max_depth:
            return
        try:
            children = sorted(root.iterdir())
        except PermissionError:
            return
        for child in children:
            if not child.is_dir():
                continue
            if not is_active_paper_dir(child.name):
                continue
            paper_files = list(child.glob("*.tex")) + list(child.glob("*.pdf"))
            if paper_files:
                trace_dir = child / TRACE_DIR_NAME
                has_trace = trace_dir.exists()
                latest_version: int | None = None
                if has_trace:
                    versions = [
                        int(m.group(1))
                        for d in trace_dir.iterdir()
                        if d.is_dir() and (m := re.fullmatch(r"v(\d+)", d.name))
                    ]
                    latest_version = max(versions, default=None) if versions else None
                results.append(
                    {
                        "dir_name": child.name,
                        "path": str(child),
                        "paper_files": [str(f) for f in paper_files],
                        "has_trace": has_trace,
                        "trace_version": latest_version,
                    }
                )
            else:
                self._scan_papers(child, results, current_depth + 1, max_depth)
