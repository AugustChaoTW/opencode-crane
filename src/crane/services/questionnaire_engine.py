"""Questionnaire engine for dynamic paper submission setup."""

from __future__ import annotations

from typing import Any, Callable


class QuestionnaireEngine:
    """Interactive questionnaire engine for paper submission setup."""

    # Predefined options for common questions
    RESEARCH_FIELDS = {
        "ai_ml_dl": "AI/Machine Learning/Deep Learning",
        "cv": "Computer Vision (Computer Vision)",
        "nlp": "Natural Language Processing (NLP)",
        "systems": "Systems (OS, Database, Distributed Systems)",
        "ir": "Information Retrieval (Information Retrieval)",
        "hci": "Human-Computer Interaction (HCI)",
        "bioinformatics": "Bioinformatics/Life Sciences",
        "other": "Other (Please specify)",
    }

    JOURNALS_BY_FIELD = {
        "ai_ml_dl": {
            "jmlr": "Journal of Machine Learning Research (JMLR)",
            "icml": "ICML (Conference)",
            "nips": "NeurIPS (Conference)",
            "ieee_tpami": "IEEE TPAMI",
            "acm_tist": "ACM TIST",
        },
        "cv": {
            "ieee_tpami": "IEEE TPAMI",
            "iccv": "ICCV (Conference)",
            "ijcv": "International Journal of Computer Vision",
        },
        "nlp": {
            "acl": "ACL (Conference)",
            "emnlp": "EMNLP (Conference)",
            "tacl": "Transactions of ACL",
        },
        "systems": {
            "ieee_tse": "IEEE Transactions on Software Engineering",
            "sigmod": "SIGMOD (Conference)",
        },
    }

    TIMELINE_OPTIONS = {
        "rush": "Urgent (Submit within 1-2 weeks)",
        "normal": "Normal (Submit within 1-2 months)",
        "flexible": "Flexible (No time constraint)",
    }

    ACCEPTANCE_TARGET_OPTIONS = {
        "very_high": "Very High (90%+ - Prioritize acceptance)",
        "high": "High (75-90% - Balance acceptance and rank)",
        "moderate": "Moderate (50-75% - Accept higher risk for higher rank)",
        "explorer": "Explorer (<50% - Aim for top venues)",
    }

    REVISION_TOLERANCE_OPTIONS = {
        "none": "No Revision (Accept or reject, no revision rounds)",
        "minor": "Minor Revision (1-2 weeks of work)",
        "moderate": "Moderate Revision (2-4 weeks of work)",
        "major": "Major Revision (1-2 months of work)",
    }

    def __init__(self, answers: dict[str, Any] | None = None):
        """Initialize questionnaire with optional pre-filled answers."""
        self.answers = answers or {}
        self.current_question = "field"
        self.validation_errors: list[str] = []

    def validate_required_fields(self) -> bool:
        """Validate that all required fields are present."""
        required = [
            "field",
            "journals",
            "page_limit",
            "figure_limit",
            "timeline",
            "acceptance_target",
            "revision_tolerance",
            "has_code",
            "has_human_subjects",
            "replicability_score",
        ]

        missing = [f for f in required if f not in self.answers]
        if missing:
            self.validation_errors = [f"Missing required fields: {', '.join(missing)}"]
            return False

        return True

    def validate_answer(self, question: str, answer: Any) -> tuple[bool, str]:
        """Validate an answer for a specific question."""
        if question == "field":
            if answer not in self.RESEARCH_FIELDS:
                return False, f"Invalid field. Choose from: {list(self.RESEARCH_FIELDS.keys())}"
            return True, ""

        if question == "journals":
            if not isinstance(answer, list) or not answer:
                return False, "Must select at least one journal"
            if len(answer) > 3:
                return False, "Can select maximum 3 journals"
            return True, ""

        if question == "page_limit":
            try:
                limit = int(answer)
                if limit < 5 or limit > 50:
                    return False, "Page limit must be between 5 and 50"
                return True, ""
            except ValueError:
                return False, "Page limit must be a number"

        if question == "figure_limit":
            try:
                limit = int(answer)
                if limit < 1 or limit > 50:
                    return False, "Figure limit must be between 1 and 50"
                return True, ""
            except ValueError:
                return False, "Figure limit must be a number"

        if question == "timeline":
            if answer not in self.TIMELINE_OPTIONS:
                return False, f"Invalid timeline. Choose from: {list(self.TIMELINE_OPTIONS.keys())}"
            return True, ""

        if question == "acceptance_target":
            if answer not in self.ACCEPTANCE_TARGET_OPTIONS:
                return (
                    False,
                    f"Invalid target. Choose from: {list(self.ACCEPTANCE_TARGET_OPTIONS.keys())}",
                )
            return True, ""

        if question == "revision_tolerance":
            if answer not in self.REVISION_TOLERANCE_OPTIONS:
                return False, (
                    f"Invalid tolerance. Choose from: {list(self.REVISION_TOLERANCE_OPTIONS.keys())}"
                )
            return True, ""

        if question == "has_code":
            return isinstance(answer, bool), "Must be true/false"

        if question == "has_human_subjects":
            return isinstance(answer, bool), "Must be true/false"

        if question == "replicability_score":
            try:
                score = int(answer)
                if score < 1 or score > 10:
                    return False, "Replicability score must be between 1 and 10"
                return True, ""
            except ValueError:
                return False, "Replicability score must be a number"

        return True, ""

    def set_answer(self, question: str, answer: Any) -> tuple[bool, str]:
        """Set an answer and validate it."""
        is_valid, error_msg = self.validate_answer(question, answer)

        if not is_valid:
            return False, error_msg

        self.answers[question] = answer
        return True, ""

    def get_next_question(self) -> str | None:
        """Get the next question in the flow."""
        question_flow = [
            "field",
            "journals",
            "page_limit",
            "figure_limit",
            "timeline",
            "acceptance_target",
            "revision_tolerance",
            "has_code",
            "has_human_subjects",
            "replicability_score",
        ]

        answered = [q for q in question_flow if q in self.answers]
        next_idx = len(answered)

        if next_idx >= len(question_flow):
            return None

        return question_flow[next_idx]

    def is_complete(self) -> bool:
        """Check if questionnaire is complete."""
        return self.validate_required_fields() and self.get_next_question() is None

    def get_question_info(self, question: str) -> dict[str, Any]:
        """Get information about a specific question."""
        question_info = {
            "field": {
                "prompt": "What is your research field?",
                "type": "select",
                "options": self.RESEARCH_FIELDS,
            },
            "journals": {
                "prompt": "What are your target journals?",
                "type": "multi-select",
                "max": 3,
                "options": self._get_available_journals(),
            },
            "page_limit": {
                "prompt": "What is your page limit?",
                "type": "number",
                "min": 5,
                "max": 50,
                "default": 16,
            },
            "figure_limit": {
                "prompt": "What is your figure limit?",
                "type": "number",
                "min": 1,
                "max": 50,
                "default": 8,
            },
            "timeline": {
                "prompt": "What is your submission timeline?",
                "type": "select",
                "options": self.TIMELINE_OPTIONS,
            },
            "acceptance_target": {
                "prompt": "What is your target acceptance rate?",
                "type": "select",
                "options": self.ACCEPTANCE_TARGET_OPTIONS,
            },
            "revision_tolerance": {
                "prompt": "How much revision work can you handle?",
                "type": "select",
                "options": self.REVISION_TOLERANCE_OPTIONS,
            },
            "has_code": {
                "prompt": "Do you plan to release code?",
                "type": "boolean",
                "default": True,
            },
            "has_human_subjects": {
                "prompt": "Does your paper involve human subjects?",
                "type": "boolean",
                "default": False,
            },
            "replicability_score": {
                "prompt": "Rate your paper's replicability (1-10)",
                "type": "number",
                "min": 1,
                "max": 10,
                "default": 7,
            },
        }

        return question_info.get(question, {})

    def _get_available_journals(self) -> dict[str, str]:
        """Get journals available for current field."""
        field = self.answers.get("field", "ai_ml_dl")
        field_journals = self.JOURNALS_BY_FIELD.get(field, {})

        if not field_journals:
            return {
                "ieee_tpami": "IEEE TPAMI",
                "jmlr": "JMLR",
                "nature_methods": "Nature Methods",
            }

        return field_journals

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all answers."""
        if not self.is_complete():
            return {
                "complete": False,
                "progress": f"{len(self.answers)}/10",
                "missing": self._get_missing_fields(),
            }

        return {
            "complete": True,
            "research_field": self.RESEARCH_FIELDS.get(self.answers.get("field")),
            "target_journals": self.answers.get("journals", []),
            "page_limit": self.answers.get("page_limit"),
            "figure_limit": self.answers.get("figure_limit"),
            "timeline": self.TIMELINE_OPTIONS.get(self.answers.get("timeline")),
            "acceptance_target": self.ACCEPTANCE_TARGET_OPTIONS.get(
                self.answers.get("acceptance_target")
            ),
            "revision_tolerance": self.REVISION_TOLERANCE_OPTIONS.get(
                self.answers.get("revision_tolerance")
            ),
            "has_code_release": self.answers.get("has_code"),
            "has_human_subjects": self.answers.get("has_human_subjects"),
            "replicability_score": self.answers.get("replicability_score"),
        }

    def _get_missing_fields(self) -> list[str]:
        """Get list of missing required fields."""
        required = [
            "field",
            "journals",
            "page_limit",
            "figure_limit",
            "timeline",
            "acceptance_target",
            "revision_tolerance",
            "has_code",
            "has_human_subjects",
            "replicability_score",
        ]
        return [f for f in required if f not in self.answers]
