from __future__ import annotations

from dataclasses import dataclass

from crane.models.paper_profile import DimensionScore


@dataclass
class FeynmanQuestion:
    dimension: str
    question: str
    section: str
    difficulty: str
    expected_insight: str

    def __post_init__(self) -> None:
        if not self.question:
            raise ValueError("question cannot be empty")
        if self.difficulty not in ("basic", "probing", "challenging"):
            raise ValueError("difficulty must be basic/probing/challenging")


@dataclass
class FeynmanSession:
    paper_path: str
    mode: str
    focus_dimensions: list[str]
    questions: list[FeynmanQuestion]
    total_questions: int
    weak_dimensions: list[str]

    def by_dimension(self, dim: str) -> list[FeynmanQuestion]:
        return [q for q in self.questions if q.dimension == dim]

    def by_difficulty(self, diff: str) -> list[FeynmanQuestion]:
        return [q for q in self.questions if q.difficulty == diff]


class FeynmanSessionService:
    """Generate Feynman-style probing questions from evaluation results."""

    _ALLOWED_MODES = {
        "post_evaluation",
        "pre_submission",
        "methodology",
        "writing",
    }
    _DEFAULT_METHOD_FAMILY = "your current method"
    _DEFAULT_ALTERNATIVE = "a simpler baseline"
    _DEFAULT_CLOSEST_PRIOR = "the closest prior method"
    _DEFAULT_CONCEPT = "the core idea"

    METHODOLOGY_QUESTIONS = [
        (
            "basic",
            "Can you explain your research methodology in simple terms, as if to a first-year student?",
            "Why this method is appropriate",
        ),
        (
            "probing",
            "Why did you choose {method_family} over alternative approaches? What would break if you used a simpler method?",
            "Justification for method choice",
        ),
        (
            "probing",
            "What assumptions does your method make? What happens when those assumptions are violated?",
            "Awareness of method limitations",
        ),
        (
            "challenging",
            "If a reviewer said 'this is just {alternative} with minor modifications', how would you defend your approach?",
            "Clear articulation of novelty in methodology",
        ),
        (
            "challenging",
            "Walk me through your algorithm step by step. At which step could errors compound?",
            "Deep understanding of method internals",
        ),
    ]

    NOVELTY_QUESTIONS = [
        (
            "basic",
            "What is the single most important new thing your paper contributes?",
            "Clear contribution statement",
        ),
        (
            "probing",
            "How is your work different from {closest_prior_work}? Be specific about what they can't do that you can.",
            "Concrete differentiation",
        ),
        (
            "probing",
            "If someone had unlimited compute and data, could they achieve your results with existing methods?",
            "Understanding of fundamental vs incremental contribution",
        ),
        (
            "challenging",
            "A reviewer says 'this is incremental'. In one paragraph, convince them otherwise.",
            "Strong novelty defense",
        ),
    ]

    EVALUATION_QUESTIONS = [
        (
            "basic",
            "What metrics did you use to evaluate your method, and why those specific metrics?",
            "Metric selection rationale",
        ),
        (
            "probing",
            "Your Table shows {improvement}% improvement. Is that statistically significant? How do you know?",
            "Statistical rigor awareness",
        ),
        (
            "probing",
            "Why did you choose these specific baselines? Are there stronger ones you didn't compare against?",
            "Baseline selection justification",
        ),
        (
            "challenging",
            "If I ran your experiment with different random seeds, would the results change? By how much?",
            "Reproducibility confidence",
        ),
        (
            "challenging",
            "Your ablation study removes component X and performance drops. But does that prove X is necessary, or just that the model was trained with X?",
            "Deep understanding of ablation logic",
        ),
    ]

    WRITING_QUESTIONS = [
        (
            "basic",
            "Can you summarize your abstract in one sentence? Does that sentence appear in your abstract?",
            "Abstract clarity",
        ),
        (
            "probing",
            "I read Section {section} three times and I'm still confused about {concept}. Can you explain it differently?",
            "Writing clarity check",
        ),
        (
            "challenging",
            "Your introduction promises X, but your conclusion discusses Y. Are these the same thing?",
            "Narrative consistency",
        ),
    ]

    REPRODUCIBILITY_QUESTIONS = [
        (
            "basic",
            "If I wanted to reproduce your results, what's the first thing I'd need to do?",
            "Reproduction starting point",
        ),
        (
            "probing",
            "What hyperparameters did you tune, and how sensitive are results to those choices?",
            "Hyperparameter awareness",
        ),
        (
            "challenging",
            "You mention code availability — but are your trained models and data splits also available?",
            "Full reproducibility assessment",
        ),
    ]

    LIMITATIONS_QUESTIONS = [
        (
            "basic",
            "What is the biggest limitation of your work?",
            "Self-awareness of limitations",
        ),
        (
            "probing",
            "In what scenarios would your method fail completely?",
            "Failure mode understanding",
        ),
        (
            "challenging",
            "You mention limitation X but don't discuss its impact. How much does it actually affect your conclusions?",
            "Honest limitation assessment",
        ),
    ]

    PRESENTATION_QUESTIONS = [
        (
            "basic",
            "Looking at Figure 1, what is the single most important takeaway?",
            "Figure clarity",
        ),
        (
            "probing",
            "Your Table {n} has many columns. Which comparison is the most important one?",
            "Information prioritization",
        ),
    ]

    _QUESTION_BANK = {
        "methodology": METHODOLOGY_QUESTIONS,
        "novelty": NOVELTY_QUESTIONS,
        "evaluation": EVALUATION_QUESTIONS,
        "writing_quality": WRITING_QUESTIONS,
        "writing": WRITING_QUESTIONS,
        "reproducibility": REPRODUCIBILITY_QUESTIONS,
        "limitations": LIMITATIONS_QUESTIONS,
        "presentation": PRESENTATION_QUESTIONS,
    }

    _MODE_PRIORITY = {
        "post_evaluation": ["methodology", "novelty", "evaluation"],
        "pre_submission": ["evaluation", "reproducibility", "limitations", "writing_quality"],
        "methodology": ["methodology"],
        "writing": ["writing_quality", "presentation"],
    }

    def generate_session(
        self,
        dimension_scores: list[DimensionScore],
        mode: str = "post_evaluation",
        focus_dimensions: list[str] | None = None,
        num_questions: int = 5,
        paper_path: str = "",
    ) -> FeynmanSession:
        if mode not in self._ALLOWED_MODES:
            raise ValueError(
                "mode must be one of: post_evaluation, pre_submission, methodology, writing"
            )
        if num_questions < 0:
            raise ValueError("num_questions must be >= 0")

        score_map = {s.dimension: s for s in dimension_scores}
        weak_dimensions = [s.dimension for s in dimension_scores if s.score < 70.0]
        selected_dimensions = self._select_dimensions(mode, focus_dimensions, dimension_scores)

        if num_questions == 0 or not selected_dimensions:
            return FeynmanSession(
                paper_path=paper_path,
                mode=mode,
                focus_dimensions=selected_dimensions,
                questions=[],
                total_questions=0,
                weak_dimensions=weak_dimensions,
            )

        requested_total = min(num_questions, self._total_available(selected_dimensions))
        per_dim = self._allocate_counts(selected_dimensions, requested_total)

        questions: list[FeynmanQuestion] = []
        for dim in selected_dimensions:
            score = score_map.get(dim)
            if score is None:
                continue
            selected = self._select_questions_for_dimension(dim, score, per_dim[dim])
            questions.extend(selected)

        if len(questions) > requested_total:
            questions = questions[:requested_total]

        return FeynmanSession(
            paper_path=paper_path,
            mode=mode,
            focus_dimensions=selected_dimensions,
            questions=questions,
            total_questions=len(questions),
            weak_dimensions=weak_dimensions,
        )

    def _select_questions_for_dimension(
        self,
        dimension: str,
        score: DimensionScore,
        count: int,
    ) -> list[FeynmanQuestion]:
        if count <= 0:
            return []

        canonical_dim = self._canonical_dimension(dimension)
        templates = self._QUESTION_BANK.get(canonical_dim, self.WRITING_QUESTIONS)
        format_values = self._format_values(score)
        section = self._infer_section(score)

        basic_pool = [tpl for tpl in templates if tpl[0] == "basic"]
        probing_pool = [tpl for tpl in templates if tpl[0] == "probing"]
        challenging_pool = [tpl for tpl in templates if tpl[0] == "challenging"]

        chosen: list[tuple[str, str, str]] = []
        if basic_pool:
            chosen.append(basic_pool[0])
        if count >= 2 and probing_pool:
            chosen.append(probing_pool[0])
        while len(chosen) < max(0, count - 1) and probing_pool:
            chosen.append(probing_pool[len(chosen) % len(probing_pool)])
        if count >= 3 and challenging_pool:
            chosen.append(challenging_pool[0])

        all_templates = templates.copy()
        idx = 0
        while len(chosen) < count and all_templates:
            chosen.append(all_templates[idx % len(all_templates)])
            idx += 1

        questions: list[FeynmanQuestion] = []
        for difficulty, template, expected in chosen[:count]:
            formatted = template.format(**format_values)
            questions.append(
                FeynmanQuestion(
                    dimension=score.dimension,
                    question=formatted,
                    section=section,
                    difficulty=difficulty,
                    expected_insight=expected,
                )
            )
        return questions

    def generate_session_report(self, session: FeynmanSession) -> str:
        dimensions = ", ".join(session.focus_dimensions) if session.focus_dimensions else "none"
        lines = [
            "# Feynman Session: Test Your Understanding",
            "",
            (
                f"**Mode**: {session.mode} | "
                f"**Focus**: {dimensions} | "
                f"**Questions**: {session.total_questions}"
            ),
        ]

        if not session.questions:
            lines.extend(["", "No questions generated for the current configuration."])
            return "\n".join(lines)

        grouped: dict[str, list[FeynmanQuestion]] = {}
        for question in session.questions:
            grouped.setdefault(question.dimension, []).append(question)

        question_idx = 1
        for dimension in session.focus_dimensions:
            dim_questions = grouped.get(dimension)
            if not dim_questions:
                continue
            lines.extend(["", f"## {dimension}"])
            for q in dim_questions:
                lines.extend(
                    [
                        "",
                        f"### Question {question_idx} ({q.difficulty.capitalize()})",
                        f"> {q.question}",
                        "",
                        f"*Section*: {q.section}",
                        f"*What a good answer covers*: {q.expected_insight}",
                    ]
                )
                question_idx += 1

        return "\n".join(lines)

    def _select_dimensions(
        self,
        mode: str,
        focus_dimensions: list[str] | None,
        scores: list[DimensionScore],
    ) -> list[str]:
        available = {s.dimension for s in scores}
        weak_dims = [s.dimension for s in scores if s.score < 70.0]

        if focus_dimensions:
            ordered_focus = []
            for dim in focus_dimensions:
                if dim in available and dim not in ordered_focus:
                    ordered_focus.append(dim)
            return ordered_focus

        if mode == "post_evaluation":
            return weak_dims

        if mode == "pre_submission":
            priority = self._MODE_PRIORITY[mode]
            selected: list[str] = []
            for dim in priority:
                if dim in available and (
                    dim in weak_dims or dim in {"reproducibility", "limitations"}
                ):
                    selected.append(dim)
            for dim in weak_dims:
                if dim not in selected:
                    selected.append(dim)
            return selected

        priority = self._MODE_PRIORITY[mode]
        selected_mode_dims = [dim for dim in priority if dim in available]
        return selected_mode_dims or weak_dims

    def _allocate_counts(self, dimensions: list[str], total: int) -> dict[str, int]:
        if not dimensions:
            return {}
        allocation = {dim: 0 for dim in dimensions}
        base = total // len(dimensions)
        remainder = total % len(dimensions)
        for idx, dim in enumerate(dimensions):
            allocation[dim] = base + (1 if idx < remainder else 0)
        return allocation

    def _total_available(self, dimensions: list[str]) -> int:
        total = 0
        for dim in dimensions:
            canonical = self._canonical_dimension(dim)
            total += len(self._QUESTION_BANK.get(canonical, self.WRITING_QUESTIONS))
        return total

    @staticmethod
    def _canonical_dimension(dimension: str) -> str:
        if dimension == "writing":
            return "writing_quality"
        return dimension

    def _format_values(self, score: DimensionScore) -> dict[str, str]:
        method_family = self._first_non_empty(score.reason_codes, self._DEFAULT_METHOD_FAMILY)
        alternative = self._first_non_empty(score.missing_evidence, self._DEFAULT_ALTERNATIVE)
        closest_prior = self._first_non_empty(score.evidence_spans, self._DEFAULT_CLOSEST_PRIOR)
        concept = self._first_non_empty(score.missing_evidence, self._DEFAULT_CONCEPT)
        section = self._infer_section(score)

        return {
            "method_family": method_family,
            "alternative": alternative,
            "closest_prior_work": closest_prior,
            "improvement": self._extract_improvement(score),
            "section": section,
            "concept": concept,
            "n": "1",
        }

    @staticmethod
    def _first_non_empty(items: list[str], fallback: str) -> str:
        for item in items:
            if item.strip():
                return item.strip()
        return fallback

    @staticmethod
    def _infer_section(score: DimensionScore) -> str:
        if not score.evidence_spans:
            return "General"
        span = score.evidence_spans[0]
        separators = [":", " - "]
        for sep in separators:
            if sep in span:
                return span.split(sep, 1)[0].strip() or "General"
        return "General"

    @staticmethod
    def _extract_improvement(score: DimensionScore) -> str:
        for token in score.reason_codes + score.evidence_spans + score.suggestions:
            stripped = token.replace("%", " ")
            for part in stripped.split():
                if part.replace(".", "", 1).isdigit():
                    return part
        return "5"
