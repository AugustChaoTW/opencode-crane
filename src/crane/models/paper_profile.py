from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PaperType(str, Enum):
    EMPIRICAL = "empirical"
    SYSTEM = "system"
    THEORETICAL = "theoretical"
    SURVEY = "survey"
    UNKNOWN = "unknown"


class EvidenceSignal(str, Enum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    MISSING = "missing"


class EvidencePattern(str, Enum):
    BENCHMARK_HEAVY = "benchmark_heavy"
    APPLICATION_HEAVY = "application_heavy"
    THEOREM_HEAVY = "theorem_heavy"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class NoveltyShape(str, Enum):
    NEW_METHOD = "new_method"
    NEW_APPLICATION = "new_application"
    NEW_ANALYSIS = "new_analysis"
    INCREMENTAL = "incremental"
    UNKNOWN = "unknown"


class RevisionPriority(str, Enum):
    IMMEDIATE = "immediate"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"


class RevisionEffort(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class EvidenceItem:
    claim: str
    section: str
    span: str
    signal: EvidenceSignal = EvidenceSignal.OBSERVED
    confidence: float = 1.0

    def __post_init__(self):
        if not self.claim:
            raise ValueError("claim cannot be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass
class EvidenceLedger:
    items: list[EvidenceItem] = field(default_factory=list)

    def by_section(self, section: str) -> list[EvidenceItem]:
        return [i for i in self.items if i.section == section]

    def by_signal(self, signal: EvidenceSignal) -> list[EvidenceItem]:
        return [i for i in self.items if i.signal == signal]

    @property
    def observed_count(self) -> int:
        return len(self.by_signal(EvidenceSignal.OBSERVED))

    @property
    def missing_count(self) -> int:
        return len(self.by_signal(EvidenceSignal.MISSING))


@dataclass
class PaperProfile:
    paper_type: PaperType = PaperType.UNKNOWN
    method_family: str = ""
    evidence_pattern: EvidencePattern = EvidencePattern.UNKNOWN
    validation_scale: str = ""
    citation_neighborhood: list[str] = field(default_factory=list)
    novelty_shape: NoveltyShape = NoveltyShape.UNKNOWN
    reproducibility_maturity: float = 0.0
    problem_domain: str = ""
    keywords: list[str] = field(default_factory=list)
    word_count: int = 0
    has_code: bool = False
    has_appendix: bool = False
    num_figures: int = 0
    num_tables: int = 0
    num_equations: int = 0
    num_references: int = 0

    def __post_init__(self):
        if not 0.0 <= self.reproducibility_maturity <= 1.0:
            raise ValueError("reproducibility_maturity must be between 0.0 and 1.0")


@dataclass
class DimensionScore:
    dimension: str
    score: float
    confidence: float
    reason_codes: list[str] = field(default_factory=list)
    evidence_spans: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.dimension:
            raise ValueError("dimension cannot be empty")
        if not 0.0 <= self.score <= 100.0:
            raise ValueError("score must be between 0.0 and 100.0")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass
class JournalFit:
    journal_name: str
    scope_fit: float = 0.0
    contribution_style_fit: float = 0.0
    evaluation_style_fit: float = 0.0
    citation_neighborhood_fit: float = 0.0
    operational_fit: float = 0.0
    overall_fit: float = 0.0
    desk_reject_risk: float = 0.0
    risk_factors: list[str] = field(default_factory=list)
    recommendation: str = ""

    def __post_init__(self):
        if not self.journal_name:
            raise ValueError("journal_name cannot be empty")

    def calculate_overall(self) -> float:
        self.overall_fit = (
            0.35 * self.scope_fit
            + 0.20 * self.contribution_style_fit
            + 0.20 * self.evaluation_style_fit
            + 0.15 * self.citation_neighborhood_fit
            + 0.10 * self.operational_fit
        )
        return self.overall_fit


@dataclass
class RevisionItem:
    dimension: str
    suggestion: str
    priority: RevisionPriority
    effort: RevisionEffort
    expected_impact: float = 0.0
    depends_on: list[str] = field(default_factory=list)
    status: str = "pending"


@dataclass
class RevisionPlan:
    items: list[RevisionItem] = field(default_factory=list)
    current_score: float = 0.0
    projected_score: float = 0.0

    def by_priority(self, priority: RevisionPriority) -> list[RevisionItem]:
        return [i for i in self.items if i.priority == priority]

    @property
    def immediate_items(self) -> list[RevisionItem]:
        return self.by_priority(RevisionPriority.IMMEDIATE)

    @property
    def pending_items(self) -> list[RevisionItem]:
        return [i for i in self.items if i.status == "pending"]

    def sort_by_impact(self) -> None:
        self.items.sort(key=lambda x: x.expected_impact, reverse=True)
