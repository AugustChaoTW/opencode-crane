# pyright: reportMissingImports=false
from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from crane.config.domain_packs.schema import DomainPackLoader
from crane.models.writing_style_models import (
    ExemplarSnippet,
    RewriteSuggestion,
    SectionDiagnosis,
    StyleGuide,
    StyleIssue,
    StyleMetrics,
)
from crane.services.section_chunker import Section, SectionChunker
from crane.services.style_guide_builder import StyleGuideBuilder

_CRITICAL_THRESHOLD = 0.40
_MAJOR_THRESHOLD = 0.20
_MINOR_THRESHOLD = 0.10

_METRIC_LABELS: dict[str, str] = {
    "flesch_kincaid_grade": "Flesch-Kincaid grade level",
    "smog_index": "SMOG readability index",
    "avg_sentence_length": "average sentence length",
    "avg_word_length": "average word length",
    "type_token_ratio": "lexical diversity (type-token ratio)",
    "technical_term_density": "technical term density",
    "passive_voice_ratio": "passive voice ratio",
    "nominalization_ratio": "nominalisation ratio",
}

_METRIC_CATEGORIES: dict[str, str] = {
    "flesch_kincaid_grade": "readability",
    "smog_index": "readability",
    "avg_sentence_length": "readability",
    "avg_word_length": "readability",
    "type_token_ratio": "vocabulary",
    "technical_term_density": "vocabulary",
    "passive_voice_ratio": "grammar",
    "nominalization_ratio": "grammar",
}

_DOMAIN_METRIC_WEIGHTS: dict[str, dict[str, float]] = {
    "ai_ml": {
        "technical_term_density": 1.3,
        "passive_voice_ratio": 0.8,
        "avg_sentence_length": 1.1,
    },
    "cybersecurity": {
        "technical_term_density": 1.4,
        "passive_voice_ratio": 0.7,
        "nominalization_ratio": 1.2,
    },
    "iot": {
        "technical_term_density": 1.2,
        "avg_sentence_length": 1.0,
    },
    "mis": {
        "passive_voice_ratio": 1.3,
        "nominalization_ratio": 1.1,
        "type_token_ratio": 1.2,
    },
}


def _flatten_metrics(metrics: StyleMetrics) -> dict[str, float]:
    return {
        "flesch_kincaid_grade": metrics.readability.flesch_kincaid_grade,
        "smog_index": metrics.readability.smog_index,
        "avg_sentence_length": float(metrics.readability.avg_sentence_length),
        "avg_word_length": metrics.readability.avg_word_length,
        "type_token_ratio": metrics.vocabulary.type_token_ratio,
        "technical_term_density": metrics.vocabulary.technical_term_density,
        "passive_voice_ratio": metrics.grammar.passive_voice_ratio,
        "nominalization_ratio": metrics.grammar.nominalization_ratio,
    }


def _target_dict_to_metrics(targets: dict[str, float]) -> StyleMetrics:
    from crane.models.writing_style_models import (
        ArgumentationMetrics,
        GrammarMetrics,
        ReadabilityMetrics,
        VocabularyMetrics,
    )

    return StyleMetrics(
        readability=ReadabilityMetrics(
            flesch_kincaid_grade=targets.get("flesch_kincaid_grade", 0.0),
            smog_index=targets.get("smog_index", 0.0),
            avg_sentence_length=int(targets.get("avg_sentence_length", 0)),
            avg_word_length=targets.get("avg_word_length", 0.0),
        ),
        vocabulary=VocabularyMetrics(
            type_token_ratio=targets.get("type_token_ratio", 0.0),
            technical_term_density=targets.get("technical_term_density", 0.0),
        ),
        grammar=GrammarMetrics(
            passive_voice_ratio=targets.get("passive_voice_ratio", 0.0),
            nominalization_ratio=targets.get("nominalization_ratio", 0.0),
        ),
        argumentation=ArgumentationMetrics(),
    )


