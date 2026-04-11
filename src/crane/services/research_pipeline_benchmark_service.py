import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict


class StageResult(TypedDict):
    score: float
    sub_dimensions: dict[str, float]
    signal_counts: dict[str, int]
    key_terms: list[str]
    summary: str


@dataclass(frozen=True)
class SubDimensionRubric:
    name: str
    patterns: tuple[str, ...]
    target_hits: int
    weight: float


class ResearchPipelineBenchmarkService:
    STAGES: tuple[str, ...] = (
        "ideation",
        "literature",
        "design",
        "implementation",
        "writing",
        "submission",
    )

    STAGE_WEIGHTS: dict[str, float] = {
        "ideation": 0.14,
        "literature": 0.16,
        "design": 0.18,
        "implementation": 0.17,
        "writing": 0.17,
        "submission": 0.18,
    }

    STAGE_RUBRICS: dict[str, tuple[SubDimensionRubric, ...]] = {
        "ideation": (
            SubDimensionRubric(
                name="novelty_signal",
                patterns=(
                    r"\bnovel\b",
                    r"\bfirst\s+to\b",
                    r"\bnew\s+paradigm\b",
                    r"\bwe\s+introduce\b",
                ),
                target_hits=3,
                weight=0.35,
            ),
            SubDimensionRubric(
                name="motivation_clarity",
                patterns=(
                    r"\bmotivation\b",
                    r"\bproblem\s+statement\b",
                    r"\bchallenge\b",
                    r"\bresearch\s+question\b",
                ),
                target_hits=4,
                weight=0.35,
            ),
            SubDimensionRubric(
                name="impact_articulation",
                patterns=(
                    r"\bimpact\b",
                    r"\bpractical\s+value\b",
                    r"\bbroad\s+applicability\b",
                    r"\bsignificance\b",
                ),
                target_hits=3,
                weight=0.30,
            ),
        ),
        "literature": (
            SubDimensionRubric(
                name="coverage",
                patterns=(
                    r"\\cite\{",
                    r"\bprior\s+work\b",
                    r"\brelated\s+work\b",
                    r"\bstate[- ]of[- ]the[- ]art\b",
                ),
                target_hits=12,
                weight=0.35,
            ),
            SubDimensionRubric(
                name="positioning",
                patterns=(
                    r"\bunlike\b",
                    r"\bin\s+contrast\s+to\b",
                    r"\bcompared\s+with\b",
                    r"\bdiffers?\s+from\b",
                ),
                target_hits=4,
                weight=0.35,
            ),
            SubDimensionRubric(
                name="citation_quality",
                patterns=(
                    r"\brecent\b",
                    r"\breproducible\s+baseline\b",
                    r"\bbenchmark\b",
                    r"\bopenreview\b",
                ),
                target_hits=3,
                weight=0.30,
            ),
        ),
        "design": (
            SubDimensionRubric(
                name="methodology_soundness",
                patterns=(
                    r"\\section\{[^}]*method",
                    r"\bmethodology\b",
                    r"\bobjective\b",
                    r"\bloss\b",
                    r"\\begin\{equation\}",
                ),
                target_hits=5,
                weight=0.40,
            ),
            SubDimensionRubric(
                name="hypothesis_clarity",
                patterns=(
                    r"\bhypothesis\b",
                    r"\bwe\s+hypothesize\b",
                    r"\bwe\s+expect\b",
                    r"\btest\s+whether\b",
                ),
                target_hits=3,
                weight=0.30,
            ),
            SubDimensionRubric(
                name="experimental_design",
                patterns=(
                    r"\bablation\b",
                    r"\bcontrol\b",
                    r"\bexperimental\s+setup\b",
                    r"\bstatistical\s+significance\b",
                ),
                target_hits=4,
                weight=0.30,
            ),
        ),
        "implementation": (
            SubDimensionRubric(
                name="code_availability",
                patterns=(
                    r"\bcode\s+is\s+available\b",
                    r"\brepository\b",
                    r"\bgithub\.com\b",
                    r"\bopen[- ]source\b",
                ),
                target_hits=3,
                weight=0.35,
            ),
            SubDimensionRubric(
                name="reproducibility",
                patterns=(
                    r"\brandom\s+seed\b",
                    r"\bhyperparameter\b",
                    r"\bimplementation\s+details\b",
                    r"\bcompute\s+budget\b",
                ),
                target_hits=4,
                weight=0.35,
            ),
            SubDimensionRubric(
                name="artifact_quality",
                patterns=(
                    r"\brelease\b",
                    r"\bdocker\b",
                    r"\brequirements\.txt\b",
                    r"\bscript\b",
                ),
                target_hits=3,
                weight=0.30,
            ),
        ),
        "writing": (
            SubDimensionRubric(
                name="clarity",
                patterns=(
                    r"\bin\s+this\s+paper\b",
                    r"\bwe\s+show\b",
                    r"\bwe\s+demonstrate\b",
                    r"\bconclusion\b",
                ),
                target_hits=4,
                weight=0.35,
            ),
            SubDimensionRubric(
                name="figure_quality",
                patterns=(
                    r"\\begin\{figure\}",
                    r"\\caption\{",
                    r"\bvisualization\b",
                    r"\berror\s+bar\b",
                ),
                target_hits=5,
                weight=0.30,
            ),
            SubDimensionRubric(
                name="completeness",
                patterns=(
                    r"\blimitation\b",
                    r"\bfuture\s+work\b",
                    r"\bappendix\b",
                    r"\bethics\b",
                ),
                target_hits=3,
                weight=0.35,
            ),
        ),
        "submission": (
            SubDimensionRubric(
                name="q1_readiness",
                patterns=(
                    r"\bstrong\s+baseline\b",
                    r"\bstatistical\s+test\b",
                    r"\bcomprehensive\s+evaluation\b",
                    r"\brobustness\b",
                ),
                target_hits=4,
                weight=0.40,
            ),
            SubDimensionRubric(
                name="venue_fit",
                patterns=(
                    r"\bneurips\b",
                    r"\bicml\b",
                    r"\biclr\b",
                    r"\bconference\s+track\b",
                ),
                target_hits=2,
                weight=0.30,
            ),
            SubDimensionRubric(
                name="final_readiness",
                patterns=(
                    r"\breproducibility\s+checklist\b",
                    r"\bartifact\s+evaluation\b",
                    r"\bcamera[- ]ready\b",
                    r"\bsupplementary\s+material\b",
                ),
                target_hits=3,
                weight=0.30,
            ),
        ),
    }

    STAGE_LINKS: tuple[tuple[str, str], ...] = (
        ("ideation", "literature"),
        ("literature", "design"),
        ("design", "implementation"),
        ("implementation", "writing"),
        ("writing", "submission"),
    )

    def __init__(self, refs_dir: str):
        self.refs_dir = refs_dir

    def evaluate_pipeline(self, paper_path: str) -> dict[str, object]:
        paper_data = self._extract_paper_data(paper_path)

        stage_outputs: dict[str, StageResult] = {}
        for stage in self.STAGES:
            stage_outputs[stage] = self._evaluate_stage(stage, paper_data)

        coherence_scores: dict[str, float] = {}
        for left, right in self.STAGE_LINKS:
            pair_key = f"{left}_to_{right}"
            coherence_scores[pair_key] = self.check_stage_coherence(
                stage_outputs[left], stage_outputs[right]
            )

        coherence_scores["overall"] = round(
            sum(coherence_scores.values()) / len(self.STAGE_LINKS), 2
        )

        base_health = self.calculate_pipeline_health_score(stage_outputs)
        health_score = round(0.85 * base_health + 0.15 * coherence_scores["overall"], 2)

        critical_stage_min = min(
            stage_outputs["design"]["score"],
            stage_outputs["implementation"]["score"],
            stage_outputs["submission"]["score"],
        )
        accept_probability = self._sigmoid((health_score - 70.0) / 7.5)
        if health_score >= 70.0 and critical_stage_min >= 60.0:
            label = "accept"
        else:
            label = "reject"

        return {
            "paper_path": str(Path(paper_path)),
            "stages": stage_outputs,
            "coherence_scores": coherence_scores,
            "health_score": health_score,
            "prediction": {
                "label": label,
                "confidence": round(max(accept_probability, 1.0 - accept_probability), 3),
                "accept_probability": round(accept_probability, 3),
                "threshold": 70.0,
            },
        }

    def calculate_stage_scores(self, paper_data: dict[str, object], stage: str) -> float:
        if stage not in self.STAGE_RUBRICS:
            raise ValueError(f"Unknown stage: {stage}")

        text = str(paper_data.get("text", ""))
        score = 0.0
        for rubric in self.STAGE_RUBRICS[stage]:
            hits = sum(self._count_pattern(text, pattern) for pattern in rubric.patterns)
            dimension_score = min(100.0, (hits / max(1, rubric.target_hits)) * 100.0)
            score += dimension_score * rubric.weight
        return round(min(100.0, score), 2)

    def check_stage_coherence(
        self,
        stage1_output: Mapping[str, object],
        stage2_output: Mapping[str, object],
    ) -> float:
        score_1 = self._to_float(stage1_output.get("score", 0.0))
        score_2 = self._to_float(stage2_output.get("score", 0.0))

        terms_1 = self._to_str_set(stage1_output.get("key_terms", []))
        terms_2 = self._to_str_set(stage2_output.get("key_terms", []))

        overlap = len(terms_1.intersection(terms_2))
        union = len(terms_1.union(terms_2))
        lexical_alignment = 100.0 if union == 0 else (overlap / union) * 100.0

        score_gap_penalty = min(35.0, abs(score_1 - score_2) * 0.9)
        base = 70.0 + 0.3 * lexical_alignment
        coherence = max(0.0, min(100.0, base - score_gap_penalty))
        return round(coherence, 2)

    def calculate_pipeline_health_score(
        self,
        all_stages: Mapping[str, Mapping[str, object]],
    ) -> float:
        weighted = 0.0
        for stage in self.STAGES:
            stage_payload = all_stages.get(stage, {})
            stage_score = self._to_float(stage_payload.get("score", 0.0))
            weighted += stage_score * self.STAGE_WEIGHTS[stage]
        return round(min(100.0, max(0.0, weighted)), 2)

    def _evaluate_stage(self, stage: str, paper_data: dict[str, object]) -> StageResult:
        text = str(paper_data.get("text", ""))
        sub_scores: dict[str, float] = {}
        signal_counts: dict[str, int] = {}
        key_terms: set[str] = set()

        for rubric in self.STAGE_RUBRICS[stage]:
            hits = sum(self._count_pattern(text, pattern) for pattern in rubric.patterns)
            signal_counts[rubric.name] = hits
            sub_scores[rubric.name] = round(
                min(100.0, (hits / max(1, rubric.target_hits)) * 100.0),
                2,
            )
            key_terms.update(self._extract_key_terms(text, rubric.patterns))

        stage_score = self.calculate_stage_scores(paper_data, stage)
        summary = (
            f"{stage.title()} stage scored {stage_score:.1f} with "
            f"{len(key_terms)} salient terms and {sum(signal_counts.values())} matched signals."
        )
        return {
            "score": stage_score,
            "sub_dimensions": sub_scores,
            "signal_counts": signal_counts,
            "key_terms": sorted(key_terms),
            "summary": summary,
        }

    def _extract_paper_data(self, paper_path: str) -> dict[str, object]:
        path = Path(paper_path)
        if not path.exists():
            raise FileNotFoundError(f"Paper not found: {paper_path}")

        text = path.read_text(encoding="utf-8")
        sections = re.findall(r"\\section\{([^}]+)\}", text, flags=re.IGNORECASE)
        section_names = [section.strip().lower() for section in sections]

        return {
            "text": text.lower(),
            "section_names": section_names,
            "word_count": len(re.findall(r"\b\w+\b", text)),
            "refs_dir": self.refs_dir,
        }

    def _count_pattern(self, text: str, pattern: str) -> int:
        return len(re.findall(pattern, text, flags=re.IGNORECASE))

    def _extract_key_terms(self, text: str, patterns: tuple[str, ...]) -> set[str]:
        key_terms: set[str] = set()
        for pattern in patterns:
            literal_tokens = re.findall(r"[a-zA-Z]{4,}", pattern)
            for token in literal_tokens:
                token_lower = token.lower()
                if token_lower in text and token_lower not in {"begin", "section", "figure"}:
                    key_terms.add(token_lower)
        return key_terms

    def _sigmoid(self, x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x))

    def _to_float(self, value: object) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return 0.0
        return 0.0

    def _to_str_set(self, value: object) -> set[str]:
        if isinstance(value, (list, tuple, set)):
            return {str(item) for item in value}
        return set()
