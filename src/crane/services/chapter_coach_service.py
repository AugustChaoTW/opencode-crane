"""Chapter coaching service - Provides real-time feedback on paper chapters."""

from __future__ import annotations

from typing import Any

from crane.services.journal_submission_service import JournalSubmissionService


class ChapterCoachService:
    """Provides coaching and feedback for individual paper chapters."""

    CHAPTER_EXPECTATIONS = {
        "abstract": {
            "min_words": 100,
            "max_words": 250,
            "required_elements": [
                "background",
                "problem",
                "solution",
                "results",
                "conclusion",
            ],
            "focus": "Clear, concise summary with specific numbers",
        },
        "introduction": {
            "min_pages": 1.5,
            "max_pages": 2.5,
            "required_sections": [
                "background",
                "research_gap",
                "problem_statement",
                "contributions",
            ],
            "focus": "Clear problem definition and contribution claims",
        },
        "related_work": {
            "min_pages": 1.5,
            "max_pages": 3,
            "required_elements": [
                "organized_by_topic",
                "comparison_table",
                "coverage_of_sota",
            ],
            "focus": "Organized comparison with clear differentiation",
        },
        "methods": {
            "min_pages": 2,
            "max_pages": 5,
            "required_elements": [
                "algorithm_description",
                "hyperparameters",
                "data_description",
                "experimental_setup",
            ],
            "focus": "Sufficient detail for reproducibility",
        },
        "results": {
            "min_pages": 1.5,
            "max_pages": 3,
            "required_elements": [
                "main_results_table_or_figure",
                "error_bars_or_ci",
                "ablation_study",
                "statistical_significance",
            ],
            "focus": "Pure presentation of facts with error measures",
        },
        "discussion": {
            "min_pages": 1.5,
            "max_pages": 2.5,
            "required_elements": [
                "result_interpretation",
                "sota_comparison",
                "limitations",
                "future_work",
            ],
            "focus": "Explanation, comparison, and honest limitations",
        },
        "conclusion": {
            "min_pages": 0.3,
            "max_pages": 1,
            "required_elements": [
                "contribution_summary",
                "clear_conclusion_sentence",
            ],
            "focus": "Concise and clear, no new information",
        },
    }

    def __init__(self, project_dir: str | None = None):
        self.submission_service = JournalSubmissionService(project_dir)
        self.config = self.submission_service.load_config()

    def coach_chapter(self, chapter: str, content: str | None = None) -> dict[str, Any]:
        """Provide coaching feedback for a chapter."""
        if chapter not in self.CHAPTER_EXPECTATIONS:
            return {
                "status": "error",
                "message": f"Unknown chapter: {chapter}",
                "valid_chapters": list(self.CHAPTER_EXPECTATIONS.keys()),
            }

        expectations = self.CHAPTER_EXPECTATIONS[chapter]

        result = {
            "chapter": chapter,
            "expectations": expectations,
            "diagnostics": {},
        }

        if content:
            result["diagnostics"] = self._analyze_chapter(chapter, content)

        return result

    def _analyze_chapter(self, chapter: str, content: str) -> dict[str, Any]:
        """Analyze chapter content against expectations."""
        expectations = self.CHAPTER_EXPECTATIONS[chapter]
        diagnostics = {
            "strengths": [],
            "improvements": [],
            "key_points_to_check": [],
            "next_steps": "",
        }

        word_count = len(content.split())

        if "max_words" in expectations:
            if word_count > expectations["max_words"]:
                diagnostics["improvements"].append(
                    {
                        "issue": f"Exceeds word limit ({word_count} > {expectations['max_words']})",
                        "priority": "high",
                        "suggestion": "Consider condensing or moving to supplementary material",
                    }
                )
            else:
                diagnostics["strengths"].append("✅ Word count within limit")

        if chapter == "abstract":
            diagnostics["key_points_to_check"] = [
                "Does it start with clear background (1-2 sentences)?",
                "Is the problem statement specific (not vague like 'better system')?",
                "Does it report concrete results with numbers?",
                "Is there a clear conclusion sentence?",
                "Are there any reference citations [#]? (Should not have)",
            ]

        elif chapter == "introduction":
            diagnostics["key_points_to_check"] = [
                "Does it progress from broad to specific?",
                "Is the research gap clearly identified (ideally with comparison table)?",
                "Is the problem definition concrete and important?",
                "Are contributions ≤4 and clearly stated?",
                "Does it avoid saying 'we want a better system'?",
            ]

        elif chapter == "related_work":
            diagnostics["key_points_to_check"] = [
                "Is it organized by topic/method, not by year?",
                "Is there a comparison table or figure?",
                "Does it cover 3+ related subdisciplines?",
                "Does it clearly differentiate your work from SOTA?",
                "Is it missing any key competing methods?",
            ]

        elif chapter == "methods":
            diagnostics["key_points_to_check"] = [
                "Is the algorithm expressed via pseudo code or formula?",
                "Are ALL hyperparameters explicitly listed with values?",
                "Can someone reproduce this without seeing your code?",
                "Are datasets described (size, distribution, preprocessing)?",
                "Is the statistical method clear (t-test, ANOVA, etc)?",
            ]

        elif chapter == "results":
            diagnostics["key_points_to_check"] = [
                "Are results pure facts, without interpretive words like 'significantly'?",
                "Do all figures have clear axes labels and legends?",
                "Are there error bars or confidence intervals?",
                "Is statistical significance reported (p-values)?",
                "Are all proposed components ablated (consumed in ablation study)?",
            ]

        elif chapter == "discussion":
            diagnostics["key_points_to_check"] = [
                "Does it explain WHY you got these results (not just repeat them)?",
                "Is the comparison with SOTA fair and specific?",
                "Are ≥3 limitations clearly acknowledged?",
                "Does it avoid over-claiming ('best' → 'better than SOTA')?",
                "Does future work avoid unfounded promises?",
            ]

        elif chapter == "conclusion":
            diagnostics["key_points_to_check"] = [
                "Is it a summary, not a repetition of abstract?",
                "Does it have a clear concluding sentence (not a question)?",
                "Does it introduce any new information? (Should not)",
                "Is it <1 page?",
            ]

        if self.config and self.config.target_journals:
            journal = self.config.target_journals[0]
            diagnostics["journal_specific_notes"] = (
                f"For {journal}: Prioritize clarity and reproducibility, "
                "which are core evaluation dimensions."
            )

        diagnostics["next_steps"] = self._suggest_next_steps(chapter)

        return diagnostics

    def _suggest_next_steps(self, chapter: str) -> str:
        """Suggest what to write next."""
        chapter_order = [
            "abstract",
            "introduction",
            "related_work",
            "methods",
            "results",
            "discussion",
            "conclusion",
        ]

        try:
            idx = chapter_order.index(chapter)
            if idx < len(chapter_order) - 1:
                next_chapter = chapter_order[idx + 1]
                return (
                    f"Next: Draft '{next_chapter}' chapter. "
                    f"Remember: {self.CHAPTER_EXPECTATIONS[next_chapter]['focus']}"
                )
            else:
                return (
                    "Congratulations! You've drafted all major sections. "
                    "Now run 'crane review --full' for pre-submission check."
                )
        except ValueError:
            return "Continue with the next chapter or run full review."
