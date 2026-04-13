"""Traceability inference: extract RQs, contributions, experiments, risks from paper content."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from crane.models.traceability import (
    ContributionItem,
    ExperimentEntry,
    ResearchQuestion,
    ReviewerRisk,
)
from crane.services.traceability_service import TraceabilityService


class TraceabilityInferenceService:
    """Infer traceability structure from paper content using heuristic patterns.

    No LLM call is made — this service performs lightweight regex-based
    extraction so that a useful first-pass trace is available immediately.
    """

    TEMPLATE_DIR = Path(__file__).parent.parent / "config" / "templates" / "llm"

    def __init__(self, paper_path: str = "") -> None:
        self.paper_path = Path(paper_path) if paper_path else Path()
        self._content_cache: str | None = None

    # ------------------------------------------------------------------
    # Content helpers
    # ------------------------------------------------------------------

    def _read_paper_content(self, max_chars: int = 8000) -> str:
        """Read paper content (LaTeX or plain text). Truncate to *max_chars*."""
        path = self.paper_path
        if not path.exists():
            return ""
        text = path.read_text(encoding="utf-8", errors="ignore")
        if path.suffix == ".tex":
            # Strip common LaTeX syntax for cleaner pattern matching
            text = re.sub(r"\\[a-zA-Z]+\{[^}]*\}", " ", text)
            text = re.sub(r"\\[a-zA-Z]+", " ", text)
            text = re.sub(r"\{|\}", " ", text)
            text = re.sub(r"%.*$", "", text, flags=re.MULTILINE)
            text = re.sub(r"\s+", " ", text)
        return text[:max_chars]

    def _load_template(self, name: str) -> str:
        """Load an LLM template by filename (returns empty string if not found)."""
        path = self.TEMPLATE_DIR / name
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _fill_template(self, template: str, paper_content: str) -> str:
        """Substitute ``{paper_content}`` placeholder in *template*."""
        return template.replace("{paper_content}", paper_content)

    # ------------------------------------------------------------------
    # Inference methods
    # ------------------------------------------------------------------

    def infer_research_questions(self) -> list[ResearchQuestion]:
        """Extract research questions from paper content using heuristic patterns."""
        content = self._read_paper_content()
        rqs: list[ResearchQuestion] = []

        rq_patterns = [
            r"RQ\d+[:\.]?\s+([^\n\.]{20,200})",
            r"research question[:\s]+([^\n\.]{20,200})",
            r"we investigate\s+([^\n\.]{20,200})",
            r"we ask\s+([^\n\.]{20,200})",
            r"does\s+([^\n\.]{10,100})\?",
            r"can\s+([^\n\.]{10,100})\?",
        ]

        seen: set[str] = set()
        rq_num = 1
        for pattern in rq_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                text = match.group(1).strip()
                if text not in seen and len(text) > 15:
                    seen.add(text)
                    rqs.append(
                        ResearchQuestion(
                            rq_id=f"RQ{rq_num}",
                            text=text,
                            motivation="(inferred — review and edit)",
                            hypothesis="(inferred — review and edit)",
                            status="draft",
                            inferred=True,
                            confidence=0.7,
                        )
                    )
                    rq_num += 1
                    if rq_num > 5:
                        break
            if rq_num > 5:
                break

        if not rqs:
            rqs.append(
                ResearchQuestion(
                    rq_id="RQ1",
                    text="(auto-generated placeholder — edit to reflect your actual RQ)",
                    motivation="",
                    hypothesis="",
                    status="draft",
                    inferred=True,
                    confidence=0.3,
                )
            )

        return rqs

    def infer_contributions(self) -> list[ContributionItem]:
        """Extract contributions from paper content using heuristic patterns."""
        content = self._read_paper_content()
        contributions: list[ContributionItem] = []

        patterns = [
            r"we propose\s+([^\n\.]{20,200})",
            r"we present\s+([^\n\.]{20,200})",
            r"we introduce\s+([^\n\.]{20,200})",
            r"we develop\s+([^\n\.]{20,200})",
            r"our contribution[s]?[:\s]+([^\n\.]{20,200})",
            r"our main contribution[s]?[:\s]+([^\n\.]{20,200})",
            r"the contribution[s]?[:\s]+([^\n\.]{20,200})",
            r"we demonstrate\s+([^\n\.]{20,200})",
        ]

        seen: set[str] = set()
        c_num = 1
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                text = match.group(1).strip()
                if text not in seen and len(text) > 15:
                    seen.add(text)
                    contributions.append(
                        ContributionItem(
                            contribution_id=f"C{c_num}",
                            claim=text,
                            why_it_matters="(inferred — review and edit)",
                            strongest_defensible_wording=text,
                            status="draft",
                            inferred=True,
                            confidence=0.7,
                        )
                    )
                    c_num += 1
                    if c_num > 5:
                        break
            if c_num > 5:
                break

        if not contributions:
            contributions.append(
                ContributionItem(
                    contribution_id="C1",
                    claim="(auto-generated placeholder — edit to reflect your actual contribution)",
                    why_it_matters="",
                    strongest_defensible_wording="",
                    status="draft",
                    inferred=True,
                    confidence=0.3,
                )
            )

        return contributions

    def infer_experiments(self) -> list[ExperimentEntry]:
        """Extract experiment descriptions using heuristic patterns."""
        content = self._read_paper_content()
        experiments: list[ExperimentEntry] = []

        patterns = [
            r"experiment[s]?\s+\d+[:\s]+([^\n\.]{20,200})",
            r"we evaluate\s+([^\n\.]{20,200})",
            r"we test\s+([^\n\.]{20,200})",
            r"we compare\s+([^\n\.]{20,200})",
            r"we conducted\s+([^\n\.]{20,200})",
        ]

        seen: set[str] = set()
        e_num = 1
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                text = match.group(1).strip()
                if text not in seen and len(text) > 15:
                    seen.add(text)
                    experiments.append(
                        ExperimentEntry(
                            exp_id=f"E{e_num}",
                            goal=text,
                            status="done",
                            inferred=True,
                            confidence=0.6,
                        )
                    )
                    e_num += 1
                    if e_num > 5:
                        break
            if e_num > 5:
                break

        if not experiments:
            experiments.append(
                ExperimentEntry(
                    exp_id="E1",
                    goal="(auto-generated placeholder — edit to reflect your experiments)",
                    status="pending",
                    inferred=True,
                    confidence=0.3,
                )
            )

        return experiments

    def infer_risks(self) -> list[ReviewerRisk]:
        """Extract reviewer risks using signal-word heuristics."""
        content = self._read_paper_content()
        risks: list[ReviewerRisk] = []

        risk_signals: list[tuple[str, str, str]] = [
            ("limitation", "medium", "Limitation section"),
            ("future work", "low", "Conclusion"),
            ("we assume", "medium", "Methodology"),
            ("we do not", "medium", "Methodology"),
            ("without loss of generality", "medium", "Reviewer 2"),
            ("state of the art", "high", "Related Work"),
            ("state-of-the-art", "high", "Related Work"),
            ("outperform", "high", "Results"),
            ("significant improvement", "high", "Abstract"),
            ("novel", "medium", "Introduction"),
        ]

        r_num = 1
        seen: set[str] = set()
        for signal, severity, location in risk_signals:
            if signal.lower() in content.lower() and signal not in seen:
                seen.add(signal)
                risks.append(
                    ReviewerRisk(
                        risk_id=f"R{r_num}",
                        description=f"Paper uses '{signal}' — reviewers may challenge this",
                        severity=severity,
                        likely_appears_in=location,
                        response_strategy="(inferred — add specific response strategy)",
                        status="open",
                        inferred=True,
                        confidence=0.6,
                    )
                )
                r_num += 1
                if r_num > 6:
                    break

        if not risks:
            risks.append(
                ReviewerRisk(
                    risk_id="R1",
                    description="(auto-generated placeholder — add specific reviewer risks)",
                    severity="medium",
                    likely_appears_in="Reviewer 2",
                    response_strategy="",
                    status="open",
                    inferred=True,
                    confidence=0.3,
                )
            )

        return risks

    # ------------------------------------------------------------------
    # Combined inference
    # ------------------------------------------------------------------

    def infer_all(self) -> dict[str, Any]:
        """Run all inference methods and return structured results."""
        return {
            "research_questions": self.infer_research_questions(),
            "contributions": self.infer_contributions(),
            "experiments": self.infer_experiments(),
            "risks": self.infer_risks(),
        }

    # ------------------------------------------------------------------
    # Write inferred items into YAML files
    # ------------------------------------------------------------------

    def write_to_traceability_dir(
        self,
        version_dir: Path,
        inferred: dict[str, Any],
        traceability_service: TraceabilityService,
    ) -> dict[str, int]:
        """Write inferred items into the version directory's YAML files.

        Returns a count dict ``{rqs, contributions, experiments, risks}``.
        """
        counts: dict[str, int] = {
            "rqs": 0,
            "contributions": 0,
            "experiments": 0,
            "risks": 0,
        }

        for rq in inferred.get("research_questions", []):
            traceability_service.add_research_question(
                version_dir,
                rq_id=rq.rq_id,
                text=rq.text,
                motivation=rq.motivation,
                hypothesis=rq.hypothesis,
            )
            counts["rqs"] += 1

        for c in inferred.get("contributions", []):
            traceability_service.add_contribution(
                version_dir,
                contribution_id=c.contribution_id,
                claim=c.claim,
                why_it_matters=c.why_it_matters,
                strongest_defensible_wording=c.strongest_defensible_wording,
                status=c.status,
                inferred=c.inferred,
                confidence=c.confidence,
            )
            counts["contributions"] += 1

        for e in inferred.get("experiments", []):
            traceability_service.add_experiment(
                version_dir,
                exp_id=e.exp_id,
                goal=e.goal,
                status=e.status,
                inferred=e.inferred,
                confidence=e.confidence,
            )
            counts["experiments"] += 1

        for r in inferred.get("risks", []):
            traceability_service.add_reviewer_risk(
                version_dir,
                risk_id=r.risk_id,
                description=r.description,
                severity=r.severity,
                likely_appears_in=r.likely_appears_in,
                response_strategy=r.response_strategy,
                status=r.status,
                inferred=r.inferred,
                confidence=r.confidence,
            )
            counts["risks"] += 1

        return counts