def _dict_to_style_metrics(raw: dict[str, Any]) -> StyleMetrics:
    from crane.models.writing_style_models import (
        ArgumentationMetrics,
        GrammarMetrics,
        ReadabilityMetrics,
        VocabularyMetrics,
    )

    return StyleMetrics(
        readability=ReadabilityMetrics(
            flesch_kincaid_grade=float(raw.get("flesch_kincaid_grade", 0.0)),
            smog_index=float(raw.get("smog_index", 0.0)),
            avg_sentence_length=int(raw.get("avg_sentence_length", 0)),
            avg_word_length=float(raw.get("avg_word_length", 0.0)),
        ),
        vocabulary=VocabularyMetrics(
            type_token_ratio=float(raw.get("type_token_ratio", 0.0)),
            technical_term_density=float(raw.get("technical_term_density", 0.0)),
        ),
        grammar=GrammarMetrics(
            passive_voice_ratio=float(raw.get("passive_voice_ratio", 0.0)),
            nominalization_ratio=float(raw.get("nominalization_ratio", 0.0)),
        ),
        argumentation=ArgumentationMetrics(),
    )


def _classify_severity(deviation: float) -> str:
    if deviation >= _CRITICAL_THRESHOLD:
        return "critical"
    if deviation >= _MAJOR_THRESHOLD:
        return "major"
    return "minor"


def _extract_example_span(metric_name: str, text: str) -> str:
    if metric_name == "passive_voice_ratio":
        match = re.search(
            r"\b(?:is|are|was|were|been|being|be)\s+\w+(?:ed|en)\b",
            text,
            re.IGNORECASE,
        )
        if match:
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 20)
            return text[start:end].strip()

    if metric_name == "avg_sentence_length":
        sentences = re.split(r"[.!?]+", text)
        long_sents = [s.strip() for s in sentences if len(s.split()) > 35]
        if long_sents:
            return long_sents[0][:120] + ("..." if len(long_sents[0]) > 120 else "")

    if metric_name == "nominalization_ratio":
        match = re.search(
            r"\b\w+(?:tion|ment|ness|ity|ence|ance)\b",
            text,
            re.IGNORECASE,
        )
        if match:
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 20)
            return text[start:end].strip()

    return ""


def _recommend_fix(metric_name: str, direction: str, current: float, target: float) -> str:
    fixes: dict[str, dict[str, str]] = {
        "passive_voice_ratio": {
            "high": "Convert passive constructions to active voice (e.g. 'X was computed' -> 'We computed X').",
            "low": "Consider using passive voice for objectivity in Methods/Results sections.",
        },
        "avg_sentence_length": {
            "high": "Break long sentences into shorter ones. Target ~20-25 words per sentence.",
            "low": "Combine short sentences for better flow. Vary sentence length.",
        },
        "flesch_kincaid_grade": {
            "high": "Simplify vocabulary and shorten sentences to improve readability.",
            "low": "Use more precise technical vocabulary appropriate for the journal audience.",
        },
        "type_token_ratio": {
            "high": "Reduce vocabulary diversity -- use consistent terminology throughout.",
            "low": "Vary word choice to avoid repetition. Use synonyms where appropriate.",
        },
        "technical_term_density": {
            "high": "Reduce jargon density. Define technical terms on first use.",
            "low": "Use more domain-specific terminology to match journal expectations.",
        },
        "nominalization_ratio": {
            "high": "Replace nominalisations with verb forms (e.g. 'utilization' -> 'use').",
            "low": "Consider using nominal forms for conciseness where appropriate.",
        },
        "smog_index": {
            "high": "Reduce polysyllabic words. Prefer simpler alternatives.",
            "low": "Use more precise multi-syllable terms appropriate for the audience.",
        },
        "avg_word_length": {
            "high": "Prefer shorter, clearer words where possible.",
            "low": "Use more precise, domain-specific vocabulary.",
        },
    }
    metric_fixes = fixes.get(metric_name, {})
    return metric_fixes.get(direction, f"Adjust {metric_name} closer to target ({target:.2f}).")


def _safe_filename(name: str) -> str:
    safe = re.sub(r"[^\w\s-]", "", name.strip().lower())
    return re.sub(r"[\s]+", "_", safe)


