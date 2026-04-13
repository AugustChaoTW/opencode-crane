"""
Paper Traceability System models for CRANE.

Provides dataclasses representing every node in the paper traceability graph:
research questions, contributions, experiments, figures/tables, references,
sections, reviewer risks, datasets, baselines, artifacts, change-log entries,
and the top-level index.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TRACE_DIR_NAME = "_paper_trace"

SKIP_KEYWORDS = [
    "reject",
    "nogo",
    "no-go",
    "no_go",
    "withdrawn",
    "withdraw",
    "abandon",
    "cancelled",
    "cancel",
]

NODE_TYPES = frozenset([
    "rq",
    "contribution",
    "experiment",
    "figure",
    "table",
    "section",
    "reference",
    "risk",
    "artifact",
])

SEVERITY_LEVELS = ("low", "medium", "high", "critical")
STATUSES = (
    "draft",
    "active",
    "retired",
    "pending",
    "final",
    "deprecated",
    "open",
    "mitigated",
    "resolved",
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def is_active_paper_dir(dir_name: str) -> bool:
    """Return True if *dir_name* does not match any skip keyword (case-insensitive)."""
    lower = dir_name.lower()
    return not any(kw in lower for kw in SKIP_KEYWORDS)


def get_node_type_from_id(node_id: str) -> str:
    """Infer node type from ID format.

    Mapping:
        RQ{n}      → "rq"
        C{n}       → "contribution"
        E{n}       → "experiment"
        Fig:{n}    → "figure"
        T:{n}      → "table"
        Sec:{n}    → "section"
        Ref:{key}  → "reference"
        R{n}       → "risk"
        A{nnn}     → "artifact"
        CH{nnn}    → "change"
        else       → "unknown"
    """
    if re.fullmatch(r"RQ\d+", node_id):
        return "rq"
    if re.fullmatch(r"C\d+", node_id):
        return "contribution"
    if re.fullmatch(r"E\d+", node_id):
        return "experiment"
    if re.fullmatch(r"Fig:.+", node_id):
        return "figure"
    if re.fullmatch(r"T:.+", node_id):
        return "table"
    if re.fullmatch(r"Sec:.+", node_id):
        return "section"
    if re.fullmatch(r"Ref:.+", node_id):
        return "reference"
    if re.fullmatch(r"R\d+", node_id):
        return "risk"
    if re.fullmatch(r"A\d+", node_id):
        return "artifact"
    if re.fullmatch(r"CH\d+", node_id):
        return "change"
    return "unknown"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ResearchQuestion:
    """A single research question in the paper."""

    rq_id: str
    text: str
    motivation: str
    hypothesis: str
    tested_by_experiments: list[str] = field(default_factory=list)
    tested_by_figures: list[str] = field(default_factory=list)
    tested_by_tables: list[str] = field(default_factory=list)
    tested_by_sections: list[str] = field(default_factory=list)
    related_contributions: list[str] = field(default_factory=list)
    status: str = "draft"
    inferred: bool = False
    confidence: float = 1.0


@dataclass
class ContributionItem:
    """A claimed contribution with evidence links."""

    contribution_id: str
    claim: str
    why_it_matters: str
    strongest_defensible_wording: str
    avoid_overclaiming: list[str] = field(default_factory=list)
    reviewer_risk: str = ""
    response_strategy: str = ""
    rq_ids: list[str] = field(default_factory=list)
    evidence_figures: list[str] = field(default_factory=list)
    evidence_tables: list[str] = field(default_factory=list)
    evidence_sections: list[str] = field(default_factory=list)
    evidence_experiments: list[str] = field(default_factory=list)
    status: str = "draft"
    inferred: bool = False
    confidence: float = 1.0


@dataclass
class ExperimentSetting:
    """Hardware / software / hyper-parameter context for an experiment."""

    dataset: str = ""
    model: str = ""
    training_epochs: int | None = None
    batch_size: int | None = None
    seed: int | list[int] | None = None
    hardware: str = ""
    framework: str = ""
    hyperparameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class CanonicalNumber:
    """A locked numeric result to be cited in the paper."""

    value: float | str | None = None
    locked: bool = False
    locked_at: str = ""


@dataclass
class ExperimentEntry:
    """One experiment with full provenance."""

    exp_id: str
    goal: str
    setting: ExperimentSetting = field(default_factory=ExperimentSetting)
    final_numbers: dict[str, Any] = field(default_factory=dict)
    canonical_number: CanonicalNumber = field(default_factory=CanonicalNumber)
    deprecated_numbers: list[dict[str, Any]] = field(default_factory=list)
    citation_needed: list[dict[str, str]] = field(default_factory=list)
    output_files: list[dict[str, str]] = field(default_factory=list)
    controlled_variables: dict[str, list[str]] = field(default_factory=dict)
    used_in_paper: dict[str, list[str]] = field(default_factory=dict)
    related_contributions: list[str] = field(default_factory=list)
    related_rqs: list[str] = field(default_factory=list)
    notes: str = ""
    status: str = "pending"
    inferred: bool = False
    confidence: float = 1.0


@dataclass
class AxisSpec:
    """Axis specification for a visualization."""

    label: str = ""
    range: list[float] | None = None


@dataclass
class VisualizationSpec:
    """Specification for a figure or table visualization."""

    type: str = ""
    x_axis: AxisSpec = field(default_factory=AxisSpec)
    y_axis: AxisSpec = field(default_factory=AxisSpec)
    columns: list[str] = field(default_factory=list)
    annotations: dict[str, str] = field(default_factory=dict)
    style_rules: list[str] = field(default_factory=list)


@dataclass
class FigureTableEntry:
    """A figure or table in the paper, linked to experiments and contributions."""

    ft_id: str
    type: str
    purpose: str
    claim_supported: str
    related_rqs: list[str] = field(default_factory=list)
    source_experiments: list[str] = field(default_factory=list)
    exact_numbers: list[dict[str, Any]] = field(default_factory=list)
    final_values: dict[str, Any] = field(default_factory=dict)
    visualization: VisualizationSpec = field(default_factory=VisualizationSpec)
    caption_draft: str = ""
    presentation_rules: dict[str, Any] = field(default_factory=dict)
    mentioned_in: list[str] = field(default_factory=list)
    needs_update_if: list[str] = field(default_factory=list)
    text_reference_rule: str = ""
    inferred: bool = False
    confidence: float = 1.0


@dataclass
class ReferenceMapEntry:
    """A bibliographic reference with placement rules."""

    ref_key: str
    title: str
    purpose: str
    role: str
    should_appear_in: list[str] = field(default_factory=list)
    should_not_appear_in: list[str] = field(default_factory=list)
    must_cite_before: list[str] = field(default_factory=list)
    supports_contributions: list[str] = field(default_factory=list)
    citation_needed_by: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class SectionEntry:
    """A section (or subsection) of the paper."""

    section_id: str
    name: str
    goal: str
    must_include: list[str] = field(default_factory=list)
    must_not_do: list[str] = field(default_factory=list)
    citations_needed: list[str] = field(default_factory=list)
    supports_contributions: list[str] = field(default_factory=list)
    related_rqs: list[str] = field(default_factory=list)
    figures: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    reviewer_check: str = ""
    notes: str = ""
    subsections: list[SectionEntry] = field(default_factory=list)


@dataclass
class ReviewerRisk:
    """A reviewer risk with mitigation strategy."""

    risk_id: str
    description: str
    severity: str
    likely_appears_in: str
    response_strategy: str
    fallback_claim: str = ""
    related_contributions: list[str] = field(default_factory=list)
    related_sections: list[str] = field(default_factory=list)
    status: str = "open"
    mitigation_evidence: list[str] = field(default_factory=list)
    inferred: bool = False
    confidence: float = 1.0


@dataclass
class DatasetSpec:
    """A dataset used in experiments."""

    dataset_id: str
    name: str
    description: str = ""
    split: str = ""
    split_source_citation: str = ""
    metrics: list[str] = field(default_factory=list)
    used_in_experiments: list[str] = field(default_factory=list)
    preprocessing: dict[str, str] = field(default_factory=dict)
    download_url: str = ""
    notes: str = ""


@dataclass
class BaselineSpec:
    """A baseline method for comparison."""

    baseline_id: str
    name: str
    full_name: str = ""
    source_citation: str = ""
    implementation_source: str = ""
    implementation_url: str = ""
    configuration: dict[str, Any] = field(default_factory=dict)
    reproduced_by: str = ""
    reproduced_results: list[dict[str, Any]] = field(default_factory=list)
    used_in_experiments: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class ArtifactEntry:
    """A tracked artifact (file, notebook, checkpoint, …)."""

    artifact_id: str
    path: str
    type: str
    purpose: str
    used_by: list[str] = field(default_factory=list)
    generated_by: str = ""
    git_tracked: bool = True
    created_at: str = ""
    last_modified: str = ""
    notes: str = ""


@dataclass
class MustUpdateItem:
    """One item in the must-update list of a change-log entry."""

    artifact: str
    artifact_type: str
    reason: str
    status: str = "pending"
    resolved_at: str = ""


@dataclass
class ChangeLogEntry:
    """A recorded change and its downstream impact."""

    change_id: str
    date: str
    change: str
    why: str
    changed_artifact: str
    impact_severity: str
    must_update: list[MustUpdateItem] = field(default_factory=list)

    @property
    def pending_count(self) -> int:
        """Return the number of must-update items that are still pending."""
        return sum(1 for item in self.must_update if item.status == "pending")

    @property
    def is_resolved(self) -> bool:
        """Return True when every must-update item has been resolved."""
        return all(item.status != "pending" for item in self.must_update)


@dataclass
class TraceabilityNode:
    """A node in the traceability graph."""

    node_id: str
    node_type: str
    depends_on: list[str] = field(default_factory=list)
    depended_by: list[str] = field(default_factory=list)
    document_ref: str = ""
    inferred: bool = False


@dataclass
class TraceabilityIndex:
    """Top-level summary of the traceability document."""

    generated_at: str
    paper_path: str
    trace_dir: str
    output_dir: str
    chain_coverage: float
    rq_count: int
    contribution_count: int
    experiment_count: int
    figure_table_count: int
    reference_count: int
    risk_count: int
    artifact_count: int
    pending_changes: int
    orphan_detection: dict[str, list[str]] = field(default_factory=dict)
    chain_completeness: dict[str, dict] = field(default_factory=dict)