class WritingStyleService:
    def __init__(
        self,
        journal_name: str,
        domain: str | None = None,
        profiles_path: str | Path | None = None,
        cache_dir: str | Path | None = None,
    ) -> None:
        self.journal_name = journal_name

        root = Path(__file__).resolve().parents[3]
        self._profiles_path = (
            Path(profiles_path)
            if profiles_path is not None
            else root / "data" / "journals" / "q1_journal_profiles.yaml"
        )
        self._cache_dir = (
            Path(cache_dir) if cache_dir is not None else root / "data" / "style_guides"
        )

        self._journal_meta = self._load_journal_metadata()
        self.domain = domain or self._detect_domain(journal_name)
        self._domain_weights = _DOMAIN_METRIC_WEIGHTS.get(self.domain, {})

        self.section_chunker = SectionChunker()
        self.style_guide_builder = StyleGuideBuilder()
        self.style_guide = self._load_or_build_style_guide()

    def diagnose_section(self, section: Section) -> SectionDiagnosis:
        current_metrics = self.style_guide_builder.calculate_style_metrics(section.content)
        target_metrics = self._target_metrics_for_section(section.canonical_name)

        current_flat = _flatten_metrics(current_metrics)
        target_flat = _flatten_metrics(target_metrics)

        issues = self._identify_issues(current_flat, target_flat, section)
        deviation_score = self._compute_deviation_score(current_flat, target_flat)
        suggestions = self._generate_rule_suggestions(issues, section)

        return SectionDiagnosis(
            section_name=section.canonical_name or section.name,
            current_metrics=current_metrics,
            target_metrics=target_metrics,
            deviation_score=round(deviation_score, 2),
            issues=issues,
            suggestions=suggestions,
        )

    def diagnose_full_paper(self, paper_path: str | Path) -> dict[str, SectionDiagnosis]:
        path = Path(paper_path)
        if not path.exists():
            raise FileNotFoundError(f"Paper file not found: {paper_path}")

        sections = self._extract_sections(path)
        diagnoses: dict[str, SectionDiagnosis] = {}

        for sec in sections:
            if not sec.content.strip():
                continue
            diag = self.diagnose_section(sec)
            diagnoses[diag.section_name] = diag

        self._detect_cross_section_patterns(diagnoses)
        return diagnoses

    def suggest_rewrites(
        self,
        diagnosis: SectionDiagnosis,
        style: str = "hybrid",
        max_suggestions: int = 5,
    ) -> list[RewriteSuggestion]:
        suggestions: list[RewriteSuggestion] = []

        if style in ("rule", "hybrid"):
            suggestions.extend(self._generate_rule_suggestions(diagnosis.issues))

        suggestions.sort(key=lambda s: -s.confidence)
        return suggestions[:max_suggestions]

    def get_exemplars(self, section_name: str, count: int = 3) -> list[ExemplarSnippet]:
        matching = [
            ex for ex in self.style_guide.exemplars if ex.section.lower() == section_name.lower()
        ]
        if not matching:
            matching = list(self.style_guide.exemplars)
        return matching[:count]

    def compare_journals(
        self,
        other_journal_names: list[str],
        section_name: str | None = None,
    ) -> dict[str, dict[str, float]]:
        result: dict[str, dict[str, float]] = {}

        if section_name and section_name in self.style_guide.section_targets:
            result[self.journal_name] = dict(self.style_guide.section_targets[section_name])
        else:
            result[self.journal_name] = _flatten_metrics(self.style_guide.metrics)

        for name in other_journal_names:
            try:
                other_service = WritingStyleService(
                    journal_name=name,
                    profiles_path=self._profiles_path,
                    cache_dir=self._cache_dir,
                )
                if section_name and section_name in other_service.style_guide.section_targets:
                    result[name] = dict(other_service.style_guide.section_targets[section_name])
                else:
                    result[name] = _flatten_metrics(other_service.style_guide.metrics)
            except (FileNotFoundError, ValueError):
                continue

        return result

    def get_style_guide(self) -> StyleGuide:
        return self.style_guide

    def _load_or_build_style_guide(self) -> StyleGuide:
        cache_path = self._cache_dir / f"{_safe_filename(self.journal_name)}.yaml"

        if cache_path.exists():
            return self._load_style_guide_yaml(cache_path)

        ref_papers = self._get_reference_papers_for_journal()
        if ref_papers:
            paper_paths: list[str | Path] = list(ref_papers)
            guide = self.style_guide_builder.build_from_papers(
                self.journal_name,
                paper_paths,
                self.domain,
            )
            self._save_style_guide_yaml(guide, cache_path)
            return guide

        return self._build_default_style_guide()

    def _load_style_guide_yaml(self, path: Path) -> StyleGuide:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"Invalid style guide YAML: {path}")

        metrics = _dict_to_style_metrics(raw.get("metrics", {}))
        exemplars = [
            ExemplarSnippet(
                text=str(ex.get("text", "")),
                section=str(ex.get("section", "")),
                source_paper=str(ex.get("source_paper", "")),
                metrics=_dict_to_style_metrics(ex.get("metrics", {})),
            )
            for ex in raw.get("exemplars", [])
        ]

        return StyleGuide(
            journal_name=str(raw.get("journal_name", self.journal_name)),
            domain=str(raw.get("domain", self.domain)),
            metrics=metrics,
            section_targets=raw.get("section_targets", {}),
            exemplars=exemplars,
            sample_size=int(raw.get("sample_size", 0)),
            confidence_score=float(raw.get("confidence_score", 0.0)),
            created_at=str(raw.get("created_at", "")),
        )

    @staticmethod
    def _save_style_guide_yaml(guide: StyleGuide, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {
            "journal_name": guide.journal_name,
            "domain": guide.domain,
            "metrics": _flatten_metrics(guide.metrics),
            "section_targets": guide.section_targets,
            "exemplars": [
                {
                    "text": ex.text,
                    "section": ex.section,
                    "source_paper": ex.source_paper,
                    "metrics": _flatten_metrics(ex.metrics),
                }
                for ex in guide.exemplars
            ],
            "sample_size": guide.sample_size,
            "confidence_score": guide.confidence_score,
            "created_at": guide.created_at,
        }
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    def _load_journal_metadata(self) -> dict[str, Any]:
        if not self._profiles_path.exists():
            return {}

        raw = yaml.safe_load(self._profiles_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {}

        journals = raw.get("journals", [])
        if not isinstance(journals, list):
            return {}

        name_lower = self.journal_name.strip().lower()
        for journal in journals:
            if not isinstance(journal, dict):
                continue
            if (
                str(journal.get("name", "")).strip().lower() == name_lower
                or str(journal.get("abbreviation", "")).strip().lower() == name_lower
            ):
                return journal

        return {}

    def _detect_domain(self, journal_name: str) -> str:
        scope_keywords = self._journal_meta.get("scope_keywords", [])
        if scope_keywords:
            text = " ".join(str(kw) for kw in scope_keywords)
            try:
                loader = DomainPackLoader()
                detected = loader.detect_domain(text)
                if detected:
                    return detected
            except (FileNotFoundError, ValueError):
                pass

        try:
            loader = DomainPackLoader()
            detected = loader.detect_domain(journal_name)
            if detected:
                return detected
        except (FileNotFoundError, ValueError):
            pass

        return "computer_science"

    def _get_reference_papers_for_journal(self) -> list[str]:
        root = Path(__file__).resolve().parents[3]
        refs_dir = root / "references" / "papers"
        pdfs_dir = root / "references" / "pdfs"

        if not refs_dir.exists():
            return []

        citation_venues = [
            str(v).strip().lower() for v in self._journal_meta.get("citation_venues", [])
        ]
        journal_name_lower = self.journal_name.strip().lower()

        matching_pdfs: list[str] = []
        for yaml_path in refs_dir.glob("*.yaml"):
            try:
                ref = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
                if not isinstance(ref, dict):
                    continue
                venue = str(ref.get("venue", "")).strip().lower()
                if venue == journal_name_lower or venue in citation_venues:
                    tex_path = pdfs_dir / f"{yaml_path.stem}.tex"
                    pdf_path = pdfs_dir / f"{yaml_path.stem}.pdf"
                    if tex_path.exists():
                        matching_pdfs.append(str(tex_path))
                    elif pdf_path.exists():
                        matching_pdfs.append(str(pdf_path))
            except (yaml.YAMLError, OSError):
                continue

        return matching_pdfs

    def _target_metrics_for_section(self, section_name: str) -> StyleMetrics:
        targets = self.style_guide.section_targets.get(section_name)
        if targets:
            return _target_dict_to_metrics(targets)
        return self.style_guide.metrics

    def _identify_issues(
        self,
        current: dict[str, float],
        target: dict[str, float],
        section: Section | None = None,
    ) -> list[StyleIssue]:
        issues: list[StyleIssue] = []

        for metric_name, target_val in target.items():
            current_val = current.get(metric_name, 0.0)
            if target_val == 0.0 and current_val == 0.0:
                continue

            base = max(abs(target_val), 0.01)
            deviation = abs(current_val - target_val) / base

            domain_weight = self._domain_weights.get(metric_name, 1.0)
            weighted_deviation = deviation * domain_weight

            if weighted_deviation < _MINOR_THRESHOLD:
                continue

            severity = _classify_severity(weighted_deviation)
            category = _METRIC_CATEGORIES.get(metric_name, "readability")
            label = _METRIC_LABELS.get(metric_name, metric_name)

            direction = "high" if current_val > target_val else "low"
            description = (
                f"{label} is too {direction}: "
                f"{current_val:.2f} vs target {target_val:.2f} "
                f"(deviation {deviation:.0%})"
            )

            example_span = ""
            if section and section.content:
                example_span = _extract_example_span(metric_name, section.content)

            recommended_fix = _recommend_fix(metric_name, direction, current_val, target_val)

            issues.append(
                StyleIssue(
                    category=category,
                    severity=severity,
                    description=description,
                    example_span=example_span,
                    journal_target=f"{label}: {target_val:.2f}",
                    recommended_fix=recommended_fix,
                )
            )

        severity_order = {"critical": 0, "major": 1, "minor": 2}
        issues.sort(key=lambda i: severity_order.get(i.severity, 3))
        return issues

    def _compute_deviation_score(
        self,
        current: dict[str, float],
        target: dict[str, float],
    ) -> float:
        deviations: list[float] = []
        for metric_name, target_val in target.items():
            current_val = current.get(metric_name, 0.0)
            base = max(abs(target_val), 0.01)
            dev = abs(current_val - target_val) / base
            domain_weight = self._domain_weights.get(metric_name, 1.0)
            deviations.append(dev * domain_weight)

        if not deviations:
            return 0.0

        rms = math.sqrt(sum(d * d for d in deviations) / len(deviations))
        return min(rms * 100.0, 100.0)

    def _generate_rule_suggestions(
        self,
        issues: list[StyleIssue],
        section: Section | None = None,
    ) -> list[RewriteSuggestion]:
        suggestions: list[RewriteSuggestion] = []

        for issue in issues:
            if not issue.recommended_fix:
                continue

            confidence = {"critical": 0.9, "major": 0.7, "minor": 0.5}.get(issue.severity, 0.3)

            suggestions.append(
                RewriteSuggestion(
                    original_text=issue.example_span or "",
                    suggested_text="",
                    rationale=issue.recommended_fix,
                    exemplar_source=self.journal_name,
                    confidence=confidence,
                )
            )

        suggestions.sort(key=lambda s: -s.confidence)
        return suggestions

    def _detect_cross_section_patterns(
        self,
        diagnoses: dict[str, SectionDiagnosis],
    ) -> None:
        if len(diagnoses) < 2:
            return

        passive_issues = [
            name
            for name, diag in diagnoses.items()
            if any(
                i.category == "grammar" and "passive" in i.description.lower() for i in diag.issues
            )
        ]
        if len(passive_issues) >= 2:
            first_section = next(iter(diagnoses))
            diagnoses[first_section].issues.append(
                StyleIssue(
                    category="grammar",
                    severity="major",
                    description=(
                        f"Consistent passive voice overuse across "
                        f"{len(passive_issues)} sections: {', '.join(passive_issues)}"
                    ),
                    example_span="",
                    journal_target="Reduce passive voice across the paper",
                    recommended_fix=(
                        "Convert passive constructions to active voice throughout. "
                        "Focus on Methods and Results sections first."
                    ),
                )
            )

        readability_issues = [
            name
            for name, diag in diagnoses.items()
            if any(i.category == "readability" for i in diag.issues)
        ]
        if len(readability_issues) >= 3:
            first_section = next(iter(diagnoses))
            diagnoses[first_section].issues.append(
                StyleIssue(
                    category="readability",
                    severity="major",
                    description=(
                        f"Readability concerns in {len(readability_issues)} sections -- "
                        "paper may be consistently too complex or too simple for the target journal"
                    ),
                    example_span="",
                    journal_target="Match journal readability norms",
                    recommended_fix=(
                        "Review sentence structure and vocabulary complexity across the entire paper."
                    ),
                )
            )

    def _build_default_style_guide(self) -> StyleGuide:
        word_range = self._journal_meta.get("typical_word_count", [6000, 10000])
        avg_words = (
            (word_range[0] + word_range[1]) / 2
            if isinstance(word_range, list) and len(word_range) == 2
            else 8000
        )
        complexity_factor = min(avg_words / 8000.0, 1.5)

        default_targets: dict[str, dict[str, float]] = {
            "Introduction": {
                "flesch_kincaid_grade": 12.0 * complexity_factor,
                "avg_sentence_length": 22.0,
                "passive_voice_ratio": 0.15,
                "type_token_ratio": 0.55,
                "technical_term_density": 0.08,
                "nominalization_ratio": 0.06,
                "smog_index": 14.0,
                "avg_word_length": 5.0,
            },
            "Related Work": {
                "flesch_kincaid_grade": 12.5 * complexity_factor,
                "avg_sentence_length": 24.0,
                "passive_voice_ratio": 0.18,
                "type_token_ratio": 0.58,
                "technical_term_density": 0.10,
                "nominalization_ratio": 0.07,
                "smog_index": 14.5,
                "avg_word_length": 5.1,
            },
            "Methods": {
                "flesch_kincaid_grade": 14.0 * complexity_factor,
                "avg_sentence_length": 20.0,
                "passive_voice_ratio": 0.25,
                "type_token_ratio": 0.50,
                "technical_term_density": 0.12,
                "nominalization_ratio": 0.08,
                "smog_index": 15.0,
                "avg_word_length": 5.2,
            },
            "Results": {
                "flesch_kincaid_grade": 13.0 * complexity_factor,
                "avg_sentence_length": 18.0,
                "passive_voice_ratio": 0.20,
                "type_token_ratio": 0.45,
                "technical_term_density": 0.10,
                "nominalization_ratio": 0.07,
                "smog_index": 14.5,
                "avg_word_length": 5.1,
            },
            "Experiments": {
                "flesch_kincaid_grade": 13.0 * complexity_factor,
                "avg_sentence_length": 19.0,
                "passive_voice_ratio": 0.22,
                "type_token_ratio": 0.47,
                "technical_term_density": 0.11,
                "nominalization_ratio": 0.07,
                "smog_index": 14.5,
                "avg_word_length": 5.1,
            },
            "Discussion": {
                "flesch_kincaid_grade": 12.5 * complexity_factor,
                "avg_sentence_length": 24.0,
                "passive_voice_ratio": 0.15,
                "type_token_ratio": 0.55,
                "technical_term_density": 0.09,
                "nominalization_ratio": 0.07,
                "smog_index": 14.0,
                "avg_word_length": 5.0,
            },
            "Conclusion": {
                "flesch_kincaid_grade": 11.5 * complexity_factor,
                "avg_sentence_length": 22.0,
                "passive_voice_ratio": 0.12,
                "type_token_ratio": 0.50,
                "technical_term_density": 0.07,
                "nominalization_ratio": 0.05,
                "smog_index": 13.5,
                "avg_word_length": 4.9,
            },
        }

        all_values: dict[str, list[float]] = {}
        for targets in default_targets.values():
            for key, val in targets.items():
                all_values.setdefault(key, []).append(val)

        avg_targets = {k: sum(v) / len(v) for k, v in all_values.items()}
        aggregated = _target_dict_to_metrics(avg_targets)

        return StyleGuide(
            journal_name=self.journal_name,
            domain=self.domain,
            metrics=aggregated,
            section_targets=default_targets,
            exemplars=[],
            sample_size=0,
            confidence_score=0.0,
            created_at=datetime.now(tz=timezone.utc).isoformat(),
        )

    def _extract_sections(self, path: Path) -> list[Section]:
        if path.suffix == ".tex":
            return self.section_chunker.chunk_latex_paper(path)
        if path.suffix == ".pdf":
            return self.section_chunker.chunk_pdf_paper(path)
        return self.section_chunker.chunk_text(path.read_text(encoding="utf-8"))
